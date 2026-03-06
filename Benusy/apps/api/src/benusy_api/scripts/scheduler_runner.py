"""Benusy metrics scheduler entrypoint."""
from __future__ import annotations

import asyncio
import logging
import signal

from benusy_api.core.config import get_settings
from benusy_api.services.scheduler import metrics_update_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    settings.ensure_data_dirs()

    interval = settings.METRICS_UPDATE_INTERVAL_SECONDS
    if interval <= 0:
        logger.info("Scheduler disabled (METRICS_UPDATE_INTERVAL_SECONDS=%s), exiting.", interval)
        return

    logger.info("Metrics scheduler starting (interval=%ss)", interval)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _handle_signal() -> None:
        logger.info("Shutdown signal received, stopping scheduler...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)

    await metrics_update_loop(stop_event)
    logger.info("Scheduler stopped cleanly")


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()

