"""
Archivo: events.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
API de Server-Sent Events (SSE) para el backend de AgriSearch.
Proporciona notificaciones en tiempo real al frontend sobre el estado de las
tareas en segundo plano, como el procesamiento de PDFs y descargas.

Acciones Principales:
    - Mantiene colas de eventos en memoria por proyecto.
    - Publica eventos asíncronos a todos los suscriptores activos de un proyecto.
    - Transmite (stream) actualizaciones en vivo al cliente HTTP manteniendo la conexión abierta.

Estructura Interna:
    - `publish_event`: Función para emitir un evento a un proyecto específico.
    - `stream_events`: Endpoint GET que gestiona la conexión SSE de un cliente.

Entradas / Dependencias:
    - El módulo estándar `asyncio` para la gestión de colas.
    - `FastAPI` para las rutas y `StreamingResponse`.

Salidas / Efectos:
    - Retorna un flujo continuo de texto plano de tipo `text/event-stream`.
    - Modifica la variable global `_project_queues` cuando los clientes se conectan y desconectan.

Integración UI:
    - Este archivo renderiza el flujo de notificaciones que consume el frontend para las barras de progreso.
    - Es invocado internamente por los servicios que emiten eventos mediante `publish_event`.
"""

import asyncio
import json
import logging
from typing import Set, List, Dict, Any, AsyncGenerator
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["Events"])

# Cola de tareas en memoria (project_id -> lista de colas para múltiples oyentes)
_project_queues: Dict[str, List[asyncio.Queue]] = {}

async def publish_event(project_id: str, message: Dict[str, Any]) -> None:
    """
    Transmite un evento a todos los suscriptores activos de un proyecto.

    Args:
        project_id (str): Identificador único del proyecto al que pertenece el evento.
        message (Dict[str, Any]): El mensaje o datos del evento a transmitir (normalmente un diccionario JSON).

    Returns:
        None
    """
    if project_id in _project_queues:
        for queue in _project_queues[project_id]:
            await queue.put(message)

@router.get("/{project_id}")
async def stream_events(project_id: str, request: Request) -> StreamingResponse:
    """
    Transmite los eventos del proyecto en tiempo real al frontend.

    Mantiene una conexión abierta usando Server-Sent Events (SSE). Envía mensajes
    'keep-alive' si no hay actividad para evitar que el navegador cierre la conexión.

    Args:
        project_id (str): Identificador del proyecto al cual suscribirse.
        request (Request): El objeto de petición HTTP nativo de FastAPI.

    Returns:
        StreamingResponse: Una respuesta HTTP de tipo 'text/event-stream'.
    """
    
    async def event_generator() -> AsyncGenerator[str, None]:
        queue: asyncio.Queue = asyncio.Queue()
        if project_id not in _project_queues:
            _project_queues[project_id] = []
        _project_queues[project_id].append(queue)
        
        logger.info(f"New SSE client for project {project_id}")
        
        # Enviar un evento vacío o comentario inicial INMEDIATAMENTE para forzar el envío de los Headers HTTP
        # Esto previene que el navegador (EventSource) desconecte al no recibir el estatus 200 inicial
        yield ": start\n\n"
        
        try:
            while True:
                if await request.is_disconnected():
                    break
                
                try:
                    # Espera un mensaje o envía un keep-alive tras el timeout
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
