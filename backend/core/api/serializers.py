# -*- coding: utf-8 -*-
"""Serializerهای API."""
from rest_framework import serializers

from core.models import (BattleLog, GlobalBattleEvent, Notification, Player,
                         Statement, UnionRequest)
from core.serializers_min import BaseSerializer  # noqa: F401 — re-export برای سازگاری


class PlayerSummarySerializer(serializers.ModelSerializer):
    country = serializers.SerializerMethodField()
    continent = serializers.SerializerMethodField()
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Player
        fields = ["id", "player_name", "username", "country", "continent", "score", "credit",
                  "defense", "attack_power", "daily_profit", "population"]

    def get_country(self, obj):
        return obj.country.name if obj.country else None

    def get_continent(self, obj):
        return obj.country.continent.key if obj.country else None


class BattleLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = BattleLog
        fields = ["id", "ts", "text"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "body", "is_read", "created_at"]


class StatementSerializer(serializers.ModelSerializer):
    player_name = serializers.CharField(source="player.player_name", read_only=True)
    username = serializers.CharField(source="player.user.username", read_only=True)
    country = serializers.SerializerMethodField()

    class Meta:
        model = Statement
        fields = ["id", "kind", "text", "likes", "created_at", "player_name", "username", "country"]

    def get_country(self, obj):
        return obj.player.country.name if obj.player.country else None


class GlobalEventSerializer(serializers.ModelSerializer):
    attacker = serializers.CharField(source="attacker.player_name", read_only=True)
    defender = serializers.CharField(source="defender.player_name", read_only=True)

    class Meta:
        model = GlobalBattleEvent
        fields = ["id", "attacker", "defender", "summary", "created_at"]
