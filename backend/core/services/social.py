# -*- coding: utf-8 -*-
"""اتحادها و پایگاه‌ها — پورت کامل unions.py و bases.py نسخه تلگرام."""
import random

from django.conf import settings
from django.utils import timezone

from ..models import (
    Base, BasePermissionRequest, Country, Notification, Player, Union, UnionDonation,
    UnionMembership, UnionRequest, UsedCountry,
)
from . import gamestate as gs
from .combat import change_credit, notify

G = settings.GAME


def generate_union_id():
    return "".join(str(random.randint(0, 9)) for _ in range(12))


# ==================== اتحاد ====================
def create_union(player, name):
    if player.union:
        return {"ok": False, "error": "شما قبلاً عضو یک اتحاد هستید!"}
    if not (3 <= len(name) <= 20):
        return {"ok": False, "error": "نام باید بین ۳ تا ۲۰ کاراکتر باشد"}
    if Union.objects.filter(name=name).exists():
        return {"ok": False, "error": f"اتحاد '{name}' وجود دارد!"}
    union = Union.objects.create(name=name, union_id=generate_union_id(), owner=player)
    UnionMembership.objects.create(player=player, union=union)
    player.union = union
    player.save(update_fields=["union"])
    from . import events
    events.log_event("alliance_created", player, f"🤝 {player.player_name} اتحاد {name} را تاسیس کرد",
                     target_id=union.id, target_kind="union")
    return {"ok": True, "union": serialize_union(union, viewer=player)}


def serialize_union(union, viewer=None):
    members = list(union.members.all())
    return {
        "id": union.id, "name": union.name, "union_id": union.union_id,
        "owner_id": union.owner_id, "owner_name": union.owner.player_name,
        "level": union.level, "treasury": union.treasury,
        "total_deposits": union.total_deposits, "total_withdrawals": union.total_withdrawals,
        "members_count": len(members), "capacity": gs.get_union_capacity(union.level),
        "donation_limit": G["UNION_DONATION_LIMITS"].get(union.level, 20000),
        "max_item_donation": G["MAX_ITEM_DONATION"],
        "members": [{"id": m.id, "name": m.player_name, "country": m.country.name if m.country else None,
                     "score": m.score, "daily_profit": m.daily_profit} for m in members],
        "is_owner": viewer.id == union.owner_id if viewer else False,
    }


def request_join(player, union):
    if player.union:
        return {"ok": False, "error": "شما قبلاً عضو یک اتحاد هستید!"}
    if UnionRequest.objects.filter(user=player, union=union, status="pending", expires_at__gt=timezone.now()).exists():
        return {"ok": False, "error": "درخواست فعالی دارید!"}
    req = UnionRequest.objects.create(user=player, union=union,
                                      expires_at=timezone.now() + timezone.timedelta(hours=24))
    notify(union.owner, "union", "📥 درخواست عضویت جدید",
           f"{player.player_name} ({player.country.name if player.country else '—'}) درخواست عضویت در {union.name} را داد.")
    return {"ok": True, "request_id": req.id}


def approve_join(owner, request_id):
    req = UnionRequest.objects.filter(id=request_id, union__owner=owner, status="pending").first()
    if not req:
        return {"ok": False, "error": "درخواست یافت نشد"}
    if req.expires_at <= timezone.now():
        req.status = "expired"
        req.save()
        return {"ok": False, "error": "درخواست منقضی شده"}
    union = req.union
    if union.members.count() >= gs.get_union_capacity(union.level):
        return {"ok": False, "error": "ظرفیت اتحاد پر است"}
    if req.user.union:
        req.status = "rejected"
        req.save()
        return {"ok": False, "error": "کاربر قبلاً عضو اتحاد دیگری شده"}
    UnionMembership.objects.get_or_create(player=req.user, union=union)
    req.user.union = union
    req.user.save(update_fields=["union"])
    req.status = "approved"
    req.save()
    notify(req.user, "union", "✅ درخواست شما تایید شد", f"به اتحاد {union.name} اضافه شدید!")
    return {"ok": True}


