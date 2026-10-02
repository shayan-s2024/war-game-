# -*- coding: utf-8 -*-
"""API Ø§ØµÙ„ÛŒ Ø¨Ø§Ø²ÛŒ â€” auth Ùˆ registration Ø¯Ø± auth_views/reg_viewsØ› Ø§ØªØ­Ø§Ø¯/Ù¾Ø§ÛŒÚ¯Ø§Ù‡ Ø¯Ø± social_views."""
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.gamedata import (
    AIR_DEFENSES, AIRCRAFT_CARRIERS, ARTILLERY, BOMBS, BUILDINGS, CABINET_KEYS,
    CABINET_OPTIONS, CONTINENT_GEO, COUNTRIES_LIST, DRONES, ECONOMIC_ITEMS,
    FIGHTERS, GROUND_FORCES, GUIDE_SECTIONS, HACKERS, HELICOPTERS, MINES,
    MISSILES, NAVAL_VESSELS, PILOTS, SHOP_PRICE_MULTIPLIER, SUBMARINES, TANKS, TOMAN_SHOP_ITEMS,
    get_total_countries_count,
)
from core.models import (
    CabinetCode, Country, CreditTransaction, GlobalBattleEvent, Notification,
    Player, SeasonWinner, Statement, StatementRecord, UsedCountry,
)
from core.services import achievements as ach_service
from core.services import combat, country_geo, economy, events, gamestate as gs, spy
from .common import require_player
from .serializers import (BattleLogSerializer, GlobalEventSerializer,
                          NotificationSerializer, PlayerSummarySerializer,
                          StatementSerializer)


# ==================== Ø«Ø¨Øªâ€ŒÙ†Ø§Ù… (Ù†Ø§Ù… â†’ Ú©Ø´ÙˆØ± â†’ Ú©Ø§Ø¨ÛŒÙ†Ù‡) ====================
@api_view(["GET"])
def registration_status(request):
    closed = gs.get_config("registration_closed") == "1"
    used = UsedCountry.objects.count()
    total = get_total_countries_count()
    player = Player.objects.filter(user=request.user).first()
    return Response({
        "closed": closed, "used": used, "total": total, "remaining": max(0, total - used),
        "registered": bool(player and player.player_name),
        "has_player_record": bool(player),
    })


@api_view(["POST"])
def register_name(request):
    """Ù…Ø±Ø­Ù„Ù‡ Û± Ø«Ø¨Øªâ€ŒÙ†Ø§Ù…: Ù†Ø§Ù… Ø¨Ø§Ø²ÛŒÚ©Ù† (Û³ ØªØ§ Û³Û° Ú©Ø§Ø±Ø§Ú©ØªØ±ØŒ ÛŒÚ©ØªØ§) + Ø¬Ø§ÛŒØ²Ù‡ Ø¯Ø¹ÙˆØª"""
    name = (request.data.get("name") or "").strip()
    if not (3 <= len(name) <= 30):
        return Response({"error": "Ø§Ø³Ù… Ø¨Ø§ÛŒØ¯ Û³ ØªØ§ Û³Û° Ú©Ø§Ø±Ø§Ú©ØªØ± Ø¨Ø§Ø´Ø¯"}, status=400)
    if Player.objects.filter(player_name=name).exists():
        return Response({"error": "Ø§ÛŒÙ† Ù†Ø§Ù… Ù‚Ø¨Ù„Ø§Ù‹ Ø§Ù†ØªØ®Ø§Ø¨ Ø´Ø¯Ù‡ Ø§Ø³Øª"}, status=400)
    if gs.get_config("registration_closed") == "1":
        return Response({"error": "Ø«Ø¨Øªâ€ŒÙ†Ø§Ù… Ø¨Ø³ØªÙ‡ Ø´Ø¯Ù‡ Ø§Ø³Øª"}, status=403)
    player, _ = Player.objects.get_or_create(user=request.user)
    if player.player_name:
        return Response({"error": "Ø´Ù…Ø§ Ù‚Ø¨Ù„Ø§Ù‹ Ø«Ø¨Øªâ€ŒÙ†Ø§Ù… Ú©Ø±Ø¯Ù‡â€ŒØ§ÛŒØ¯"}, status=400)
    player.player_name = name
    player.credit = settings.GAME["START_CREDIT"]
    player.defense = settings.GAME["START_DEFENSE"]
    player.population = settings.GAME["START_POPULATION"]
    player.save()
    CreditTransaction.objects.create(player=player, amount=settings.GAME["START_CREDIT"],
                                     reason="start_bonus", balance_after=player.credit)
    ref_code = request.data.get("ref")
    if ref_code:
        referrer = Player.objects.filter(player_name=ref_code).exclude(id=player.id).first()
        if referrer:
            player.referred_by = referrer
            referrer.credit += 10000
            referrer.invite_count += 1
            referrer.save(update_fields=["credit", "invite_count"])
            player.save(update_fields=["referred_by"])
            Notification.objects.create(player=referrer, kind="reward", title="ðŸŽ‰ Ø¬Ø§ÛŒØ²Ù‡ Ø¯Ø¹ÙˆØª",
                                        body="ÛŒÚ©ÛŒ Ø§Ø² Ø¯ÙˆØ³ØªØ§Ù† Ø´Ù…Ø§ ÙˆØ§Ø±Ø¯ Ø¨Ø§Ø²ÛŒ Ø´Ø¯! Û±Û°,Û°Û°Û° Ø³Ú©Ù‡ Ø¯Ø±ÛŒØ§ÙØª Ú©Ø±Ø¯ÛŒØ¯.")
            ach_service.evaluate_achievements(referrer)
    return Response({"ok": True, "next": "country"})


@api_view(["GET"])
def countries(request):
    """Ù„ÛŒØ³Øª Ú©Ø§Ù…Ù„ Û´ÛµÛ° Ú©Ø´ÙˆØ± Ú¯Ø±ÙˆÙ‡â€ŒØ¨Ù†Ø¯ÛŒâ€ŒØ´Ø¯Ù‡ Ø¨Ø± Ø§Ø³Ø§Ø³ Ù‚Ø§Ø±Ù‡ + ÙˆØ¶Ø¹ÛŒØª Ø±Ø²Ø±Ùˆ"""
    used_ids = set(UsedCountry.objects.values_list("country_id", flat=True))
    continents = [{"key": ck, "name": cd["name"], "flag": cd["flag"],
                   "lat": CONTINENT_GEO.get(ck, {}).get("lat", 0),
                   "lon": CONTINENT_GEO.get(ck, {}).get("lon", 0)}
                  for ck, cd in COUNTRIES_LIST.items()]
    grouped = {}
    for c in Country.objects.select_related("continent").order_by("continent__key", "name"):
        grouped.setdefault(c.continent.key, []).append({
            "name": c.name, "command_name": c.command_name, "emoji": c.emoji,
            "population": c.population_millions,
            "taken": c.id in used_ids,
            "lat": c.lat, "lon": c.lon,
            "continent": c.continent.key,
            "imaginary": country_geo.is_imaginary_country(c.name),
        })
    return Response({"continents": continents, "countries": grouped})


@api_view(["POST"])
def register_country(request):
    """Ù…Ø±Ø­Ù„Ù‡ Û²: Ø§Ù†ØªØ®Ø§Ø¨ Ú©Ø´ÙˆØ± â€” Ù‡Ø± Ú©Ø´ÙˆØ± ÙÙ‚Ø· ÛŒÚ© ØµØ§Ø­Ø¨ (Ø¶Ø¯ Ø±Ù‚Ø§Ø¨Øª Ø¨Ø§ select_for_update)"""
    name = request.data.get("country", "").strip()
    player, err = require_player(request)
    if err:
        return err
    if player.country:
        return Response({"error": "Ø´Ù…Ø§ Ù‚Ø¨Ù„Ø§Ù‹ Ú©Ø´ÙˆØ± Ø§Ù†ØªØ®Ø§Ø¨ Ú©Ø±Ø¯Ù‡â€ŒØ§ÛŒØ¯"}, status=400)
    with transaction.atomic():
        country = Country.objects.select_for_update().filter(
            Q(name=name) | Q(command_name__iexact=name)
        ).first()
        if not country:
            return Response({"error": "Ú©Ø´ÙˆØ± ÛŒØ§ÙØª Ù†Ø´Ø¯"}, status=404)
        if UsedCountry.objects.filter(country=country).exists():
            return Response({"error": "Ø§ÛŒÙ† Ú©Ø´ÙˆØ± Ù‚Ø¨Ù„Ø§Ù‹ ØªÙˆØ³Ø· Ø¨Ø§Ø²ÛŒÚ©Ù† Ø¯ÛŒÚ¯Ø±ÛŒ Ø§Ù†ØªØ®Ø§Ø¨ Ø´Ø¯Ù‡"}, status=409)
        UsedCountry.objects.create(country=country, player=player)
        player.country = country
        player.save(update_fields=["country"])
    return Response({"ok": True, "next": "cabinet"})


@api_view(["GET"])
def cabinet_view(request):
    player = Player.objects.filter(user=request.user).first()
    if not player:
        return Response({"cabinet": {}, "options": CABINET_OPTIONS, "keys": CABINET_KEYS})
    return Response({
        "cabinet": player.cabinet or {}, "options": CABINET_OPTIONS, "keys": CABINET_KEYS,
        "codes": {cc.position_key: cc.code for cc in CabinetCode.objects.filter(player=player)},
    })


@api_view(["POST"])
def cabinet_set(request):
    """ØªÙ†Ø¸ÛŒÙ… ÛŒÚ© Ù…Ù‚Ø§Ù… Ú©Ø§Ø¨ÛŒÙ†Ù‡ (Ú¯Ø²ÛŒÙ†Ù‡ Ù¾ÛŒØ´â€ŒÙØ±Ø¶ ÛŒØ§ Ù†ÙˆØ´ØªÙ† Ø¯Ø³ØªÛŒ)"""
    player, err = require_player(request)
    if err:
        return err
    key = request.data.get("key")
    value = (request.data.get("value") or "").strip()[:64]
    if key not in CABINET_KEYS:
        return Response({"error": "Ù…Ù‚Ø§Ù… Ù†Ø§Ù…Ø¹ØªØ¨Ø±"}, status=400)
    if not value:
        return Response({"error": "Ù…Ù‚Ø¯Ø§Ø± Ù†Ø§Ù…Ø¹ØªØ¨Ø±"}, status=400)
    cabinet = player.cabinet or {}
    cabinet[key] = value
    player.cabinet = cabinet
    player.cabinet_changed = True
    player.save(update_fields=["cabinet", "cabinet_changed"])
    return Response({"ok": True, "cabinet": cabinet})


