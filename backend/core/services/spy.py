# -*- coding: utf-8 -*-
"""جاسوسی و ترور — پورت کامل hacks.py نسخه تلگرام."""
import random

from django.utils import timezone

from ..gamedata import ASSASSINATION_DAMAGE_RATES, CABINET_OPTIONS
from ..models import AssassinationInfo, CabinetCode, HackCooldown
from . import gamestate as gs
from .combat import log_battle, notify, reduce_weapon

MAX_CODE_ATTEMPTS = 20


def get_hacker_defense_power(player):
    """قدرت دفاع هکری — مطابق get_defense_power:
    ضعیف×1 + متوسط×5 + قوی×25 + نخبه×50
    """
    weak = gs.get_item_qty(player, "hacker_count", "weak")
    medium = gs.get_item_qty(player, "hacker_count", "medium")
    strong = gs.get_item_qty(player, "hacker_count", "strong")
    elite = gs.get_item_qty(player, "hacker_count", "elite")
    return weak * 1 + medium * 5 + strong * 25 + elite * 50


def is_defense_hacker_active(player):
    cd = HackCooldown.objects.filter(player=player, hack_type="defense_hackers").first()
    if cd and cd.expires_at > timezone.now():
        return True
    if cd:
        cd.delete()
    return False


def process_hack_attack(attacker, target, hacker_level, count):
    """💻 حمله هکری: سرقت کدهای امنیتی کابینه — مطابق process_hack_attack
    هکر متوسط قدرت ۵ و هکر قوی قدرت ۲۵ دارد؛ تلفات ۲۰٪ در هر صورت.
    """
    specs = {
        "medium": {"power": 5, "name": "هکر متوسط"},
        "strong": {"power": 25, "name": "هکر قوی"},
    }
    spec = specs.get(hacker_level)
    if not spec:
        return {"ok": False, "error": "هکر ضعیف فقط برای دفاع است"}
    owned = gs.get_item_qty(attacker, "hacker_count", hacker_level)
    if count < 1 or owned < count:
        return {"ok": False, "error": f"شما {owned} {spec['name']} دارید"}

    attack_power = count * spec["power"]
    defense_power = get_hacker_defense_power(target)
    if is_defense_hacker_active(target):
        # حالت تدافعی: حملات ۵۰٪ ضعیف‌تر
        attack_power = int(attack_power * 0.5)

    attacker_loss = 0 if defense_power == 0 else max(1, int(count * 0.2))
    success = defense_power == 0 or attack_power > defense_power

    gs.set_item_qty(attacker, "hacker_count", hacker_level, owned - attacker_loss)
    gs.recalc_attack_power(attacker)

    if not success:
        log_battle(attacker, target, f"💻 حمله هکری {spec['name']}×{count} ناموفق بود")
        notify(target, "hack", "🛡 دفاع هکری موفق!",
               f"{attacker.player_name} با {spec['name']}×{count} حمله کرد و شکست خورد")
        return {"ok": True, "success": False, "attack_power": attack_power,
                "defense_power": defense_power, "hacker_loss": attacker_loss}

    codes = CabinetCode.objects.filter(player=target)
    if not codes.exists():
        log_battle(attacker, target, f"💻 حمله هکری {spec['name']}×{count} — هدف کد نداشت")
        return {"ok": True, "success": False, "no_codes": True,
                "error": "هدف کدهای امنیتی ندارد"}

    stolen = []
    for code_obj in codes:
        member_name = target.cabinet.get(code_obj.position_key, "نامشخص")
        AssassinationInfo.objects.update_or_create(
            hacker=attacker, target=target, position_key=code_obj.position_key,
            defaults={"code": code_obj.code, "member_name": member_name})
        pos = CABINET_OPTIONS.get(code_obj.position_key, {})
        stolen.append({
            "position": pos.get("name", code_obj.position_key),
            "icon": pos.get("icon", "🔑"),
            "member": member_name,
            "code": code_obj.code,
        })
    log_battle(attacker, target, f"💻 {spec['name']}×{count} کدهای امنیتی {target.player_name} را سرقت کرد")
    notify(target, "hack", "⚠️ هشدار امنیتی شدید!",
           f"کدهای امنیتی کابینه شما به سرقت رفت! قدرت دفاع: {defense_power} در برابر حمله {attack_power}")
    from .achievements import evaluate_achievements
    result = {"ok": True, "success": True, "stolen": stolen,
              "attack_power": attack_power, "defense_power": defense_power,
              "hacker_loss": attacker_loss}
    result["achievements_unlocked"] = evaluate_achievements(attacker)
    return result


