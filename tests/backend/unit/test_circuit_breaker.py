"""
Archivo: test_circuit_breaker.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Suite de pruebas unitarias para validar el comportamiento del componente `CircuitBreaker`.
Asegura que el circuito se abra tras fallos repetidos, se cierre tras el timeout 
y mantenga estados independientes por servicio.

Acciones Principales:
    - Validación de apertura por umbral de fallos.
    - Validación de cierre por expiración de tiempo (timeout).
    - Verificación de independencia entre servicios (OpenAlex vs ArXiv).
    - Validación del reseteo del contador ante éxitos.

Estructura Interna:
    - `TestCircuitBreaker`: Clase contenedora de los casos de prueba.

Entradas / Dependencias:
    - `app.services.circuit_breaker.CircuitBreaker`.
    - `pytest`.

Salidas / Efectos:
    - Genera reportes de éxito/fallo en la consola de pytest.
    - No modifica archivos persistentes; usa estados en memoria.

Ejecución:
    pytest tests/backend/unit/test_circuit_breaker.py
"""

import time
import pytest
from app.services.circuit_breaker import CircuitBreaker


class TestCircuitBreaker:
    """Tests de CircuitBreaker."""

    def test_opens_after_3_failures(self):
        """Circuito abre después de 3 fallos consecutivos."""
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=60.0)

        cb.record_failure("openalex")
        assert not cb.is_open("openalex")

        cb.record_failure("openalex")
        assert not cb.is_open("openalex")

        cb.record_failure("openalex")
        assert cb.is_open("openalex")

    def test_resets_after_timeout(self):
        """Circuito se cierra después de reset_timeout."""
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=0.1)

        cb.record_failure("arxiv")
        cb.record_failure("arxiv")
        assert cb.is_open("arxiv")

        time.sleep(0.15)
        assert not cb.is_open("arxiv")

    def test_success_resets_counter(self):
        """Éxito reinicia el contador de fallos."""
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=60.0)

        cb.record_failure("crossref")
        cb.record_failure("crossref")
        cb.record_success("crossref")
        cb.record_failure("crossref")
        cb.record_failure("crossref")

        # Solo 2 fallos desde el último éxito, no 3
        assert not cb.is_open("crossref")

    def test_success_closes_open_circuit(self):
        """Éxito cierra un circuito abierto."""
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=60.0)

        cb.record_failure("core")
        cb.record_failure("core")
        assert cb.is_open("core")

        cb.record_success("core")
        assert not cb.is_open("core")

    def test_different_bd_independent(self):
        """Circuitos de diferentes BDs son independientes."""
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=60.0)

        cb.record_failure("openalex")
        cb.record_failure("openalex")
        assert cb.is_open("openalex")
        assert not cb.is_open("arxiv")

    def test_initial_state_not_open(self):
        """Estado inicial: circuito cerrado."""
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=60.0)
        assert not cb.is_open("openalex")
        assert not cb.is_open("arxiv")

    def test_failure_count_tracked(self):
        """Conteo de fallos se mantiene correctamente."""
        cb = CircuitBreaker(failure_threshold=5, reset_timeout=60.0)

        cb.record_failure("test")
        assert cb.failures["test"] == 1

        cb.record_failure("test")
        assert cb.failures["test"] == 2

        cb.record_success("test")
        assert cb.failures["test"] == 0
