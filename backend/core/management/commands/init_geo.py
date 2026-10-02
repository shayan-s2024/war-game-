# -*- coding: utf-8 -*-
"""🌍 پر کردن مختصات واقعی کشورها از world-atlas GeoJSON (بدون بسته بیرونی).

- نام atlas (انگلیسی) با دیکشنری atlas_names به DB (فارسی) وصل می‌شود
- مرکز هر کشور = میانگین رئوس بزرگ‌ترین ring (کافی برای فوکوس و fallback)
- idempotent: فقط کشورهای بدون lat/lon را پر می‌کند
"""
import json

from django.core.management.base import BaseCommand

from core.models import Country
from core.services import atlas_names


def _largest_ring_center(feature):
    """مرکز بزرگ‌ترین ring (مساحت تقریبی bbox) — مرکز معتبر کشور."""
    g = feature.get("geometry") or {}
    rings = []
    if g.get("type") == "Polygon":
        rings = list(g.get("coordinates", []))
    elif g.get("type") == "MultiPolygon":
        for poly in g.get("coordinates", []):
            rings.append(poly[0])
    best, best_area = None, -1.0
    for ring in rings:
        lats = [p[1] for p in ring]
        lons = [p[0] for p in ring]
        area = (max(lats) - min(lats)) * (max(lons) - min(lons))
        if area > best_area:
            best_area = area
            best = (sum(lats) / len(lats), sum(lons) / len(lons))
    return best


class Command(BaseCommand):
    help = "پر کردن lat/lon واقعی کشورها از world-atlas GeoJSON"

    def handle(self, *args, **options):
        with open("core/assets/countries-110m.geojson", encoding="utf-8") as f:
            atlas = json.load(f)
        fa_by_name = {f["properties"]["name"]: atlas_names.ATLAS_TO_DB.get(f["properties"]["name"])
                      for f in atlas["features"]}
        db_by_name = {c.name: c for c in Country.objects.all()}
        filled, missing = 0, []
        for en, fa in fa_by_name.items():
            if not fa:
                missing.append(en)
                continue
            country = db_by_name.get(fa)
            if not country or country.lat is not None:
                continue
            for feat in atlas["features"]:
                if feat["properties"]["name"] == en:
                    center = _largest_ring_center(feat)
                    if center:
                        country.lat, country.lon = round(center[0], 3), round(center[1], 3)
                        country.save(update_fields=["lat", "lon"])
                        filled += 1
                    break
        self.stdout.write(self.style.SUCCESS(
            f"filled: {filled} countries | unmatched atlas names: {len(missing)}"))
        if missing:
            self.stdout.write("no DB match: " + "، ".join(missing))
