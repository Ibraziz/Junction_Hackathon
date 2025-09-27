import numpy as np
import pandas as pd
from datetime import datetime, UTC
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

    def _seed_rng(self, base_time: datetime) -> np.random.Generator:
        """Create a seeded RNG based on asset_id and time."""
        seed = hash(f"{self.asset_id}_{base_time.isoformat()}") % (2**32)
        return np.random.default_rng(seed)

    def _smooth_noise(self, rng: np.random.Generator, size: int,
                     base_frequency: float = 0.1) -> np.ndarray:
        """Generate smooth noise using sine waves with random amplitudes."""
        noise = np.zeros(size)
        frequencies = np.array([1, 2, 3, 5, 8]) * base_frequency

        for freq in frequencies:
            phase = rng.uniform(0, 2 * np.pi)
            amplitude = rng.exponential(1.0) / freq
            noise += amplitude * np.sin(2 * np.pi * freq * np.arange(size) / size + phase)

        return noise / np.std(noise)

    def generate_telemetry(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Generate 1-minute interval telemetry between start and end times."""
        # Create time range
        times = pd.date_range(start_time, end_time, freq='1min', inclusive='left')
        n_points = len(times)

        if n_points == 0:
            return []

        # Seed RNG based on the request time
        rng = self._seed_rng(start_time)

        # Generate realistic patterns
        minutes = np.arange(n_points)

        # Daily load pattern (peaks during day, dips at night)
        daily_pattern = np.sin(2 * np.pi * (minutes % (24 * 60)) / (24 * 60) - np.pi/2)
        daily_pattern = np.clip(daily_pattern, -0.5, 1.0)

        # Weekly pattern (lower on weekends)
        day_of_week = (minutes // (24 * 60)) % 7
        weekend_factor = np.where(day_of_week >= 5, 0.7, 1.0)

        # Add smooth noise
        noise = self._smooth_noise(rng, n_points, base_frequency=0.05)

        # Combine patterns
        load_factor = 0.6 + 0.3 * daily_pattern * weekend_factor + 0.1 * noise
        load_factor = np.clip(load_factor, 0.1, 1.0)

        # Calculate power generation
        power_gen = load_factor * self.max_power

        # Calculate fuel flow (less efficient at partial load)
        efficiency_curve = 0.85 + 0.15 * load_factor - 0.1 * (1 - load_factor)**2
        fuel_flow = (power_gen / efficiency_curve / self.efficiency) * 3.6  # kg/h

        # Engine metrics
        engine_load = load_factor * 100  # %
        engine_rpm = 1500 + 300 * load_factor + rng.normal(0, 10, n_points)  # typical for power gen

        # Temperature rises with load and ambient variation
        temp_variation = 5 * np.sin(2 * np.pi * minutes / (24 * 60 * 7)) + rng.normal(0, 2, n_points)
        engine_temp = self.base_temp + 30 * load_factor + temp_variation
        ambient_temp = self.base_temp + temp_variation

        # Electrical characteristics
        voltage = 11000 + rng.normal(0, 50, n_points)  # 11kV ± 50V
        current = power_gen * 1000 / (np.sqrt(3) * voltage * 0.85)  # I = P/(√3·V·pf)
        frequency = 50 + rng.normal(0, 0.05, n_points)  # 50Hz ± 0.05Hz

        # Battery simulation (if present)
        battery_soc = 50 + 30 * np.sin(2 * np.pi * minutes / (24 * 60 * 2)) + 5 * noise
        battery_soc = np.clip(battery_soc, 20, 95)
        battery_power = rng.normal(0, 2, n_points)  # Small charge/discharge

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