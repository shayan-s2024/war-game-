from django.urls import path

from . import admin_views, analytics_views, auth_views, profile_views, social_views, views

urlpatterns = [
    # auth
    path("auth/register/", auth_views.register),
    path("auth/login/", auth_views.login),
    path("auth/refresh/", auth_views.refresh_token),
    path("auth/telegram/", auth_views.telegram_login),
    # registration flow
    path("registration/status/", views.registration_status),
    path("registration/name/", views.register_name),
    path("registration/country/", views.register_country),
    path("countries/", views.countries),
    path("world/", views.world_state),
    path("world/borders/", views.world_borders),
    path("fleet/", views.fleet),
    path("my-map/", views.my_map),
    path("my-map/country-geometry/", views.country_geometry),
    path("my-map/country-profile/", views.country_profile),
    # Command Center / Alerts / Diplomacy
    path("command-center/", views.command_center),
    path("alerts/", views.alerts_view),
    path("diplomacy/", views.diplomacy_view),
    # cabinet
    path("cabinet/", views.cabinet_view),
    path("cabinet/set/", views.cabinet_set),
    path("cabinet/finish/", views.cabinet_finish),
    path("cabinet/change-codes/", views.cabinet_change_codes),
    # game
    path("dashboard/", views.dashboard),
    path("equipment/", views.my_equipment),
    path("achievements/", views.achievements),
    path("leaderboard/", views.leaderboard),
    path("battles/", views.battle_log),
    path("events/", views.global_events),
    path("statements/", views.statements),
    path("guide/", views.guide),
    # shop
    path("shop/catalog/", views.shop_catalog),
    path("shop/buy/", views.shop_buy),
    path("payments/request/", views.payment_request),
    # combat
    path("attack/status/", views.attack_status),
    path("attack/targets/", views.attack_targets),
    path("attack/", views.attack),
    path("attack/bomb/", views.bomb_attack),
    path("attack/artillery/", views.artillery_attack),
    # spy
    path("spy/", views.spy_overview),
    path("spy/hack/", views.hack_attack),
    path("spy/action/", views.hack_action),
    path("spy/assassinate/", views.assassinate),
    # unions
    path("unions/", social_views.unions),
    # bases
    path("bases/", social_views.bases),
    # notifications
    path("notifications/", views.notifications),
    # seasons
    path("seasons/", views.season_winners),
    # admin panel
    path("admin/stats/", admin_views.admin_stats),
    # analytics dashboard
    path("admin/analytics/", analytics_views.admin_overview),
    path("admin/charts/", analytics_views.admin_charts),
    path("admin/economy/", analytics_views.admin_economy),
    path("admin/feed/", analytics_views.admin_feed),
    path("admin/players-v2/", analytics_views.admin_players_v2),
    path("admin/player-manage/", analytics_views.admin_player_manage),
    path("admin/audit-log/", analytics_views.admin_audit_log),
    path("admin/export/players.csv", analytics_views.admin_export_players),
    # public profile
    path("players/<str:username>/", profile_views.public_profile),
    path("my/privacy/", profile_views.my_privacy),
    path("admin/players/", admin_views.admin_players),
    path("admin/player-action/", admin_views.admin_player_action),
    path("admin/war/", admin_views.admin_war),
    path("admin/broadcast/", admin_views.admin_broadcast),
    path("admin/sanction/", admin_views.admin_sanction),
    path("admin/virus/", admin_views.admin_virus),
    path("admin/registration/", admin_views.admin_registration),
    path("admin/global-reward/", admin_views.admin_global_reward),
    path("admin/payments/", admin_views.admin_payments),
    path("admin/end-season/", admin_views.admin_end_season),
    path("admin/last-winners/", admin_views.admin_last_winners),
    path("admin/admins/", admin_views.admin_admins),
    path("admin/countries/", admin_views.admin_countries),
    path("admin/country-manage/", admin_views.admin_country_manage),
    path("admin/transactions/", admin_views.admin_transactions),
]
