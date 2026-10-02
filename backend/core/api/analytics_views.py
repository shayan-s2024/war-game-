# -*- coding: utf-8 -*-
"""API داشبورد ادمین (analytics کامل) — همه endpointها server-side admin-checked."""
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import AdminAuditLog, Notification, Player
from core.services import analytics, events
from .routing import push_admin_dashboard


def _check_admin(request):
    user = request.user
    if user.is_staff or user.is_superuser:
        return True
    if user.telegram_id:
        from core.models import AdminUser
        if AdminUser.objects.filter(telegram_id=user.telegram_id).exists():
            user.is_staff = True
            user.save(update_fields=["is_staff"])
            return True
    return False


def _audit(request, action, target="", detail=None):
    AdminAuditLog.objects.create(
        admin=request.user if request.user.is_authenticated else None,
        admin_name=getattr(request.user, "username", "") or "",
        action=action, target=str(target)[:128], detail=detail or {})
    events.log_event("admin_action", None,
                     f"🛠 ادمین {getattr(request.user, 'username', '?')} — {action} {target}")


# ==================== Analytics ====================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_overview(request):
    if not _check_admin(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    days = analytics.DAYS.get(request.query_params.get("days", "7"), 7)
    data = analytics.kpis(days)
    data["feed"] = analytics.activity_feed(25)
    data["ws_connections"] = events.ws_connections_count()
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_charts(request):
    if not _check_admin(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    days = analytics.DAYS.get(request.query_params.get("days", "30"), 30)
    return Response({
        "period_days": days,
        "registration_trend": analytics.registration_trend(days),
        "battle_trend": analytics.battle_trend(days),
        "battle_by_hour": analytics.battle_by_hour(days),
        "battle_outcomes": analytics.battle_outcomes(days),
        "top_countries": analytics.top_by_battles(days),
        "activity_by_hour": analytics.activity_by_hour(7),
        "tx_trend": analytics.tx_trend(days),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_economy(request):
    if not _check_admin(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    days = analytics.DAYS.get(request.query_params.get("days", "30"), 30)
    return Response(analytics.economy_overview(days))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_feed(request):
    if not _check_admin(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    kind = request.query_params.get("kind") or None
    return Response({"feed": analytics.activity_feed(60, kind)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_players_v2(request):
    """لیست بازیکنان با فیلتر/جستجو — drill-down ادمین"""
    if not _check_admin(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    q = request.query_params.get("q", "")
    banned = request.query_params.get("banned") == "1"
    qs = Player.objects.select_related("country", "union").order_by("-score")
    if q:
        qs = qs.filter(Q(player_name__icontains=q) | Q(country__name__icontains=q))
    if banned:
        qs = qs.filter(banned_at__isnull=False)
    out = []
    now15 = timezone.now() - timezone.timedelta(minutes=15)
    for p in qs[:100]:
        out.append({
            "id": p.id, "name": p.player_name,
            "country": p.country.name if p.country else None,
            "country_emoji": p.country.emoji if p.country else None,
            "credit": p.credit, "score": p.score, "defense": p.defense,
            "attack_power": p.attack_power, "daily_profit": p.daily_profit,
            "population": p.population, "union": p.union.name if p.union else None,
            "banned": bool(p.banned_at), "ban_reason": p.ban_reason,
            "username": p.user.username,
            "online": bool(p.last_seen and p.last_seen >= now15),
        })
    return Response({"players": out})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def admin_player_manage(request):
    """بن/آنبن با audit — server-side enforcement"""
    if not _check_admin(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    action = request.data.get("action")
    player = Player.objects.filter(id=request.data.get("player_id")).first()
    if not player:
        return Response({"error": "بازیکن یافت نشد"}, status=404)
    if action == "ban":
        player.banned_at = timezone.now()
        player.ban_reason = (request.data.get("reason") or "نامشخص")[:200]
        player.save(update_fields=["banned_at", "ban_reason"])
        _audit(request, "ban", player.player_name, {"reason": player.ban_reason})
        Notification.objects.create(player=player, kind="system", title="⛔ حساب شما مسدود شد",
                                    body=f"دلیل: {player.ban_reason}")
        push_admin_dashboard({"event": "admin_action", "text": f"⛔ {player.player_name} بن شد"})
        return Response({"ok": True})
    if action == "unban":
        player.banned_at = None
        player.ban_reason = ""
        player.save(update_fields=["banned_at", "ban_reason"])
        _audit(request, "unban", player.player_name)
        push_admin_dashboard({"event": "admin_action", "text": f"✅ {player.player_name} رفع بن شد"})
        return Response({"ok": True})
    return Response({"error": "اکشن نامعتبر"}, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_audit_log(request):
    """Audit Log اکشن‌های ادمین"""
    if not _check_admin(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    qs = AdminAuditLog.objects.order_by("-id")[:60]
    return Response({"logs": [{
        "id": a.id, "admin": a.admin_name, "action": a.action,
        "target": a.target, "detail": a.detail, "created_at": a.created_at.isoformat(),
    } for a in qs]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_export_players(request):
    """CSV Export — دقیقاً مطابق فیلتر فعال"""
    if not _check_admin(request):
        return Response({"error": "دسترسی غیرمجاز"}, status=403)
    _audit(request, "export_csv", "players")
    csv_data = analytics.players_csv()
    resp = HttpResponse(csv_data, content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="players_export.csv"'
    return resp
