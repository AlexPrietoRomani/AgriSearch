"""
Archivo: benchmark_latency.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Suite de benchmark para medir la latencia de respuesta del Active Learning Worker (Rust/Axum).
Calcula métricas de rendimiento (p50, p95, p99) simulando una carga de trabajo de cribado.

Acciones Principales:
    - Verificación de estado del worker (/health).
    - Simulación de peticiones de decisión (/decide) secuenciales.
    - Cálculo estadístico de percentiles de latencia.
    - Validación contra objetivos de rendimiento (sub-10ms).

Estructura Interna:
    - `check_worker_alive`: Validación de conectividad.
    - `get_next_article_id`: Recuperación de IDs pendientes.
    - `send_decision`: Medición de tiempo de ida y vuelta (RTT).
    - `percentile`: Utilidad estadística para métricas.

Entradas / Dependencias:
    - Active Learning Worker en ejecución (localhost:3001).
    - Base de datos `datos_cribado.sqlite` con datos de prueba.

Salidas / Efectos:
    - Reporte detallado de latencias en consola.
    - Código de salida 0 si cumple objetivos, 1 si falla.

Ejecución:
    uv run python scripts/benchmark_latency.py

Ejemplo de Uso:
    python scripts/benchmark_latency.py
"""
import json
import statistics
import sys
import time
import urllib.request
import urllib.error

AL_WORKER_URL = "http://localhost:3001"
NUM_REQUESTS = 100


def check_worker_alive() -> bool:
    """
    Verifica que el worker de Active Learning en Rust esté en ejecución y responda.

    Returns:
        bool: True si el worker responde con estado 'ok', False en caso contrario.

    Salidas / Efectos:
        - Realiza una petición GET al endpoint /health.
    """
    try:
        req = urllib.request.Request(f"{AL_WORKER_URL}/health")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read())
            return data.get("status") == "ok"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False


def get_next_article_id() -> str | None:
    """
    Recupera el identificador del próximo artículo pendiente de cribado desde el worker.

    Returns:
        str | None: El UUID del artículo si existe, None si no hay pendientes o hay error.

    Salidas / Efectos:
        - Consulta el endpoint /next del worker Rust.
    """
    try:
        req = urllib.request.Request(f"{AL_WORKER_URL}/next")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read())
            return data.get("id") if data.get("id") else None
    except (urllib.error.URLError, TimeoutError):
        return None


def send_decision(article_id: str, status: str) -> float:
    """
    Envía una decisión de clasificación (accepted/rejected/maybe) al worker y mide el tiempo.

    Args:
        article_id (str): Identificador único del artículo.
        status (str): Estado de la decisión (accepted, rejected, maybe).

    Returns:
        float: Latencia de la petición en milisegundos (ms).

    Salidas / Efectos:
        - Envía una petición POST al endpoint /decide.
        - Registra la decisión en la base de datos gestionada por el worker.
    """
    payload = json.dumps({"id": article_id, "status": status}).encode("utf-8")
    req = urllib.request.Request(
        f"{AL_WORKER_URL}/decide",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=5) as resp:
        resp.read()
    elapsed_ms = (time.perf_counter() - start) * 1000
    return elapsed_ms


def percentile(data: list[float], pct: float) -> float:
    """
    Calcula el percentil especificado para una serie de datos de latencia.

    Args:
        data (list[float]): Lista de valores numéricos (latencias).
        pct (float): Percentil a calcular (0-100).

    Returns:
        float: El valor del percentil calculado mediante interpolación lineal.
    """
    sorted_data = sorted(data)
    n = len(sorted_data)
    idx = (pct / 100) * (n - 1)
    lower = int(idx)
    upper = lower + 1
    if upper >= n:
        return sorted_data[-1]
    frac = idx - lower
    return sorted_data[lower] * (1 - frac) + sorted_data[upper] * frac


def main():
    print("=" * 60)
    print("  Benchmark: Active Learning Worker (Rust/Axum)")
    print("=" * 60)

    # 1. Verificar worker
    print("\n[1/3] Verificando worker Rust en", AL_WORKER_URL)
    if not check_worker_alive():
        print("  ERROR: El worker no responde en", AL_WORKER_URL)
        print("  Inicialo con: cd active_learning_worker && cargo run --release")
        sys.exit(1)
    print("  OK: Worker disponible")

    # 2. Verificar articulos disponibles
    print("\n[2/3] Verificando articulos de prueba")
    first_id = get_next_article_id()
    if not first_id:
        print("  ERROR: No hay articulos pendientes en datos_cribado.sqlite")
        print("  Ejecuta primero: uv run python scripts/prepare_embeddings.py --project-id <UUID>")
        sys.exit(1)
    print(f"  OK: Primer articulo disponible: {first_id[:8]}...")

    # 3. Benchmark
    print(f"\n[3/3] Ejecutando {NUM_REQUESTS} peticiones POST /decide...")
    latencies: list[float] = []
    statuses = ["accepted", "rejected", "maybe"]

    for i in range(NUM_REQUESTS):
        # Rotar entre articulos pendientes
        article_id = get_next_article_id()
        if not article_id:
            print(f"\n  Se agotaron los articulos tras {i} peticiones")
            break

        status = statuses[i % 3]
        try:
            lat = send_decision(article_id, status)
            latencies.append(lat)
            if (i + 1) % 20 == 0:
                print(f"  {i + 1}/{NUM_REQUESTS} completadas")
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"\n  ERROR en peticion {i + 1}: {e}")
            break

    if not latencies:
        print("\n  ERROR: No se pudieron completar peticiones")
        sys.exit(1)

    # 4. Resultados
    print("\n" + "=" * 60)
    print("  RESULTADOS")
    print("=" * 60)

    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    p99 = percentile(latencies, 99)
    mean = statistics.mean(latencies)
    min_lat = min(latencies)
    max_lat = max(latencies)
    total = len(latencies)

    print(f"\n  Peticiones completadas: {total}")
    print(f"  Media:    {mean:.2f} ms")
    print(f"  Min:      {min_lat:.2f} ms")
    print(f"  Max:      {max_lat:.2f} ms")
    print(f"  p50:      {p50:.2f} ms")
    print(f"  p95:      {p95:.2f} ms")
    print(f"  p99:      {p99:.2f} ms")

    # 5. Verificacion de objetivos
    print("\n" + "-" * 60)
    print("  VERIFICACION DE OBJETIVOS")
    print("-" * 60)

    targets = [
        ("p50 < 3ms", p50 < 3.0),
        ("p95 < 5ms", p95 < 5.0),
        ("p99 < 10ms", p99 < 10.0),
    ]

    all_pass = True
    for label, passed in targets:
        status_icon = "PASS" if passed else "FAIL"
        print(f"  [{status_icon}] {label} (actual: {eval(label.split()[0]):.2f} ms)")
        if not passed:
            all_pass = False

    print("\n" + "=" * 60)
    if all_pass:
        print("  TODOS LOS OBJETIVOS CUMPLIDOS")
    else:
        print("  ALGUNOS OBJETIVOS NO CUMPLIDOS")
    print("=" * 60)

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
