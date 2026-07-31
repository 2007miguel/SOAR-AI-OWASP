import logging
import sys


def configure(level: str = "INFO") -> None:
    """Configure stdlib logging with a structured single-line format."""
    logging.basicConfig(
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        force=True,
    )
