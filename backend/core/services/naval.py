# -*- coding: utf-8 -*-
"""⚓ ناوگان دریایی — مأموریت واقعی با زمان سفر و برگشت (Game Core واقعی).

منطق:
- اعزام از کشور خودی که اسکله (dock) دارد؛ ناو/زیردریایی از موجودی کسر می‌شود
- زمان رفت: ۴ دقیقه پایه + ۲ دقیقه به‌ازای هر قاره فاصله (دریایی برد جهانی دارد)
- رسیدن: نبرد خودکار با ناوهای مدافع هدف — همان فرمول کیفی combat.calculate_battle_power
- غنیمت به مهاجم؛ ناوهای بازمانده پس از زمان برگشت به موجودی برمی‌گردند
- همه اعداد Server-Authoritative؛ Globe فقط نمایش می‌دهد
"""
import random

from django.utils import timezone
from django.conf import settings

from ..gamedata import WEAPONS_SYSTEM
from ..models import Country, FleetMission, Notification, Player
from . import combat, gamestate as gs
from . import events

# زمان سفر (ثانیه)
BASE_SAIL_SECONDS = 240          # ۴ دقیقه پایه
PER_CONTINENT_SECONDS = 120      # ۲ دقیقه به‌ازای هر قاره فاصله
RETURN_SECONDS = 180             # ۳ دقیقه برگشت

CONTINENT_ORDER = ["asia", "europe", "africa", "north_america", "south_america", "oceania"]


def _continent_index(key):
    try:
        return CONTINENT_ORDER.index(key)
    except ValueError:
        return 3


def _sail_seconds(origin_cont, target_cont):
    dist = abs(_continent_index(origin_cont) - _continent_index(target_cont))
    return BASE_SAIL_SECONDS + PER_CONTINENT_SECONDS * dist


def _owned_naval(player):
    """ناوها و زیردریایی‌های موجود بازیکن"""
    out = {}
    for suffix, cat in (("naval_count", gs.CATEGORY_MAP["navy"][0]),
                        ("submarine_count", gs.CATEGORY_MAP["submarine"][0])):
        for key in cat:
            qty = gs.get_item_qty(player, suffix, key)
            if qty > 0:
                out[key] = {"qty": qty, "suffix": suffix}
    return out


def launch_fleet(player, target_player, ships, dock_country=None):
    """اعزام ناوگان — ships: {item_key: qty} | dock_country: نام کشور دارای اسکله"""
    if not gs.is_war_allowed():
        return {"ok": False, "error": "جنگ جهانی فعال نیست"}
    if not target_player.player_name or not target_player.country:
        return {"ok": False, "error": "هدف نامعتبر"}
    if target_player.id == player.id:
        return {"ok": False, "error": "نمی‌توانید به خودتان حمله کنید"}
    # 🤝 پیمان عدم تجاوز/اتحاد = اعزام ممنوع (server-authoritative)
    if player.country_id and target_player.country_id:
        from . import diplomacy
        for t in ("non_aggression", "alliance"):
            if diplomacy.agreement_between(player.country, target_player.country, t):
                return {"ok": False, "error": f"پیمان {diplomacy.agreement_between(player.country, target_player.country, t).get_type_display()} فعال است"}

    # مأموریت فعال محدود: حداکثر ۲ ناوگان همزمان
    active = FleetMission.objects.filter(player=player, status__in=("outbound", "returning")).count()
    if active >= 2:
        return {"ok": False, "error": "حداکثر ۲ ناوگان فعال همزمان"}

    owned = _owned_naval(player)
    picked = {}
    for key, qty in (ships or {}).items():
        try:
            qty = int(qty)
        except (TypeError, ValueError):
            return {"ok": False, "error": "تعداد نامعتبر"}
        if qty <= 0:
            continue
        if key not in owned or owned[key]["qty"] < qty:
            return {"ok": False, "error": f"موجودی {key} کافی نیست"}
        picked[key] = {"qty": qty, "suffix": owned[key]["suffix"]}
    if not picked:
        return {"ok": False, "error": "هیچ شناوری برای اعزام انتخاب نشده"}

    # اسکله: کشور مبدأ باید dock داشته باشد (خودی یا پایگاه‌دار)
    origin_country = None
    if player.country and gs.get_item_qty(player, "count", "dock") > 0:
        origin_country = player.country
    else:
        base_with_dock = None
        from ..models import Base
        for b in Base.objects.filter(owner=player).select_related("country"):
            base_with_dock = b.country
            break
        origin_country = base_with_dock
    if origin_country is None:
        return {"ok": False, "error": "برای اعزام ناوگان به اسکله (dock) نیاز دارید"}

    # کسر شناورها از موجودی
    for key, info in picked.items():
        cur = gs.get_item_qty(player, info["suffix"], key)
        gs.set_item_qty(player, info["suffix"], key, cur - info["qty"])
    gs.recalc_attack_power(player)

    now = timezone.now()
    sail = _sail_seconds(player.country.continent.key if player.country else origin_country.continent.key,
                         target_player.country.continent.key)
    mission = FleetMission.objects.create(
        player=player, origin_country=origin_country,
        target=target_player, target_country=target_player.country,
        ships=picked, status="outbound",
        departed_at=now, arrive_at=now + timezone.timedelta(seconds=sail),
    )
    events.log_event("fleet_launched", player,
                     f"⚓ ناوگان {player.player_name} به سمت {target_player.player_name} اعزام شد",
                     target_id=mission.id, target_kind="fleet")
    return {"ok": True, "mission_id": mission.id,
            "arrive_at": mission.arrive_at.isoformat(), "sail_seconds": sail}


