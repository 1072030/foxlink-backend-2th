import asyncio
import logging
import traceback
from typing import Callable
from contextlib import suppress

from app.log import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


class Ticker:
    def __init__(self, func: Callable, time: int):
        self.func = func
        self.time = time
        self.is_started = False
        self._task = None

    async def start(self):
        if not self.is_started:
            self.is_started = True
            # Start task to call func periodically:
            self._task = asyncio.create_task(self._run())

    async def stop(self):
        if self.is_started:
            self.is_started = False
            # Stop task and await it stopped:
            with suppress(asyncio.CancelledError):
                self._task.cancel()
                await self._task

    async def _run(self):
        while True:
            await asyncio.sleep(self.time)
            try:
                await self.func()
            except Exception as e:
                logger.error(
                    f"""
                    Ticker error: {repr(e)}
                    Traceback: {traceback.format_exc()}
                    """)
