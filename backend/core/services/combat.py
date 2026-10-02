# -*- coding: utf-8 -*-
"""سیستم نبرد — پورت کامل منطق attack.py و helpers.py نسخه تلگرام.

تمام محاسبات سمت سرور انجام می‌شود؛ نتیجه از فرانت قابل دستکاری نیست.
"""
import math
import random

from django.conf import settings
from django.utils import timezone

from ..gamedata import (
    AIR_DEFENSES, ARTILLERY, BOMBS, BUILDINGS, DRONES, FIGHTERS, GROUND_FORCES,
    HACKERS, HELICOPTERS, MISSILES, NAVAL_VESSELS, SUBMARINES, TANKS, WEAPONS_SYSTEM,
    ASSASSINATION_DAMAGE_RATES,
)
from ..models import (
    AttackRecord, BattleLog, GlobalBattleEvent, HackCooldown, Notification, Player,
)
from . import gamestate as gs

G = settings.GAME

DEFENDER_WEAPON_MAP = {
    "tank": "tank", "fighter": "air_defense", "helicopter": "air_defense",
    "drone": "air_defense", "navy": "navy", "submarine": "submarine", "missile": "navy",
}

# نقشه دسته‌های مدل WEAPONS_SYSTEM
_WS_CATEGORY = {
    "tank": "tank", "fighter": "fighter", "helicopter": "helicopter", "drone": "drone",
    "navy": "navy", "submarine": "submarine", "missile": "missile", "artillery": "artillery",
    "air_defense": "air_defense",
}

# ترتیب کاهش تلفات — مطابق reduce_user_weapon (لیست‌های صریح تلگرام)
_REDUCE_ORDER = {
    "tank": list(TANKS.keys()),
    "fighter": list(FIGHTERS.keys()),
    "helicopter": list(HELICOPTERS.keys()),
    "drone": list(DRONES.keys()),
    "navy": list(NAVAL_VESSELS.keys()),
    "submarine": list(SUBMARINES.keys()),
    "missile": [k for k in MISSILES if k != "icbm"] + ["icbm"],
    "artillery": list(ARTILLERY.keys()),
    "air_defense": list(AIR_DEFENSES.keys()),
    "ground": list(GROUND_FORCES.keys()),
    "bomb": list(BOMBS.keys()),
}


def reduce_weapon(player, weapon_type, loss_count):
    """کاهش تجهیزات از دسته‌های پرتعدادتر — منطق reduce_user_weapon"""
    order = _REDUCE_ORDER.get(weapon_type, [])
    cat, suffix = gs.CATEGORY_MAP[weapon_type]
    remaining = int(loss_count)
    for key in order:
        if remaining <= 0:
            break
        cur = gs.get_item_qty(player, suffix, key)
        take = min(cur, remaining)
        if take > 0:
            gs.set_item_qty(player, suffix, key, cur - take)
            remaining -= take
    if weapon_type == "air_defense":
        gs.recalc_defense(player)
    else:
        gs.recalc_attack_power(player)


def is_defense_disabled(player):
    cd = HackCooldown.objects.filter(player=player, hack_type="disabled_defenses").first()
    if cd and cd.expires_at > timezone.now():
        return True
    if cd:
        cd.delete()
    return False


def is_missile_disabled(player):
    cd = HackCooldown.objects.filter(player=player, hack_type="disabled_missiles").first()
    if cd and cd.expires_at > timezone.now():
        return True
    if cd:
        cd.delete()
    return False


