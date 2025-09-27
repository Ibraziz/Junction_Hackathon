import argparse
import uvicorn
from api import app


def main():
    """Run the telemetry service API server."""
    parser = argparse.ArgumentParser(description="Telemetry Service API")
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    args = parser.parse_args()

    uvicorn.run(
        "api:app",
        host=args.host,
        port=args.port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
