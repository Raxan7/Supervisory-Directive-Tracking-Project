import asyncio
import logging
from app.core.config import get_settings
from app.db import SessionLocal
from app.services import process_deadline_alerts

logger = logging.getLogger(__name__)


async def alert_scheduler(stop: asyncio.Event) -> None:
    settings = get_settings()
    while not stop.is_set():
        try:
            with SessionLocal() as db:
                process_deadline_alerts(db, settings)
        except Exception:
            logger.exception("Deadline alert scan failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.alert_scan_seconds)
        except TimeoutError:
            continue

