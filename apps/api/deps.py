"""FastAPI dependencies: a request-scoped DB session and the job queue."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from packages.core.db import session_factory
from packages.core.queue import JobQueue
from sqlalchemy.ext.asyncio import AsyncSession


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a session and commit on success, rollback on error."""
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_queue(request: Request) -> JobQueue:
    return cast(JobQueue, request.app.state.queue)


SessionDep = Annotated[AsyncSession, Depends(get_session)]
QueueDep = Annotated[JobQueue, Depends(get_queue)]
