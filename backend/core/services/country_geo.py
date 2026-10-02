# -*- coding: utf-8 -*-
"""🗺 هندسه کشور برای «کشور من» — دو منبع، یک موتور:

- واقعی (atlas): رینگ‌های countries-110m.geojson (Natural Earth 1:110m)
- خیالی (داستانی بازی، بدون رینگ atlas): تولید رویه‌ای seed-پایدار از نام کشور
  — قطعه‌های ساحلی + جزیره‌ها با شبه‌تصادف hash-based؛ دو بار تولید = نتیجه یکسان.

خروجی استاندارد:
  {"kind": "real"|"imaginary", "polygons": [[[lon,lat],...], ...], "center": [lat,lon],
   "bbox": [minLon,minLat,maxLon,maxLat], "span_deg": {"lat": .., "lon": ..}}
"""
import hashlib
import math
import json
import os

from .map_view import _load_atlas, _rings_by_country, ATLAS_PATH

_FICTIONAL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "fictional_islands.json")
_FICTIONAL_CACHE = None
_CAPITALS_CACHE = None


def capital_for_country(name: str) -> str:
    """Return the designated capital or seat for every playable country/territory."""
    global _CAPITALS_CACHE
    if _CAPITALS_CACHE is None:
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "country_capitals.json")
        try:
            with open(path, encoding="utf-8") as f:
                _CAPITALS_CACHE = json.load(f)
        except Exception:
            _CAPITALS_CACHE = {}
    return _CAPITALS_CACHE.get(name, f"شهر مرکزی {name}")

def _fictional_centers():
    global _FICTIONAL_CACHE
    if _FICTIONAL_CACHE is None:
        try:
            with open(_FICTIONAL_PATH, encoding="utf-8") as f:
                _FICTIONAL_CACHE = json.load(f)
        except Exception:
            _FICTIONAL_CACHE = {}
    return _FICTIONAL_CACHE

def is_imaginary_country(name: str) -> bool:
    return name in _fictional_centers()


# ==================== تولید رویه‌ای قلمرو خیالی (seed-پایدار) ====================


