# -*- coding: utf-8 -*-
"""📍 نقشه شخصی کشور — مرز GeoJSON واقعی، قلمرو بازیکن و جای‌گذاری سازه‌ها.

- مرزها از world-atlas (GeoJSON) در core/assets/countries-110m.geojson
- قلمرو بازیکن: کشورهای UsedCountry + کشورهای Base ها (قلمرو واقعی Game Core)
- جای‌گذاری: سرور نقطه را داخل پلی‌گان کشور خودی اعتبارسنجی می‌کند (server-authoritative)
- تطبیق نام atlas (انگلیسی) با DB (فارسی) از طریق مختصات مرکز کشور در DB انجام می‌شود
"""
import json
import logging
import math
import os

from django.conf import settings

logger = logging.getLogger(__name__)

ATLAS_PATH = os.path.join(settings.BASE_DIR, "core", "assets", "countries-110m.geojson")
_atlas_cache = None


def _load_atlas():
    """خواندن GeoJSON مرز کشورها (با cache)."""
    global _atlas_cache
    if _atlas_cache is not None:
        return _atlas_cache
    try:
        with open(ATLAS_PATH, encoding="utf-8") as f:
            _atlas_cache = json.load(f)
    except Exception:
        logger.warning("world atlas asset missing — polygon borders unavailable (fallback radius)")
        _atlas_cache = {"type": "FeatureCollection", "features": []}
    return _atlas_cache


def _feature_rings(feature):
    """همه ringهای یک feature به شکل [(lon, lat), ...]"""
    g = feature.get("geometry") or {}
    rings = []
    if g.get("type") == "Polygon":
        rings = list(g.get("coordinates", []))
    elif g.get("type") == "MultiPolygon":
        for poly in g.get("coordinates", []):
            rings.extend(poly)
    return rings


_rings_by_name = None


def _rings_by_country():
    """{نام فارسی DB: [ring...]} — تطبیق قطعی با نام (نه نزدیکی!) + cache پروسه."""
    global _rings_by_name
    if _rings_by_name is None:
        from .atlas_names import ATLAS_TO_DB
        _rings_by_name = {}
        for f in _load_atlas().get("features", []):
            db = ATLAS_TO_DB.get((f.get("properties") or {}).get("name", ""))
            if db:
                _rings_by_name.setdefault(db, []).extend(_feature_rings(f))
    return _rings_by_name


def _db_center(country):
    """مرکز واقعی کشور در DB — lat/lon ثبت‌شده یا مرکز قاره."""
    lat = country.lat if country.lat is not None else country.continent.lat
    lon = country.lon if country.lon is not None else country.continent.lon
    return lat, lon


def point_in_ring(lat, lon, ring):
    """ray casting — ورودی ring: [(lon, lat), ...]"""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / ((yj - yi) + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def point_in_country(lat, lon, country):
    """آیا نقطه داخل پلی‌گان atlas کشور است؟ (country = شیء DB)
    کشورهای واقعی: همه جزیره‌ها با پلی‌گان دقیق؛ کشورهای داستانی بازی: شعاع ۳.۵ درجه‌ای دور مرکز.
    """
    rings = _rings_by_country().get(country.name)
    if rings:
        return any(point_in_ring(lat, lon, r) for r in rings)
    # Fictional countries use the same deterministic island polygons shown on the globe.
    try:
        from . import country_geo
        if country_geo.is_imaginary_country(country.name):
            geo = country_geo.geometry_for_country(country.name, country.lat, country.lon, country.continent.lat, country.continent.lon)
            for ring in geo.get("polygons", []):
                if point_in_ring(lat, lon, ring):
                    return True
            return False
    except Exception:
        pass
    clat, clon = _db_center(country)
    return math.hypot(lat - clat, lon - clon) <= 3.5


def borders_geojson():
    """FeatureCollection کامل مرز کشورها برای Globe (asset واقعی)."""
    return _load_atlas()


def enrich_borders(geo):
    """افزودن نام فارسی DB به هر feature — برای رنگ سرزمین روی Globe.
    خروجی JSON-safe (بدون ارجاع به cache داخلی)."""
    from .atlas_names import ATLAS_TO_DB
    out_features = []
    for f in geo.get("features", []):
        name = (f.get("properties") or {}).get("name", "")
        props = dict(f.get("properties") or {})
        props["db_name"] = ATLAS_TO_DB.get(name)
        out_features.append({"type": "Feature", "properties": props,
                             "geometry": f.get("geometry")})
    return {"type": "FeatureCollection", "features": out_features}


def owned_countries(player):
    """کشورهای قلمرو بازیکن — مالکیت (UsedCountry) + پایگاه‌ها (Base)."""
    from ..models import Base, UsedCountry
    seen = {}
    for uc in UsedCountry.objects.filter(player=player).select_related("country", "country__continent"):
        if uc.country_id and uc.country.name not in seen:
            seen[uc.country.name] = uc.country
    for b in Base.objects.filter(owner=player).select_related("country", "country__continent"):
        if b.country_id and b.country.name not in seen:
            seen[b.country.name] = b.country
    return list(seen.values())


def validate_placement(player, lat, lon):
    """اعتبارسنجی سروری نقطه: باید داخل قلمرو خودی باشد. خروجی: (ok, country یا پیام)"""
    owned = owned_countries(player)
    if not owned:
        return False, "هنوز قلمرویی ندارید — اول کشور انتخاب کنید یا پایگاه بسازید"
    for country in owned:
        if point_in_country(lat, lon, country):
            return True, country
    names = "، ".join(c.name for c in owned[:5])
    return False, f"این نقطه داخل قلمرو شما نیست ({names})"


def serialize_placements(player):
    """سازه‌های جای‌گذاری‌شده بازیکن برای نقشه شخصی."""
    from ..models import Placement
    return [{"id": p.id, "item_key": p.item_key, "suffix": p.suffix, "qty": p.qty,
             "lat": p.lat, "lon": p.lon, "city_name": p.city_name, "created_at": p.created_at.isoformat()}
            for p in Placement.objects.filter(player=player).order_by("id")]
