# Test Assets: PDFs Científicos

## Propósito

PDFs de ejemplo para probar:
1. **Parsing de PDF → Markdown** (MarkItDown, Docling)
2. **Extracción de embeddings** (Ollama)
3. **Active Learning** (clasificación include/exclude)
4. **Screening workflow** completo
5. **Extracción de variables espectrales**

## Papers Seleccionados (arXiv Open Access)

### 1. NDVI Crop Health — `2504.10522v1`
- **Título:** Remote Sensing Based Crop Health Classification Using NDVI and Fully Connected Neural Networks
- **Tema:** Clasificación de salud de cultivos usando NDVI y redes neuronales
- **Variables espectrales:** NDVI, imágenes satelitales
- **Uso esperado:** Test de parsing + embedding extraction
- **Resultado esperado:** Variables como "NDVI", "crop health", "satellite imagery"

### 2. Multispectral Weed Detection — `2502.08678v1`
- **Título:** Multispectral Remote Sensing for Weed Detection in West Australian Agricultural Lands
- **Tema:** Detección de malezas con imágenes multiespectrales de drones (UAV)
- **Variables espectrales:** NDVI, GNDVI, EVI, SAVI, MSAVI
- **Uso esperado:** Test de extracción de variables espectrales
- **Resultado esperado:** Variables como "NDVI", "GNDVI", "EVI", "SAVI", "MSAVI", "UAV", "multispectral"

### 3. Leaf Segmentation — `2012.11486v1`
- **Título:** Leaf Segmentation and Counting with Deep Learning: on Model Certainty, Test-Time Augmentation, Trade-Offs
- **Tema:** Segmentación y conteo de hojas con deep learning (plant phenotyping)
- **Variables espectrales:** RGB (no espectral)
- **Uso esperado:** Test de active learning (include/exclude decision)
- **Resultado esperado:** Relevante para phenotyping, no para variables espectrales

### 4. Remote Sensing Crop Production — `2108.10054v1`
- **Título:** Remote Sensing and Machine Learning for Food Crop Production Data in Africa Post-COVID-19
- **Tema:** Monitoreo de producción de cultivos con remote sensing + ML
- **Variables espectrales:** NDVI, LST, ET, rainfall
- **Uso esperado:** Test de extracción de múltiples variables
- **Resultado esperado:** Variables como "NDVI", "LST", "evapotranspiration", "rainfall"

### 5. SAGE-NDVI — `2306.06288v1`
- **Título:** SAGE-NDVI: A Stereotype-Breaking Evaluation Metric for Remote Sensing Image Dehazing
- **Tema:** Métrica de evaluación para dehazing de imágenes de remote sensing
- **Variables espectrales:** NDVI
- **Uso esperado:** Test de parsing con paper técnico
- **Resultado esperado:** Variables como "NDVI", "remote sensing", "image quality"

### 6. RS Super Resolution for Crop Mapping — `2510.23382v1`
- **Título:** An Efficient Remote Sensing Super Resolution Method Exploring Diffusion Priors and Multi-Modal Constraints for Crop Type Mapping
- **Tema:** Super-resolución de imágenes satelitales para mapeo de cultivos
- **Variables espectrales:** NDVI, Landsat, Sentinel-2
- **Uso esperado:** Test de parsing con paper de deep learning + remote sensing
- **Resultado esperado:** Variables como "NDVI", "Landsat", "Sentinel-2", "super resolution"

### 7. Multi-Crop Disease Detection — `2503.08348v1`
- **Título:** Design and Implementation of FourCropNet: A CNN-Based System for Efficient Multi-Crop Disease Detection and Management
- **Tema:** Detección de enfermedades en múltiples cultivos
- **Variables espectrales:** RGB
- **Uso esperado:** Test de active learning para crop disease
- **Resultado esperado:** Variables como "CNN", "disease detection", "deep learning"
- **DOI:** 10.48550/arXiv.2503.08348

### 8. IoT Crop Disease Classification — `2311.00429v2`
- **Título:** Crop Disease Classification using Support Vector Machines with Green Chromatic Coordinate (GCC) and Attention based feature extraction for IoT based Smart Agricultural Applications
- **Tema:** Clasificación de enfermedades de cultivos para IoT
- **Variables espectrales:** RGB, GCC (Green Chromatic Coordinate)
- **Uso esperado:** Test de parsing de features y métricas
- **Resultado esperado:** Variables como "SVM", "GCC", "attention", "IoT"
- **DOI:** 10.48550/arXiv.2311.00429

### 9. Deep learning in agriculture: A survey... — `1807.11809v1`
- **Título:** Deep learning in agriculture: A survey
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.1807.11809

