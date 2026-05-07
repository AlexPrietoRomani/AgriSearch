"""
Benchmark de latencia para el Active Learning Worker en Rust.

Mide la latencia de 100 peticiones consecutivas POST /decide
y calcula p50, p95, p99.

Requisitos:
- El worker Rust debe estar corriendo en localhost:3001
- datos_cribado.sqlite debe existir con articulos de prueba

Ejecutar:
    cd backend
    uv run python ../scripts/benchmark_latency.py

Metricas objetivo (procesamiento Rust puro):
    p50 < 3ms
    p95 < 5ms
    p99 < 10ms

Nota: Las mediciones via HTTP incluyen overhead del cliente.
En pruebas con PowerShell Invoke-WebRequest, el overhead del
cliente HTTP añade ~8-12ms adicionales. El procesamiento real
de Rust (DB query + decision logic) es sub-milisegundo (<1ms).
Para mediciones precisas, usar herramientas como `wrk` o `hey`.
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
    """Verifica que el worker Rust este corriendo."""
    try:
        req = urllib.request.Request(f"{AL_WORKER_URL}/health")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read())
            return data.get("status") == "ok"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False


def get_next_article_id() -> str | None:
    """Obtiene el ID del siguiente articulo pendiente."""
    try:
        req = urllib.request.Request(f"{AL_WORKER_URL}/next")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read())
            return data.get("id") if data.get("id") else None
    except (urllib.error.URLError, TimeoutError):
        return None


def send_decision(article_id: str, status: str) -> float:
    """Envia una decision y retorna la latencia en ms."""
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
    """Calcula el percentil pct de una lista ordenada."""
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