def _stable_seed(name: str) -> int:
    h = hashlib.sha256(name.encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big")


def _rand(seed_state: list) -> float:
    """PCG-lite — دترمینیستیک، از state لیبی int کپی می‌شود."""
    seed_state[0] = (seed_state[0] * 6364136223846793005 + 1442695040888963407) % (1 << 64)
    return (seed_state[0] >> 11) / float(1 << 53)


def _is_land(name_hash: int) -> bool:
    """کشور خیالی جزیره‌ای است؟ — دترمینیستیک از نام (~۳۰٪)."""
    return (name_hash >> 8) % 100 < 30


def _imaginary_polygons(name: str, center_lat: float, center_lon: float):
    """تولید قلمرو خیالی: ۱ قطعه اصلی + جزیره‌های اختیاری — هر دو seed-پایدار."""
    seed = _stable_seed("imag:" + name)
    state = [seed]
    name_hash = seed
    is_island = True

    # جزیره اصلی کوچک و قابل مشاهده، مناسب کره جهانی و بدون تداخل با سرزمین واقعی.
    n_pts = 8 + int(_rand(state) * 4)          # 8..11
    base_r = 0.55 + _rand(state) * 0.55
    wobble = 0.35 + _rand(state) * 0.5          # ناهمواری ساحل
    phase = _rand(state) * math.tau
    poly = []
    for i in range(n_pts):
        ang = phase + math.tau * i / n_pts
        r = base_r * (1.0 + wobble * (math.sin(3 * ang + phase) * 0.5 + _rand(state) * 0.5 - 0.25))
        r = max(0.35, r)
        lat = center_lat + r * math.sin(ang) * 0.8   # فشرده‌سازی lat برای باورپذیری
        lon = center_lon + r * math.cos(ang)
        poly.append([round(_norm_lon(lon), 4), round(max(-85, min(85, lat)), 4)])

    polys = [poly]

    # ۱ تا ۲ جزیره کوچک همراه برای حس مجمع‌الجزایر.
    if is_island:
        n_isles = 1 + int(_rand(state) * 2)
        for _ in range(n_isles):
            ilat = center_lat + (_rand(state) - 0.5) * (base_r * 3.8)
            ilon = _norm_lon(center_lon + (_rand(state) - 0.5) * (base_r * 4.6))
            ir = 0.12 + _rand(state) * 0.22
            ipts = 5 + int(_rand(state) * 3)
            isle = []
            for i in range(ipts):
                ang = math.tau * i / ipts + _rand(state) * 0.4
                r = ir * (0.75 + _rand(state) * 0.5)
                isle.append([round(_norm_lon(ilon + r * math.cos(ang)), 4),
                             round(max(-85, min(85, ilat + r * math.sin(ang))), 4)])
            polys.append(isle)
    else:
        n_isles = int(_rand(state) * 4)          # 0..3
        for _ in range(n_isles):
            ilat = center_lat + (_rand(state) - 0.5) * (base_r * 2.6)
            ilon = _norm_lon(center_lon + (_rand(state) - 0.5) * (base_r * 3.2))
            ir = 0.25 + _rand(state) * 0.45
            ipts = 5 + int(_rand(state) * 3)
            isle = []
            for i in range(ipts):
                ang = math.tau * i / ipts + _rand(state) * 0.4
                r = ir * (0.75 + _rand(state) * 0.5)
                isle.append([round(_norm_lon(ilon + r * math.cos(ang)), 4),
                             round(max(-85, min(85, ilat + r * math.sin(ang))), 4)])
            polys.append(isle)

    return polys


def _norm_lon(lon: float) -> float:
    return ((lon + 180.0) % 360.0) - 180.0


def _bbox_center(polys):
    lats, lons = [], []
    for poly in polys:
        for lon, lat in poly:
            lats.append(lat)
            lons.append(lon)
    if not lats:
        return [0, 0], [0, 0, 0, 0], 1.0
    bbox = [min(lons), min(lats), max(lons), max(lats)]
    center = [(bbox[1] + bbox[3]) / 2.0, (bbox[0] + bbox[2]) / 2.0]
    span = max(1.0, max(bbox[2] - bbox[0], bbox[3] - bbox[1]))
    return center, bbox, span


def _polygon_area_deg2(ring) -> float:
    a = 0.0
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def _polygon_area_km2(ring) -> float:
    """مساحت تقریبی km² — هر درجه lat ≈ 111km؛ lon با cos مرکز."""
    lat_ref = sum(p[1] for p in ring) / max(1, len(ring))
    return _polygon_area_deg2(ring) * 111.0 * 111.0 * math.cos(math.radians(lat_ref))


def geometry_for_country(name: str, lat, lon, continent_lat: float, continent_lon: float) -> dict:
    """هندسه استاندارد کشور — واقعی از atlas، خیالی تولیدی (seed-پایدار)."""
    rings = _rings_by_country().get(name)
    if rings:
        # کشور واقعی — مرز atlas بدون تغییر (ممکن است MultiPolygon باشد)
        polys = [list(r) for r in rings]
        center, bbox, span = _bbox_center(polys)
        area = sum(_polygon_area_km2(r) for r in polys)
        return {"kind": "real", "polygons": polys, "center": center,
                "bbox": bbox, "span_deg": round(span, 2), "area_km2": int(area)}
    # خیالی — همیشه یک جزیره کوچک در اقیانوس با مرکز seed-پایدار.
    center_hint = _fictional_centers().get(name)
    if center_hint:
        clat, clon = center_hint
    else:
        clat = lat if lat is not None else continent_lat
        clon = lon if lon is not None else continent_lon
    polys = _imaginary_polygons(name, clat, clon)
    center, bbox, span = _bbox_center(polys)
    area = sum(_polygon_area_km2(r) for r in polys)
    return {"kind": "imaginary", "polygons": polys, "center": center,
            "bbox": bbox, "span_deg": round(span, 2), "area_km2": int(area)}


# ==================== تقسیمات کشوری (استان/شهر) ====================

PROVINCE_NAMES = ["آذربایجان", "خراسان", "فارس", "سیستان", "کرمان", "خوزستان", "گیلان",
                  "مازندران", "اصفهان", "یزد", "کرمانشاه", "هرمزگان", "سمنان", "لرستان"]
CITY_SUFFIX = ["آباد", "شهر", "پور", "ستان", "سرا", "کوه", "دشت", "بندر"]
CITY_PREFIX = ["نو", "شاه", "آرتا", "پارسا", "کیان", "رایا", "مهر", "اسب", "آرم"]

DEFAULT_GOV = ["جمهوری", "پادشاهی", "امارات", "فدراسیون", "جمهوری خلق"]


def generate_divisions(name: str, polygons, count: int = 6):
    """تولید seed-پایدار استان‌ها و شهرها داخل قلمرو — خروجی ثابت برای هر کشور."""
    center, bbox, _ = _bbox_center(polygons)
    state = [_stable_seed("div:" + name)]
    out = []
    # پایتخت نزدیک مرکز
    out.append({"name": capital_for_country(name), "kind": "capital",
                "lat": round(center[0] + (_rand(state) - 0.5) * 0.4, 4),
                "lon": round(_norm_lon(center[1] + (_rand(state) - 0.5) * 0.4), 4)})
    n_prov = max(3, min(5, count - 1))
    # پراکنش درون bbox قلمرو (کلیک کلاینت داخل پلی‌گان اعتبارسنجی می‌شود)
    used_names = set()
    for i in range(n_prov):
        base = PROVINCE_NAMES[(state[0] + i * 7) % len(PROVINCE_NAMES)]
        pname = base if base not in used_names else f"{base} {i+1}"
        used_names.add(pname)
        t = (i + 1) / (n_prov + 1.0)
        out.append({"name": f"استان {pname}", "kind": "province",
                    "lat": round(bbox[1] + (bbox[3] - bbox[1]) * (0.2 + 0.6 * t), 4),
                    "lon": round(_norm_lon(bbox[0] + (bbox[2] - bbox[0]) * (0.25 + 0.5 * _rand(state))), 4)})
    n_city = max(3, count - n_prov - 1)
    for i in range(n_city):
        pre = CITY_PREFIX[(state[0] + i * 13) % len(CITY_PREFIX)]
        suf = CITY_SUFFIX[(state[0] + i * 5) % len(CITY_SUFFIX)]
        cname = f"{pre}{suf}"
        out.append({"name": f"شهر {cname}", "kind": "city",
                    "lat": round(bbox[1] + (bbox[3] - bbox[1]) * (0.15 + 0.7 * _rand(state)), 4),
                    "lon": round(_norm_lon(bbox[0] + (bbox[2] - bbox[0]) * (0.15 + 0.7 * _rand(state))), 4)})
    return out


def atlas_info() -> dict:
    """متادیتا atlas برای کلاینت (مسیر + تعداد کشور)."""
    n = len(_load_atlas().get("features", []))
    return {"path": ATLAS_PATH.replace("\\", "/"), "features": n,
            "source": "Natural Earth via world-atlas (۱:۱۱۰م)"}