def execute_hack_defense(player):
    """🛡 حالت تدافعی هکری — ۱ ساعت، ۱ هکر ضعیف"""
    weak = gs.get_item_qty(player, "hacker_count", "weak")
    if weak <= 0:
        return {"ok": False, "error": "هکر ضعیف برای حالت تدافعی ندارید!"}
    gs.set_item_qty(player, "hacker_count", "weak", weak - 1)
    HackCooldown.objects.update_or_create(
        player=player, hack_type="defense_hackers",
        defaults={"expires_at": timezone.now() + timezone.timedelta(hours=1)})
    return {"ok": True, "message": "حالت تدافعی فعال شد! ۱ ساعت محافظت هکری دارید."}


def execute_missile_hack(attacker, target, hacker_level, count):
    """🚀 از کار انداختن موشک‌های حریف (هکر قوی/نخبه) — ۳۰ دقیقه"""
    if hacker_level not in ("strong", "elite"):
        return {"ok": False, "error": "این هکر قابلیت missile_hack ندارد"}
    owned = gs.get_item_qty(attacker, "hacker_count", hacker_level)
    if count < 1 or owned < count:
        return {"ok": False, "error": "موجودی هکر کافی نیست"}
    defense_power = get_hacker_defense_power(target)
    attack_power = count * (25 if hacker_level == "strong" else 50)
    attacker_loss = max(1, int(count * 0.2))
    gs.set_item_qty(attacker, "hacker_count", hacker_level, owned - attacker_loss)
    gs.recalc_attack_power(attacker)
    if attack_power <= defense_power:
        notify(target, "hack", "🛡 دفاع هکری موفق!",
               f"حمله اختلال موشکی {attacker.player_name} دفع شد")
        return {"ok": True, "success": False, "hacker_loss": attacker_loss,
                "error": "دفاع هکری حریف قوی‌تر بود"}
    HackCooldown.objects.update_or_create(
        player=target, hack_type="disabled_missiles",
        defaults={"expires_at": timezone.now() + timezone.timedelta(minutes=30)})
    notify(target, "hack", "🚀 سیستم موشکی شما از کار افتاد!",
           "تا ۳۰ دقیقه نمی‌توانید موشک شلیک کنید.")
    log_battle(attacker, target, f"💻 موشک‌های {target.player_name} توسط هکر از کار افتاد")
    return {"ok": True, "success": True, "hacker_loss": attacker_loss,
            "message": "موشک‌های حریف ۳۰ دقیقه غیرفعال شد"}


def execute_defense_hack(attacker, target, hacker_level, count):
    """🛡 از کار انداختن پدافند حریف (هکر متوسط به بالا) — ۳۰ دقیقه"""
    if hacker_level not in ("medium", "strong", "elite"):
        return {"ok": False, "error": "این هکر قابلیت defense_hack ندارد"}
    owned = gs.get_item_qty(attacker, "hacker_count", hacker_level)
    if count < 1 or owned < count:
        return {"ok": False, "error": "موجودی هکر کافی نیست"}
    defense_power = get_hacker_defense_power(target)
    per = {"medium": 5, "strong": 25, "elite": 50}[hacker_level]
    attack_power = count * per
    attacker_loss = max(1, int(count * 0.2))
    gs.set_item_qty(attacker, "hacker_count", hacker_level, owned - attacker_loss)
    gs.recalc_attack_power(attacker)
    if attack_power <= defense_power:
        notify(target, "hack", "🛡 دفاع هکری موفق!",
               f"حمله اختلال پدافندی {attacker.player_name} دفع شد")
        return {"ok": True, "success": False, "hacker_loss": attacker_loss,
                "error": "دفاع هکری حریف قوی‌تر بود"}
    HackCooldown.objects.update_or_create(
        player=target, hack_type="disabled_defenses",
        defaults={"expires_at": timezone.now() + timezone.timedelta(minutes=30)})
    notify(target, "hack", "🛡 پدافند شما از کار افتاد!",
           "تا ۳۰ دقیقه پدافندهای شما ۷۰٪ ضعیف‌ترند!")
    log_battle(attacker, target, f"💻 پدافند {target.player_name} از کار افتاد")
    return {"ok": True, "success": True, "hacker_loss": attacker_loss,
            "message": "پدافند حریف ۳۰ دقیقه تضعیف شد"}


# ==================== ترور ====================
def get_my_intel(player):
    info = AssassinationInfo.objects.filter(hacker=player).select_related("target")
    out = []
    for i in info:
        pos = CABINET_OPTIONS.get(i.position_key, {})
        out.append({
            "target_id": i.target_id, "target_name": i.target.player_name,
            "member_key": i.position_key,
            "position": pos.get("name", i.position_key), "icon": pos.get("icon", "🔑"),
            "member": i.member_name, "code": i.code,
        })
    return out


