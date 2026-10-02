# -*- coding: utf-8 -*-
"""داده اولیه: قاره‌ها + ۴۵۰ کشور + ادمین اصلی.

اجرا: python manage.py seed_gamedata
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from core.gamedata import CONTINENT_GEO, COUNTRY_GEO_HINTS, COUNTRIES_LIST
from core.models import AdminUser, Continent, Country
from core.services.country_commands import unique_command_name
import json
from pathlib import Path

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # ویندوز: جلوگیری از UnicodeEncodeError


class Command(BaseCommand):
    help = "بارگذاری قاره‌ها، ۴۵۰ کشور و ادمین اصلی"

    def handle(self, *args, **options):
        island_path = Path(__file__).resolve().parents[2] / "data" / "fictional_islands.json"
        fictional_islands = json.loads(island_path.read_text(encoding="utf-8")) if island_path.exists() else {}
        existing = set(Country.objects.exclude(command_name__isnull=True).values_list("command_name", flat=True))
        for ck, cd in COUNTRIES_LIST.items():
            geo = CONTINENT_GEO.get(ck, {})
            continent, _ = Continent.objects.update_or_create(
                key=ck,
                defaults={"name": cd["name"], "flag": cd["flag"],
                          "neighbors": cd.get("neighbors", []),
                          "lat": geo.get("lat", 0), "lon": geo.get("lon", 0)})
            created = 0
            for cname, cinfo in cd["countries"].items():
                existing_obj = Country.objects.filter(name=cname).first()
                command = existing_obj.command_name if existing_obj and existing_obj.command_name else unique_command_name(cname, existing)
                lat = existing_obj.lat if existing_obj and existing_obj.lat is not None else None
                lon = existing_obj.lon if existing_obj and existing_obj.lon is not None else None
                if cname in fictional_islands:
                    lat, lon = fictional_islands[cname]
                elif cname in COUNTRY_GEO_HINTS and lat is None and COUNTRY_GEO_HINTS[cname]:
                    lat, lon = COUNTRY_GEO_HINTS[cname]
                obj, was_created = Country.objects.update_or_create(
                    name=cname,
                    defaults={"continent": continent, "emoji": cinfo.get("emoji", "🏳️"),
                              "population_millions": cinfo.get("population", 0),
                              "command_name": command, "lat": lat, "lon": lon})
                created += 1 if was_created else 0
            self.stdout.write(f"  {cd['name']}: {len(cd['countries'])} کشور")
        AdminUser.objects.get_or_create(telegram_id=settings.GAME["MAIN_ADMIN_TELEGRAM_ID"])
        total = Country.objects.count()
        self.stdout.write(self.style.SUCCESS(f"✅ {total} کشور بارگذاری شد (هدف: ۴۵۰)"))