def reject_join(owner, request_id):
    req = UnionRequest.objects.filter(id=request_id, union__owner=owner, status="pending").first()
    if not req:
        return {"ok": False, "error": "درخواست یافت نشد"}
    req.status = "rejected"
    req.save()
    return {"ok": True}


def kick_member(owner, union, member_id):
    if union.owner_id != owner.id:
        return {"ok": False, "error": "دسترسی ندارید!"}
    if member_id == owner.id:
        return {"ok": False, "error": "نمی‌توانید خودتان را اخراج کنید"}
    member = union.members.filter(id=member_id).first()
    if not member:
        return {"ok": False, "error": "عضو یافت نشد"}
    UnionMembership.objects.filter(player=member, union=union).delete()
    member.union = None
    member.save(update_fields=["union"])
    notify(member, "union", "🚪 اخراج از اتحاد", f"از اتحاد {union.name} اخراج شدید!")
    return {"ok": True}


def leave_union(player, union):
    if player.union_id != union.id:
        return {"ok": False, "error": "شما عضو این اتحاد نیستید!"}
    UnionMembership.objects.filter(player=player, union=union).delete()
    player.union = None
    player.save(update_fields=["union"])
    if union.owner_id == player.id:
        next_member = union.members.exclude(id=player.id).first()
        if next_member:
            union.owner = next_member
            union.save(update_fields=["owner"])
            notify(next_member, "union", "👑 لیدر جدید", f"شما لیدر جدید اتحاد {union.name} شدید!")
        else:
            union.delete()
            return {"ok": True, "deleted": True}
    return {"ok": True}


def delete_union(owner, union):
    if union.owner_id != owner.id:
        return {"ok": False, "error": "دسترسی ندارید!"}
    for m in union.members.all():
        m.union = None
        m.save(update_fields=["union"])
    union.delete()
    return {"ok": True}


def upgrade_union(owner, union):
    if union.owner_id != owner.id:
        return {"ok": False, "error": "دسترسی ندارید!"}
    level = union.level
    if level >= 5:
        return {"ok": False, "error": "حداکثر لول 5 است!"}
    price = 50000 * level
    if union.treasury < price:
        return {"ok": False, "error": f"خزانه کافی نیست! به {price:,} سکه نیاز دارید"}
    union.treasury -= price
    union.level += 1
    union.save(update_fields=["treasury", "level"])
    from .achievements import evaluate_achievements
    result = {"ok": True, "level": union.level, "capacity": gs.get_union_capacity(union.level)}
    result["achievements_unlocked"] = evaluate_achievements(owner)
    return result


def treasury_deposit(owner, union, amount):
    if union.owner_id != owner.id:
        return {"ok": False, "error": "دسترسی ندارید!"}
    if amount <= 0:
        return {"ok": False, "error": "مقدار باید بیشتر از 0 باشد!"}
    if owner.credit < amount:
        return {"ok": False, "error": "موجودی کافی نیست!"}
    change_credit(owner, -amount, "union_deposit", {"union": union.name})
    union.treasury += amount
    union.total_deposits += amount
    union.save(update_fields=["treasury", "total_deposits"])
    return {"ok": True, "treasury": union.treasury}


def treasury_withdraw(owner, union, amount):
    if union.owner_id != owner.id:
        return {"ok": False, "error": "دسترسی ندارید!"}
    if amount <= 0:
        return {"ok": False, "error": "مقدار باید بیشتر از 0 باشد!"}
    if union.treasury < amount:
        return {"ok": False, "error": "موجودی خزانه کافی نیست!"}
    union.treasury -= amount
    union.total_withdrawals += amount
    union.save(update_fields=["treasury", "total_withdrawals"])
    change_credit(owner, amount, "union_withdraw", {"union": union.name})
    return {"ok": True, "treasury": union.treasury}


