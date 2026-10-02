# -*- coding: utf-8 -*-
"""اتحاد و پایگاه — اکشن‌های POST با تراکنش اتمیک و ارزیابی دستاورد."""
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.models import Base, BasePermissionRequest, Player, Union, UnionRequest
from core.serializers_min import BaseSerializer
from core.services import achievements as ach_service
from core.services import social
from .common import require_player


@api_view(["GET", "POST"])
def unions(request):
    player, err = require_player(request)
    if err:
        return err
    if request.method == "GET":
        metric = request.query_params.get("metric")
        qs = list(Union.objects.prefetch_related("members").all())
        if metric == "wealth":
            qs.sort(key=lambda u: u.treasury, reverse=True)
        elif metric == "production":
            qs.sort(key=lambda u: sum(m.daily_profit for m in u.members.all()), reverse=True)
        elif metric == "power":
            qs.sort(key=lambda u: sum(m.defense + m.attack_power for m in u.members.all())
                    / max(1, u.members.count()), reverse=True)
        unions_data = [social.serialize_union(u, viewer=player) for u in qs[:20]]
        my_union = social.serialize_union(player.union, viewer=player) if player.union else None
        pending = []
        if my_union and my_union["is_owner"]:
            reqs = UnionRequest.objects.filter(union=player.union, status="pending",
                                               expires_at__gt=timezone.now())
            pending = [{"id": r.id, "user_id": r.user.id, "name": r.user.player_name,
                        "country": r.user.country.name if r.user.country else None,
                        "score": r.user.score} for r in reqs]
        return Response({"unions": unions_data, "my_union": my_union, "pending_requests": pending})

    action = request.data.get("action")
    try:
        # اکشن‌های حساس اقتصادی/ساختاری در تراکنش اتمیک — خطای نیمه‌راه rollback می‌شود
        if action in ("deposit", "withdraw", "donate_credit", "donate_item", "upgrade", "create"):
            with transaction.atomic():
                result = _dispatch(request, player, action)
                if result.get("ok"):
                    result["achievements_unlocked"] = ach_service.evaluate_achievements(player)
        else:
            result = _dispatch(request, player, action)
    except (Union.DoesNotExist, Player.DoesNotExist, TypeError, ValueError):
        return Response({"ok": False, "error": "پارامتر نامعتبر"}, status=400)
    return Response(result, status=200 if result.get("ok") else 400)


def _dispatch(request, player, action):
    if action == "create":
        return social.create_union(player, (request.data.get("name") or "").strip())
    if action == "join_request":
        return social.request_join(player, Union.objects.get(id=request.data.get("union_id")))
    if action == "approve":
        return social.approve_join(player, request.data.get("request_id"))
    if action == "reject":
        return social.reject_join(player, request.data.get("request_id"))
    if action == "leave":
        return social.leave_union(player, Union.objects.get(id=request.data.get("union_id")))
    if action == "delete":
        return social.delete_union(player, Union.objects.get(id=request.data.get("union_id")))
    if action == "upgrade":
        return social.upgrade_union(player, Union.objects.get(id=request.data.get("union_id")))
    if action == "kick":
        return social.kick_member(player, Union.objects.get(id=request.data.get("union_id")),
                                  request.data.get("member_id"))
    if action == "deposit":
        return social.treasury_deposit(player, Union.objects.get(id=request.data.get("union_id")),
                                       int(request.data.get("amount", 0)))
    if action == "withdraw":
        return social.treasury_withdraw(player, Union.objects.get(id=request.data.get("union_id")),
                                        int(request.data.get("amount", 0)))
    if action == "donate_credit":
        return social.donate_credit(player, Union.objects.get(id=request.data.get("union_id")),
                                    Player.objects.get(id=request.data.get("recipient_id")),
                                    int(request.data.get("amount", 0)))
    if action == "donate_item":
        return social.donate_item(player, Union.objects.get(id=request.data.get("union_id")),
                                  Player.objects.get(id=request.data.get("recipient_id")),
                                  request.data.get("category"), request.data.get("item"),
                                  int(request.data.get("count", 1)))
    return {"ok": False, "error": "اکشن نامعتبر"}


@api_view(["GET", "POST"])
def bases(request):
    player, err = require_player(request)
    if err:
        return err
    if request.method == "GET":
        my_bases = Base.objects.filter(owner=player).select_related("country", "country__continent")
        all_bases = Base.objects.select_related("country", "country__continent", "owner")
        pending_in = BasePermissionRequest.objects.filter(owner=player, status="pending",
                                                          expires_at__gt=timezone.now())
        pending_out = BasePermissionRequest.objects.filter(requester=player, status="pending",
                                                           expires_at__gt=timezone.now())
        return Response({
            "my_bases": BaseSerializer(my_bases, many=True).data,
            "world_bases": BaseSerializer(all_bases, many=True).data,
            "permission_requests_in": [{"id": r.id, "requester": r.requester.player_name,
                                        "country": r.country.name, "expires_at": r.expires_at.isoformat()}
                                       for r in pending_in],
            "permission_requests_out": [{"id": r.id, "country": r.country.name, "status": r.status,
                                         "expires_at": r.expires_at.isoformat()} for r in pending_out],
            "price": settings.GAME["BASE_PRICE"], "build_seconds": settings.GAME["BASE_BUILD_SECONDS"],
        })
    action = request.data.get("action")
    if action == "build":
        with transaction.atomic():
            result = social.build_base(player, (request.data.get("country") or "").strip())
        if result.get("ok"):
            result.setdefault("achievements_unlocked", ach_service.evaluate_achievements(player))
    elif action == "approve_permission":
        result = social.approve_base_permission(player, request.data.get("request_id"))
    elif action == "deny_permission":
        result = social.deny_base_permission(player, request.data.get("request_id"))
    else:
        return Response({"error": "اکشن نامعتبر"}, status=400)
    return Response(result, status=200 if result.get("ok") else 400)
