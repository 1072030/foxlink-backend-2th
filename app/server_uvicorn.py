import sys
import asyncio
import signal
from app.env import *
from app.daemon.daemon import _daemons


daemons = []


async def creator():
    # start background daemons
    for args in _daemons:
        daemons.append(
            await asyncio.create_subprocess_exec(
                sys.executable, '-m', *args,
            )
        )


async def terminator():
    # kill background daemons
    await asyncio.gather(*[
        asyncio.wait_for(d.wait(), timeout=10)
        for d in daemons
        if d.terminate() or True
    ])


def startup_daemons():
    asyncio.run(creator())


def terminate_daemons():
    asyncio.run(terminator())


if __name__ == "__main__":
    import uvicorn
    startup_daemons()
    signal.signal(signal.SIGINT, terminate_daemons)
    signal.signal(signal.SIGTERM, terminate_daemons)
    uvicorn.run("app.main:app", host="0.0.0.0", port=80, workers=8)