def resolve_arrival(mission):
    """رسیدن ناوگان: نبرد خودکار با پدافند دریایی هدف — فرمول کیفی موجود"""
    target = mission.target
    if target is None or not target.player_name:
        mission.status = "done"
        mission.save()
        return

    # پدافند دریایی هدف: ناو + زیردریایی
    def_count = gs.get_category_count(target, "navy") + gs.get_category_count(target, "submarine")
    def_count = max(1, def_count)
    atk_count = sum(i["qty"] for i in mission.ships.values())

    # کیفیت وزنی هر دو طرف
    aq_n, _ = gs.get_weighted_quality(mission.player, "navy")
    aq_s, _ = gs.get_weighted_quality(mission.player, "submarine")
    dq_n, _ = gs.get_weighted_quality(target, "navy")
    dq_s, _ = gs.get_weighted_quality(target, "submarine")
    aq = (aq_n + aq_s) / 2 if aq_n or aq_s else 1.0
    dq = (dq_n + dq_s) / 2 if dq_n or dq_s else 1.0

    result, attacker_loss, defender_loss, ratio = combat.calculate_battle_power(
        "navy", "navy", max(1, atk_count), def_count, target,
        attacker_quality=aq, defender_quality=dq)

    # تلفات: از ناوها شروع، بعد زیردریایی
    ships_left = {}
    remaining_loss = min(attacker_loss, atk_count)
    for key, info in mission.ships.items():
        take = min(info["qty"], remaining_loss)
        ships_left[key] = info["qty"] - take
        remaining_loss -= take
        if remaining_loss <= 0 and take == 0:
            ships_left[key] = info["qty"]
    mission.ships_left = ships_left

    d_loss = min(defender_loss, def_count)
    combat.reduce_weapon(target, "navy", d_loss)

    outcome_fa = {"victory": "🔥 پیروزی قاطع!", "narrow_victory": "⚡ پیروزی سخت!",
                  "narrow_defeat": "💔 شکست نزدیک", "defeat": "💀 شکست سنگین"}[result]

    loot = 0
    if result in ("victory", "narrow_victory"):
        base = random.randint(20000, 90000) if result == "victory" else random.randint(10000, 45000)
        loot = combat.dock_loot_bonus(mission.player, "navy", base)
        combat.change_credit(mission.player, loot, "battle_loot", {"fleet": mission.id})
        target.credit = max(0, target.credit - loot // 2)
        target.save(update_fields=["credit"])

    score = max(1, min(30, int(10 * ratio)))
    if result in ("victory", "narrow_victory"):
        combat.change_score(mission.player, score + 5)
        combat.change_score(target, -(score + 10))
    else:
        combat.change_score(mission.player, -(score + 10))
        combat.change_score(target, score)

    combat.add_attack_record(mission.player)
    summary = f"⚓ ناوگان {mission.player.player_name} به {target.player_name} رسید — {outcome_fa} تلفات: {attacker_loss} / {d_loss}"
    mission.summary = summary
    mission.status = "returning"
    mission.return_at = timezone.now() + timezone.timedelta(seconds=RETURN_SECONDS)
    mission.loot = loot
    mission.save()

    combat.log_battle(mission.player, target, summary)
    combat.notify(target, "battle", "⚓ حمله دریایی!",
                  f"ناوگان {mission.player.player_name} به سواحل شما رسید\n{outcome_fa}\nناوهای از دست رفته: {d_loss}")
    from ..api.routing import push_admin_dashboard
    push_admin_dashboard({"event": "battle", "text": summary})
    events.log_event("battle_end", mission.player, summary,
                     target_id=target.id, target_kind="player")


def complete_return(mission):
    """بازگشت ناوهای بازمانده به موجودی"""
    if mission.ships_left:
        for key, qty in mission.ships_left.items():
            if qty <= 0:
                continue
            info = mission.ships.get(key, {})
            suffix = info.get("suffix") or ("submarine_count" if key in
                                            gs.CATEGORY_MAP["submarine"][0] else "naval_count")
            gs.add_item_qty(mission.player, suffix, key, qty)
        gs.recalc_attack_power(mission.player)
    if mission.loot > 0:
        combat.notify(mission.player, "reward", "⚓ ناوگان بازگشت",
                      f"غنیمت {mission.loot:,} سکه + شناورهای بازمانده به کشور شما برگشتند.")
    else:
        combat.notify(mission.player, "battle", "⚓ ناوگان بازگشت",
                      "شناورهای بازمانده به بندر برگشتند.")
    mission.status = "done"
    mission.save()
    events.log_event("fleet_returned", mission.player,
                     f"⚓ ناوگان {mission.player.player_name} به بندر برگشت",
                     target_id=mission.id, target_kind="fleet")


def tick_fleets():
    """کار زمان‌بندی: رسیدن و برگشت ناوگان‌ها — Celery/beat یا manual"""
    now = timezone.now()
    arrived = FleetMission.objects.filter(status="outbound", arrive_at__lte=now).select_related(
        "player", "target", "target__country", "origin_country")
    for m in arrived:
        resolve_arrival(m)
    returned = FleetMission.objects.filter(status="returning", return_at__lte=now)
    for m in returned:
        complete_return(m)
    return f"{arrived.count()} arrived, {returned.count()} returned"


def serialize_mission(m):
    """برای Globe و UI — موقعیت زنده بین مبدأ و هدف"""
    prog = 0.0
    if m.status == "outbound" and m.arrive_at:
        total = (m.arrive_at - m.departed_at).total_seconds()
        elapsed = (timezone.now() - m.departed_at).total_seconds()
        prog = min(1.0, max(0.0, elapsed / total if total > 0 else 1))
    elif m.status == "returning" and m.return_at:
        total = (m.return_at - m.arrive_at).total_seconds() if m.arrive_at else RETURN_SECONDS
        elapsed = (timezone.now() - m.arrive_at).total_seconds() if m.arrive_at else 0
        prog = min(1.0, max(0.0, elapsed / total if total > 0 else 1))
    return {
        "id": m.id, "player": m.player.player_name, "username": m.player.user.username,
        "status": m.status, "progress": round(prog, 3),
        "origin": {"name": m.origin_country.name if m.origin_country else None,
                   "lat": m.origin_country.lat if m.origin_country else None,
                   "lon": m.origin_country.lon if m.origin_country else None,
                   "clat": m.origin_country.continent.lat if m.origin_country else 0,
                   "clon": m.origin_country.continent.lon if m.origin_country else 0},
        "target": {"name": m.target_country.name if m.target_country else None,
                   "lat": m.target_country.lat if m.target_country else None,
                   "lon": m.target_country.lon if m.target_country else None,
                   "clat": m.target_country.continent.lat if m.target_country else 0,
                   "clon": m.target_country.continent.lon if m.target_country else 0},
        "ships": {k: v.get("qty", v) if isinstance(v, dict) else v for k, v in (m.ships or {}).items()},
        "loot": m.loot, "summary": m.summary,
        "arrive_at": m.arrive_at.isoformat() if m.arrive_at else None,
        "return_at": m.return_at.isoformat() if m.return_at else None,
    }
