# Satellite-Based Deforestation Monitoring

A web-based satellite analysis platform for monitoring vegetation change and screening for potential deforestation using Sentinel-2 imagery, NDVI change analysis, cloud/shadow masking, and an interactive map dashboard.

> **Hackathon:** National Level Hackathon on AI for Sustainability — JAIN (Deemed-to-be University), 24–25 September 2026

## Live Demo

**https://satellite-based-deforestation-monitoring.onrender.com/**

## GitHub Repository

**https://github.com/Shashank-d404/satellite-based-deforestation-monitoring**

---

## Problem

Deforestation and vegetation degradation are spatial and time-dependent problems. Monitoring large areas manually using satellite imagery is difficult because:

- Satellite scenes can contain clouds and shadows that affect analysis.
- Large raster datasets are difficult to inspect manually.
- Comparing vegetation conditions across different time periods requires consistent processing.
- A useful monitoring workflow should present the results in a form that non-specialist users can explore visually.

This project addresses these challenges with an automated satellite-image processing pipeline and an interactive web dashboard.

---

## Solution

The system retrieves Sentinel-2 Level-2A imagery for a selected year pair, processes the spectral bands required for vegetation analysis, masks unwanted scene classes, calculates NDVI, compares the two years, and visualizes areas showing substantial vegetation-index decline.

The current prototype is a **satellite-analysis and potential vegetation-loss screening system**. A detected change is **not automatically classified as confirmed deforestation**.

### Core pipeline

```text
Sentinel-2 L2A
      |
      v
 B04 + B08 + SCL
      |
      v
Cloud / Shadow Masking
      |
      v
     NDVI
      |
      v
Baseline Year vs Present Year
      |
      v
    NDVI Change
      |
      v
Potential Vegetation-Loss Mask
      |
      v
 GeoJSON + Statistics
      |
      v
Flask API + Leaflet Dashboard
```

---

## Key Features

### Satellite analysis

- Sentinel-2 Level-2A imagery
- Dynamic year selection from **2016–2026**
- Consistent January comparison workflow
- Automatic scene selection using cloud-cover information
- B04 (Red) and B08 (Near Infrared) spectral bands
- Scene Classification Layer (SCL) filtering
- Vegetation and bare-soil pixel filtering
- NDVI calculation
- NDVI change calculation between two selected years
- Potential vegetation-loss screening using an NDVI-change threshold
- GeoJSON generation for mapped potential-loss regions
- Analysis caching for repeated year pairs

### Interactive dashboard

- Interactive Leaflet map
- OpenStreetMap and satellite imagery base layers
- Toggleable analysis layers
- Year-pair selection
- Location search/geocoding
- Analysis statistics
- Report export
- GeoJSON export
- Responsive interface with light/dark theme support

### Community and reporting prototype

- Community creation interface
- Join/open community workflow
- Share-analysis interface
- Local issue/complaint submission
- Browser-based report history and status tracking

> Community and reporting data are currently stored in the browser using `localStorage`; there is no multi-user database in the current prototype.

---

## Technology Stack

### Backend

- Python
- Flask
- Gunicorn
- NumPy
- Rasterio
- Requests
- STAC / Planetary Computer tooling
- GeoJSON generation

### Frontend

- HTML5
- CSS3
- JavaScript
- Leaflet.js
- OpenStreetMap
- Esri satellite basemap

### Satellite data

- Microsoft Planetary Computer STAC catalog
- Sentinel-2 Level-2A imagery
- B04 — Red
- B08 — Near Infrared
- SCL — Scene Classification Layer

### Deployment

- Render Web Service
- Gunicorn
- HTTPS public deployment

---

## NDVI Method

The Normalized Difference Vegetation Index is calculated as:

```text
NDVI = (NIR - Red) / (NIR + Red)
```

For Sentinel-2 in this project:

```text
NIR = B08
Red = B04
```

For a selected baseline year `Y1` and present year `Y2`:

```text
NDVI Change = NDVI(Y2) - NDVI(Y1)
```

The current screening threshold is:

```text
NDVI Change <= -0.20
```

Pixels meeting this condition are marked as **potential vegetation loss** after the project’s scene-class filtering and common-valid-pixel processing.

The threshold is a screening rule for the prototype. It should not be interpreted as proof that a location has been deforested.

---

## Study Area

The current dynamic analysis uses Sentinel-2 tile **T43PEP** as the study tile.

The prototype compares imagery from the same tile and processing workflow to reduce differences caused by changing spatial coverage.

For the default January workflow, the system searches available Sentinel-2 Level-2A scenes and selects a suitable scene using cloud-cover metadata.

---

## Project Structure

```text
satellite-based-deforestation-monitoring/
|
├── backend/
│   ├── app.py
│   └── dynamic_analysis.py
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── data/
│   ├── sentinel2/              # local/raw satellite data when used
│   ├── ndvi/                   # generated NDVI rasters
│   ├── dynamic_analysis/       # generated year-pair analysis outputs
│   └── ai_dataset/             # future AI/ML dataset
│
├── models/                     # future trained models
├── requirements.txt
├── .gitignore
└── README.md
```

Generated satellite rasters, analysis outputs, datasets, models, virtual environments, and secrets should not be committed to the repository.

