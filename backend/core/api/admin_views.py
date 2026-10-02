# -*- coding: utf-8 -*-
"""پنل مدیریت وب — جانشین کامل admin.py نسخه تلگرام."""
from django.conf import settings
from django.db import transaction
from django.db.models import Avg, Sum, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.gamedata import VIRUSES
from core.models import (AdminUser, AttackRecord, Base, Country, Player,
                         PendingPayment, Sanction, SeasonWinner, UsedCountry,
                         CreditTransaction, GlobalBattleEvent, Notification, AdminAuditLog)
from core.services import gamestate as gs
from core.services import country_geo


def _check(request):
    user = request.user
    if user.is_staff or user.is_superuser:
        return True
    if user.telegram_id and AdminUser.objects.filter(telegram_id=user.telegram_id).exists():
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        return True
    return False


def _broadcast(title, body, kind="system"):
    """ارسال اعلان به همه بازیکنان — DB + realtime (بدون ساخت event loop به ازای هر بازیکن)"""
    from core.api.routing import notify_player_sync
    for p in Player.objects.filter(player_name__isnull=False):
        Notification.objects.create(player=p, kind=kind, title=title, body=body)
        notify_player_sync(p.id, {"kind": kind, "title": title, "body": body})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_stats(request):
    if not _check(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    players = Player.objects.filter(player_name__isnull=False)
    total_credit = players.aggregate(s=Sum("credit"))["s"] or 0
    recent = timezone.now() - timezone.timedelta(days=1)
    active = AttackRecord.objects.filter(at__gte=recent).values("player_id").distinct().count()
    return Response({
        "players_count": players.count(),
        "total_credit": total_credit,
        "avg_score": round(players.aggregate(a=Avg("score"))["a"] or 0, 1),
        "active_24h": active,
        "countries_used": UsedCountry.objects.count(),
        "countries_total": Country.objects.count(),
        "bases": Base.objects.count(),
        "battles": GlobalBattleEvent.objects.count(),
        "pending_payments": PendingPayment.objects.filter(status="pending").count(),
        "war_active": gs.is_war_allowed(),
        "game_day": gs.get_game_day(),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_players(request):
    if not _check(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    q = request.query_params.get("q", "")
    qs = Player.objects.select_related("country", "user").order_by("-score")
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(player_name__icontains=q) | Q(country__name__icontains=q))
    out = []
    for p in qs[:200]:
        out.append({
            "id": p.id, "name": p.player_name, "country": p.country.name if p.country else None,
            "credit": p.credit, "score": p.score, "defense": p.defense,
            "attack_power": p.attack_power, "population": p.population,
            "daily_profit": p.daily_profit, "union": p.union.name if p.union else None,
            "telegram_id": p.user.telegram_id, "username": p.user.username,
        })
    return Response({"players": out})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_player_action(request):
    if not _check(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    action = request.data.get("action")
    player = Player.objects.filter(id=request.data.get("player_id")).first()
    if not player:
        return Response({"error": "بازیکن یافت نشد"}, status=404)
    if action in ("add_credit", "remove_credit"):
        try:
            amount = int(request.data.get("amount", 0))
        except (TypeError, ValueError):
            return Response({"error": "مقدار نامعتبر"}, status=400)
        if action == "add_credit":
            player.credit += amount
        else:
            player.credit = max(0, player.credit - amount)
        player.save(update_fields=["credit"])
        CreditTransaction.objects.create(
            player=player, amount=amount if action == "add_credit" else -amount,
            reason="admin_grant" if action == "add_credit" else "admin_remove",
            balance_after=player.credit)
        return Response({"ok": True, "credit": player.credit})
    if action == "delete":
        UsedCountry.objects.filter(player=player).delete()
        player.delete()
        return Response({"ok": True})
    if action in ("edit_defense", "edit_attack", "edit_score", "edit_population"):
        try:
            value = int(request.data.get("value", 0))
        except (TypeError, ValueError):
            return Response({"error": "مقدار نامعتبر"}, status=400)
        field = {"edit_defense": "defense", "edit_attack": "attack_power",
                 "edit_score": "score", "edit_population": "population"}[action]
        setattr(player, field, value)
        player.save(update_fields=[field])
        return Response({"ok": True})
    return Response({"error": "اکشن نامعتبر"}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_war(request):
    if not _check(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    from core.models import WarEvent
    action = request.data.get("action")
    if action == "start":
        ev = WarEvent.objects.filter(active=True).order_by("-id").first()
        if not ev:
            WarEvent.objects.create(active=True)
        else:
            ev.start_time = None
            ev.end_time = None
            ev.save()
        _broadcast("🔥 جنگ جهانی آغاز شد!", "همه کشورها آماده نبرد باشند!", kind="war")
        return Response({"ok": True})
    if action == "end":
        WarEvent.objects.filter(active=True).update(active=False)
        _broadcast("🕊️ جنگ جهانی به پایان رسید!", "حالت صلح برقرار شد.", kind="war")
        return Response({"ok": True})
    if action == "schedule":
        try:
            from datetime import datetime as _dt
            start = _dt.fromisoformat(request.data["start"])
            end = _dt.fromisoformat(request.data["end"])
        except (KeyError, ValueError):
            return Response({"error": "زمان نامعتبر (ISO format)"}, status=400)
        WarEvent.objects.create(active=True, start_time=start, end_time=end)
        return Response({"ok": True})
    return Response({"error": "اکشن نامعتبر"}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_broadcast(request):
    if not _check(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    text = (request.data.get("text") or "").strip()[:1000]
    if not text:
        return Response({"error": "متن خالی"}, status=400)
    _broadcast("📢 بیانیه همگانی از طرف سازمان ملل", text)
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_sanction(request):
    """🌐 سازمان ملل — تحریم سبک (۳روز/۳۰٪) یا سنگین (۷روز/۶۰٪)"""
    if not _check(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    player = Player.objects.filter(id=request.data.get("player_id")).first()
    if not player:
        return Response({"error": "بازیکن یافت نشد"}, status=404)
    if request.data.get("remove"):
        Sanction.objects.filter(player=player).delete()
        return Response({"ok": True, "removed": True})
    stype = request.data.get("type", "light")
    if stype == "light":
        days, penalty = 3, 0.3
    elif stype == "heavy":
        days, penalty = 7, 0.6
    else:
        return Response({"error": "نوع نامعتبر"}, status=400)
    sanction, _ = Sanction.objects.update_or_create(
        player=player,
        defaults={"sanction_type": stype, "sanctioner": None,
                  "start_date": timezone.now(),
                  "end_date": timezone.now() + timezone.timedelta(days=days),
                  "price_penalty": penalty})
    Notification.objects.create(
        player=player, kind="sanction",
        title=f"🌐 تحریم {'سبک' if stype == 'light' else 'سنگین'}",
        body=f"کشور شما به مدت {days} روز تحریم شد. جریمه خرید: {int(penalty*100)}٪")
    return Response({"ok": True, "end_date": sanction.end_date.isoformat()})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_virus(request):
    """🦠 اعطای ویروس به بازیکن"""
    if not _check(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    player = Player.objects.filter(id=request.data.get("player_id")).first()
    vkey = request.data.get("virus")
    if not player or vkey not in VIRUSES:
        return Response({"error": "پارامتر نامعتبر"}, status=400)
    player.active_viruses = {**(player.active_viruses or {}), vkey: {
        "remaining_days": settings.GAME["VIRUS_DURATION_DAYS"],
        "daily_loss": VIRUSES[vkey]["daily_loss"],
        "damage_base": VIRUSES[vkey]["damage_base"],
        "start_date": timezone.now().timestamp()}}
    player.save(update_fields=["active_viruses"])
    Notification.objects.create(
        player=player, kind="virus", title=f"⚠️ {VIRUSES[vkey]['name']} شناسایی شد!",
        body=f"ضرر روزانه: {VIRUSES[vkey]['daily_loss']} | مدت: {settings.GAME['VIRUS_DURATION_DAYS']} روز")
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_registration(request):
    """🔒/🔓 بستن یا باز کردن ثبت‌نام"""
    if not _check(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    action = request.data.get("action")
    if action == "close":
        gs.set_config("registration_closed", "1")
    elif action == "open":
        gs.set_config("registration_closed", "0")
    else:
        return Response({"error": "اکشن نامعتبر"}, status=400)
    return Response({"ok": True, "closed": gs.get_config("registration_closed") == "1"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_global_reward(request):
    """🎁 جایزه همگانی — سکه یا تجهیز"""
    if not _check(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    reward_type = request.data.get("reward_type", "credit")
    try:
        amount = int(request.data.get("amount", 0))
    except (TypeError, ValueError):
        return Response({"error": "مقدار نامعتبر"}, status=400)
    if reward_type == "credit" and amount > 0:
        for p in Player.objects.filter(player_name__isnull=False):
            p.credit += amount
            p.save(update_fields=["credit"])
            CreditTransaction.objects.create(player=p, amount=amount, reason="admin_grant",
                                             balance_after=p.credit)
        _broadcast("🎁 جایزه همگانی", f"{amount:,} سکه به همه بازیکنان اهدا شد!", kind="reward")
        return Response({"ok": True})
    if reward_type == "item":
        from core.services.economy import BUY_CATEGORIES
        category = request.data.get("category")
        item_key = request.data.get("item")
        catalog, suffix = BUY_CATEGORIES.get(category, (None, None))
        if not catalog or item_key not in catalog:
            return Response({"error": "آیتم نامعتبر"}, status=400)
        for p in Player.objects.filter(player_name__isnull=False):
            gs.add_item_qty(p, suffix, item_key, amount)
            if category == "defense":
                gs.recalc_defense(p)
            else:
                gs.recalc_attack_power(p)
        _broadcast("🎁 جایزه همگانی", f"{amount} عدد {catalog[item_key]['name']} به همه اهدا شد!",
                   kind="reward")
        return Response({"ok": True})
    return Response({"error": "نوع نامعتبر"}, status=400)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def admin_payments(request):
    if not _check(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    if request.method == "GET":
        qs = PendingPayment.objects.select_related("player").order_by("-id")[:100]
        return Response({"payments": [{
            "id": p.id, "payment_id": p.payment_id, "player": p.player.player_name,
            "coins": p.coins, "amount": p.amount_toman, "status": p.status,
            "receipt": p.receipt.url if p.receipt else None,
            "created_at": p.created_at.isoformat(),
        } for p in qs]})
    payment = PendingPayment.objects.filter(id=request.data.get("id")).first()
    if not payment:
        return Response({"error": "یافت نشد"}, status=404)
    action = request.data.get("action")
    if action == "approve":
        payment.status = "approved"
        payment.reviewed_by = request.user
        payment.reviewed_at = timezone.now()
        payment.save()
        payment.player.credit += payment.coins
        payment.player.save(update_fields=["credit"])
        CreditTransaction.objects.create(player=payment.player, amount=payment.coins,
                                         reason="toman_purchase", balance_after=payment.player.credit,
                                         meta={"payment_id": payment.payment_id})
        Notification.objects.create(player=payment.player, kind="payment",
                                    title="✅ پرداخت تایید شد",
                                    body=f"{payment.coins:,} سکه به حساب شما اضافه شد.")
        return Response({"ok": True})
    if action == "reject":
        payment.status = "rejected"
        payment.reviewed_by = request.user
        payment.save()
        Notification.objects.create(player=payment.player, kind="payment", title="❌ پرداخت رد شد",
                                    body="رسید شما تایید نشد. با پشتیبانی تماس بگیرید.")
        return Response({"ok": True})
    return Response({"error": "اکشن نامعتبر"}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def admin_end_season(request):
    """🏁 پایان فصل — ثبت برندگان + ریست کامل (مطابق admin_end_season_confirm)"""
    if not _check(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    season_id = SeasonWinner.objects.order_by("-season_id") \
        .values_list("season_id", flat=True).first() or 0
    season_id += 1
    top = Player.objects.filter(player_name__isnull=False).order_by("-score")[:10]
    winners = []
    for rank, p in enumerate(top, 1):
        SeasonWinner.objects.create(
            season_id=season_id, player=p, player_name=p.player_name,
            country=p.country.name if p.country else "",
            score=p.score, credit=p.credit, defense=p.defense,
            attack_power=p.attack_power, population=p.population, rank=rank)
        winners.append({"rank": rank, "name": p.player_name, "score": p.score})
    # ریست کامل: حذف رکوردهای بازی (کاربران Django حفظ می‌شوند)
    from core.models import (AssassinationInfo, AttackRecord, BattleLog, CabinetCode,
                             HackCooldown, PlayerItem, Statement, StatementRecord,
                             Union, UnionDonation, UnionMembership, UnionRequest,
                             UsedCountry, BasePermissionRequest)
    UnionDonation.objects.all().delete()
    UnionRequest.objects.all().delete()
    UnionMembership.objects.all().delete()
    Union.objects.all().delete()
    BasePermissionRequest.objects.all().delete()
    PlayerItem.objects.all().delete()
    UsedCountry.objects.all().delete()
    Base.objects.all().delete()
    CabinetCode.objects.all().delete()
    AssassinationInfo.objects.all().delete()
    HackCooldown.objects.all().delete()
    AttackRecord.objects.all().delete()
    StatementRecord.objects.all().delete()
    Statement.objects.all().delete()
    BattleLog.objects.all().delete()
    Sanction.objects.all().delete()
    Player.objects.all().delete()
    gs.set_config("registration_closed", "0")
    gs.set_config("game_start_date", str(timezone.now().timestamp()))
    return Response({"ok": True, "season_id": season_id, "winners": winners})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_last_winners(request):
    season_id = SeasonWinner.objects.order_by("-season_id") \
        .values_list("season_id", flat=True).first()
    if not season_id:
        return Response({"winners": []})
    winners = SeasonWinner.objects.filter(season_id=season_id).order_by("rank")
    return Response({"season_id": season_id, "winners": [
        {"rank": w.rank, "name": w.player_name, "country": w.country, "score": w.score}
        for w in winners]})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def admin_admins(request):
    """👥 مدیریت ادمین‌ها بر اساس آیدی تلگرام"""
    if not _check(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    if request.method == "GET":
        return Response({"admins": list(AdminUser.objects.values_list("telegram_id", flat=True))})
    action = request.data.get("action")
    tg_id = str(request.data.get("telegram_id", ""))
    if action == "add" and tg_id:
        AdminUser.objects.get_or_create(telegram_id=tg_id)
        return Response({"ok": True})
    if action == "remove" and tg_id:
        if tg_id == settings.GAME["MAIN_ADMIN_TELEGRAM_ID"]:
            return Response({"error": "ادمین اصلی قابل حذف نیست"}, status=400)
        AdminUser.objects.filter(telegram_id=tg_id).delete()
        return Response({"ok": True})
    return Response({"error": "اکشن نامعتبر"}, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_transactions(request):
    if not _check(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    qs = CreditTransaction.objects.select_related("player").order_by("-id")[:100]
    return Response({"transactions": [{
        "id": t.id, "player": t.player.player_name, "amount": t.amount,
        "reason": t.reason, "balance_after": t.balance_after,
        "created_at": t.created_at.isoformat(),
    } for t in qs]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_countries(request):
    """Directory of countries + command aliases + live ownership for admins."""
    if not _check(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    q = (request.query_params.get("q") or "").strip()
    qs = Country.objects.select_related("continent").order_by("continent__key", "name")
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(command_name__icontains=q)
            | Q(reservation__player__player_name__icontains=q)
            | Q(reservation__player__user__username__icontains=q)
        ).distinct()
    rows = []
    for c in qs[:500]:
        owner = UsedCountry.objects.filter(country=c).select_related("player").first()
        rows.append({
            "id": c.id, "name": c.name, "command_name": c.command_name, "emoji": c.emoji,
            "continent": c.continent.name, "imaginary": country_geo.is_imaginary_country(c.name),
            "lat": c.lat, "lon": c.lon,
            "owner_id": owner.player_id if owner else None,
            "owner": owner.player.player_name if owner else None,
            "owner_username": owner.player.user.username if owner else None,
        })
    return Response({"countries": rows, "total": Country.objects.count()})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_country_manage(request):
    """Admin country directory actions: rename alias, move island, release or assign."""
    if not _check(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    action = request.data.get("action")
    country = Country.objects.filter(id=request.data.get("country_id")).first()
    if not country:
        return Response({"error": "کشور یافت نشد"}, status=404)

    if action == "update":
        updates = {}
        if "command_name" in request.data:
            alias = str(request.data.get("command_name") or "").strip().lower()
            if not alias or not alias.replace("-", "").replace("_", "").isalnum():
                return Response({"error": "نام فرمان فقط حروف لاتین، عدد، - یا _ باشد"}, status=400)
            if Country.objects.filter(command_name=alias).exclude(id=country.id).exists():
                return Response({"error": "این نام فرمان قبلاً استفاده شده"}, status=409)
            updates["command_name"] = alias[:72]
        if "lat" in request.data or "lon" in request.data:
            try:
                lat = float(request.data.get("lat", country.lat))
                lon = float(request.data.get("lon", country.lon))
            except (TypeError, ValueError):
                return Response({"error": "مختصات نامعتبر"}, status=400)
            if not (-85 <= lat <= 85 and -180 <= lon <= 180):
                return Response({"error": "مختصات خارج از محدوده"}, status=400)
            updates.update(lat=lat, lon=lon)
        if not updates:
            return Response({"error": "تغییری ارسال نشده"}, status=400)
        for k, v in updates.items():
            setattr(country, k, v)
        country.save(update_fields=list(updates.keys()))
        AdminAuditLog.objects.create(admin=request.user, admin_name=request.user.username,
                                     action="country_update", target=country.name, detail=updates)
        return Response({"ok": True})

    if action == "release":
        uc = UsedCountry.objects.filter(country=country).select_related("player").first()
        if uc:
            player = uc.player
            if player.country_id == country.id:
                player.country = None
                player.save(update_fields=["country"])
            uc.delete()
            AdminAuditLog.objects.create(admin=request.user, admin_name=request.user.username,
                                         action="country_release", target=country.name, detail={"player": player.player_name})
        return Response({"ok": True})

    if action == "assign":
        player_query = str(request.data.get("player") or "").strip()
        player = Player.objects.select_related("user").filter(
            Q(player_name__iexact=player_query) | Q(user__username__iexact=player_query)
        ).first()
        if not player:
            return Response({"error": "بازیکن پیدا نشد"}, status=404)
        with transaction.atomic():
            old = UsedCountry.objects.filter(country=country).select_related("player").first()
            if old and old.player_id != player.id:
                if old.player.country_id == country.id:
                    old.player.country = None
                    old.player.save(update_fields=["country"])
                old.delete()
            old_for_player = UsedCountry.objects.filter(player=player).exclude(country=country).first()
            if old_for_player:
                old_country = old_for_player.country
                if player.country_id == old_country.id:
                    player.country = None
                old_for_player.delete()
            UsedCountry.objects.update_or_create(country=country, defaults={"player": player})
            player.country = country
            player.save(update_fields=["country"])
        AdminAuditLog.objects.create(admin=request.user, admin_name=request.user.username,
                                     action="country_assign", target=country.name, detail={"player": player.player_name})
        return Response({"ok": True, "player": player.player_name, "country": country.name})

    return Response({"error": "اکشن نامعتبر"}, status=400)