def calculate_battle_power(attacker_weapon, defender_weapon, attacker_count, defender_count,
                           target=None, attacker_quality=1.0, defender_quality=1.0):
    """⚖️ نبرد کیفی — فرمول دقیقاً مطابق helpers.calculate_battle_power:
    قدرت = آسیب × √(تعداد × کیفیت) × اثربخشی × شانس
    """
    a = WEAPONS_SYSTEM[attacker_weapon]
    d = WEAPONS_SYSTEM[defender_weapon]
    effectiveness = a["effectiveness"].get(defender_weapon, 1.0)
    attacker_power = a["damage"] * math.sqrt(max(1, attacker_count) * attacker_quality) * effectiveness
    defender_power = d["defense"] * math.sqrt(max(1, defender_count) * defender_quality)
    if defender_weapon == "air_defense" and target is not None and is_defense_disabled(target):
        defender_power *= 0.3
    rf = random.uniform(0.85, 1.15)
    attacker_power *= rf
    defender_power *= rf
    power_ratio = attacker_power / (defender_power + 1)
    if power_ratio > 1.5:
        result, a_f, d_f = "victory", 0.05, 0.7
    elif power_ratio > 0.9:
        result, a_f, d_f = "narrow_victory", 0.2, 0.5
    elif power_ratio > 0.6:
        result, a_f, d_f = "narrow_defeat", 0.5, 0.3
    else:
        result, a_f, d_f = "defeat", 0.7, 0.1
    attacker_loss = min(attacker_count, max(1, int(attacker_count * a_f / max(0.3, attacker_quality))))
    defender_loss = min(defender_count, max(1, int(defender_count * d_f / max(0.3, defender_quality))))
    return result, attacker_loss, defender_loss, power_ratio


def can_attack(player):
    """۴ حمله در ۲۴ ساعت — مطابق can_attack؛ برمی‌گرداند (ok، remaining، wait_seconds)"""
    window_start = timezone.now() - timezone.timedelta(seconds=G["ATTACK_WINDOW"])
    recent = AttackRecord.objects.filter(player=player, at__gte=window_start)
    used = recent.count()
    if used >= G["ATTACK_LIMIT"]:
        oldest = recent.order_by("at").first()
        wait = int((oldest.at + timezone.timedelta(seconds=G["ATTACK_WINDOW"]) - timezone.now()).total_seconds())
        return False, 0, max(0, wait)
    return True, G["ATTACK_LIMIT"] - used, 0


def add_attack_record(player):
    AttackRecord.objects.create(player=player)


def log_battle(attacker, defender, summary):
    """📜 ثبت نبرد در تاریخچه هر دو طرف + خبر جهانی"""
    BattleLog.objects.create(player=attacker, text=summary)
    BattleLog.objects.create(player=defender, text=summary)
    # نگهداری ۱۰ لاگ آخر برای هر بازیکن (مطابق تلگرام)
    ids = BattleLog.objects.filter(player=attacker).order_by("-id").values_list("id", flat=True)[10:]
    BattleLog.objects.filter(id__in=list(ids)).delete()
    ids = BattleLog.objects.filter(player=defender).order_by("-id").values_list("id", flat=True)[10:]
    BattleLog.objects.filter(id__in=list(ids)).delete()
    GlobalBattleEvent.objects.create(attacker=attacker, defender=defender, summary=summary)


def notify(player, kind, title, body):
    """ثبت اعلان در دیتابیس + ارسال realtime از طریق WebSocket (اگر Redis فعال باشد)."""
    Notification.objects.create(player=player, kind=kind, title=title, body=body)
    try:
        from asgiref.sync import async_to_sync
        from ..api.routing import push_notification
        async_to_sync(push_notification)(player.id, {"kind": kind, "title": title, "body": body})
    except Exception:
        pass  # بدون Redis، اعلان در دیتابیس باقی می‌ماند و فرانت polling می‌کند


def dock_loot_bonus(attacker_player, weapon, base_loot):
    """⛴️ اسکله: غنیمت حملات دریایی تا ۲ برابر (هر اسکله ۱۵٪)"""
    if weapon not in ("navy", "submarine"):
        return base_loot
    docks = gs.get_item_qty(attacker_player, "count", "dock")
    if docks <= 0:
        return base_loot
    return int(base_loot * (1 + min(1.0, 0.15 * docks)))


def metro_shelter_factor(player):
    """🚉 مترو پناهگاه است: هر مترو ۱۵٪ کاهش تلفات جمعیت، حداکثر ۶۰٪"""
    metros = gs.get_item_qty(player, "count", "metro")
    return max(0.4, 1.0 - 0.15 * metros)