def donate_credit(donor, union, recipient, amount):
    """🎁 اهدای سکه به هم‌اتحدی — سقف لول + کول‌داون ۴۸ ساعت"""
    if donor.union_id != union.id or recipient.union_id != union.id:
        return {"ok": False, "error": "هر دو طرف باید عضو اتحاد باشند"}
    last = UnionDonation.objects.filter(donor=donor, union=union).order_by("-created_at").first()
    if last:
        elapsed = (timezone.now() - last.created_at).total_seconds()
        if elapsed < G["DONATION_COOLDOWN"]:
            h = int((G["DONATION_COOLDOWN"] - elapsed) // 3600)
            m = int(((G["DONATION_COOLDOWN"] - elapsed) % 3600) // 60)
            return {"ok": False, "error": f"شما در محدودیت اهدا هستید! {h} ساعت {m} دقیقه دیگر"}
    limit = G["UNION_DONATION_LIMITS"].get(union.level, 20000)
    if amount > limit:
        return {"ok": False, "error": f"سقف اهدا در این لول: {limit:,} سکه"}
    if donor.credit < amount:
        return {"ok": False, "error": "موجودی کافی نیست!"}
    change_credit(donor, -amount, "donation_sent", {"to": recipient.player_name})
    change_credit(recipient, amount, "donation_received", {"from": donor.player_name})
    UnionDonation.objects.create(donor=donor, recipient=recipient, union=union, kind="credit", qty=amount)
    notify(recipient, "reward", "🎁 اهدا دریافت شد", f"{donor.player_name} {amount:,} سکه به شما اهدا کرد!")
    return {"ok": True}


def donate_item(donor, union, recipient, category, item_key, count):
    """📦 اهدای تجهیزات — حداکثر ۱۰۰ عدد"""
    from .economy import BUY_CATEGORIES
    if donor.union_id != union.id or recipient.union_id != union.id:
        return {"ok": False, "error": "هر دو طرف باید عضو اتحاد باشند"}
    if count < 1 or count > G["MAX_ITEM_DONATION"]:
        return {"ok": False, "error": f"سقف اهدای تجهیزات: {G['MAX_ITEM_DONATION']} عدد"}
    catalog, suffix = BUY_CATEGORIES.get(category, (None, None))
    if not catalog or item_key not in catalog:
        return {"ok": False, "error": "آیتم نامعتبر"}
    owned = gs.get_item_qty(donor, suffix, item_key)
    if owned < count:
        return {"ok": False, "error": "موجودی کافی ندارید"}
    cap = catalog[item_key].get("cap", catalog[item_key].get("max"))
    recipient_current = gs.get_item_qty(recipient, suffix, item_key)
    if cap is not None and recipient_current + count > cap:
        return {"ok": False, "error": f"گیرنده سقف {cap:,} عدد را دارد"}
    gs.set_item_qty(donor, suffix, item_key, owned - count)
    gs.add_item_qty(recipient, suffix, item_key, count)
    if category == "defense":
        gs.recalc_defense(recipient)
    else:
        gs.recalc_attack_power(recipient)
    UnionDonation.objects.create(donor=donor, recipient=recipient, union=union, kind="item",
                                 item_key=item_key, qty=count)
    notify(recipient, "reward", "📦 تجهیز دریافت شد",
           f"{donor.player_name} {count} عدد {catalog[item_key]['name']} به شما اهدا کرد!")
    return {"ok": True}


# ==================== پایگاه‌ها ====================
def build_base(player, country_name, permission_request_id=None):
    """🏗️ ساخت پایگاه — ۲۰,۰۰۰ سکه، ۳۰ دقیقه، مجوز مالک برای کشور صاحب‌دار"""
    country = Country.objects.filter(name=country_name).first()
    if not country:
        return {"ok": False, "error": "کشور یافت نشد"}
    if Base.objects.filter(country=country).exists():
        return {"ok": False, "error": f"در کشور {country_name} قبلاً پایگاه وجود دارد!"}

    reservation = UsedCountry.objects.filter(country=country).select_related("player").first()
    price = G["BASE_PRICE"]

    if reservation and reservation.player_id != player.id:
        # کشور صاحب‌دار (غیرخودی)
        if player.union and player.union_id == reservation.player.union_id:
            # هم‌اتحاد: مستقیم تا سقف ۲
            mine = Base.objects.filter(owner=player, country=country).count()
            if mine >= 2:
                return {"ok": False, "error": "در کشور هم‌اتحد بیش از ۲ پایگاه نمی‌توان ساخت!"}
        elif permission_request_id:
            req = BasePermissionRequest.objects.filter(
                id=permission_request_id, requester=player, country=country,
                status="approved").first()
            if not req or req.expires_at <= timezone.now():
                return {"ok": False, "error": "مجوز ساخت نامعتبر یا منقضی است"}
        else:
            if BasePermissionRequest.objects.filter(requester=player, status="pending",
                                                    expires_at__gt=timezone.now()).exists():
                return {"ok": False, "error": "شما قبلاً یک درخواست مجوز فعال دارید!"}
            req = BasePermissionRequest.objects.create(
                requester=player, owner=reservation.player, country=country,
                expires_at=timezone.now() + timezone.timedelta(seconds=G["BASE_PERMISSION_TIMEOUT"]))
            notify(reservation.player, "base", "🏗️ درخواست ساخت پایگاه",
                   f"{player.player_name} درخواست ساخت پایگاه در {country_name} را داده است. (۵ دقیقه اعتبار)")
            return {"ok": True, "pending_permission": True, "request_id": req.id,
                    "message": "درخواست مجوز برای مالک کشور ارسال شد"}

    # کشور خودی: حداکثر ۲ پایگاه
    if reservation and reservation.player_id == player.id:
        mine = Base.objects.filter(owner=player, country=country).count()
        if mine >= 2:
            return {"ok": False, "error": "نمی‌توانید بیش از ۲ پایگاه در کشور خودتان بسازید!"}

    # کشور بدون صاحب: ۱ پایگاه + سقف ۱۰ کشور بدون صاحبِ دارای پایگاه
    if not reservation:
        free_with_base = (Country.objects.filter(bases__isnull=False, owners__isnull=True)
                          .exclude(id=country.id).distinct().count())
        if free_with_base >= 10:
            return {"ok": False, "error": "حداکثر ۱۰ کشور بدون صاحب می‌توانند پایگاه داشته باشند!"}

    if player.credit < price:
        return {"ok": False, "error": f"موجودی کافی نیست! به {price:,} سکه نیاز دارید"}

    change_credit(player, -price, "base_build", {"country": country_name})
    base = Base.objects.create(
        owner=player, country=country,
        ready_at=timezone.now() + timezone.timedelta(seconds=G["BASE_BUILD_SECONDS"]))
    notify(player, "base", "🏗️ ساخت پایگاه آغاز شد",
           f"پایگاه {country_name} تا ۳۰ دقیقه دیگر آماده می‌شود.")
    from . import events
    events.log_event("base_built", player, f"🏕️ {player.player_name} در {country_name} پایگاه ساخت")
    from .achievements import evaluate_achievements
    result = {"ok": True, "base_id": base.id, "ready_at": base.ready_at.isoformat()}
    result["achievements_unlocked"] = evaluate_achievements(player)
    return result


def approve_base_permission(owner, request_id):
    req = BasePermissionRequest.objects.filter(id=request_id, owner=owner, status="pending").first()
    if not req:
        return {"ok": False, "error": "درخواست یافت نشد"}
    if req.expires_at <= timezone.now():
        req.status = "expired"
        req.save()
        return {"ok": False, "error": "زمان درخواست به اتمام رسیده است (بیش از ۵ دقیقه)"}
    req.status = "approved"
    req.save()
    notify(req.requester, "base", "✅ مجوز ساخت پایگاه دریافت شد",
           f"حالا می‌توانید پایگاه در {req.country.name} بسازید.")
    return {"ok": True}


def deny_base_permission(owner, request_id):
    req = BasePermissionRequest.objects.filter(id=request_id, owner=owner, status="pending").first()
    if not req:
        return {"ok": False, "error": "درخواست یافت نشد"}
    req.status = "denied"
    req.save()
    notify(req.requester, "base", "❌ درخواست رد شد", f"مالک {req.country.name} درخواست شما را رد کرد.")
    return {"ok": True}
