# IIT Bombay LULC Water Cycle Dashboard

Interactive **Land Use / Land Cover (LULC)** dashboard for IIT Bombay campus.  
Reads `Landuse_landcover.shp` (878 features, EPSG:4326) and computes water-cycle balances (runoff, evapotranspiration, infiltration) using SCS/NRCS hydrological coefficients.

## Project Structure

```
Landuse_landcover/
├── app.py                   # Flask backend (Python)
├── requirements.txt         # Python dependencies
├── index.html               # Frontend (GitHub Pages)
├── Landuse_landcover.shp    # Shapefile (+ .dbf / .shx / .prj / .cpg)
└── README.md
```

## Run Locally

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Start backend
```bash
py app.py
# or
python app.py
```
Backend starts at **http://localhost:5050**

### 3. Open frontend
Open `index.html` in your browser, **or** serve it:
```bash
py -m http.server 8080
# then visit http://localhost:8080
```

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/campus` | Health check + campus metadata |
| GET | `/api/lulc/stats` | Aggregate area stats per LULC class |
| GET | `/api/lulc/geojson` | Full GeoJSON FeatureCollection |
| GET | `/api/lulc/classes` | Class list with colours & hydro coefficients |
| POST | `/api/run` | Water balance model calculation |
| GET | `/api/lulc/query?lat=&lon=` | Point-in-polygon LULC lookup |

### POST `/api/run` body example
```json
{
  "rainfall_mm": 2200,
  "WATER": 18.95,
  "TREE COVER": 20.10,
  "SHRUB": 55.56,
  "BUILTUP": 1.04,
  "WASTELAND": 1.18,
  "MANMADE": 0.84,
  "12M EOAD": 0.77,
  "6M EOAD": 1.56
}
```

## GitHub Pages Deployment

1. Push **all files** (including shapefiles) to a GitHub repository.
2. Enable **GitHub Pages** → branch `main` → folder `/` (root).
3. The frontend (`index.html`) will be served automatically.
4. **The backend must run locally** (or on a server you control).  
   Update `const API = "..."` in `index.html` to point to your deployed backend URL.

### Deploying backend to Render (free tier)
1. Create a new **Web Service** on [render.com](https://render.com)
2. Connect your GitHub repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `python app.py`
5. Copy the `https://your-app.onrender.com` URL into `index.html` → `const API`

## LULC Classes & Hydrological Coefficients

| Code | Class | Runoff | ET | Infiltration |
|------|-------|--------|-----|--------------|
| 3 | WATER | 1.00 | 0.00 | 0.00 |
| 2 | TREE COVER | 0.12 | 0.55 | 0.33 |
| 4 | SHRUB | 0.20 | 0.38 | 0.42 |
| 6 | BUILTUP | 0.75 | 0.05 | 0.20 |
| 1 | WASTELAND | 0.45 | 0.20 | 0.35 |
| 5 | MANMADE | 0.80 | 0.04 | 0.16 |
| 7 | 12M EOAD | 0.90 | 0.03 | 0.07 |
| 8 | 6M EOAD | 0.85 | 0.03 | 0.12 |

*Coefficients are based on SCS/NRCS curve numbers adapted for tropical urban campus conditions.*
