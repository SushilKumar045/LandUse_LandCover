"""
Water Cycle – IIT Bombay LULC Dashboard
Backend  ·  Flask + GeoPandas
Run:  py app.py
API base: http://localhost:5050
"""

import os, json, math
from flask import Flask, jsonify, request
from flask_cors import CORS
import geopandas as gpd
import pandas as pd
from shapely.geometry import mapping

# ─── App setup ─────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)   # Allow all origins so GitHub Pages frontend can reach localhost

# ─── Paths ─────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SHP_PATH = os.path.join(BASE_DIR, "Landuse_landcover.shp")

# ─── Hydrological coefficients per LULC class ──────────────────────────────
HYDRO = {
    "WATER":      {"runoff": 1.00, "et": 0.00, "inf": 0.00},
    "TREE COVER": {"runoff": 0.12, "et": 0.55, "inf": 0.33},
    "SHRUB":      {"runoff": 0.20, "et": 0.38, "inf": 0.42},
    "BUILTUP":    {"runoff": 0.75, "et": 0.05, "inf": 0.20},
    "WASTELAND":  {"runoff": 0.45, "et": 0.20, "inf": 0.35},
    "MANMADE":    {"runoff": 0.80, "et": 0.04, "inf": 0.16},
    "12M EOAD":   {"runoff": 0.90, "et": 0.03, "inf": 0.07},
    "6M EOAD":    {"runoff": 0.85, "et": 0.03, "inf": 0.12},
    "DEFAULT":    {"runoff": 0.40, "et": 0.30, "inf": 0.30},
}

COLOR_MAP = {
    1: "#c97c3a",
    2: "#2e7d4f",
    3: "#1f78b4",
    4: "#7cb342",
    5: "#e65100",
    6: "#6b7785",
    7: "#546e7a",
    8: "#78909c",
}

_code_name = {1:"WASTELAND",2:"TREE COVER",3:"WATER",4:"SHRUB",
              5:"MANMADE",6:"BUILTUP",7:"12M EOAD",8:"6M EOAD"}

# ─── Load shapefile once at startup ────────────────────────────────────────
print(f"[LULC] Loading shapefile -> {SHP_PATH}")
try:
    GDF_RAW = gpd.read_file(SHP_PATH)
    if GDF_RAW.crs and GDF_RAW.crs.to_epsg() != 4326:
        GDF_RAW = GDF_RAW.to_crs(epsg=4326)
    GDF_RAW["color"] = GDF_RAW["LULC"].map(COLOR_MAP).fillna("#888888")
    GDF_RAW["LULC_NAME"] = GDF_RAW.apply(
        lambda r: r["LULC_NAME"] if pd.notna(r["LULC_NAME"]) and r["LULC_NAME"]
                  else _code_name.get(int(r["LULC"]), "UNKNOWN"), axis=1)
    print(f"[LULC] Loaded {len(GDF_RAW)} features, CRS={GDF_RAW.crs}")
except Exception as exc:
    GDF_RAW = None
    print(f"[LULC] ERROR loading shapefile: {exc}")


def compute_stats(gdf):
    total = gdf["Area"].sum()
    rows = []
    for lulc_code, grp in gdf.groupby("LULC"):
        area = grp["Area"].sum()
        name = grp["LULC_NAME"].iloc[0]
        rows.append({
            "code":    int(lulc_code),
            "CLASS":   name,
            "area_m2": int(area),
            "pct":     round(area / total * 100, 2),
            "color":   COLOR_MAP.get(int(lulc_code), "#888888"),
        })
    rows.sort(key=lambda r: r["area_m2"], reverse=True)
    return {"total_m2": int(total), "classes": rows}


def run_water_model(rainfall_mm, pct_override, gdf):
    stats = compute_stats(gdf)
    total_m2 = stats["total_m2"]
    classes  = stats["classes"]
    breakdown = []
    w_runoff = w_et = w_inf = 0.0
    for cls in classes:
        name = cls["CLASS"].upper()
        coef = HYDRO.get(name, HYDRO["DEFAULT"])
        if pct_override and name in pct_override:
            pct = float(pct_override[name]) / 100.0
        else:
            pct = cls["pct"] / 100.0
        w_runoff += pct * coef["runoff"]
        w_et     += pct * coef["et"]
        w_inf    += pct * coef["inf"]
        breakdown.append({
            "class":       cls["CLASS"],
            "code":        cls["code"],
            "color":       cls["color"],
            "area_m2":     cls["area_m2"],
            "pct":         cls["pct"],
            "runoff_frac": coef["runoff"],
            "et_frac":     coef["et"],
            "inf_frac":    coef["inf"],
        })
    total_w = w_runoff + w_et + w_inf
    if total_w > 0:
        scale = 1.0 / total_w
        w_runoff *= scale; w_et *= scale; w_inf *= scale
    runoff = round(rainfall_mm * w_runoff, 2)
    et     = round(rainfall_mm * w_et,     2)
    inf    = round(rainfall_mm * w_inf,    2)
    return {
        "rainfall":           rainfall_mm,
        "runoff":             runoff,
        "evapotranspiration": et,
        "infiltration":       inf,
        "runoff_vol_m3":      round(runoff / 1000 * total_m2, 0),
        "et_vol_m3":          round(et     / 1000 * total_m2, 0),
        "inf_vol_m3":         round(inf    / 1000 * total_m2, 0),
        "total_area_m2":      total_m2,
        "breakdown":          breakdown,
    }