@api_view(["POST"])
def cabinet_finish(request):
    """ØªØ§ÛŒÛŒØ¯ Ù†Ù‡Ø§ÛŒÛŒ Ú©Ø§Ø¨ÛŒÙ†Ù‡ â€” ØªÙˆÙ„ÛŒØ¯ Ú©Ø¯Ù‡Ø§ÛŒ Ø§Ù…Ù†ÛŒØªÛŒ Ø¨Ø±Ø§ÛŒ Ù‡Ù…Ù‡ Ûµ Ù…Ù‚Ø§Ù…"""
    player, err = require_player(request)
    if err:
        return err
    cabinet = player.cabinet or {}
    missing = [k for k in CABINET_KEYS if not cabinet.get(k)]
    if missing:
        return Response({"error": f"Ù…Ù‚Ø§Ù…â€ŒÙ‡Ø§ÛŒ Ù†Ø§ØªÙ…Ø§Ù…: {', '.join(missing)}"}, status=400)
    return Response(spy.change_cabinet_code(player))


@api_view(["POST"])
def cabinet_change_codes(request):
    """ðŸ” ØªØºÛŒÛŒØ± Ú©Ø¯Ù‡Ø§ÛŒ Ø§Ù…Ù†ÛŒØªÛŒ Ø®ÙˆØ¯Ù…"""
    player, err = require_player(request)
    if err:
        return err
    key = request.data.get("key")
    return Response(spy.change_cabinet_code(player, position_key=key if key in CABINET_KEYS else None))


# ==================== Ø¯Ø§Ø´Ø¨ÙˆØ±Ø¯ ====================
@api_view(["GET"])
def dashboard(request):
    player = Player.objects.filter(user=request.user).select_related(
        "country", "country__continent").first()
    if not player or not player.player_name:
        return Response({"needs_registration": True})
    ok, remaining, wait = combat.can_attack(player)
    cabinet_full = all((player.cabinet or {}).get(k) for k in CABINET_KEYS)
    return Response({
        "player": {
            "id": player.id, "name": player.player_name,
            "country": player.country.name if player.country else None,
            "emoji": player.country.emoji if player.country else "ðŸ³ï¸",
            "continent": player.country.continent.key if player.country else None,
            "credit": player.credit, "defense": player.defense,
            "attack_power": player.attack_power, "daily_profit": player.daily_profit,
            "score": player.score, "population": player.population,
            "invite_count": player.invite_count,
            "on_fire": bool(player.on_fire_until and player.on_fire_until > timezone.now()),
            "viruses": player.active_viruses or {},
        },
        "cabinet": player.cabinet or {}, "cabinet_complete": cabinet_full,
        "war_active": gs.is_war_allowed(),
        "attacks_remaining": remaining, "attack_limit": settings.GAME["ATTACK_LIMIT"],
        "sanctioned": bool(getattr(player, "sanction", None)),
        "next_step": None if (player.country and cabinet_full) else ("country" if not player.country else "cabinet"),
    })


@api_view(["GET"])
def my_equipment(request):
    """ðŸ“¦ ØªØ¬Ù‡ÛŒØ²Ø§Øª Ú©Ø§Ù…Ù„ Ù…Ù† â€” Ù‡Ù…Ù‡ Ø¯Ø³ØªÙ‡â€ŒÙ‡Ø§ Ø¨Ø§ Ú©ÛŒÙÛŒØª Ùˆ Ø³Ù‚Ù (Ø¨Ø¯ÙˆÙ† N+1: ÛŒÚ© query Ø¨Ø±Ø§ÛŒ Ù‡Ù…Ù‡)"""
    player, err = require_player(request)
    if err:
        return err
    from core.services.gamestate import CATEGORY_MAP
    from core.models import PlayerItem
    rows = PlayerItem.objects.filter(player=player)
    qty_map = {}
    # Ù¾Ø³ÙˆÙ†Ø¯Ù‡Ø§ÛŒ Ø·ÙˆÙ„Ø§Ù†ÛŒâ€ŒØªØ± Ø§ÙˆÙ„ â€” ØªØ§ "count" Ù‚Ø¨Ù„ Ø§Ø² "tank_count" Ø§Ø´ØªØ¨Ø§Ù‡ Ù†Ú¯ÛŒØ±Ø¯
    known_suffixes = sorted({sfx for _cat, sfx in CATEGORY_MAP.values()}, key=len, reverse=True)
    for r in rows:
        # item_key Ø³Ø§Ø®ØªØ§Ø± "<item>_<suffix>" Ø¯Ø§Ø±Ø¯Ø› suffix Ø®ÙˆØ¯Ø´ _ Ø¯Ø§Ø±Ø¯ (Ù…Ø«Ù„ tank_count)
        # â†’ Ø¨Ø§ Ù¾ÛŒØ¯Ø§ Ú©Ø±Ø¯Ù† suffix Ø´Ù†Ø§Ø®ØªÙ‡â€ŒØ´Ø¯Ù‡ Ø§Ø² Ø§Ù†ØªÙ‡Ø§ ØªØ¬Ø²ÛŒÙ‡ Ù…ÛŒâ€ŒÚ©Ù†ÛŒÙ…
        for sfx in known_suffixes:
            if r.item_key.endswith("_" + sfx):
                item_key = r.item_key[: -(len(sfx) + 1)]
                qty_map.setdefault(sfx, {})[item_key] = r.qty
                break
    out = {}
    for category, (catalog, suffix) in CATEGORY_MAP.items():
        items = []
        suffix_qty = qty_map.get(suffix, {})
        for key, item in catalog.items():
            items.append({
                "key": key, "name": item.get("name", key), "icon": item.get("icon", "📦"),
                "qty": suffix_qty.get(key, 0), "cap": item.get("cap", item.get("max")),
                "q": item.get("q"), "power": item.get("power"),
            })
        out[category] = items
    return Response({"categories": out})


@api_view(["GET"])
def leaderboard(request):
    metric = request.query_params.get("metric", "score")
    order = {"score": "-score", "credit": "-credit", "attack_power": "-attack_power",
             "daily_profit": "-daily_profit", "population": "-population"}.get(metric, "-score")
    qs = Player.objects.filter(player_name__isnull=False).select_related("country").order_by(order)[:50]
    player = Player.objects.filter(user=request.user).first()
    my_rank = None
    if player and player.player_name and metric in ("score", "credit", "attack_power", "daily_profit", "population"):
        my_value = getattr(player, metric)
        my_rank = Player.objects.filter(player_name__isnull=False, **{f"{metric}__gt": my_value}).count() + 1
    return Response({"leaderboard": PlayerSummarySerializer(qs, many=True).data, "my_rank": my_rank})


@api_view(["GET"])
def battle_log(request):
    player, err = require_player(request)
    if err:
        return err
    logs = player.battle_logs.order_by("-id")[:10]
    return Response({"logs": BattleLogSerializer(logs, many=True).data})


@api_view(["GET"])
def global_events(request):
    qs = GlobalBattleEvent.objects.select_related("attacker", "defender").order_by("-id")[:30]
    return Response({"events": GlobalEventSerializer(qs, many=True).data})


# ==================== Ø¨ÛŒØ§Ù†ÛŒÙ‡ Ùˆ ØªÙˆÛŒÛŒØª ====================
def _can_statement(player):
    window = timezone.now() - timezone.timedelta(seconds=settings.GAME["STATEMENT_WINDOW"])
    used = StatementRecord.objects.filter(player=player, at__gte=window).count()
    if used >= settings.GAME["STATEMENT_LIMIT"]:
        oldest = StatementRecord.objects.filter(player=player, at__gte=window).order_by("at").first()
        wait = int((oldest.at + timezone.timedelta(seconds=settings.GAME["STATEMENT_WINDOW"]) - timezone.now()).total_seconds())
        return False, 0, max(0, wait)
    return True, settings.GAME["STATEMENT_LIMIT"] - used, 0


@api_view(["GET", "POST"])
def statements(request):
    player, err = require_player(request)
    if err:
        return err
    if request.method == "GET":
        qs = Statement.objects.select_related("player", "player__country").order_by("-id")[:50]
        return Response({"statements": StatementSerializer(qs, many=True).data})
    text = (request.data.get("text") or "").strip()[:500]
    kind = request.data.get("kind", "statement")
    if not text:
        return Response({"error": "Ù…ØªÙ† Ø®Ø§Ù„ÛŒ Ø§Ø³Øª"}, status=400)
    if kind not in ("statement", "tweet"):
        kind = "statement"
    remaining = None
    if kind == "statement":
        ok, rem, wait = _can_statement(player)
        if not ok:
            h, m = wait // 3600, (wait % 3600) // 60
            return Response({"error": f"Ù…Ø­Ø¯ÙˆØ¯ÛŒØª Ø¨ÛŒØ§Ù†ÛŒÙ‡! {h} Ø³Ø§Ø¹Øª {m} Ø¯Ù‚ÛŒÙ‚Ù‡ Ø¯ÛŒÚ¯Ø±"}, status=429)
        StatementRecord.objects.create(player=player)
        remaining = rem - 1
    stmt = Statement.objects.create(player=player, kind=kind, text=text)
    return Response({"ok": True, "statement": StatementSerializer(stmt).data, "remaining": remaining})


