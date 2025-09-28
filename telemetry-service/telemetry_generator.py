import numpy as np
import pandas as pd
from datetime import datetime, UTC, timedelta
from typing import Iterator, List, Dict, Any
from collections import defaultdict


class TelemetryGenerator:
    """Generates realistic time-series telemetry data for power assets.

    Uses seeded noise for deterministic, yet realistic, patterns that evolve
    smoothly over time based on request timestamp.
    """

    def __init__(self, asset_id: str):
        self.asset_id = asset_id
        # Base characteristics for this asset
        np.random.seed(hash(asset_id) % (2**32))
        self.max_power = 50 + np.random.uniform(-10, 40)  # 40-90 MW
        self.efficiency = 0.35 + np.random.uniform(-0.05, 0.1)  # 30-45%
        self.fuel_rate_at_max = 220 + np.random.uniform(-30, 50)  # kg/h
        self.base_temp = 25 + np.random.uniform(-5, 15)  # °C

    def _seed_rng(self, base_time: datetime, time_offset: int = 0) -> np.random.Generator:
        """Create a seeded RNG based on asset_id and time with offset."""
        # Use hours from base_time as additional seed component
        hours_offset = (base_time.hour * 60 + base_time.minute + time_offset) // 60
        seed = hash(f"{self.asset_id}_{base_time.date()}_{hours_offset}") % (2**32)
        return np.random.default_rng(seed)

    def _smooth_noise(self, rng: np.random.Generator, size: int,
                     base_frequency: float = 0.1) -> np.ndarray:
        """Generate smooth noise using sine waves with random amplitudes."""
        if size < 2:
            return np.array([0.0])

        noise = np.zeros(size)
        frequencies = np.array([1, 2, 3, 5, 8]) * base_frequency

        for freq in frequencies:
            phase = rng.uniform(0, 2 * np.pi)
            amplitude = rng.exponential(1.0) / freq
            noise += amplitude * np.sin(2 * np.pi * freq * np.arange(size) / size + phase)

        # Avoid division by zero
        std_dev = np.std(noise)
        return noise / std_dev if std_dev > 0 else noise

    def generate_telemetry(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Generate 1-minute interval telemetry between start and end times."""
        # Create time range
        times = pd.date_range(start_time, end_time, freq='1min', inclusive='left')
        n_points = len(times)

        if n_points == 0:
            return []

        # Generate realistic patterns
        minutes = np.arange(n_points)

        # More realistic daily load pattern for Finland
        # Finland has strong industrial base, significant heating demand, and distinct Nordic consumption patterns
        hour_of_day = (minutes // 60) % 24
        minute_of_hour = minutes % 60
        day_of_year = start_time.timetuple().tm_yday

        # Finland-specific patterns:
        # - High industrial consumption (24/7 but with day peaks)
        # - Strong morning peak (7-9 AM) with heating demand
        # - Evening peak (5-8 PM) but less pronounced than morning
        # - Very low night consumption (Finns sleep early)
        # - Winter has much higher demand due to electric heating

        # Base industrial load (Finland has strong paper, metal, and electronics industries)
        industrial_load = 0.6  # High base load from industry

        # Morning peak - higher in winter due to heating startup
        morning_peak_factor = 0.35 if (day_of_year > 300 or day_of_year < 60) else 0.25  # Winter boost
        morning_peak = morning_peak_factor * np.exp(-((hour_of_day + minute_of_hour/60 - 7.5) ** 2) / 1.5)

        # Office/industrial daytime peak (9 AM - 4 PM)
        office_pattern = 0.3 * (1 + np.cos(2 * np.pi * (hour_of_day - 13.5) / 10))
        office_pattern = np.where((hour_of_day >= 9) & (hour_of_day <= 16), office_pattern, 0)

        # Evening residential peak (5-9 PM) - softened by long twilight in summer
        evening_peak = 0.25 * np.exp(-((hour_of_day + minute_of_hour/60 - 19) ** 2) / 4)

        # Night reduction (10 PM - 6 AM) - more pronounced in Finland
        night_reduction = 0.4 * np.where(
            (hour_of_day >= 22) | (hour_of_day <= 6),
            np.cos(2 * np.pi * (hour_of_day - 14) / 16),
            0
        )

        # Combine patterns for Finland
        daily_pattern = industrial_load + morning_peak + office_pattern + evening_peak - night_reduction
        daily_pattern = np.clip(daily_pattern, 0.3, 1.0)  # Higher minimum load in Finland

        # Strong seasonal variation for Finland
        # Winter: October - March (high heating demand)
        # Summer: June - August (lower demand, but some cooling)
        if day_of_year < 80:  # Jan-Mar
            seasonal_factor = 1.4 + 0.2 * np.sin(2 * np.pi * (day_of_year - 15) / 365)
        elif day_of_year < 172:  # Apr-Jun
            seasonal_factor = 1.0 - 0.3 * (day_of_year - 80) / 92
        elif day_of_year < 266:  # Jul-Sep
            seasonal_factor = 0.7 + 0.1 * np.sin(2 * np.pi * (day_of_year - 172) / 92)
        else:  # Oct-Dec
            seasonal_factor = 0.8 + 0.6 * (day_of_year - 266) / 99

        daily_pattern *= seasonal_factor

        # Weekly pattern - industry heavy so less weekend reduction
        day_of_week = (minutes // (24 * 60)) % 7
        weekend_factor = np.where(day_of_week >= 5, 0.9, 1.0)  # Only 10% reduction on weekends

        # Add realistic, gradual noise patterns (Finland's grid is very stable)
        noise = np.zeros(n_points)

        # Create base RNG for this time period
        rng_base = self._seed_rng(start_time, 0)

        # Very low high-frequency noise (Finland has stable grid)
        noise += rng_base.normal(0, 0.01, n_points)  # Reduced from 0.02

        # Medium-frequency noise (30-minute variations, more gradual)
        for chunk_start in range(0, n_points, 30):
            chunk_end = min(chunk_start + 30, n_points)
            if chunk_end - chunk_start > 0:
                chunk_time = start_time + timedelta(minutes=chunk_start)
                rng_med = self._seed_rng(chunk_time, chunk_start // 30)
                chunk_noise = rng_med.normal(0, 0.015, chunk_end - chunk_start)
                # Smooth transitions between chunks
                if chunk_start > 0:
                    fade_in = np.linspace(0, 1, min(5, chunk_end - chunk_start))
                    chunk_noise[:len(fade_in)] = chunk_noise[:len(fade_in)] * fade_in
                if chunk_end < n_points:
                    fade_out = np.linspace(1, 0, min(5, n_points - chunk_end))
                    chunk_noise[-len(fade_out):] = chunk_noise[-len(fade_out):] * fade_out
                noise[chunk_start:chunk_end] += chunk_noise

        # Low-frequency variations (hourly, very gradual)
        hourly_variation = np.zeros(n_points)
        for hour in range(0, 24):
            hour_start = hour * 60
            hour_end = min(hour_start + 60, n_points)
            if hour_end - hour_start > 0:
                chunk_time = start_time + timedelta(hours=hour)
                rng_hour = self._seed_rng(chunk_time, hour)
                base_variation = rng_hour.normal(0, 0.02)  # Reduced from 0.05
                # Smooth sine wave transition within hour
                hour_minutes = np.arange(hour_end - hour_start)
                smooth_factor = 0.5 * (1 - np.cos(2 * np.pi * hour_minutes / 60))
                hourly_variation[hour_start:hour_end] = base_variation * smooth_factor
        noise += hourly_variation

        # Very gradual random walk for load following (industrial processes change slowly)
        random_walk_scale = 0.005  # Reduced from 0.01
        random_walk = np.cumsum(rng_base.normal(0, random_walk_scale, n_points))
        # Remove drift with smooth correction
        drift_correction = np.linspace(0, random_walk[-1], n_points)
        drift_correction = drift_correction * 0.5 * (1 - np.cos(2 * np.pi * np.arange(n_points) / n_points))
        random_walk = random_walk - drift_correction
        noise += random_walk

        # Add occasional step changes for industrial processes starting/stopping
        # But make them smooth, not instantaneous
        for step_hour in range(0, 24, 3):  # Every 3 hours
            step_pos = step_hour * 60
            if step_pos < n_points - 30:  # Need room for ramp
                if rng_base.random() < 0.3:  # 30% chance of step change
                    step_size = rng_base.normal(0, 0.03)
                    # Create smooth ramp over 30 minutes
                    ramp_minutes = min(30, n_points - step_pos)
                    ramp = np.linspace(0, step_size, ramp_minutes)
                    noise[step_pos:step_pos + ramp_minutes] += ramp

        # Combine patterns with realistic base load for Finland
        # Finland has high base load due to 24/7 industrial processes
        base_load = 0.4  # Higher base load for Finland
        load_factor = base_load + 0.45 * daily_pattern * weekend_factor + noise
        load_factor = np.clip(load_factor, 0.25, 1.0)  # Higher minimum for Finland

        # Calculate power generation
        power_gen = load_factor * self.max_power

        # Calculate fuel flow (less efficient at partial load)
        efficiency_curve = 0.85 + 0.15 * load_factor - 0.1 * (1 - load_factor)**2
        fuel_flow = (power_gen / efficiency_curve / self.efficiency) * 3.6  # kg/h

        # Engine metrics - more stable operation
        engine_load = load_factor * 100  # %
        # RPM should be very stable for synchronous generator (grid frequency locked)
        # For 50Hz grid, 1500 RPM (4-pole) or 3000 RPM (2-pole) are common
        base_rpm = 1500 if self.max_power < 100 else 3000
        rpm_variation = rng_base.normal(0, 1, n_points)  # Very tight control
        engine_rpm = base_rpm + rpm_variation

        # Add more gradual temperature changes
        temp_variation = 5 * np.sin(2 * np.pi * minutes / (24 * 60 * 7))  # Weekly variation
        temp_variation += 2 * np.sin(2 * np.pi * minutes / (24 * 60))  # Daily variation
        temp_variation += rng_base.normal(0, 1, n_points)  # Random variation
        engine_temp = self.base_temp + 30 * load_factor + temp_variation
        ambient_temp = self.base_temp + temp_variation

        # Electrical characteristics - more stable for grid connection
        voltage = 11000 + rng_base.normal(0, 20, n_points)  # 11kV ± 20V (tighter regulation)
        current = power_gen * 1000 / (np.sqrt(3) * voltage * 0.85)  # I = P/(√3·V·pf)
        frequency = 50.0 + rng_base.normal(0, 0.02, n_points)  # 50Hz ± 0.02Hz (more stable grid)

        # Battery simulation (if present) - more gradual changes
        battery_base = 50 + 20 * daily_pattern  # Follows load pattern loosely
        battery_daily = 10 * np.sin(2 * np.pi * minutes / (24 * 60 * 1))  # Daily cycle
        battery_noise = 2 * noise  # Small random variations
        battery_soc = battery_base + battery_daily + battery_noise
        battery_soc = np.clip(battery_soc, 20, 95)

        # Battery power - smoother charge/discharge cycles
        battery_power_gradient = np.gradient(battery_soc)
        battery_power = -battery_power_gradient * 0.5 + rng_base.normal(0, 0.5, n_points)
        battery_power = np.clip(battery_power, -5, 5)  # Limit max charge/discharge

        # Generate readings
        telemetry = []
        for i, ts in enumerate(times):
            # Calculate CO2 emissions (diesel: ~2.68 kg CO2 per kg fuel)
            co2_emissions = fuel_flow[i] * 2.68 / 60  # kg per minute

            reading = {
                "timestamp": ts.isoformat(),
                "asset_id": self.asset_id,
                "power_gen_MW": round(float(power_gen[i]), 2),
                "fuel_flow_kg_h": round(float(fuel_flow[i]), 2),
                "engine_load_percent": round(float(engine_load[i]), 1),
                "engine_rpm": round(float(engine_rpm[i]), 0),
                "engine_temp_C": round(float(engine_temp[i]), 1),
                "ambient_temp_C": round(float(ambient_temp[i]), 1),
                "voltage_V": round(float(voltage[i]), 0),
                "current_A": round(float(current[i]), 1),
                "frequency_Hz": round(float(frequency[i]), 2),
                "battery_soc_percent": round(float(battery_soc[i]), 1),
                "battery_power_MW": round(float(battery_power[i]), 2),
                "co2_emissions_kg_min": round(float(co2_emissions), 3),
                "efficiency_percent": round(float(efficiency_curve[i] * self.efficiency * 100), 1)
            }
            telemetry.append(reading)

        return telemetry