def hospital_heal(player, lost_units):
    """🏥 بیمارستان‌ها بخشی از تلفات زمینی را درمان می‌کنند (با سقف روزانه)"""
    if lost_units <= 0:
        return 0
    normal = gs.get_item_qty(player, "count", "normal_hospital")
    pro = gs.get_item_qty(player, "count", "professional_hospital")
    if normal <= 0 and pro <= 0:
        return 0
    today = timezone.now().strftime("%Y%m%d")
    if player.heal_date != today:
        player.heal_date = today
        player.healed_today = 0
    remaining = (normal * 1500 + pro * 3000) - player.healed_today
    if remaining <= 0:
        return 0
    heal_pct = min(0.5, normal * 0.15 + pro * 0.25)
    healed = min(int(lost_units * heal_pct), remaining)
    if healed > 0:
        player.healed_today += healed
        player.save(update_fields=["heal_date", "healed_today"])
        gs.add_item_qty(player, "ground_count", "normal_soldier", healed)
    return healed


def transfer_credit(sender, receiver, amount, reason, meta=None):
    """انتقال سونه با ثبت تراکنش (audit)"""
    sender.credit -= amount
    receiver.credit += amount
    sender.save(update_fields=["credit"])
    receiver.save(update_fields=["credit"])
    from ..models import CreditTransaction
    CreditTransaction.objects.create(player=sender, amount=-amount, reason=reason,
                                     balance_after=sender.credit, meta=meta or {})
    CreditTransaction.objects.create(player=receiver, amount=amount, reason=reason,
                                     balance_after=receiver.credit, meta=meta or {})


def change_credit(player, delta, reason, meta=None):
    player.credit = max(0, player.credit + delta)
    player.save(update_fields=["credit"])
    from ..models import CreditTransaction
    CreditTransaction.objects.create(player=player, amount=delta, reason=reason,
                                     balance_after=player.credit, meta=meta or {})


def change_score(player, delta):
    player.score = max(0, player.score + delta)
    player.save(update_fields=["score"])


# ==================== گرفتن اهداف مجاز ====================
def get_available_targets(attacker, weapon_type):
    """برد سلاح‌ها — منطق دقیق get_available_targets تلگرام:
    - موشک/بمب غیرقاره‌ای: قاره خود + قاره پایگاه‌ها
    - دریایی: همه‌جا
    - هوایی: قاره خود + پایگاه‌ها + همه‌جا اگر فرودگاه داشته باشد
    - زمینی: قاره خود
    """
    from ..models import Base
    from ..gamedata import get_country_continent_key

    atk_cont = get_country_continent_key(attacker.country.name) if attacker.country else None
    ready_bases = Base.objects.filter(owner=attacker, ready_at__lte=timezone.now())
    base_continents = {b.country.continent.key for b in ready_bases}
    targets = []
    for p in Player.objects.exclude(id=attacker.id).exclude(player_name__isnull=True).select_related("country"):
        if not p.player_name or not p.country:
            continue
        t_cont = p.country.continent.key
        if weapon_type in ("navy", "submarine"):
            targets.append(p)
        elif weapon_type == "missile":
            if atk_cont == t_cont or t_cont in base_continents:
                targets.append(p)
        elif weapon_type in ("fighter", "helicopter", "drone"):
            if atk_cont == t_cont or t_cont in base_continents or gs.get_item_qty(attacker, "count", "airport") > 0:
                targets.append(p)
        else:  # tank / artillery
            if atk_cont == t_cont:
                targets.append(p)
    return targets