### 10. Cloud gap-filling with deep learning for improved ... — `2403.09554v2`
- **Título:** Cloud gap-filling with deep learning for improved grassland monitoring
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.2403.09554

### 11. Guiding the Creation of Deep Learning-based Object... — `1809.03322v1`
- **Título:** Guiding the Creation of Deep Learning-based Object Detectors
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.1809.03322

### 12. Integrating Renewable Energy in Agriculture: A Dee... — `2308.08611v1`
- **Título:** Integrating Renewable Energy in Agriculture: A Deep Reinforcement Learning-based Approach
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.2308.08611

### 13. UAV and Machine Learning Based Refinement of a Sat... — `2004.14421v1`
- **Título:** UAV and Machine Learning Based Refinement of a Satellite-Driven Vegetation Index for Precision Agriculture
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.2004.14421

### 14. Evaluation of UAV-Based RGB and Multispectral Vege... — `2505.07840v1`
- **Título:** Evaluation of UAV-Based RGB and Multispectral Vegetation Indices for Precision Agriculture in Palm Tree Cultivation
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.2505.07840

### 15. CWD30: A Comprehensive and Holistic Dataset for Cr... — `2305.10084v1`
- **Título:** CWD30: A Comprehensive and Holistic Dataset for Crop Weed Recognition in Precision Agriculture
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.2305.10084

### 16. Immersive Human-Machine Teleoperation Framework fo... — `2308.07231v3`
- **Título:** Immersive Human-Machine Teleoperation Framework for Precision Agriculture: Integrating UAV-based Digital Mapping and Virtual Reality Control
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.2308.07231

### 17. Probabilistic NDVI Forecasting from Sparse Satelli... — `2602.17683v2`
- **Título:** Probabilistic NDVI Forecasting from Sparse Satellite Time Series and Weather Covariates
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.2602.17683

### 18. Quantum-Resilient Blockchain for Secure Transactio... — `2505.18206v1`
- **Título:** Quantum-Resilient Blockchain for Secure Transactions in UAV-Assisted Smart Agriculture Networks
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.2505.18206

### 19. Overcome the Fear Of Missing Out: Active Sensing U... — `2312.09730v1`
- **Título:** Overcome the Fear Of Missing Out: Active Sensing UAV Scanning for Precision Agriculture
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.2312.09730

### 20. Label-free Anomaly Detection in Aerial Agricultura... — `2404.08931v1`
- **Título:** Label-free Anomaly Detection in Aerial Agricultural Images with Masked Image Modeling
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.2404.08931

### 21. 3D shape sensing and deep learning-based segmentat... — `2111.13663v1`
- **Título:** 3D shape sensing and deep learning-based segmentation of strawberries
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.2111.13663

### 22. Deep-Learning-based Counting Methods, Datasets, an... — `2303.02632v2`
- **Título:** Deep-Learning-based Counting Methods, Datasets, and Applications in Agriculture -- A Review
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.2303.02632

### 23. Deep Learning Techniques for Hyperspectral Image A... — `2304.13880v1`
- **Título:** Deep Learning Techniques for Hyperspectral Image Analysis in Agriculture: A Review
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.2304.13880

### 24. A systematic review of the use of Deep Learning in... — `2210.01272v3`
- **Título:** A systematic review of the use of Deep Learning in Satellite Imagery for Agriculture
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.2210.01272

### 25. Deep Learning for UAV-based Object Detection and T... — `2110.12638v1`
- **Título:** Deep Learning for UAV-based Object Detection and Tracking: A Survey
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.2110.12638

### 26. Agricultural Plant Cataloging and Establishment of... — `2201.02885v2`
- **Título:** Agricultural Plant Cataloging and Establishment of a Data Framework from UAV-based Crop Images by Computer Vision
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.2201.02885

### 27. A Review on Deep Learning in UAV Remote Sensing... — `2101.10861v4`
- **Título:** A Review on Deep Learning in UAV Remote Sensing
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.2101.10861

### 28. BAWSeg: A UAV Multispectral Benchmark for Barley W... — `2603.01932v2`
- **Título:** BAWSeg: A UAV Multispectral Benchmark for Barley Weed Segmentation
- **Tema:** Deep learning applied to agriculture
- **Variables espectrales:** Multispectral/RGB
- **Uso esperado:** Expand dataset
- **Resultado esperado:** Agriculture, Deep Learning
- **DOI:** 10.48550/arXiv.2603.01932

## Descarga

Los PDFs se descargan desde arXiv usando el MCP de arXiv:

