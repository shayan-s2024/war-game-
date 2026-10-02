# -*- coding: utf-8 -*-
"""Serializerهای کوچک — جدا از core.api.serializers برای جلوگیری از import چرخشی."""
from rest_framework import serializers

from core.models import Base


class BaseSerializer(serializers.ModelSerializer):
    country = serializers.CharField(source="country.name")
    country_emoji = serializers.CharField(source="country.emoji")
    continent = serializers.CharField(source="country.continent.key")
    owner_name = serializers.CharField(source="owner.player_name")
    is_ready = serializers.SerializerMethodField()

    class Meta:
        model = Base
        fields = ["id", "country", "country_emoji", "continent", "owner_name",
                  "built_at", "ready_at", "is_ready", "ground_troops", "air_troops",
                  "max_ground", "max_air"]

    def get_is_ready(self, obj):
        from django.utils import timezone
        return obj.ready_at <= timezone.now()
