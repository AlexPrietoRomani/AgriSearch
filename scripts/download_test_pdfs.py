"""Descarga PDFs de ejemplo desde arXiv para tests."""
import asyncio
import aiohttp
from pathlib import Path

PDFS = [
    ("2504.10522v1", "ndvi_crop_health.pdf"),
    ("2502.08678v1", "multispectral_weed_detection.pdf"),
    ("2012.11486v1", "leaf_segmentation.pdf"),
    ("2108.10054v1", "remote_sensing_crop_production.pdf"),
    ("2306.06288v1", "sage_ndvi.pdf"),
    ("2510.23382v1", "crop_type_mapping.pdf"),
]

OUTPUT_DIR = Path(__file__).parent.parent / "tests" / "assets" / "pdf"

async def download_pdf(session: aiohttp.ClientSession, paper_id: str, filename: str):
    url = f"https://arxiv.org/pdf/{paper_id}"
    output_path = OUTPUT_DIR / filename
    if output_path.exists():
        print(f"  [OK] {filename} ya existe")
        return True
    
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                content = await resp.read()
                output_path.write_bytes(content)
                size_mb = len(content) / (1024 * 1024)
                print(f"  [OK] {filename} ({paper_id}) — {size_mb:.1f} MB")
                return True
            else:
                print(f"  [ERROR] {filename} — HTTP {resp.status}")
                return False
    except Exception as e:
        print(f"  [ERROR] {filename} — {e}")
        return False

async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Descargando {len(PDFS)} PDFs en {OUTPUT_DIR}...")
    
    async with aiohttp.ClientSession() as session:
        tasks = [download_pdf(session, pid, fname) for pid, fname in PDFS]
        results = await asyncio.gather(*tasks)
    
    ok = sum(results)
    print(f"\n{ok}/{len(PDFS)} PDFs descargados correctamente")

if __name__ == "__main__":
    asyncio.run(main())