# ==================== ÙØ±ÙˆØ´Ú¯Ø§Ù‡ ====================
@api_view(["GET"])
def shop_catalog(request):
    """ðŸ›’ Ú©Ø§ØªØ§Ù„ÙˆÚ¯ Ú©Ø§Ù…Ù„ ÙØ±ÙˆØ´Ú¯Ø§Ù‡ Ø¨Ø§ Ù‚ÛŒÙ…Øª Ø²Ù†Ø¯Ù‡ (Ø¬Ø±ÛŒÙ…Ù‡ ØªØ­Ø±ÛŒÙ… Ø§Ø¹Ù…Ø§Ù„ Ù…ÛŒâ€ŒØ´ÙˆØ¯)"""
    player, err = require_player(request)
    if err:
        return err
    penalty = economy.get_sanction_penalty(player)
    catalogs = {
        "mine": MINES, "economic": ECONOMIC_ITEMS, "defense": AIR_DEFENSES,
        "tank": TANKS, "fighter": FIGHTERS, "helicopter": HELICOPTERS,
        "missile": MISSILES, "drone": DRONES, "naval": NAVAL_VESSELS,
        "submarine": SUBMARINES, "carrier": AIRCRAFT_CARRIERS, "ground": GROUND_FORCES,
        "artillery": ARTILLERY, "hacker": HACKERS, "bomb": BOMBS, "pilot": PILOTS,
        "building": BUILDINGS,
    }
    out = {}
    for category, catalog in catalogs.items():
        items = []
        for key, item in catalog.items():
            base_price = item["price"]
            items.append({
                "key": key, "name": item.get("name", key), "icon": item.get("icon", "📦"),
                "base_price": base_price, "price": int(base_price * SHOP_PRICE_MULTIPLIER * (1 + penalty)),
                "sanctioned": penalty > 0, "count": item.get("count", 1),
                "q": item.get("q"), "power": item.get("power"),
                "cap": item.get("cap", item.get("max")),
                "daily_profit": item.get("daily_profit") or item.get("profit"),
                "description": item.get("description"), "abilities": item.get("abilities"),
                "fighters": item.get("fighters"), "capacity": item.get("capacity"),
            })
        out[category] = sorted(items, key=lambda product: (product["price"], product["name"]))
    return Response({"categories": out, "sanction_penalty": int(penalty * 100),
                     "toman_items": TOMAN_SHOP_ITEMS})


@api_view(["POST"])
def shop_buy(request):
    player, err = require_player(request)
    if err:
        return err
    try:
        count = int(request.data.get("count", 1))
    except (TypeError, ValueError):
        return Response({"error": "ØªØ¹Ø¯Ø§Ø¯ Ù†Ø§Ù…Ø¹ØªØ¨Ø±"}, status=400)
    with transaction.atomic():
        result = economy.purchase(player, request.data.get("category"),
                                  request.data.get("item"), count)
    if result.get("ok"):
        result["achievements_unlocked"] = ach_service.evaluate_achievements(player)
    return Response(result, status=200 if result.get("ok") else 400)


# ==================== Ø­Ù…Ù„Ù‡ ====================
@api_view(["GET"])
def attack_status(request):
    player, err = require_player(request)
    if err:
        return err
    ok, remaining, wait = combat.can_attack(player)
    return Response({"war_active": gs.is_war_allowed(), "can_attack": ok,
                     "remaining": remaining, "wait_seconds": wait,
                     "limit": settings.GAME["ATTACK_LIMIT"],
                     "missile_disabled": combat.is_missile_disabled(player),
                     "defense_disabled": combat.is_defense_disabled(player)})


@api_view(["GET"])
def attack_targets(request):
    """ðŸŽ¯ Ø§Ù‡Ø¯Ø§Ù Ù…Ø¬Ø§Ø² Ø¨Ø±Ø§ÛŒ Ù‡Ø± Ø³Ù„Ø§Ø­ â€” Ù…Ù†Ø·Ù‚ Ø¨Ø±Ø¯ Ø¯Ù‚ÛŒÙ‚Ø§Ù‹ Ù…Ø·Ø§Ø¨Ù‚ ØªÙ„Ú¯Ø±Ø§Ù…"""
    player, err = require_player(request)
    if err:
        return err
    weapon = request.query_params.get("weapon", "tank")
    targets = combat.get_available_targets(player, weapon)
    return Response({"targets": [
        {"id": t.id, "name": t.player_name, "country": t.country.name if t.country else None,
         "emoji": t.country.emoji if t.country else "ðŸ³ï¸", "score": t.score,
         "defense": t.defense, "continent": t.country.continent.key if t.country else None}
        for t in targets[:50]
    ], "war_active": gs.is_war_allowed()})


@api_view(["POST"])
def attack(request):
    player, err = require_player(request)
    if err:
        return err
    try:
        count = int(request.data.get("count", 1))
        target = Player.objects.get(id=request.data.get("target_id"))
    except (Player.DoesNotExist, TypeError, ValueError):
        return Response({"error": "Ù¾Ø§Ø±Ø§Ù…ØªØ± Ù†Ø§Ù…Ø¹ØªØ¨Ø±"}, status=400)
    if target.id == player.id:
        return Response({"error": "Ù†Ù…ÛŒâ€ŒØªÙˆØ§Ù†ÛŒØ¯ Ø¨Ù‡ Ø®ÙˆØ¯ØªØ§Ù† Ø­Ù…Ù„Ù‡ Ú©Ù†ÛŒØ¯"}, status=400)
    with transaction.atomic():
        result = combat.process_attack(player, target, request.data.get("weapon"), count)
    if result.get("ok"):
        result["achievements_unlocked"] = ach_service.evaluate_achievements(player)
    return Response(result, status=200 if result.get("ok") else 400)


@api_view(["POST"])
def bomb_attack(request):
    player, err = require_player(request)
    if err:
        return err
    try:
        count = int(request.data.get("count", 1))
        target = Player.objects.get(id=request.data.get("target_id"))
    except (Player.DoesNotExist, TypeError, ValueError):
        return Response({"error": "Ù¾Ø§Ø±Ø§Ù…ØªØ± Ù†Ø§Ù…Ø¹ØªØ¨Ø±"}, status=400)
    with transaction.atomic():
        result = combat.process_bomb_strike(player, target, request.data.get("bomb"), count)
    if result.get("ok"):
        result["achievements_unlocked"] = ach_service.evaluate_achievements(player)
    return Response(result, status=200 if result.get("ok") else 400)


@api_view(["POST"])
def artillery_attack(request):
    player, err = require_player(request)
    if err:
        return err
    try:
        count = int(request.data.get("count", 1))
        target = Player.objects.get(id=request.data.get("target_id"))
    except (Player.DoesNotExist, TypeError, ValueError):
        return Response({"error": "Ù¾Ø§Ø±Ø§Ù…ØªØ± Ù†Ø§Ù…Ø¹ØªØ¨Ø±"}, status=400)
    with transaction.atomic():
        result = combat.process_artillery_attack(player, target, request.data.get("artillery"), count)
    if result.get("ok"):
        result["achievements_unlocked"] = ach_service.evaluate_achievements(player)
    return Response(result, status=200 if result.get("ok") else 400)


# ==================== Ù‡Ú© Ùˆ ØªØ±ÙˆØ± ====================
@api_view(["GET"])
def spy_overview(request):
    player, err = require_player(request)
    if err:
        return err
    return Response({
        "hackers": {k: gs.get_item_qty(player, "hacker_count", k) for k in HACKERS},
        "defense_mode": spy.is_defense_hacker_active(player),
        "defense_power": spy.get_hacker_defense_power(player),
        "intel": spy.get_my_intel(player),
        "my_codes": {cc.position_key: cc.code for cc in CabinetCode.objects.filter(player=player)},
    })


@api_view(["POST"])
def hack_attack(request):
    player, err = require_player(request)
    if err:
        return err
    try:
        target = Player.objects.get(id=request.data.get("target_id"))
        count = int(request.data.get("count", 1))
    except (Player.DoesNotExist, TypeError, ValueError):
        return Response({"error": "Ù¾Ø§Ø±Ø§Ù…ØªØ± Ù†Ø§Ù…Ø¹ØªØ¨Ø±"}, status=400)
    with transaction.atomic():
        result = spy.process_hack_attack(player, target, request.data.get("level", "medium"), count)
    return Response(result, status=200 if result.get("ok") else 400)


@api_view(["POST"])
def hack_action(request):
    """Ø¯ÙØ§Ø¹ Ù‡Ú©Ø±ÛŒ / Ù‚Ø·Ø¹ Ù…ÙˆØ´Ú© Ø­Ø±ÛŒÙ / Ù‚Ø·Ø¹ Ù¾Ø¯Ø§ÙÙ†Ø¯ Ø­Ø±ÛŒÙ"""
    player, err = require_player(request)
    if err:
        return err
    action = request.data.get("action")
    if action == "defense_mode":
        result = spy.execute_hack_defense(player)
        return Response(result, status=200 if result.get("ok") else 400)
    try:
        target = Player.objects.get(id=request.data.get("target_id"))
        count = int(request.data.get("count", 1))
    except (Player.DoesNotExist, TypeError, ValueError):
        return Response({"error": "Ù¾Ø§Ø±Ø§Ù…ØªØ± Ù†Ø§Ù…Ø¹ØªØ¨Ø±"}, status=400)
    if action == "disable_missiles":
        result = spy.execute_missile_hack(player, target, request.data.get("level", "strong"), count)
    elif action == "disable_defenses":
        result = spy.execute_defense_hack(player, target, request.data.get("level", "medium"), count)
    else:
        return Response({"error": "Ø§Ú©Ø´Ù† Ù†Ø§Ù…Ø¹ØªØ¨Ø±"}, status=400)
    return Response(result, status=200 if result.get("ok") else 400)


@api_view(["POST"])
def assassinate(request):
    player, err = require_player(request)
    if err:
        return err
    try:
        result = spy.execute_assassination(
            player, int(request.data.get("target_id")), request.data.get("member_key"),
            request.data.get("method"), request.data.get("code", ""))
    except (TypeError, ValueError):
        return Response({"error": "Ù¾Ø§Ø±Ø§Ù…ØªØ± Ù†Ø§Ù…Ø¹ØªØ¨Ø±"}, status=400)
    return Response(result, status=200 if result.get("ok") else 400)


# ==================== Ø¯Ø³ØªØ§ÙˆØ±Ø¯Ù‡Ø§ ====================
@api_view(["GET"])
def achievements(request):
    player, err = require_player(request)
    if err:
        return err
    unlocked_now = ach_service.evaluate_achievements(player)  # sync lazy
    data = ach_service.achievement_overview(player)
    data["just_unlocked"] = unlocked_now
    return Response(data)


# ==================== Ø§Ø¹Ù„Ø§Ù†â€ŒÙ‡Ø§ ====================
@api_view(["GET", "POST"])
def notifications(request):
    player, err = require_player(request)
    if err:
        return err
    if request.method == "GET":
        qs = Notification.objects.filter(player=player).order_by("-id")[:50]
        return Response({"notifications": NotificationSerializer(qs, many=True).data,
                         "unread_count": Notification.objects.filter(player=player, is_read=False).count()})
    Notification.objects.filter(player=player, is_read=False).update(is_read=True)
    return Response({"ok": True})


