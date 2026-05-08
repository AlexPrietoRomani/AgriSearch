"""
Archivo: circuit_breaker.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Implementación del patrón Circuit Breaker para prevenir la saturación de APIs externas 
(OpenAlex, Semantic Scholar, ArXiv) cuando estas presentan fallos consecutivos. 
El circuito se abre tras un umbral de errores y se cierra automáticamente después de un tiempo.

Acciones Principales:
    - Seguimiento de fallos por nombre de servicio.
    - Apertura automática del circuito al alcanzar el umbral.
    - Reseteo automático basado en tiempo (timeout).

Estructura Interna:
    - `CircuitBreaker`: Clase principal que gestiona el estado de los circuitos.

Entradas / Dependencias:
    - No tiene dependencias externas, usa `time` para el control de timeouts.

Salidas / Efectos:
    - Mantiene un estado interno en memoria de los servicios bloqueados.

Ejemplo de Integración:
    from app.services.circuit_breaker import CircuitBreaker
    cb = CircuitBreaker(failure_threshold=3, reset_timeout=60.0)
    if not cb.is_open("arxiv"):
        # realizar llamada...
"""

import time
import logging

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Gestiona el estado de conexión con servicios externos para evitar reintentos inútiles.

    Implementa una lógica de 'cortocircuito' que bloquea las peticiones a un servicio
    específico si este ha superado un número determinado de fallos consecutivos.
    """

    def __init__(self, failure_threshold: int = 3, reset_timeout: float = 60.0):
        """
        Inicializa el Circuit Breaker.

        Args:
            failure_threshold (int): Número de fallos permitidos antes de abrir el circuito.
            reset_timeout (float): Tiempo en segundos a esperar antes de intentar cerrar el circuito.
        """
        self.threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures: dict[str, int] = {}
        self.last_failure: dict[str, float] = {}
        self.open_circuits: set[str] = set()

    def is_open(self, name: str) -> bool:
        """
        Verifica si el circuito está abierto para un servicio específico.

        Si el circuito estaba abierto pero ha pasado el `reset_timeout`, se cierra 
        automáticamente (estado semi-abierto implícito).

        Args:
            name (str): Identificador del servicio (ej. 'arxiv').

        Returns:
            bool: True si el circuito está abierto (bloqueado), False si está cerrado (operativo).
        """
        if name not in self.open_circuits:
            return False
        elapsed = time.time() - self.last_failure.get(name, 0)
        if elapsed > self.reset_timeout:
            self.open_circuits.discard(name)
            self.failures[name] = 0
            return False
        return True

    def record_success(self, name: str):
        """
        Registra una operación exitosa para un servicio.

        Esto reinicia el contador de fallos y cierra el circuito si estaba abierto.

        Args:
            name (str): Identificador del servicio.
        """
        self.failures[name] = 0
        self.open_circuits.discard(name)

    def record_failure(self, name: str):
        """
        Registra un fallo en la operación de un servicio.

        Si el número de fallos alcanza el umbral establecido, el circuito se abre.

        Args:
            name (str): Identificador del servicio.
        """
        self.failures[name] = self.failures.get(name, 0) + 1
        self.last_failure[name] = time.time()
        if self.failures[name] >= self.threshold:
            self.open_circuits.add(name)
            logger.error("[CIRCUIT OPEN] %s — %d fallos", name, self.failures[name])
