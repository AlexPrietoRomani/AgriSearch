"""
AgriSearch Backend - SSE (Server-Sent Events) API.

Provides real-time notifications for background tasks like PDF parsing and downloads.
"""

import asyncio
import json
import logging
from typing import Set, List
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["Events"])

# Tasks queue in memory (project_id -> list of queues for multiple listeners)
_project_queues: dict[str, List[asyncio.Queue]] = {}

async def publish_event(project_id: str, message: dict):
    """Broadcast an event to all subscribers of a project."""
    if project_id in _project_queues:
        for queue in _project_queues[project_id]:
            await queue.put(message)

@router.get("/{project_id}")
async def stream_events(project_id: str, request: Request):
    """Stream live project events to the frontend."""
    
    async def event_generator():
        queue = asyncio.Queue()
        if project_id not in _project_queues:
            _project_queues[project_id] = []
        _project_queues[project_id].append(queue)
        
        logger.info(f"New SSE client for project {project_id}")
        
        try:
            while True:
                if await request.is_disconnected():
                    break
                
                try:
                    # Wait for message or timeout for keep-alive
                    msg = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"data: {json.dumps(msg)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            if project_id in _project_queues and queue in _project_queues[project_id]:
                _project_queues[project_id].remove(queue)
                if not _project_queues[project_id]:
                    del _project_queues[project_id]
            logger.info(f"SSE client disconnected for project {project_id}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")