# ==================== Ø±Ø§Ù‡Ù†Ù…Ø§ ====================
@api_view(["GET"])
def guide(request):
    return Response({"sections": [{"key": k, "title": t, "content": c} for k, t, c in GUIDE_SECTIONS]})


# ==================== Ù¾Ø±Ø¯Ø§Ø®Øª ØªÙˆÙ…Ø§Ù†ÛŒ ====================
@api_view(["POST"])
def payment_request(request):
    player, err = require_player(request)
    if err:
        return err
    item = TOMAN_SHOP_ITEMS.get(str(request.data.get("package", "")))
    if not item:
        return Response({"error": "Ù¾Ú©ÛŒØ¬ Ù†Ø§Ù…Ø¹ØªØ¨Ø±"}, status=400)
    receipt = request.FILES.get("receipt")
    if not receipt:
        return Response({"error": "Ø±Ø³ÛŒØ¯ Ø±Ø§ Ø¨Ø§Ø±Ú¯Ø°Ø§Ø±ÛŒ Ú©Ù†ÛŒØ¯"}, status=400)
    if receipt.size > 5 * 1024 * 1024:
        return Response({"error": "Ø­Ø¬Ù… ÙØ§ÛŒÙ„ Ø­Ø¯Ø§Ú©Ø«Ø± Ûµ Ù…Ú¯Ø§Ø¨Ø§ÛŒØª"}, status=400)
    from core.models import PendingPayment
    payment = PendingPayment.objects.create(
        payment_id=str(random.randint(100000, 999999)),
        player=player, coins=item["coins"], amount_toman=item["price_toman"],
        receipt=receipt)
    return Response({"ok": True, "payment_id": payment.payment_id,
                     "message": "Ø±Ø³ÛŒØ¯ Ø´Ù…Ø§ Ø«Ø¨Øª Ø´Ø¯. Ù¾Ø³ Ø§Ø² ØªØ§ÛŒÛŒØ¯ Ø§Ø¯Ù…ÛŒÙ† Ø³Ú©Ù‡â€ŒÙ‡Ø§ Ø§Ø¶Ø§ÙÙ‡ Ù…ÛŒâ€ŒØ´ÙˆØ¯."})


# ==================== Ù†Ø§ÙˆÚ¯Ø§Ù† Ø¯Ø±ÛŒØ§ÛŒÛŒ ====================
@api_view(["GET", "POST"])
def fleet(request):
    player, err = require_player(request)
    if err:
        return err
    from core.models import Base, FleetMission
    from core.services import naval
    naval.tick_fleets()  # âš“ Ø­Ù„ Ø²Ù†Ø¯Ù‡ Ø¨Ø¯ÙˆÙ† Celery (Ø¯Ø± production Ú©Ø§Ø± beat Ù‡Ù… Ù‡Ø³Øª)
    if request.method == "GET":
        missions = FleetMission.objects.filter(player=player).exclude(status="done") \
            .select_related("origin_country__continent", "target_country__continent", "target__user")
        done = FleetMission.objects.filter(player=player, status="done") \
            .select_related("origin_country__continent", "target_country__continent")[:10]
        owned_naval = {}
        for suffix, cat in (("naval_count", gs.CATEGORY_MAP["navy"][0]),
                            ("submarine_count", gs.CATEGORY_MAP["submarine"][0])):
            for k in cat:
                q = gs.get_item_qty(player, suffix, k)
                if q:
                    owned_naval[k] = {"qty": q, "name": cat[k]["name"], "icon": cat[k]["icon"],
                                      "q": cat[k].get("q")}
        docks = gs.get_item_qty(player, "count", "dock")
        return Response({
            "missions": [naval.serialize_mission(m) for m in missions],
            "history": [{"id": m.id, "summary": m.summary, "loot": m.loot,
                         "created_at": m.created_at.isoformat()} for m in done],
            "ships": owned_naval, "docks": docks,
            "has_dock": docks > 0 or Base.objects.filter(owner=player).exists(),
        })
    action = request.data.get("action")
    if action == "launch":
        target = Player.objects.filter(id=request.data.get("target_id")).first()
        if not target:
            return Response({"error": "Ù‡Ø¯Ù ÛŒØ§ÙØª Ù†Ø´Ø¯"}, status=404)
        with transaction.atomic():
            result = naval.launch_fleet(player, target, request.data.get("ships") or {})
        return Response(result, status=200 if result.get("ok") else 400)
    return Response({"error": "Ø§Ú©Ø´Ù† Ù†Ø§Ù…Ø¹ØªØ¨Ø±"}, status=400)


# ==================== World Globe API (Ù…Ù†Ø¨Ø¹ ÙˆØ§Ø­Ø¯ Ø­Ù‚ÛŒÙ‚Øª Ø¨Ø±Ø§ÛŒ Ú©Ø±Ù‡ Û³D) ====================
def _placements_payload():
    """ðŸ“ Ø³Ø§Ø²Ù‡â€ŒÙ‡Ø§ÛŒ Ø¬Ø§ÛŒâ€ŒÚ¯Ø°Ø§Ø±ÛŒâ€ŒØ´Ø¯Ù‡ Ù‡Ù…Ù‡ Ø¨Ø§Ø²ÛŒÚ©Ù†Ø§Ù† â€” Ù†Ù…Ø§ÛŒØ´ ØªØ§Ú©ØªÛŒÚ©ÛŒ Ø±ÙˆÛŒ Globe (public Ù…Ø«Ù„ Ù¾Ø§ÛŒÚ¯Ø§Ù‡â€ŒÙ‡Ø§)."""
    from core.models import Placement
    return [{"id": p.id, "item_key": p.item_key, "qty": p.qty,
             "player": p.player.player_name, "username": p.player.user.username,
             "lat": p.lat, "lon": p.lon}
            for p in Placement.objects.select_related("player__user").order_by("-id")[:100]]


def _admin_world_block():
    """ðŸ›¡ Ù„Ø§ÛŒÙ‡ Ø§Ø¯Ù…ÛŒÙ† Ø¨Ø±Ø§ÛŒ Globe â€” Ù‡Ù…Ù‡ Ø¨Ø§Ø²ÛŒÚ©Ù†Ø§Ù† + ØªØ±Ø§Ú©Ù†Ø´â€ŒÙ‡Ø§ÛŒ Ù„Ø­Ø¸Ù‡â€ŒØ§ÛŒ (ÙÙ‚Ø· is_staffØ› server-side)."""
    from core.models import GlobalBattleEvent as GBE
    players = []
    for p in Player.objects.filter(player_name__isnull=False).select_related("country", "country__continent", "user")[:80]:
        c = p.country
        players.append({
            "id": p.id, "name": p.player_name, "username": p.user.username,
            "country": c.name if c else None,
            "lat": c.lat if c else None, "lon": c.lon if c else None,
            "clat": c.continent.lat if c else 0, "clon": c.continent.lon if c else 0,
            "credit": p.credit, "score": p.score,
            "army": p.attack_power,
            "online": p.last_seen is not None and p.last_seen >= timezone.now() - timezone.timedelta(minutes=15),
        })
    txs = []
    for t in CreditTransaction.objects.select_related("player", "player__country", "player__country__continent").order_by("-id")[:30]:
        c = t.player.country if t.player else None
        txs.append({"id": t.id, "player": t.player.player_name if t.player else "ØŸ",
                    "amount": t.amount, "reason": t.reason,
                    "created_at": t.created_at.isoformat(),
                    "lat": (c.lat if c.lat is not None else c.continent.lat) if c else None,
                    "lon": (c.lon if c.lon is not None else c.continent.lon) if c else None})
    return {
        "players": players, "transactions": txs,
        "battles_24h": GBE.objects.filter(created_at__gte=timezone.now() - timezone.timedelta(hours=24)).count(),
        "total_players": Player.objects.filter(player_name__isnull=False).count(),
        "total_credit": sum(p["credit"] for p in players),
    }