# ==================== حمله اصلی ====================
def process_attack(attacker, target, weapon, count):
    """حمله با تانک/جنگنده/بالگرد/پهپاد/ناو/زیردریایی/موشک — پورت کامل process_attack"""
    if weapon not in DEFENDER_WEAPON_MAP:
        return {"ok": False, "error": "سلاح نامعتبر است"}
    if not gs.is_war_allowed():
        return {"ok": False, "error": "جنگ جهانی فعال نیست"}
    # 🤝 توافق دیپلماتیک: پیمان عدم تجاوز/اتحاد فعال = حمله ممنوع (server-authoritative)
    if attacker.country_id and target.country_id:
        from . import diplomacy
        for t in ("non_aggression", "alliance"):
            if diplomacy.agreement_between(attacker.country, target.country, t):
                return {"ok": False, "error": f"پیمان {diplomacy.agreement_between(attacker.country, target.country, t).get_type_display()} با این کشور فعال است — اول توافق را لغو کنید"}
    ok, remaining, wait = can_attack(attacker)
    if not ok:
        h, m = wait // 3600, (wait % 3600) // 60
        return {"ok": False, "error": f"سهمیه حملات تمام شده. {h} ساعت {m} دقیقه دیگر"}

    # موجودی
    if weapon == "fighter":
        weapon_count = gs.get_ready_fighters(attacker)
    elif weapon == "helicopter":
        weapon_count = gs.get_ready_helicopters(attacker)
    else:
        weapon_count = gs.get_category_count(attacker, weapon)
    if count < 1 or count > weapon_count:
        return {"ok": False, "error": f"شما فقط {weapon_count} عدد از این تجهیز آماده دارید"}

    # موشک از کار افتاده
    if weapon == "missile" and is_missile_disabled(attacker):
        return {"ok": False, "error": "سیستم موشکی شما توسط هکرها از کار افتاده است"}

    defender_weapon = DEFENDER_WEAPON_MAP[weapon]
    if defender_weapon == "tank":
        defender_count = gs.get_category_count(target, "tank")
    elif defender_weapon == "air_defense":
        defender_count = gs.get_category_count(target, "air_defense")
    elif defender_weapon == "navy":
        defender_count = gs.get_category_count(target, "navy")
    else:
        defender_count = gs.get_category_count(target, "submarine")
    defender_count = max(1, defender_count)

    aq, _ = gs.get_weighted_quality(attacker, weapon)
    dq, _ = gs.get_weighted_quality(target, defender_weapon)
    result, attacker_loss, defender_loss, ratio = calculate_battle_power(
        weapon, defender_weapon, count, defender_count, target,
        attacker_quality=aq, defender_quality=dq)

    # کاهش تجهیزات
    reduce_weapon(attacker, weapon, attacker_loss)
    reduce_weapon(target, defender_weapon, defender_loss)

    heal_notes = []
    if weapon == "tank" and attacker_loss > 0:
        healed = hospital_heal(attacker, attacker_loss)
        if healed:
            heal_notes.append(f"🏥 بیمارستان‌های شما {healed} سرباز زخمی را درمان کردند")
    if defender_weapon == "tank" and defender_loss > 0:
        healed = hospital_heal(target, defender_loss)
        if healed:
            heal_notes.append(f"🏥 بیمارستان‌های حریف {healed} سرباز زخمی را درمان کردند")

    # امتیاز و غنیمت — دقیقاً مطابق جدول تلگرام
    base_score = max(1, min(30, int(10 * ratio)))
    if result == "victory":
        loot = dock_loot_bonus(attacker, weapon, random.randint(10000, 100000))
        a_score = base_score + 5
        d_score = -(base_score + 10)
        change_credit(attacker, loot, "battle_loot", {"target": target.id})
        target.credit = max(0, target.credit - loot // 2)
        target.save(update_fields=["credit"])
        outcome = "🔥 پیروزی قاطع!"
    elif result == "narrow_victory":
        loot = dock_loot_bonus(attacker, weapon, random.randint(5000, 50000))
        a_score = base_score
        d_score = -(base_score + 5)
        change_credit(attacker, loot, "battle_loot", {"target": target.id})
        target.credit = max(0, target.credit - loot // 3)
        target.save(update_fields=["credit"])
        outcome = "⚡ پیروزی سخت!"
    elif result == "narrow_defeat":
        loot = dock_loot_bonus(attacker, weapon, random.randint(5000, 50000))
        a_score = -(base_score + 10)
        d_score = base_score
        attacker.credit = max(0, attacker.credit - loot)
        attacker.save(update_fields=["credit"])
        target.credit += loot // 3
        target.save(update_fields=["credit"])
        outcome = "💔 شکست نزدیک"
    else:
        loot = dock_loot_bonus(attacker, weapon, random.randint(10000, 100000))
        a_score = -(base_score + 20)
        d_score = base_score + 10
        attacker.credit = max(0, attacker.credit - loot)
        attacker.save(update_fields=["credit"])
        target.credit += loot // 2
        target.save(update_fields=["credit"])
        outcome = "💀 شکست سنگین"

    change_score(attacker, a_score)
    change_score(target, d_score)
    add_attack_record(attacker)

    wname = WEAPONS_SYSTEM[weapon]["name"]
    summary = f"⚔️ {wname}×{count} علیه {target.player_name} — {outcome}"
    log_battle(attacker, target, summary)
    from . import events
    events.log_event("battle_end", attacker, summary, target_id=target.id, target_kind="player")
    events.log_large_transaction(attacker, loot, "battle_loot")

    notify(target, "battle", "⚠️ هشدار نظامی",
           f"{attacker.player_name} با {wname}×{count} به شما حمله کرد!\n{outcome}\nتلفات شما: {defender_loss}")

    _, remaining, _ = can_attack(attacker)
    return {
        "ok": True, "outcome": outcome, "result": result, "power_ratio": round(ratio, 2),
        "attacker_loss": attacker_loss, "defender_loss": defender_loss, "loot": loot,
        "score_change": a_score, "remaining_attacks": remaining, "heal_notes": heal_notes,
        "summary": summary,
    }


# ==================== بمب‌افکن ====================
def process_bomb_strike(attacker, target, bomb_key, count):
    """💣 پورت کامل process_bomb_strike — سه نوع بمب با افکت‌های واقعی"""
    bomb = BOMBS.get(bomb_key)
    if not bomb:
        return {"ok": False, "error": "بمب نامعتبر"}
    if not gs.is_war_allowed():
        return {"ok": False, "error": "جنگ جهانی فعال نیست"}
    ok, remaining, wait = can_attack(attacker)
    if not ok:
        h, m = wait // 3600, (wait % 3600) // 60
        return {"ok": False, "error": f"سهمیه حملات تمام شده. {h} ساعت {m} دقیقه دیگر"}

    owned = gs.get_item_qty(attacker, "bomb_count", bomb_key)
    if owned <= 0:
        return {"ok": False, "error": "از این بمب موجودی ندارید"}
    count = max(1, min(count, owned))

    old_def = target.defense
    base_damage = bomb["power"] * count
    extra_lines = []

    if bomb_key == "fire":
        ad_q, ad_n = gs.get_weighted_quality(target, "air_defense")
        intercept_pct = min(55, int(ad_n * ad_q * 2))
        intercepted = int(base_damage * intercept_pct / 100)
        damage = base_damage - intercepted
        if intercepted > 0:
            extra_lines.append(f"🛡 پدافند حریف {intercept_pct}٪ از بمب‌ها را رهگیری کرد")
        else:
            extra_lines.append("🛡 پدافند حریف هیچ بمبی را رهگیری نکرد!")
        target.on_fire_until = timezone.now() + timezone.timedelta(days=3)
        target.save(update_fields=["on_fire_until"])
        extra_lines.append("🔥 شهر هدف در آتش گرفت! ۳ روز آتش‌سوزی و تلفات جمعی")
    elif bomb_key == "space":
        high_def = (gs.get_item_qty(target, "air_defense_count", "iron_dome") * 1.7 * 6
                    + gs.get_item_qty(target, "air_defense_count", "s400") * 1.2 * 4)
        pct = min(60, int(high_def))
        if pct > 0:
            saved = int(base_damage * pct / 100)
            damage = base_damage - saved
            extra_lines.append(f"🛡 پدافند پیشرفته حریف {pct}٪ بمب فضایی را دفع کرد")
        else:
            damage = base_damage
        destroyed = 0
        for cat, suffix in ((FIGHTERS, "fighter_count"), (HELICOPTERS, "helicopter_count"), (DRONES, "drone_count")):
            for k in cat:
                cur = gs.get_item_qty(target, suffix, k)
                if cur > 0:
                    kill = min(cur, max(1, int(cur * 0.15 * count)))
                    gs.set_item_qty(target, suffix, k, cur - kill)
                    destroyed += kill
        gs.recalc_attack_power(target)
        if destroyed > 0:
            extra_lines.append(f"💥 {destroyed} هواپیمای حریف روی زمین نابود شد!")
        extra_lines.append("🛰 ضربه از فضا — پدافند هوایی حریف کاملاً بی‌اثر بود")
    else:  # continental
        high_def = (gs.get_item_qty(target, "air_defense_count", "iron_dome") * 1.7 * 5
                    + gs.get_item_qty(target, "air_defense_count", "s400") * 1.2 * 3)
        pct = min(50, int(high_def * 0.8))
        if pct > 0:
            damage = int(base_damage * 1.2 * (100 - pct) / 100)
            extra_lines.append(f"🛡 پدافند پیشرفته حریف {pct}٪ بمب قاره‌ای را خنثی کرد")
        else:
            damage = int(base_damage * 1.2)
        destroyed_b = []
        for bkey in ("metro", "airport", "dock", "normal_hospital", "professional_hospital", "barracks"):
            bcount = gs.get_item_qty(target, "count", bkey)
            if bcount > 0 and random.random() < min(0.9, 0.5 * count):
                gs.set_item_qty(target, "count", bkey, bcount - 1)
                destroyed_b.append(BUILDINGS[bkey]["name"])
        pop_loss = int(target.population * 0.05 * count)
        if gs.get_item_qty(target, "count", "metro") > 0:
            pop_loss = int(pop_loss * metro_shelter_factor(target))
            extra_lines.append("🚉 متروهای حریف جان بخشی از مردم را نجات داد")
        target.population = max(0, target.population - pop_loss)
        if pop_loss > 0:
            extra_lines.append(f"👥 {pop_loss:,} نفر تلفات غیرنظامی")
        if destroyed_b:
            extra_lines.append("🏚 ساختمان‌های نابودشده: " + "، ".join(destroyed_b))
        extra_lines.append("☢️ بمب قاره‌ای: برد جهانی")
        target.save(update_fields=["population"])

    new_def = max(0, old_def - damage)
    target.defense = new_def
    target.save(update_fields=["defense"])
    gs.set_item_qty(attacker, "bomb_count", bomb_key, owned - count)
    gs.recalc_attack_power(attacker)

    score_change = min(30, 5 + damage // 3000)
    change_score(attacker, score_change)
    change_score(target, -score_change)
    loot = random.randint(15000, 40000)
    change_credit(attacker, loot, "bomb_loot", {"target": target.id})
    target.credit = max(0, target.credit - loot // 2)
    target.save(update_fields=["credit"])

    add_attack_record(attacker)
    summary = f"💣 {bomb['name']}×{count} روی {target.player_name} — آسیب {damage:,}"
    log_battle(attacker, target, summary)
    notify(target, "bomb", f"🚨 {bomb['name']} روی شهر شما فرود آمد!",
           f"مهاجم: {attacker.player_name}\nآسیب: {damage:,}\nدفاع: {old_def:,} ← {new_def:,}")

    _, remaining, _ = can_attack(attacker)
    return {
        "ok": True, "damage": damage, "old_def": old_def, "new_def": new_def, "loot": loot,
        "score_change": score_change, "bombs_left": owned - count,
        "extra": extra_lines, "remaining_attacks": remaining, "summary": summary,
    }


# ==================== توپخانه ====================
def process_artillery_attack(attacker, target, art_key, count):
    """💥 پورت کامل process_artillery_attack"""
    a = ARTILLERY.get(art_key)
    if not a:
        return {"ok": False, "error": "توپخانه نامعتبر"}
    if not gs.is_war_allowed():
        return {"ok": False, "error": "جنگ جهانی فعال نیست"}
    ok, remaining, wait = can_attack(attacker)
    if not ok:
        h, m = wait // 3600, (wait % 3600) // 60
        return {"ok": False, "error": f"سهمیه حملات تمام شده. {h} ساعت {m} دقیقه دیگر"}

    from ..gamedata import get_country_continent_key
    atk_cont = get_country_continent_key(attacker.country.name) if attacker.country else None
    tgt_cont = get_country_continent_key(target.country.name) if target.country else None
    if atk_cont != tgt_cont:
        return {"ok": False, "error": "توپخانه برد کوتاه دارد! فقط اهداف قاره خودتان"}

    owned = gs.get_item_qty(attacker, "artillery_count", art_key)
    if owned <= 0:
        return {"ok": False, "error": "از این توپخانه موجودی ندارید"}
    count = max(1, min(count, owned))

    effective_count = int(count * 1.1) if art_key == "defense" else count
    defender_tanks = max(1, gs.get_category_count(target, "tank"))
    art_q = a.get("q", 1.0)
    tank_q, _ = gs.get_weighted_quality(target, "tank")
    result, attacker_loss, defender_loss, ratio = calculate_battle_power(
        "artillery", "tank", effective_count, defender_tanks, target,
        attacker_quality=art_q, defender_quality=tank_q)

    # توپخانه پدافنددار مدافع: تا ۶۰٪ تلفاتش را جبران می‌کند
    def_art = gs.get_item_qty(target, "artillery_count", "defense")
    shield_pct = min(60, def_art * 8)
    saved = int(defender_loss * shield_pct / 100)
    defender_loss -= saved
    attacker_loss = min(attacker_loss, count)
    defender_loss = min(defender_loss, defender_tanks)

    reduce_weapon(attacker, "artillery", attacker_loss)
    reduce_weapon(target, "tank", defender_loss)

    if attacker_loss > 0:
        healed = hospital_heal(attacker, attacker_loss)
        if healed:
            pass
    if defender_loss > 0:
        hospital_heal(target, defender_loss)

    base_score = max(1, min(30, int(10 * ratio)))
    if result in ("victory", "narrow_victory"):
        a_score = base_score
        d_score = -base_score
        loot = dock_loot_bonus(attacker, "artillery", random.randint(8000, 40000))
        change_credit(attacker, loot, "artillery_win", {"target": target.id})
        target.credit = max(0, target.credit - loot // 2)
        target.save(update_fields=["credit"])
        outcome = "🔥 رگبار توپخانه موفق بود!" if result == "victory" else "⚡ پیروزی سخت توپخانه"
    else:
        a_score = -base_score
        d_score = base_score
        loot = random.randint(5000, 20000)
        attacker.credit = max(0, attacker.credit - loot)
        attacker.save(update_fields=["credit"])
        target.credit += loot // 3
        target.save(update_fields=["credit"])
        outcome = "💔 توپخانه‌های شما زیر آتش تانک‌های حریف از پا درآمدند"

    change_score(attacker, a_score)
    change_score(target, d_score)
    add_attack_record(attacker)
    summary = f"💥 {a['name']}×{count} علیه {target.player_name} — {outcome}"
    log_battle(attacker, target, summary)
    notify(target, "battle", "🚨 شهر شما زیر رگبار توپخانه است!",
           f"{attacker.player_name} با {a['name']}×{count}\nتانک‌های از دست رفته: {defender_loss}")

    _, remaining, _ = can_attack(attacker)
    return {
        "ok": True, "outcome": outcome, "result": result, "power_ratio": round(ratio, 2),
        "attacker_loss": attacker_loss, "defender_loss": defender_loss,
        "shield_pct": shield_pct, "loot": loot, "score_change": a_score,
        "remaining_attacks": remaining, "summary": summary,
    }