def execute_assassination(player, target_id, member_key, method, entered_code):
    """🗡️ ترور مقام با کد سرقت‌شده — مطابق execute_assassination.
    شانس: پهپاد ۶۰٪ | جنگنده ۷۵٪ | کماندو ۵۰٪ — تجهیز مصرف می‌شود.
    موفق: کد یک‌بارمصرف و کابینه مقام خالی می‌شود.
    """
    from ..models import Player
    try:
        target = Player.objects.get(id=target_id)
    except Player.DoesNotExist:
        return {"ok": False, "error": "هدف یافت نشد"}

    info = AssassinationInfo.objects.filter(hacker=player, target=target, position_key=member_key).first()
    if not info:
        return {"ok": False, "error": "شما کد این مقام را ندارید"}
    if info.code != entered_code:
        return {"ok": False, "error": "کد وارد شده با کد سرقت‌شده مطابقت ندارد"}

    methods = {
        "drone": {"qty_fn": lambda: gs.get_category_count(player, "drone"), "success": 60,
                  "name": "پهپاد", "kind": "drone"},
        "fighter": {"qty_fn": lambda: gs.get_category_count(player, "fighter"), "success": 75,
                    "name": "جنگنده", "kind": "fighter"},
        "commando": {"qty_fn": lambda: gs.get_item_qty(player, "ground_count", "commando"), "success": 50,
                     "name": "کماندو", "kind": "ground"},
    }
    m = methods.get(method)
    if not m:
        return {"ok": False, "error": "روش نامعتبر"}
    if m["qty_fn"]() <= 0:
        return {"ok": False, "error": f"{m['name']} ندارید!"}

    # کاهش تجهیز
    if m["kind"] == "ground":
        cur = gs.get_item_qty(player, "ground_count", "commando")
        gs.set_item_qty(player, "ground_count", "commando", cur - 1)
        gs.recalc_attack_power(player)
    else:
        reduce_weapon(player, m["kind"], 1)

    success = random.randint(1, 100) <= m["success"]
    pos = CABINET_OPTIONS.get(member_key, {})
    damage_percent = ASSASSINATION_DAMAGE_RATES.get(member_key, 10)

    if success:
        old_defense = target.defense
        reduction = int(old_defense * damage_percent / 100)
        target.defense = max(0, old_defense - reduction)
        target.save(update_fields=["defense"])
        # کد مصرف می‌شود و کابینه مقام خالی
        AssassinationInfo.objects.filter(hacker=player, target=target, position_key=member_key).delete()
        CabinetCode.objects.filter(player=target, position_key=member_key).delete()
        cabinet = target.cabinet or {}
        cabinet[member_key] = "❌ (ترور شده)"
        target.cabinet = cabinet
        target.save(update_fields=["cabinet"])
        summary = f"🗡️ {pos.get('name', member_key)} {target.player_name} ترور شد (−{damage_percent}٪ استقامت)"
        log_battle(player, target, summary)
        notify(target, "assassination", "💀 ترور!",
               f"{pos.get('name', member_key)} کشور شما ترور شد! استقامت {damage_percent}٪ کاهش یافت. کدهای باقیمانده را عوض کنید!")
        return {"ok": True, "success": True, "damage_percent": damage_percent,
                "reduction": reduction, "new_defense": target.defense, "summary": summary}

    summary = f"🗡️ تلاش برای ترور {pos.get('name', member_key)} {target.player_name} نافرجام ماند"
    log_battle(player, target, summary)
    notify(target, "assassination", "⚠️ تلاش برای ترور نافرجام!",
           f"دشمن با کد شما تلاش کرد {pos.get('name')} شما را ترور کند اما ناموفق بود. کدهای خود را عوض کنید!")
    return {"ok": True, "success": False, "summary": summary}


def change_cabinet_code(player, position_key=None):
    """🔐 تغییر کدهای امنیتی (بعد از لو رفتن) — کد یکتا در کل بازی"""
    def gen_unique():
        for _ in range(MAX_CODE_ATTEMPTS):
            code = str(random.randint(100000, 999999))
            if not CabinetCode.objects.filter(code=code).exists():
                return code
        return str(random.randint(100000, 999999))
    keys = [position_key] if position_key in (player.cabinet or {}) else list((player.cabinet or {}).keys())
    for key in keys:
        CabinetCode.objects.update_or_create(player=player, position_key=key,
                                             defaults={"code": gen_unique()})
    return {"ok": True}