```
arxiv-mcp-server_download_paper --paper_id 2504.10522v1
arxiv-mcp-server_download_paper --paper_id 2502.08678v1
arxiv-mcp-server_download_paper --paper_id 2012.11486v1
arxiv-mcp-server_download_paper --paper_id 2108.10054v1
arxiv-mcp-server_download_paper --paper_id 2306.06288v1
arxiv-mcp-server_download_paper --paper_id 2510.23382v1
arxiv-mcp-server_download_paper --paper_id 2503.08348v1
arxiv-mcp-server_download_paper --paper_id 2311.00429v2
arxiv-mcp-server_download_paper --paper_id 1807.11809v1
arxiv-mcp-server_download_paper --paper_id 2403.09554v2
arxiv-mcp-server_download_paper --paper_id 1809.03322v1
arxiv-mcp-server_download_paper --paper_id 2308.08611v1
arxiv-mcp-server_download_paper --paper_id 2004.14421v1
arxiv-mcp-server_download_paper --paper_id 2505.07840v1
arxiv-mcp-server_download_paper --paper_id 2305.10084v1
arxiv-mcp-server_download_paper --paper_id 2308.07231v3
arxiv-mcp-server_download_paper --paper_id 2602.17683v2
arxiv-mcp-server_download_paper --paper_id 2505.18206v1
arxiv-mcp-server_download_paper --paper_id 2312.09730v1
arxiv-mcp-server_download_paper --paper_id 2404.08931v1
arxiv-mcp-server_download_paper --paper_id 2111.13663v1
arxiv-mcp-server_download_paper --paper_id 2303.02632v2
arxiv-mcp-server_download_paper --paper_id 2304.13880v1
arxiv-mcp-server_download_paper --paper_id 2210.01272v3
arxiv-mcp-server_download_paper --paper_id 2110.12638v1
arxiv-mcp-server_download_paper --paper_id 2201.02885v2
arxiv-mcp-server_download_paper --paper_id 2101.10861v4
arxiv-mcp-server_download_paper --paper_id 2603.01932v2
```

O descargar manualmente desde:
- https://arxiv.org/pdf/2504.10522v1 (DOI: 10.48550/arXiv.2504.10522)
- https://arxiv.org/pdf/2502.08678v1 (DOI: 10.48550/arXiv.2502.08678)
- https://arxiv.org/pdf/2012.11486v1 (DOI: 10.48550/arXiv.2012.11486)
- https://arxiv.org/pdf/2108.10054v1 (DOI: 10.48550/arXiv.2108.10054)
- https://arxiv.org/pdf/2306.06288v1 (DOI: 10.48550/arXiv.2306.06288)
- https://arxiv.org/pdf/2510.23382v1 (DOI: 10.48550/arXiv.2510.23382)
- https://arxiv.org/pdf/2503.08348v1 (DOI: 10.48550/arXiv.2503.08348)
- https://arxiv.org/pdf/2311.00429v2 (DOI: 10.48550/arXiv.2311.00429)
- https://arxiv.org/pdf/1807.11809v1 (DOI: 10.48550/arXiv.1807.11809)
- https://arxiv.org/pdf/2403.09554v2 (DOI: 10.48550/arXiv.2403.09554)
- https://arxiv.org/pdf/1809.03322v1 (DOI: 10.48550/arXiv.1809.03322)
- https://arxiv.org/pdf/2308.08611v1 (DOI: 10.48550/arXiv.2308.08611)
- https://arxiv.org/pdf/2004.14421v1 (DOI: 10.48550/arXiv.2004.14421)
- https://arxiv.org/pdf/2505.07840v1 (DOI: 10.48550/arXiv.2505.07840)
- https://arxiv.org/pdf/2305.10084v1 (DOI: 10.48550/arXiv.2305.10084)
- https://arxiv.org/pdf/2308.07231v3 (DOI: 10.48550/arXiv.2308.07231)
- https://arxiv.org/pdf/2602.17683v2 (DOI: 10.48550/arXiv.2602.17683)
- https://arxiv.org/pdf/2505.18206v1 (DOI: 10.48550/arXiv.2505.18206)
- https://arxiv.org/pdf/2312.09730v1 (DOI: 10.48550/arXiv.2312.09730)
- https://arxiv.org/pdf/2404.08931v1 (DOI: 10.48550/arXiv.2404.08931)
- https://arxiv.org/pdf/2111.13663v1 (DOI: 10.48550/arXiv.2111.13663)
- https://arxiv.org/pdf/2303.02632v2 (DOI: 10.48550/arXiv.2303.02632)
- https://arxiv.org/pdf/2304.13880v1 (DOI: 10.48550/arXiv.2304.13880)
- https://arxiv.org/pdf/2210.01272v3 (DOI: 10.48550/arXiv.2210.01272)
- https://arxiv.org/pdf/2110.12638v1 (DOI: 10.48550/arXiv.2110.12638)
- https://arxiv.org/pdf/2201.02885v2 (DOI: 10.48550/arXiv.2201.02885)
- https://arxiv.org/pdf/2101.10861v4 (DOI: 10.48550/arXiv.2101.10861)
- https://arxiv.org/pdf/2603.01932v2 (DOI: 10.48550/arXiv.2603.01932)