@api_view(["GET"])
def world_state(request):
    """ðŸŒ ÙˆØ¶Ø¹ÛŒØª Ú©Ø§Ù…Ù„ Ø¬Ù‡Ø§Ù† â€” ÙÙ‚Ø· Ø¯Ø§Ø¯Ù‡ ÙˆØ§Ù‚Ø¹ÛŒ Game CoreØŒ Ø¨Ø§ cache Û³Û° Ø«Ø§Ù†ÛŒÙ‡â€ŒØ§ÛŒ.
    Ø´Ø§Ù…Ù„: Ú©Ø´ÙˆØ±Ù‡Ø§ (Ù…Ø§Ù„Ú©/Ù‚Ø§Ø±Ù‡)ØŒ Ø§ØªØ­Ø§Ø¯Ù‡Ø§ØŒ Ù¾Ø§ÛŒÚ¯Ø§Ù‡â€ŒÙ‡Ø§ØŒ Ù†Ø¨Ø±Ø¯Ù‡Ø§ÛŒ Ø§Ø®ÛŒØ±ØŒ Ø¢Ù…Ø§Ø± Ø²Ù†Ø¯Ù‡.
    """
    from django.core.cache import cache
    from core.models import Base, FleetMission
    from core.services import naval as naval_svc
    naval_svc.tick_fleets()  # âš“ Ø±Ø³ÛŒØ¯Ù†/Ø¨Ø±Ú¯Ø´Øª Ø²Ù†Ø¯Ù‡ Ù†Ø§ÙˆÚ¯Ø§Ù†â€ŒÙ‡Ø§ Ø­ØªÛŒ Ø¨Ø¯ÙˆÙ† Celery
    cached = cache.get("world_state_v1")
    if cached:
        cached["fleets"] = [  # Ù†Ø§ÙˆÚ¯Ø§Ù†â€ŒÙ‡Ø§ Ù‡Ù…ÛŒØ´Ù‡ Ø²Ù†Ø¯Ù‡ â€” Ø§Ø² cache Ø®Ø§Ø±Ø¬
            naval_svc.serialize_mission(m)
            for m in FleetMission.objects.exclude(status="done")
            .select_related("player__user", "origin_country__continent",
                            "target_country__continent", "target__user")[:30]
        ]
        cached["stats"]["fleets_active"] = len(cached["fleets"])
        cached["placements"] = _placements_payload()  # Ø¬Ø§ÛŒâ€ŒÚ¯Ø°Ø§Ø±ÛŒâ€ŒÙ‡Ø§ Ù‡Ù…ÛŒØ´Ù‡ Ø²Ù†Ø¯Ù‡
        cached["is_staff"] = bool(request.user.is_staff)  # per-request â€” cache Ù…Ø´ØªØ±Ú© Ø§Ø³Øª
        if request.user.is_staff:
            cached["admin"] = _admin_world_block()
        return Response(cached)

    from core.models import GlobalBattleEvent, Player, Union
    used_ids = set(UsedCountry.objects.values_list("country_id", flat=True))
    owners = {}
    for uc in UsedCountry.objects.select_related("player", "player__union"):
        owners[uc.country_id] = {
            "name": uc.player.player_name, "username": uc.player.user.username,
            "union": uc.player.union.name if uc.player.union_id else None,
            "score": uc.player.score,
        }

    # Ø§ØªØ­Ø§Ø¯Ù‡Ø§ Ø¨Ø§ Ù…Ø±Ø§Ú©Ø² Ù‚Ø§Ø±Ù‡â€ŒØ§ÛŒ Ø§Ø¹Ø¶Ø§
    unions = []
    for u in Union.objects.prefetch_related("members__country"):
        member_countries = [m.country.name for m in u.members.all() if m.country_id]
        unions.append({"id": u.id, "name": u.name, "level": u.level,
                       "owner": u.owner.player_name, "members": u.members.count(),
                       "treasury": u.treasury, "countries": member_countries[:12]})

    # Ù¾Ø§ÛŒÚ¯Ø§Ù‡â€ŒÙ‡Ø§ÛŒ Ù†Ø¸Ø§Ù…ÛŒ ÙˆØ§Ù‚Ø¹ÛŒ
    bases = [{"id": b.id, "country": b.country.name, "emoji": b.country.emoji,
              "continent": b.country.continent.key, "owner": b.owner.player_name,
              "username": b.owner.user.username,
              "lat": b.country.lat, "lon": b.country.lon,
              "ready": b.ready_at <= timezone.now(),
              "lat_fallback": b.country.continent.lat, "lon_fallback": b.country.continent.lon}
             for b in Base.objects.select_related("country", "country__continent", "owner__user")]

    # Ù†Ø¨Ø±Ø¯Ù‡Ø§ÛŒ Ø§Ø®ÛŒØ± (Ø±ÙˆÛŒØ¯Ø§Ø¯ Ø¬Ù‡Ø§Ù†ÛŒ) â€” Ù…Ú©Ø§Ù† Ø§Ø² Ú©Ø´ÙˆØ± Ù…Ù‡Ø§Ø¬Ù…
    battles = []
    for e in GlobalBattleEvent.objects.select_related("attacker", "attacker__country")[:20]:
        c = e.attacker.country if e.attacker else None
        battles.append({"id": e.id, "summary": e.summary,
                        "attacker": e.attacker.player_name if e.attacker else "ØŸ",
                        "defender": e.defender.player_name if e.defender else "ØŸ",
                        "country": c.name if c else None, "emoji": c.emoji if c else "âš”ï¸",
                        "lat": c.lat if c else None, "lon": c.lon if c else None,
                        "continent": c.continent.key if c else None,
                        "created_at": e.created_at.isoformat()})

    now15 = timezone.now() - timezone.timedelta(minutes=15)
    # âš“ Ù†Ø§ÙˆÚ¯Ø§Ù†â€ŒÙ‡Ø§ÛŒ Ø¯Ø± Ø­Ø§Ù„ Ø³ÙØ± â€” Ù…ÙˆÙ‚Ø¹ÛŒØª Ø²Ù†Ø¯Ù‡
    fleets = [naval_svc.serialize_mission(m) for m in
              FleetMission.objects.exclude(status="done")
              .select_related("player__user", "origin_country__continent",
                              "target_country__continent", "target__user")[:30]]
    continents = []
    for ck, cd in COUNTRIES_LIST.items():
        geo = CONTINENT_GEO.get(ck, {})
        continents.append({"key": ck, "name": cd["name"], "flag": cd["flag"],
                           "lat": geo.get("lat", 0), "lon": geo.get("lon", 0)})

    # Ú©Ø´ÙˆØ±Ù‡Ø§ Ø¨Ø§ Ù…Ø®ØªØµØ§Øª (ÙˆØ§Ù‚Ø¹ÛŒ ÛŒØ§ fallback Ù‚Ø§Ø±Ù‡)
    countries = []
    for c in Country.objects.select_related("continent"):
        countries.append({
            "name": c.name, "command_name": c.command_name, "emoji": c.emoji, "continent": c.continent.key,
            "population": c.population_millions, "taken": c.id in used_ids,
            "lat": c.lat, "lon": c.lon,
            "clat": c.continent.lat, "clon": c.continent.lon,
            "imaginary": country_geo.is_imaginary_country(c.name),
            "owner": owners.get(c.id),
        })

    online = Player.objects.filter(player_name__isnull=False,
                                   last_seen__gte=now15).count()
    out = {
        "countries": countries, "continents": continents,
        "unions": unions, "bases": bases, "battles": battles, "fleets": fleets,
        "placements": _placements_payload(),
        "is_staff": bool(request.user.is_staff),
        **({"admin": _admin_world_block()} if request.user.is_staff else {}),
        "stats": {
            "countries_total": len(countries),
            "countries_taken": len(used_ids),
            "players": Player.objects.filter(player_name__isnull=False).count(),
            "online": online, "bases": len(bases),
            "unions": len(unions), "battles_recent": len(battles),
            "fleets_active": len(fleets),
        },
        "updated_at": timezone.now().isoformat(),
    }
    cache.set("world_state_v1", out, 30)
    return Response(out)


# ==================== Ù…Ø±Ø²Ù‡Ø§ÛŒ Ø¬Ù‡Ø§Ù†ÛŒ (GeoJSON) ====================
@api_view(["GET"])
def world_borders(request):
    """ðŸŒ Ù…Ø±Ø²Ù‡Ø§ÛŒ ÙˆØ§Ù‚Ø¹ÛŒ Ú©Ø´ÙˆØ±Ù‡Ø§ Ø¨Ø±Ø§ÛŒ Globe â€” asset Ø§Ø³ØªØ§ØªÛŒÚ© (Ø³Ø±Ø¹Øª Ø¨Ø§Ù„Ø§Ø› cache Ù…Ø±ÙˆØ±Ú¯Ø±)."""
    from django.core.cache import cache
    from django.http import HttpResponse
    import json as _json
    from core.services import map_view
    data = cache.get("world_borders_enriched_v1")
    if data is None:
        geo = map_view.borders_geojson()
        if not geo.get("features"):
            return Response({"error": "atlas asset missing"}, status=404)
        data = map_view.enrich_borders(geo)
        # Fictional countries are rendered as deterministic offshore islands on the same globe.
        atlas_names = {
            (f.get("properties") or {}).get("db_name")
            for f in data.get("features", [])
            if (f.get("properties") or {}).get("db_name")
        }
        fictional = []
        for c in Country.objects.select_related("continent"):
            if c.name in atlas_names or not country_geo.is_imaginary_country(c.name):
                continue
            geo_c = country_geo.geometry_for_country(c.name, c.lat, c.lon, c.continent.lat, c.continent.lon)
            coords = [[[[lon, lat] for lon, lat in poly] for poly in geo_c["polygons"]]]
            # geometry: MultiPolygon -> [[[ring]], [[ring]]]
            mp = []
            for poly in geo_c["polygons"]:
                mp.append([[[float(lon), float(lat)] for lon, lat in poly]])
            fictional.append({
                "type": "Feature",
                "properties": {"name": c.command_name, "db_name": c.name, "fictional": True},
                "geometry": {"type": "MultiPolygon", "coordinates": mp},
            })
        if fictional:
            data["features"] = list(data.get("features", [])) + fictional
        cache.set("world_borders_enriched_v1", data, 3600)
    return HttpResponse(_json.dumps(data, ensure_ascii=False), content_type="application/json")