---

## Running Locally

### 1. Clone the repository

```bash
git clone https://github.com/Shashank-d404/satellite-based-deforestation-monitoring.git
cd satellite-based-deforestation-monitoring
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the Flask application

From the repository root:

```bash
python backend/app.py
```

Open the local address shown by Flask, typically:

```text
http://127.0.0.1:5000/
```

### Production-style local start

```bash
gunicorn --chdir backend app:app --bind 0.0.0.0:10000
```

---

## API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/health` | GET | Health check for the deployed service |
| `/api/analysis` | GET | Returns analysis metadata/statistics |
| `/api/deforestation` | GET | Returns potential-loss GeoJSON/data |
| `/api/visuals` | GET | Returns available visualization information |
| `/api/run-analysis` | POST | Runs a selected baseline/present-year comparison |
| `/api/export/report` | GET | Exports a text report for a selected year pair |
| `/api/export/geojson` | GET | Exports GeoJSON for a selected year pair |
| `/api/geocode` | GET | Searches locations for the map interface |

---

## Example Analysis Output

One static comparison used during development was January **2025 → January 2026**.

Example prototype statistics:

- Common valid pixels: **192,608**
- Mean NDVI change: approximately **-0.0052**
- Minimum NDVI change: approximately **-0.3792**
- Maximum NDVI change: approximately **0.1958**
- Potential-loss threshold: **-0.20**
- Potential-loss pixels: **23**
- Potential-loss share: approximately **0.01%**
- GeoJSON regions: **10**

These values are specific to the processed study tile, scene selection, masking rules, and date pair used by the prototype. They should not be generalized to all of Bengaluru or to an entire state/region.

---

## Current AI Status

The project theme is **AI for Sustainability**, but the deployed MVP currently focuses on reliable satellite-data processing and change detection rather than claiming an AI classifier that has not been trained and validated.

### Current MVP

- Satellite data retrieval
- Cloud/shadow and scene-class filtering
- NDVI generation
- Multi-year comparison
- Potential vegetation-loss screening
- GeoJSON analysis output
- Interactive visualization dashboard

### Planned AI/ML extension

A future version can combine:

```text
Spectral Features
      +
Temporal Change Features
      +
Image / Texture Features
      |
      v
AI / ML Classifier
      |
      v
Change Classification
      |
      v
Confidence / Priority Score
```

Potential future classes could distinguish vegetation loss from other causes of NDVI decline, such as seasonal variation, agricultural activity, soil exposure, or other land-cover changes.

The AI component is not presented as production-validated in the current release because a suitable labeled training dataset was not available for reliable model development and evaluation.

---

## Limitations

- NDVI decline alone does not prove deforestation.
- A fixed threshold can produce false positives and false negatives.
- The current workflow uses a single Sentinel-2 tile for the dynamic prototype.
- January is used for the current standardized comparison workflow.
- Scene selection and satellite-data availability affect the result.
- The current prototype does not provide a validated AI classification accuracy metric.
- Community/report records are browser-local rather than server-side and shared.
- Free cloud hosting may restart or sleep the service, and generated analysis files should not be treated as permanent storage.

---

## Future Scope

- Integrate a labeled satellite-image dataset.
- Train and validate a supervised AI/ML change classifier.
- Add confidence scores and priority levels.
- Support larger areas and multiple satellite tiles.
- Add longer temporal histories and seasonal comparisons.
- Add additional spectral indices such as EVI and NDWI.
- Introduce persistent database-backed communities and reports.
- Add authenticated user accounts and role-based workflows.
- Add automated monitoring alerts for repeated vegetation-loss signals.
- Improve validation using field or authoritative land-cover data.

---

## Responsible Use

This project is intended as a decision-support and monitoring prototype. Satellite-derived change signals should be reviewed with appropriate geographic, seasonal, land-use, and contextual information before being treated as evidence of actual deforestation or used for enforcement decisions.

---

## AI and External Tool Disclosure

The project was developed with AI-assisted tooling during the hackathon workflow.

AI tools were used for tasks such as:

- Development assistance and debugging
- Code generation and refinement
- UI/content iteration
- Explanations and documentation support

External services/APIs used by the project include:

- Microsoft Planetary Computer / Sentinel-2 STAC data access
- OpenStreetMap-based map/geocoding services where applicable
- Leaflet.js for interactive mapping
- Render for deployment

Any generated code or AI-assisted components should be reviewed and tested by the project team before use.

---

## Hackathon Context

**Event:** National Level Hackathon on AI for Sustainability  
**Organizer:** Department of Data Analytics & Mathematical Sciences, School of Sciences, JAIN (Deemed-to-be University)  
**Dates:** 24–25 September 2026  
**Theme:** AI for Sustainability  
**Project:** Satellite-Based Deforestation Monitoring

---

## Team

Developed by a student hackathon team as a sustainability-focused software prototype.

---

## License

No open-source license has been declared for this repository at this time. Unless a license is added, reuse of the source code should not be assumed to be permitted.

---

## Links

- **Live Demo:** https://satellite-based-deforestation-monitoring.onrender.com/
- **GitHub:** https://github.com/Shashank-d404/satellite-based-deforestation-monitoring