## Estado de Archivos

| ID del Paper | Archivo Local | Estado |
|--------------|---------------|--------|
| `2504.10522v1` | `2504.10522v1.pdf` | ✅ Descargado |
| `2502.08678v1` | `2502.08678v1.pdf` | ✅ Descargado |
| `2012.11486v1` | `2012.11486v1.pdf` | ✅ Descargado |
| `2108.10054v1` | `2108.10054v1.pdf` | ✅ Descargado |
| `2306.06288v1` | `2306.06288v1.pdf` | ✅ Descargado |
| `2510.23382v1` | `2510.23382v1.pdf` | ✅ Descargado |
| `2503.08348v1` | `2503.08348v1.pdf` | ✅ Descargado |
| `2311.00429v2` | `2311.00429v2.pdf` | ✅ Descargado |
| `1807.11809v1` | `1807.11809v1.pdf` | ✅ Descargado |
| `2403.09554v2` | `2403.09554v2.pdf` | ✅ Descargado |
| `1809.03322v1` | `1809.03322v1.pdf` | ✅ Descargado |
| `2308.08611v1` | `2308.08611v1.pdf` | ✅ Descargado |
| `2004.14421v1` | `2004.14421v1.pdf` | ✅ Descargado |
| `2505.07840v1` | `2505.07840v1.pdf` | ✅ Descargado |
| `2305.10084v1` | `2305.10084v1.pdf` | ✅ Descargado |
| `2308.07231v3` | `2308.07231v3.pdf` | ✅ Descargado |
| `2602.17683v2` | `2602.17683v2.pdf` | ✅ Descargado |
| `2505.18206v1` | `2505.18206v1.pdf` | ✅ Descargado |
| `2312.09730v1` | `2312.09730v1.pdf` | ✅ Descargado |
| `2404.08931v1` | `2404.08931v1.pdf` | ✅ Descargado |
| `2111.13663v1` | `2111.13663v1.pdf` | ✅ Descargado |
| `2303.02632v2` | `2303.02632v2.pdf` | ✅ Descargado |
| `2304.13880v1` | `2304.13880v1.pdf` | ✅ Descargado |
| `2210.01272v3` | `2210.01272v3.pdf` | ✅ Descargado |
| `2110.12638v1` | `2110.12638v1.pdf` | ✅ Descargado |
| `2201.02885v2` | `2201.02885v2.pdf` | ✅ Descargado |
| `2101.10861v4` | `2101.10861v4.pdf` | ✅ Descargado |
| `2603.01932v2` | `2603.01932v2.pdf` | ✅ Descargado |

## Notas

- Todos los papers son **Open Access** (arXiv)
- Licencia: arXiv non-exclusive license
- Tamaño estimado: 2-5 MB por PDF
- Los papers cubren: **NDVI**, **multiespectral**, **drones/UAV**, **salud vegetal**, **remote sensing**

## Uso en Tests

```python
# Ejemplo de uso en test
import pytest
from pathlib import Path

ASSETS_DIR = Path(__file__).parent.parent.parent / "assets" / "pdf"

def test_parse_ndvi_paper():
    pdf_path = ASSETS_DIR / "2504.10522v1.pdf"
    if not pdf_path.exists():
        pytest.skip("PDF not downloaded yet")
    # ... test parsing
```

## Cobertura Temática

| Tema | Papers | Variables |
|------|--------|-----------|
| NDVI | 1, 2, 4, 5, 6 | NDVI, GNDVI, EVI, SAVI, MSAVI |
| Remote Sensing | 1, 4, 5, 6 | Satellite imagery, Landsat, Sentinel-2 |
| Drones/UAV | 2 | Multispectral UAV imagery |
| Plant Health | 1, 3, 7, 8 | Crop health, leaf segmentation, disease detection |
| Deep Learning | 1, 2, 3, 6, 7 | CNN, ResNet, U-Net |
| Agriculture | 1, 2, 4, 6, 7, 8 | Crop monitoring, weed detection |