# ==================== Ù†Ù‚Ø´Ù‡ Ø´Ø®ØµÛŒ Ú©Ø´ÙˆØ± + Ø¬Ø§ÛŒâ€ŒÚ¯Ø°Ø§Ø±ÛŒ Ø³Ø§Ø²Ù‡â€ŒÙ‡Ø§ ====================
def _my_country_stats(player) -> dict:
    """ðŸ“Š Ø¢Ù…Ø§Ø± ÙˆØ§Ù‚Ø¹ÛŒ Ø¯Ø§Ø´Ø¨ÙˆØ±Ø¯ Ú©Ø´ÙˆØ± Ù…Ù† â€” Ù‡Ù…Ù‡ Ø§Ø² Game Core (Ø¨Ø¯ÙˆÙ† Ø¯Ø§Ø¯Ù‡ ÙÛŒÚ©).
    Ù‡Ø± ÙÛŒÙ„Ø¯ Ø§Ø² Ù‡Ù…Ø§Ù† ØªÙˆØ§Ø¨Ø¹ÛŒ Ù…ÛŒâ€ŒØ¢ÛŒØ¯ Ú©Ù‡ Ù…Ù†Ø·Ù‚ Ø¨Ø§Ø²ÛŒ (Ø®Ø±ÛŒØ¯/Ù†Ø¨Ø±Ø¯/Ø³ÙˆØ¯) Ø§Ø³ØªÙØ§Ø¯Ù‡ Ù…ÛŒâ€ŒÚ©Ù†Ø¯.
    """
    from core.gamedata import AIR_DEFENSES, ECONOMIC_ITEMS, MINES, BUILDINGS
    from core.models import Base, BattleLog, FleetMission, Notification, Sanction
    from core.services import combat, economy, gamestate as gs
    # Ø§Ù‚ØªØµØ§Ø¯: Ø³ÙˆØ¯ Ø±ÙˆØ²Ø§Ù†Ù‡ Ø«Ø¨Øªâ€ŒØ´Ø¯Ù‡ Player + ØªÙÚ©ÛŒÚ© Ù…Ù†Ø§Ø¨Ø¹ Ø¯Ø±Ø¢Ù…Ø¯ÛŒ
    mines = {k: gs.get_item_qty(player, "count", k) for k in MINES if gs.get_item_qty(player, "count", k) > 0}
    econ = {k: gs.get_item_qty(player, "count", k) for k in ECONOMIC_ITEMS if gs.get_item_qty(player, "count", k) > 0}
    buildings = {k: gs.get_item_qty(player, "count", k) for k in BUILDINGS if gs.get_item_qty(player, "count", k) > 0}
    income_mines = sum(MINES[k]["daily_profit"] * v for k, v in mines.items())
    income_econ = sum(ECONOMIC_ITEMS[k]["profit"] * v for k, v in econ.items())
    # Ø§Ø±ØªØ´: Ù‚Ø¯Ø±Øª ÙˆØ§Ù‚Ø¹ÛŒ Ø§Ø² recalc (Ø¨Ø¯ÙˆÙ† Ø°Ø®ÛŒØ±Ù‡ â€” ÙÙ‚Ø· Ø®ÙˆØ§Ù†Ø¯Ù†)
    from core.services.gamestate import recalc_attack_power, recalc_defense
    army_power = recalc_attack_power(player)
    defense_power = player.defense
    categories = {}
    for cat in ("tank", "fighter", "helicopter", "drone", "navy", "submarine",
                "missile", "artillery", "air_defense", "ground"):
        n = gs.get_category_count(player, cat)
        if n:
            q, _tot = gs.get_weighted_quality(player, cat)
            categories[cat] = {"count": n, "quality": round(q, 2)}
    ready_fighters = gs.get_ready_fighters(player)
    ready_helis = gs.get_ready_helicopters(player)
    # Ù¾Ø§ÛŒÚ¯Ø§Ù‡â€ŒÙ‡Ø§
    now = timezone.now()
    bases = [{"id": b.id, "country": b.country.name if b.country_id else "ØŸ",
              "ready": b.ready_at <= now,
              "ground": b.ground_troops, "air": b.air_troops}
             for b in Base.objects.filter(owner=player).select_related("country")[:20]]
    # Ù†Ø§ÙˆÚ¯Ø§Ù†
    fleets_active = FleetMission.objects.filter(player=player, status="outbound").count()
    fleets_returning = FleetMission.objects.filter(player=player, status="returning").count()
    # ÙˆØ¶Ø¹ÛŒØªâ€ŒÙ‡Ø§ÛŒ ÙØ¹Ø§Ù„
    sanction_active, sanction_penalty, sanction_end = gs.get_sanction(player)
    recent_battles = BattleLog.objects.filter(player=player).order_by("-ts").values_list("text", flat=True)[:8]
    notifs = Notification.objects.filter(player=player).order_by("-id")[:5]
    infected = list(player.active_viruses.keys())
    # Ø§Ù‚ØªØµØ§Ø¯ Ù„Ø­Ø¸Ù‡â€ŒØ§ÛŒ: Ø®Ø²Ø§Ù†Ù‡ = credit ÙˆØ§Ù‚Ø¹ÛŒ
    from core.services.combat import can_attack
    combat_ready = bool(can_attack(player))
    return {
        "treasury": player.credit,
        "population": player.population,
        "score": player.score,
        "daily_profit": player.daily_profit,
        "income": {"mines": income_mines, "economic": income_econ,
                   "total": income_mines + income_econ},
        "assets": {"mines": mines, "economic": econ, "buildings": buildings},
        "army": {"attack": army_power, "defense": defense_power,
                 "categories": categories,
                 "ready_fighters": ready_fighters, "ready_helicopters": ready_helis},
        "bases": bases,
        "fleets": {"outbound": fleets_active, "returning": fleets_returning},
        "status": {"viruses": infected,
                   "sanction": {"active": sanction_active,
                                "penalty": round(sanction_penalty * 100) if sanction_active else 0,
                                "until": sanction_end.isoformat() if sanction_end else None},
                   "on_fire": bool(player.on_fire_until and player.on_fire_until > now)},
        "recent_battles": list(recent_battles),
        "notifications": [{"title": n.title, "kind": n.kind, "at": n.created_at.isoformat()} for n in notifs],
        "combat_ready": combat_ready,
    }


def _serialize_profile(prof, country) -> dict:
    """ðŸŽ¨ Ù¾Ø±ÙˆÙØ§ÛŒÙ„ Ø´Ø®ØµÛŒâ€ŒØ³Ø§Ø²ÛŒ â€” Ø¨Ø§ fallback Ø¨Ù‡ Ù…Ù‚Ø¯Ø§Ø± Ù¾ÛŒØ´â€ŒÙØ±Ø¶ Ú©Ø´ÙˆØ±."""
    return {
        "display_name": prof.display_name or country.name,
        "flag_emoji": prof.flag_emoji or country.emoji,
        "map_color": prof.map_color or ("#e8654f" if prof.imaginary else "#38bdf8"),
        "capital_name": prof.capital_name or (f"\u067e\u0627\u06cc\u062a\u062e\u062a {country.name}"),
        "government": prof.government or "\u062c\u0645\u0647\u0648\u0631\u06cc",
        "imaginary": prof.imaginary,
        "divisions": prof.divisions or [],
    }


@api_view(["GET", "POST", "DELETE"])
def my_map(request):
    """ðŸ“ Ù†Ù‚Ø´Ù‡ Ø´Ø®ØµÛŒ: Ù‚Ù„Ù…Ø±Ùˆ Ø¨Ø§Ø²ÛŒÚ©Ù† (Ú©Ø´ÙˆØ±/Ù¾Ø§ÛŒÚ¯Ø§Ù‡â€ŒÙ‡Ø§) + Ø¬Ø§ÛŒâ€ŒÚ¯Ø°Ø§Ø±ÛŒ Ø³Ø§Ø²Ù‡ Ø¨Ø§ validation Ø³Ø±ÙˆØ±."""
    player, err = require_player(request)
    if err:
        return err
    from core.models import CountryProfile, Placement
    from core.services import map_view as mv
    if request.method == "GET":
        owned = mv.owned_countries(player)
        stats = _my_country_stats(player)
        profiles = {p.country_id: p for p in CountryProfile.objects.filter(player=player)}
        territory = []
        for c in owned:
            prof = profiles.get(c.id)
            geo = country_geo.geometry_for_country(
                c.name, c.lat, c.lon, c.continent.lat, c.continent.lon)
            divs = (prof.divisions if prof and prof.divisions else
                    country_geo.generate_divisions(c.name, geo["polygons"], count=6))
            territory.append({
                "name": c.name, "emoji": c.emoji,
                "lat": c.lat, "lon": c.lon,
                "clat": c.continent.lat, "clon": c.continent.lon,
                "geo": geo,
                "divisions": divs,
                "profile": _serialize_profile(prof, c) if prof else {
                    "display_name": c.name, "flag_emoji": c.emoji,
                    "map_color": "#38bdf8" if geo["kind"] == "real" else "#e8654f",
                    "capital_name": divs[0]["name"] if divs else f"\u067e\u0627\u06cc\u062a\u062e\u062a {c.name}",
                    "government": "Ø¬Ù…Ù‡ÙˆØ±ÛŒ", "imaginary": geo["kind"] == "imaginary",
                    "divisions": divs,
                },
            })
        return Response({
            "territory": territory,
            "placements": mv.serialize_placements(player),
            "borders_url": "/api/world/borders/",
            "stats": stats,
        })
    if request.method == "POST":
        try:
            lat = float(request.data.get("lat"))
            lon = float(request.data.get("lon"))
        except (TypeError, ValueError):
            return Response({"error": "Ù…Ø®ØªØµØ§Øª Ù†Ø§Ù…Ø¹ØªØ¨Ø±"}, status=400)
        ok, res = mv.validate_placement(player, lat, lon)
        if not ok:
            return Response({"error": res}, status=400)
        item_key = str(request.data.get("item_key") or "")
        city_name = _clean_str(request.data.get("city_name"), 64)
        if city_name:
            profile = CountryProfile.objects.filter(player=player, country=res).first()
            available = (profile.divisions if profile and profile.divisions else
                         country_geo.generate_divisions(res.name, country_geo.geometry_for_country(
                             res.name, res.lat, res.lon, res.continent.lat, res.continent.lon)["polygons"], count=6))
            selected_city = next((d for d in available
                                  if d.get("name") == city_name and d.get("kind") in ("city", "capital")), None)
            if not selected_city:
                return Response({"error": "Choose a city in your territory."}, status=400)
            # Trust only the server's city point; a client cannot label an arbitrary point as that city.
            lat, lon = float(selected_city["lat"]), float(selected_city["lon"])
            if not mv.point_in_country(lat, lon, res):
                return Response({"error": "That city is outside the territory."}, status=400)
        suffix = str(request.data.get("suffix") or "count")
        try:
            qty = max(1, int(request.data.get("qty") or 1))
        except (TypeError, ValueError):
            qty = 1
        have = gs.get_item_qty(player, suffix, item_key)
        if have < 1:
            return Response({"error": "You do not own this structure."}, status=400)
        from django.db.models import Sum as _Sum
        placed = Placement.objects.filter(player=player, item_key=item_key, suffix=suffix).aggregate(total=_Sum("qty"))["total"] or 0
        if Placement.objects.filter(player=player, item_key=item_key, suffix=suffix, lat=lat, lon=lon).exists():
            return Response({"error": "This structure is already assigned to that city."}, status=400)
        remaining = have - placed
        if remaining < 1:
            return Response({"error": "You have already assigned all owned structures."}, status=400)
        qty = min(qty, remaining)
        _, created = Placement.objects.update_or_create(
            player=player, item_key=item_key, suffix=suffix, lat=lat, lon=lon,
            defaults={"qty": qty, "city_name": city_name})
        events.log_event("base_built", player,
                         f"ðŸ“ {player.player_name} Ø³Ø§Ø²Ù‡ {item_key} Ø±Ø§ Ø¯Ø± Ù‚Ù„Ù…Ø±Ùˆ {res.name} Ø¬Ø§ÛŒâ€ŒÚ¯Ø°Ø§Ø±ÛŒ Ú©Ø±Ø¯",
                         target_id=player.id, target_kind="placement")
        return Response({"ok": True, "created": created, "country": res.name,
                         "placements": mv.serialize_placements(player)})
    # DELETE
    pid = request.data.get("id")
    if not pid:
        return Response({"error": "id Ù„Ø§Ø²Ù… Ø§Ø³Øª"}, status=400)
    deleted, _ = Placement.objects.filter(player=player, id=pid).delete()
    return Response({"ok": bool(deleted), "placements": mv.serialize_placements(player)})