@app.route("/api/campus", methods=["GET"])
def campus():
    ok = GDF_RAW is not None
    return jsonify({"status": "ok" if ok else "error",
                    "campus": "IIT Bombay",
                    "features": len(GDF_RAW) if ok else 0,
                    "crs": str(GDF_RAW.crs) if ok else None})


@app.route("/api/lulc/stats", methods=["GET"])
def lulc_stats():
    if GDF_RAW is None:
        return jsonify({"error": "Shapefile not loaded"}), 500
    return jsonify(compute_stats(GDF_RAW))


@app.route("/api/lulc/geojson", methods=["GET"])
def lulc_geojson():
    if GDF_RAW is None:
        return jsonify({"error": "Shapefile not loaded"}), 500
    gdf = GDF_RAW.copy()
    gdf["geometry"] = gdf["geometry"].simplify(0.000005, preserve_topology=True)
    features = []
    for _, row in gdf.iterrows():
        geom = row["geometry"]
        if geom is None or geom.is_empty:
            continue
        features.append({
            "type": "Feature",
            "geometry": mapping(geom),
            "properties": {
                "LULC":  int(row["LULC"]),
                "CLASS": row["LULC_NAME"],
                "Area":  int(row["Area"]),
                "Floor": int(row["Floor"]) if not math.isnan(row["Floor"]) else 0,
                "color": row["color"],
            }
        })
    return jsonify({"type": "FeatureCollection", "features": features})


@app.route("/api/lulc/classes", methods=["GET"])
def lulc_classes():
    classes = []
    for code, name in _code_name.items():
        coef = HYDRO.get(name, HYDRO["DEFAULT"])
        classes.append({"code": code, "name": name,
                         "color": COLOR_MAP.get(code, "#888"), **coef})
    return jsonify(classes)


@app.route("/api/run", methods=["POST"])
def run_model():
    if GDF_RAW is None:
        return jsonify({"error": "Shapefile not loaded"}), 500
    data = request.get_json(silent=True) or {}
    rainfall_mm = float(data.get("rainfall_mm", 2200))
    known = {v.upper() for v in _code_name.values()}
    # Accept frontend keys like "Water", "Tree Cover", etc.
    key_map = {
        "WATER": "WATER", "TREE COVER": "TREE COVER", "SHRUB": "SHRUB",
        "BUILTUP": "BUILTUP", "WASTELAND": "WASTELAND",
        "MANMADE": "MANMADE", "12M ROAD": "12M EOAD", "6M ROAD": "6M EOAD",
    }
    pct_override = {}
    for k, v in data.items():
        ku = k.upper()
        mapped = key_map.get(ku, ku)
        if mapped in known and isinstance(v, (int, float)):
            pct_override[mapped] = v
    result = run_water_model(rainfall_mm, pct_override or None, GDF_RAW)
    return jsonify(result)


@app.route("/api/lulc/query", methods=["GET"])
def lulc_query():
    if GDF_RAW is None:
        return jsonify({"error": "Shapefile not loaded"}), 500
    try:
        lat = float(request.args["lat"])
        lon = float(request.args["lon"])
    except (KeyError, ValueError):
        return jsonify({"error": "Provide ?lat=&lon= parameters"}), 400
    from shapely.geometry import Point
    pt = Point(lon, lat)
    hits = GDF_RAW[GDF_RAW.geometry.contains(pt)]
    if hits.empty:
        return jsonify({"found": False, "lat": lat, "lon": lon})
    row = hits.iloc[0]
    return jsonify({"found": True, "lat": lat, "lon": lon,
                    "CLASS": row["LULC_NAME"], "LULC": int(row["LULC"]),
                    "Area": int(row["Area"]),
                    "Floor": int(row["Floor"]) if not math.isnan(row["Floor"]) else 0,
                    "color": row["color"]})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"\n LULC backend running -> http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