# ==================== ðŸ—º Ù‡Ù†Ø¯Ø³Ù‡ Ú©Ø´ÙˆØ± (ÙˆØ§Ù‚Ø¹ÛŒ/Ø®ÛŒØ§Ù„ÛŒ) ====================
@api_view(["GET"])
def country_geometry(request):
    """Ù‡Ù†Ø¯Ø³Ù‡ Ø§Ø³ØªØ§Ù†Ø¯Ø§Ø±Ø¯ ÛŒÚ© Ú©Ø´ÙˆØ± â€” real (atlas) ÛŒØ§ imaginary (ØªÙˆÙ„ÛŒØ¯ seed-Ù¾Ø§ÛŒØ¯Ø§Ø±)."""
    player, err = require_player(request)
    if err:
        return err
    name = request.GET.get("name", "").strip()
    if not name:
        return Response({"error": "Ù†Ø§Ù… Ú©Ø´ÙˆØ± Ù„Ø§Ø²Ù… Ø§Ø³Øª"}, status=400)
    c = Country.objects.select_related("continent").filter(name=name).first()
    if not c:
        return Response({"error": "Ú©Ø´ÙˆØ± ÛŒØ§ÙØª Ù†Ø´Ø¯"}, status=404)
    geo = country_geo.geometry_for_country(c.name, c.lat, c.lon, c.continent.lat, c.continent.lon)
    divs = country_geo.generate_divisions(c.name, geo["polygons"], count=6)
    return Response({"name": c.name, "emoji": c.emoji, "geo": geo, "divisions": divs})


# ==================== ðŸŽ¨ Ø´Ø®ØµÛŒâ€ŒØ³Ø§Ø²ÛŒ Ú©Ø´ÙˆØ± ====================
PROFILE_FIELDS = {"display_name": 64, "flag_emoji": 8, "map_color": 9,
                  "capital_name": 64, "government": 32}
GOVERNMENTS = {"Ø¬Ù…Ù‡ÙˆØ±ÛŒ", "Ù¾Ø§Ø¯Ø´Ø§Ù‡ÛŒ", "Ø§Ù…Ø§Ø±Ø§Øª", "ÙØ¯Ø±Ø§Ø³ÛŒÙˆÙ†", "Ø¬Ù…Ù‡ÙˆØ±ÛŒ Ø®Ù„Ù‚", "Ø¯ÙˆÙ„Øª Ø´Ù‡Ø±ÛŒ"}


def _clean_str(v, maxlen):
    return str(v or "").strip()[:maxlen]


@api_view(["GET", "POST"])
def country_profile(request):
    """Ù¾Ø±ÙˆÙØ§ÛŒÙ„ Ø´Ø®ØµÛŒâ€ŒØ³Ø§Ø²ÛŒ Ú©Ø´ÙˆØ± (CountryProfile) â€” GET: Ø®ÙˆØ§Ù†Ø¯Ù†ØŒ POST: Ø°Ø®ÛŒØ±Ù‡.
    Ù¾Ø§ÛŒØªØ®Øª Ø¨Ø§ Ú©Ù„ÛŒÚ© Ø±ÙˆÛŒ Ù†Ù‚Ø´Ù‡ (validate_placement Ø³Ø±ÙˆØ±) ÛŒØ§ Ù†Ø§Ù… Ø¢Ø²Ø§Ø¯ Ù‚Ø§Ø¨Ù„ ØªØºÛŒÛŒØ± Ø§Ø³Øª.
    """
    player, err = require_player(request)
    if err:
        return err
    from core.models import CountryProfile
    from core.services import map_view as mv
    name = (request.data.get("country") if request.method == "POST"
            else request.GET.get("country") or "").strip()
    if not name:
        return Response({"error": "country Ù„Ø§Ø²Ù… Ø§Ø³Øª"}, status=400)
    c = Country.objects.select_related("continent").filter(name=name).first()
    if not c:
        return Response({"error": "Ú©Ø´ÙˆØ± ÛŒØ§ÙØª Ù†Ø´Ø¯"}, status=404)
    owned_names = {x.name for x in mv.owned_countries(player)}
    if c.name not in owned_names:
        return Response({"error": "Ø§ÛŒÙ† Ú©Ø´ÙˆØ± Ø¬Ø²Ùˆ Ù‚Ù„Ù…Ø±Ùˆ Ø´Ù…Ø§ Ù†ÛŒØ³Øª"}, status=403)
    prof, _ = CountryProfile.objects.get_or_create(
        player=player, country=c,
        defaults={"imaginary": country_geo.geometry_for_country(
            c.name, c.lat, c.lon, c.continent.lat, c.continent.lon)["kind"] == "imaginary"})
    if request.method == "POST" and "add_city" in request.data:
        import hashlib as _hashlib
        import random as _random
        city_name = _clean_str(request.data.get("add_city"), 48)
        if not city_name:
            return Response({"error": "Enter a city name."}, status=400)
        geo = country_geo.geometry_for_country(c.name, c.lat, c.lon, c.continent.lat, c.continent.lon)
        divisions = list(prof.divisions or country_geo.generate_divisions(c.name, geo["polygons"], count=6))
        if any(d.get("name", "").casefold() == city_name.casefold() for d in divisions):
            return Response({"error": "A city with this name already exists."}, status=400)
        if sum(1 for d in divisions if d.get("custom")) >= 10:
            return Response({"error": "You can add up to 10 custom cities."}, status=400)
        min_lon, min_lat, max_lon, max_lat = geo["bbox"]
        seed = int.from_bytes(_hashlib.sha256(f"{player.id}:{c.id}:{city_name.casefold()}".encode()).digest()[:8], "big")
        rng = _random.Random(seed)
        point = None
        for _ in range(10000):
            candidate_lat = rng.uniform(min_lat, max_lat)
            candidate_lon = rng.uniform(min_lon, max_lon)
            if mv.point_in_country(candidate_lat, candidate_lon, c):
                point = (candidate_lat, candidate_lon)
                break
        if point is None:
            return Response({"error": "Could not find room for another city in this territory."}, status=400)
        divisions.append({"name": city_name, "kind": "city", "lat": round(point[0], 4),
                          "lon": round(point[1], 4), "custom": True})
        prof.divisions = divisions
        prof.save(update_fields=["divisions", "updated_at"])
        return Response({"ok": True, "country": c.name, "profile": _serialize_profile(prof, c)})
    if request.method == "GET":
        return Response({"country": c.name, "emoji": c.emoji,
                         "profile": _serialize_profile(prof, c)})
    # POST â€” Ø§Ø¹ØªØ¨Ø§Ø±Ø³Ù†Ø¬ÛŒ ÙÛŒÙ„Ø¯ Ø¨Ù‡ ÙÛŒÙ„Ø¯
    data = request.data
    updates = {}
    for f, maxlen in PROFILE_FIELDS.items():
        if f in data:
            updates[f] = _clean_str(data.get(f), maxlen)
    if "map_color" in updates and updates["map_color"]:
        col = updates["map_color"]
        import re as _re
        if not _re.fullmatch(r"#[0-9a-fA-F]{6}", col):
            return Response({"error": "Ø±Ù†Ú¯ Ø¨Ø§ÛŒØ¯ hex Ø¨Ø§Ø´Ø¯ (#RRGGBB)"}, status=400)
    if "government" in updates and updates["government"] and updates["government"] not in GOVERNMENTS:
        return Response({"error": "Ù†ÙˆØ¹ Ø­Ú©ÙˆÙ…Øª Ù†Ø§Ù…Ø¹ØªØ¨Ø±"}, status=400)
    if "capital_lat" in data and "capital_lon" in data:
        try:
            clat, clon = float(data["capital_lat"]), float(data["capital_lon"])
        except (TypeError, ValueError):
            return Response({"error": "Ù…Ø®ØªØµØ§Øª Ù¾Ø§ÛŒØªØ®Øª Ù†Ø§Ù…Ø¹ØªØ¨Ø±"}, status=400)
        ok, res = mv.validate_placement(player, clat, clon)
        if not ok:
            return Response({"error": f"Ù¾Ø§ÛŒØªØ®Øª Ø¨Ø§ÛŒØ¯ Ø¯Ø§Ø®Ù„ Ù‚Ù„Ù…Ø±Ùˆ Ø¨Ø§Ø´Ø¯: {res}"}, status=400)
        updates["capital_lat"] = clat
        updates["capital_lon"] = clon
        # Ù†Ø§Ù… Ù¾Ø§ÛŒØªØ®Øª Ù‡Ù… Ø§Ú¯Ø± Ù‡Ù…Ø±Ø§Ù‡ Ø¢Ù…Ø¯Ù‡ØŒ Ø°Ø®ÛŒØ±Ù‡ Ø´ÙˆØ¯
        if "capital_name" in updates and not updates["capital_name"]:
            updates["capital_name"] = f"Ù¾Ø§ÛŒØªØ®Øª {c.name}"
    if "divisions" in data and isinstance(data["divisions"], list):
        # ÙÙ‚Ø· Ù†Ø§Ù…â€ŒÚ¯Ø°Ø§Ø±ÛŒ Ù…Ø¬Ø§Ø² â€” Ù…ÙˆÙ‚Ø¹ÛŒØªâ€ŒÙ‡Ø§ Ø§Ø² Ø³Ø±ÙˆØ± (seed-Ù¾Ø§ÛŒØ¯Ø§Ø±) Ø­ÙØ¸ Ù…ÛŒâ€ŒØ´ÙˆØ¯
        server_divs = prof.divisions or country_geo.generate_divisions(
            c.name, country_geo.geometry_for_country(
                c.name, c.lat, c.lon, c.continent.lat, c.continent.lon)["polygons"], count=6)
        renames = {str(d.get("name", "")): _clean_str(d.get("new_name"), 64)
                   for d in data["divisions"] if isinstance(d, dict) and d.get("new_name")}
        if renames:
            for d in server_divs:
                if d["name"] in renames and renames[d["name"]]:
                    d["name"] = renames[d["name"]]
        updates["divisions"] = server_divs
    for k, v in updates.items():
        setattr(prof, k, v)
    prof.save()
    events.log_event("achievement", player,
                     f"ðŸŽ¨ {player.player_name} Ù‡ÙˆÛŒØª Ú©Ø´ÙˆØ± {c.name} Ø±Ø§ Ø¨Ù‡â€ŒØ±ÙˆØ²Ø±Ø³Ø§Ù†ÛŒ Ú©Ø±Ø¯",
                     target_id=player.id, target_kind="player")
    return Response({"ok": True, "country": c.name, "profile": _serialize_profile(prof, c)})


# ==================== ðŸŒ Command Center â€” CountryOverview ====================
@api_view(["GET"])
def command_center(request):
    """aggregate Ú©Ø§Ù…Ù„ Ú©Ø´ÙˆØ± Ø¨Ø§Ø²ÛŒÚ©Ù† â€” ÛŒÚ© endpoint Ø¨Ø±Ø§ÛŒ Ø¯Ø§Ø´Ø¨ÙˆØ±Ø¯ ÙØ±Ù…Ø§Ù† (Ø¨Ø¯ÙˆÙ† Ù…Ø­Ø§Ø³Ø¨Ù‡ Ø¯Ø± Ú©Ù„Ø§ÛŒÙ†Øª).
    lazy world tick (ØªØ¬Ø§Ø±Øª/Ù‡Ø´Ø¯Ø§Ø±) Ø¯Ø± Ù‡Ù…ÛŒÙ† Ù†Ù‚Ø·Ù‡ throttle-Ø´Ø¯Ù‡ Ø§Ø¬Ø±Ø§ Ù…ÛŒâ€ŒØ´ÙˆØ¯.
    """
    player, err = require_player(request)
    if err:
        return err
    from core.services.tick import lazy_world_tick
    try:
        lazy_world_tick()
    except Exception:
        pass
    from core.models import Alert, Agreement, DiplomaticProposal
    from core.services import alerts as al, diplomacy as dip
    stats = _my_country_stats(player)
    # Ø®Ø²Ø§Ù†Ù‡ Ø±ÙˆÙ†Ø¯: Û±Û° ØªØ±Ø§Ú©Ù†Ø´ Ø¢Ø®Ø± â†’ net flow
    txs = CreditTransaction.objects.filter(player=player).order_by("-id")[:10]
    flow = sum(t.amount for t in txs)
    alerts_active = [al.serialize_alert(a) for a in
                     Alert.objects.filter(player=player, status__in=["active", "acknowledged"]).order_by("-priority", "-updated_at")[:20]]
    agreements = []
    if player.country_id:
        for ag in (Agreement.objects.filter(status="active")
                   .filter(initiator=player.country) | Agreement.objects.filter(status="active").filter(partner=player.country)) \
                .select_related("initiator", "partner")[:20]:
            other = ag.partner if ag.initiator_id == player.country_id else ag.initiator
            agreements.append({"id": ag.id, "type": ag.type, "type_fa": ag.get_type_display(),
                               "other": other.name, "emoji": other.emoji,
                               "deliveries": ag.deliveries_done,
                               "ends_at": ag.ends_at.isoformat() if ag.ends_at else None,
                               "terms": ag.terms})
    incoming = DiplomaticProposal.objects.filter(to_country=player.country, status="pending") \
        .select_related("from_country").order_by("-created_at")[:15]
    return Response({
        "country": {"name": player.country.name if player.country_id else None,
                    "emoji": player.country.emoji if player.country_id else "ðŸ³ï¸"},
        "treasury": {"current": player.credit, "income": player.daily_profit,
                     "recent_flow": flow},
        "stats": stats,
        "alerts": alerts_active,
        "agreements": agreements,
        "incoming_proposals": [{"id": p.id, "type": p.type, "type_fa": p.get_type_display(),
                                "from": p.from_country.name, "emoji": p.from_country.emoji,
                                "terms": p.counter_terms or p.terms,
                                "expires_at": p.expires_at.isoformat()} for p in incoming],
        "relations": dip.relation_profile(player),
    })


# ==================== ðŸš¨ Ù‡Ø´Ø¯Ø§Ø±Ù‡Ø§ ====================
@api_view(["GET", "POST"])
def alerts_view(request):
    """Ù„ÛŒØ³Øª Ù‡Ø´Ø¯Ø§Ø±Ù‡Ø§ + ack/evaluate. Ù‡Ù…Ù‡ Ø§Ø² backend ØªÙˆÙ„ÛŒØ¯ Ù…ÛŒâ€ŒØ´ÙˆÙ†Ø¯ â€” Ù†Ù‡ Ú©Ù„Ø§ÛŒÙ†Øª."""
    player, err = require_player(request)
    if err:
        return err
    from core.models import Alert
    from core.services import alerts as al
    if request.method == "POST":
        action = request.data.get("action")
        if action == "ack":
            a = al.ack_alert(player, int(request.data.get("id") or 0))
            if not a:
                return Response({"error": "Ù‡Ø´Ø¯Ø§Ø± ÛŒØ§ÙØª Ù†Ø´Ø¯"}, status=404)
            return Response({"ok": True, "id": a.id, "status": a.status})
        if action == "evaluate":
            found = al.evaluate_player(player)
            return Response({"ok": True, "active": len(found)})
        return Response({"error": "Ø§Ú©Ø´Ù† Ù†Ø§Ù…Ø¹ØªØ¨Ø±"}, status=400)
    status_f = request.GET.get("status", "active")
    qs = Alert.objects.filter(player=player).order_by("-priority", "-updated_at")
    if status_f == "active":
        qs = qs.filter(status__in=["active", "acknowledged"])
    elif status_f in ("resolved",):
        qs = qs.filter(status=status_f)
    return Response({"alerts": [al.serialize_alert(a) for a in qs[:50]]})


# ==================== ðŸ¤ Ø¯ÛŒÙ¾Ù„Ù…Ø§Ø³ÛŒ ====================
@api_view(["GET", "POST"])
def diplomacy_view(request):
    """Ø±ÙˆØ§Ø¨Ø·/ØªÙˆØ§ÙÙ‚â€ŒÙ‡Ø§/Ù¾ÛŒØ´Ù†Ù‡Ø§Ø¯Ù‡Ø§ + ÙØ±Ù…Ø§Ù†â€ŒÙ‡Ø§ÛŒ send/respond/cancel â€” Ù‡Ù…Ù‡ server-authoritative."""
    player, err = require_player(request)
    if err:
        return err
    from core.models import Agreement, DiplomaticProposal
    from core.services import diplomacy as dip
    if request.method == "POST":
        action = request.data.get("action")
        if action == "send":
            r = dip.send_proposal(
                player, str(request.data.get("to_country") or ""),
                str(request.data.get("type") or ""),
                request.data.get("terms") or {},
                command_id=str(request.data.get("command_id") or ""))
            return Response(r, status=200 if r.get("ok") else 400)
        if action == "respond":
            r = dip.respond_proposal(player, int(request.data.get("id") or 0),
                                     str(request.data.get("decision") or ""),
                                     request.data.get("counter_terms"))
            return Response(r, status=200 if r.get("ok") else 400)
        if action == "cancel":
            r = dip.cancel_agreement(player, int(request.data.get("id") or 0))
            return Response(r, status=200 if r.get("ok") else 400)
        return Response({"error": "Ø§Ú©Ø´Ù† Ù†Ø§Ù…Ø¹ØªØ¨Ø±"}, status=400)
    # GET â€” ÙˆØ¶Ø¹ÛŒØª Ú©Ø§Ù…Ù„ Ø¯ÛŒÙ¾Ù„Ù…Ø§Ø³ÛŒ Ú©Ø´ÙˆØ± Ø®ÙˆØ¯ÛŒ
    if not player.country_id:
        return Response({"relations": [], "agreements": [], "proposals_in": [], "proposals_out": []})
    c = player.country
    ags = (Agreement.objects.filter(status="active").filter(initiator=c) |
           Agreement.objects.filter(status="active").filter(partner=c)) \
        .select_related("initiator", "partner").order_by("-created_at")
    pin = (DiplomaticProposal.objects.filter(to_country=c, status="pending")
           .select_related("from_country").order_by("-created_at"))
    pout = (DiplomaticProposal.objects.filter(from_country=c, status="pending")
            .select_related("to_country").order_by("-created_at"))
    return Response({
        "relations": dip.relation_profile(player),
        "agreements": [{"id": a.id, "type": a.type, "type_fa": a.get_type_display(),
                        "other": (a.partner.name if a.initiator_id == c.id else a.initiator.name),
                        "deliveries": a.deliveries_done, "terms": a.terms,
                        "ends_at": a.ends_at.isoformat() if a.ends_at else None} for a in ags],
        "proposals_in": [{"id": p.id, "type": p.type, "type_fa": p.get_type_display(),
                          "from": p.from_country.name, "emoji": p.from_country.emoji,
                          "terms": p.counter_terms or p.terms, "ai_review": p.ai_review,
                          "expires_at": p.expires_at.isoformat()} for p in pin],
        "proposals_out": [{"id": p.id, "type": p.type, "type_fa": p.get_type_display(),
                           "to": p.to_country.name, "emoji": p.to_country.emoji,
                           "terms": p.counter_terms or p.terms,
                           "expires_at": p.expires_at.isoformat()} for p in pout],
    })


# ==================== ÙØµÙ„â€ŒÙ‡Ø§ ====================
@api_view(["GET"])
def season_winners(request):
    """Ø¨Ø±Ù†Ø¯Ú¯Ø§Ù† Ø¢Ø®Ø±ÛŒÙ† ÙØµÙ„ (ØªØ§ Û±Û° Ù†ÙØ± Ø¨Ù‡ ØªØ±ØªÛŒØ¨ Ø±ØªØ¨Ù‡)"""
    season_id = SeasonWinner.objects.order_by("-season_id") \
        .values_list("season_id", flat=True).first()
    if not season_id:
        return Response({"winners": []})
    winners = SeasonWinner.objects.filter(season_id=season_id).order_by("rank")[:10]
    return Response({"season_id": season_id, "winners": [{
        "season_id": w.season_id, "player_name": w.player_name, "country": w.country,
        "score": w.score, "rank": w.rank, "ended_at": w.ended_at.isoformat()} for w in winners]})

