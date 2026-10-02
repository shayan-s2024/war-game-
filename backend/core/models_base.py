# -*- coding: utf-8 -*-
"""مدل‌های دیتابیس بازی — طراحی relational کامل.

جانشین جداول SQLite نسخه تلگرام (players, player_items, used_countries, unions,
bases, union_requests, sanctions, cabinet_codes, assassination_*, hack_cooldown,
game_config, war_status, battle_logs, season_winners, bot_messages, pending_payments).
"""
from django.conf import settings
from django.db import models


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Continent(models.Model):
    key = models.CharField(max_length=32, primary_key=True)
    name = models.CharField(max_length=64)
    flag = models.CharField(max_length=8, default="🌍")
    neighbors = models.JSONField(default=list, blank=True)
    lat = models.FloatField(default=0)
    lon = models.FloatField(default=0)


class Country(models.Model):
    """۴۵۰ کشور/جزیره/سرزمین افسانه‌ای"""
    name = models.CharField(max_length=64, unique=True, db_index=True)
    command_name = models.CharField(max_length=72, unique=True, db_index=True, null=True, blank=True)
    continent = models.ForeignKey(Continent, on_delete=models.CASCADE, related_name="countries")
    emoji = models.CharField(max_length=8, default="🏳️")
    population_millions = models.FloatField(default=0)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["continent", "name"])]


def _receipt_upload_to(instance, filename):
    """نام فایل رسید تصادفی — ضد enumeration و ضد collision (اطلاعات پرداخت است)"""
    import os
    import uuid
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"receipts/{uuid.uuid4().hex}{ext}"


class Player(models.Model):
    """جانشین جدول players — یک به یک با User"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="player")
    player_name = models.CharField(max_length=30, unique=True, null=True, blank=True)
    country = models.ForeignKey(Country, null=True, blank=True, on_delete=models.SET_NULL, related_name="owners")
    credit = models.BigIntegerField(default=10000)
    defense = models.BigIntegerField(default=5000)
    attack_power = models.BigIntegerField(default=0)
    daily_profit = models.BigIntegerField(default=0)
    score = models.IntegerField(default=0)
    population = models.BigIntegerField(default=10000)
    invite_count = models.IntegerField(default=0)
    referred_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals")
    # کابینه: {key: member_name}
    cabinet = models.JSONField(default=dict, blank=True)
    cabinet_changed = models.BooleanField(default=False)
    # ویروس‌های فعال: {virus_key: {remaining_days, daily_loss, damage_base, start_date}}
    active_viruses = models.JSONField(default=dict, blank=True)
    on_fire_until = models.DateTimeField(null=True, blank=True)
    healed_today = models.IntegerField(default=0)
    heal_date = models.CharField(max_length=8, blank=True, default="")
    # اتحاد
    union = models.ForeignKey("Union", null=True, blank=True, on_delete=models.SET_NULL, related_name="member_records")
    # Activity tracking (برای DAU/WAU و online status) — فقط تا روز؛ ساعت در ActivityLog
    last_seen = models.DateTimeField(null=True, blank=True)
    # Privacy پروفایل عمومی — enforce سمت سرور
    privacy = models.JSONField(default=dict, blank=True)
    # Ban ادمین (View suspended/banned users)
    banned_at = models.DateTimeField(null=True, blank=True)
    ban_reason = models.CharField(max_length=200, blank=True, default="")

    @property
    def is_banned(self):
        return self.banned_at is not None

    class Meta:
        indexes = [
            models.Index(fields=["-score"]),
            models.Index(fields=["country"]),
        ]

    def __str__(self):
        return f"{self.player_name or self.user_id}"


class PlayerItem(models.Model):
    """جانشین player_items — شمارش هر تجهیز/ساختمان برای هر بازیکن"""
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="items")
    item_key = models.CharField(max_length=64, db_index=True)
    qty = models.BigIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["player", "item_key"], name="uniq_player_item"),
        ]
        indexes = [models.Index(fields=["player", "item_key"])]


class UsedCountry(models.Model):
    """رزرو کشورها — هر کشور فقط یک صاحب"""
    country = models.OneToOneField(Country, on_delete=models.CASCADE, primary_key=True, related_name="reservation")
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="reserved_countries")

    class Meta:
        indexes = [models.Index(fields=["player"])]


class GameConfig(models.Model):
    """جانشین game_config / war_status — key/value ماندگار"""
    key = models.CharField(max_length=64, primary_key=True)
    value = models.TextField(blank=True, default="")


class AdminUser(models.Model):
    """جانشین جدول admins — ادمین‌های ربات بر اساس آیدی تلگرام"""
    telegram_id = models.CharField(max_length=32, unique=True)
    note = models.CharField(max_length=128, blank=True, default="")


class Union(models.Model):
    """اتحاد — جانشین جدول unions"""
    name = models.CharField(max_length=20, unique=True)
    union_id = models.CharField(max_length=12, unique=True)
    owner = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="owned_unions")
    level = models.IntegerField(default=1)
    treasury = models.BigIntegerField(default=0)
    total_deposits = models.BigIntegerField(default=0)
    total_withdrawals = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(Player, through="UnionMembership", related_name="unions")

    class Meta:
        indexes = [models.Index(fields=["-treasury"])]


class UnionMembership(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    union = models.ForeignKey(Union, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["player", "union"], name="uniq_union_member")]


class UnionRequest(models.Model):
    """درخواست عضویت در اتحاد — منقضی می‌شود"""
    STATUS = [("pending", "در انتظار"), ("approved", "تایید شده"), ("rejected", "رد شده"), ("expired", "منقضی")]
    user = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="union_requests")
    union = models.ForeignKey(Union, on_delete=models.CASCADE, related_name="requests")
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()


class UnionDonation(models.Model):
    """تاریخچه اهدا در اتحاد (سکه یا تجهیز)"""
    KIND = [("credit", "سکه"), ("item", "تجهیز")]
    donor = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="donations_sent")
    recipient = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="donations_received")
    union = models.ForeignKey(Union, on_delete=models.CASCADE, related_name="donations")
    kind = models.CharField(max_length=6, choices=KIND)
    item_key = models.CharField(max_length=64, blank=True, default="")
    qty = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class Base(models.Model):
    """پایگاه نظامی — جانشین جدول bases"""
    owner = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="bases")
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="bases")
    built_at = models.DateTimeField(auto_now_add=True)
    ready_at = models.DateTimeField()
    ground_troops = models.IntegerField(default=0)
    air_troops = models.IntegerField(default=0)
    max_ground = models.IntegerField(default=5000)
    max_air = models.IntegerField(default=1000)

    class Meta:
        indexes = [models.Index(fields=["owner"]), models.Index(fields=["country"])]


class BasePermissionRequest(models.Model):
    """درخواست مجوز ساخت پایگاه در کشورِ صاحب‌دار (۵ دقیقه اعتبار)"""
    STATUS = [("pending", "در انتظار"), ("approved", "تایید شده"), ("denied", "رد شده"), ("expired", "منقضی")]
    requester = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="base_requests_sent")
    owner = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="base_requests_received")
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()


class CabinetCode(models.Model):
    """کدهای امنیتی کابینه — جانشین cabinet_codes"""
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="cabinet_codes")
    position_key = models.CharField(max_length=16)
    code = models.CharField(max_length=6)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["player", "position_key"], name="uniq_cabinet_code")]


class AssassinationInfo(models.Model):
    """کدهای سرقت‌شده برای ترور — جانشین assassination_info"""
    hacker = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="assassination_intel")
    target = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="leaked_codes")
    position_key = models.CharField(max_length=16)
    code = models.CharField(max_length=6)
    member_name = models.CharField(max_length=64, blank=True, default="")
    obtained_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["hacker", "target", "position_key"], name="uniq_assass_intel")]


class HackCooldown(models.Model):
    """کول‌داون‌های هک — defense_hackers / disabled_missiles / disabled_defenses"""
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="hack_cooldowns")
    hack_type = models.CharField(max_length=32)
    expires_at = models.DateTimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["player", "hack_type"], name="uniq_hack_cooldown")]


class Sanction(models.Model):
    """تحریم‌ها — جانشین جدول sanctions"""
    player = models.OneToOneField(Player, on_delete=models.CASCADE, related_name="sanction")
    sanction_type = models.CharField(max_length=16)
    sanctioner = models.ForeignKey(Player, null=True, on_delete=models.SET_NULL, related_name="sanctions_issued")
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    price_penalty = models.FloatField(default=0.3)


class BattleLog(models.Model):
    """تاریخچه نبردها — برای هر دو طرف ثبت می‌شود (نگهداری ۱۰ رکورد آخر هر بازیکن)"""
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="battle_logs")
    ts = models.DateTimeField(auto_now_add=True)
    text = models.TextField()

    class Meta:
        indexes = [models.Index(fields=["player", "-ts"])]


class GlobalBattleEvent(models.Model):
    """نبردها برای نمایش عمومی (خبر جهانی نسخه وب)"""
    attacker = models.ForeignKey(Player, null=True, on_delete=models.SET_NULL, related_name="+")
    defender = models.ForeignKey(Player, null=True, on_delete=models.SET_NULL, related_name="+")
    summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class AttackRecord(models.Model):
    """سهمیه حملات: ۴ حمله در ۲۴ ساعت — جانشین user_attacks"""
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="attack_records")
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["player", "at"])]


class StatementRecord(models.Model):
    """سهمیه بیانیه: ۴ در ۲۴ ساعت"""
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="statement_records")
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["player", "at"])]


class Statement(models.Model):
    """بیانیه‌ها و توییت‌ها — دیوار عمومی بازی"""
    KIND = [("statement", "بیانیه"), ("tweet", "توییت")]
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="statements")
    kind = models.CharField(max_length=10, choices=KIND)
    text = models.TextField(max_length=500)
    likes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["-created_at"])]


class WarEvent(models.Model):
    """جنگ جهانی — start/end دستی یا زمان‌بندی‌شده"""
    active = models.BooleanField(default=False)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)


class SeasonWinner(models.Model):
    """برندگان فصل‌ها"""
    season_id = models.IntegerField()
    player = models.ForeignKey(Player, null=True, on_delete=models.SET_NULL, related_name="season_wins")
    player_name = models.CharField(max_length=30)
    country = models.CharField(max_length=64, blank=True, default="")
    score = models.IntegerField(default=0)
    credit = models.BigIntegerField(default=0)
    defense = models.BigIntegerField(default=0)
    attack_power = models.BigIntegerField(default=0)
    population = models.BigIntegerField(default=0)
    rank = models.IntegerField(default=0)
    ended_at = models.DateTimeField(auto_now_add=True)


def _receipt_upload_to(instance, filename):
    """نام فایل رسید تصادفی — ضد enumeration و ضد collision (اطلاعات پرداخت است)"""
    import uuid
    import os
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"receipts/{uuid.uuid4().hex}{ext}"


class PendingPayment(models.Model):
    """رسیدهای پرداخت تومانی در انتظار تایید ادمین"""
    STATUS = [("pending", "در انتظار"), ("approved", "تایید شده"), ("rejected", "رد شده")]
    payment_id = models.CharField(max_length=12, unique=True)
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="payments")
    coins = models.BigIntegerField()
    amount_toman = models.BigIntegerField()
    receipt = models.ImageField(upload_to=_receipt_upload_to)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)


class CreditTransaction(models.Model):
    """تمام تراکنش‌های سکه — برای audit کامل اقتصادی"""
    REASONS = [
        ("purchase", "خرید از فروشگاه"), ("daily_profit", "سود روزانه"),
        ("battle_loot", "غنیمت نبرد"), ("battle_loss", "خسارت نبرد"),
        ("bomb_loot", "غنیمت بمب"), ("artillery_win", "غنیمت توپخانه"),
        ("artillery_loss", "خسارت توپخانه"), ("base_build", "ساخت پایگاه"),
        ("union_deposit", "واریز خزانه اتحاد"), ("union_withdraw", "برداشت خزانه اتحاد"),
        ("donation_sent", "اهدای سکه"), ("donation_received", "دریافت اهدا"),
        ("referral_bonus", "جایزه دعوت"), ("admin_grant", "اهدا ادمین"),
        ("admin_remove", "کسر ادمین"), ("toman_purchase", "خرید تومانی"),
        ("start_bonus", "سرمایه شروع"), ("season_reset", "ریست فصل"),
        ("achievement_reward", "جایزه دستاورد"),
    ]
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="transactions")
    amount = models.BigIntegerField()  # مثبت = ورود، منفی = خروج
    reason = models.CharField(max_length=32, choices=REASONS)
    balance_after = models.BigIntegerField()
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["player", "-created_at"])]


class PlayerAchievement(models.Model):
    """دستاورد باز‌شده توسط بازیکن — ویژه نسخه وب"""
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="achievements")
    achievement_key = models.CharField(max_length=64)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["player", "achievement_key"], name="uniq_player_achievement")]
        indexes = [models.Index(fields=["player"])]


class FleetMission(models.Model):
    """⚓ مأموریت ناوگان — ساخت از اسکله، رفت/برگشت با زمان واقعی.
    ships: {item_key: qty} شناورهای اعزامی (از موجودی کسر شده)
    ships_left: شناورهای بازگشتی بعد از نبرد
    """
    STATUS = [("outbound", "در مسیر"), ("returning", "بازگشت"), ("done", "انجام شد")]
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="fleet_missions")
    origin_country = models.ForeignKey(Country, null=True, on_delete=models.SET_NULL, related_name="fleet_origins")
    target = models.ForeignKey(Player, null=True, on_delete=models.SET_NULL, related_name="fleets_incoming")
    target_country = models.ForeignKey(Country, null=True, on_delete=models.SET_NULL, related_name="fleet_targets")
    ships = models.JSONField(default=dict)
    ships_left = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="outbound")
    departed_at = models.DateTimeField()
    arrive_at = models.DateTimeField()
    return_at = models.DateTimeField(null=True, blank=True)
    loot = models.BigIntegerField(default=0)
    summary = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["status", "arrive_at"]), models.Index(fields=["player", "-created_at"])]


class Placement(models.Model):
    """📍 جای‌گذاری سازه روی نقشه شخصی کشور — موقعیت واقعی lat/lon داخل قلمرو.
    سازه از موجودی کسر نمی‌شود (اثرات اقتصادی/دفاعی همان قدرت قبلی را دارد)؛
    placement فقط موقعیت نمایشی-تاکتیکی است و سرور اعتبار موقعیت را چک می‌کند.
    """
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="placements")
    item_key = models.CharField(max_length=64)
    suffix = models.CharField(max_length=32, default="count")
    qty = models.PositiveIntegerField(default=1)
    lat = models.FloatField()
    lon = models.FloatField()
    city_name = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["player", "item_key"])]
        constraints = [models.UniqueConstraint(
            fields=["player", "item_key", "suffix", "lat", "lon"],
            name="uniq_player_placement")]


class CountryProfile(models.Model):
    """🎨 شخصی‌سازی کشور توسط بازیکن — فقط اسم/ظاهر؛ منطق بازی دست‌نخورده.
    برای هر Player-Country یکتاست. imaginary=False یعنی کشور واقعی atlas.
    """
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="country_profiles")
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="profiles")
    display_name = models.CharField(max_length=64, blank=True, default="")
    flag_emoji = models.CharField(max_length=8, blank=True, default="")
    map_color = models.CharField(max_length=9, blank=True, default="")
    capital_name = models.CharField(max_length=64, blank=True, default="")
    capital_lat = models.FloatField(null=True, blank=True)
    capital_lon = models.FloatField(null=True, blank=True)
    government = models.CharField(max_length=32, blank=True, default="")
    imaginary = models.BooleanField(default=False)
    # 🗂 تقسیمات کشوری — [{name, kind: province|city, lat, lon}] (seed-پایدار از سرور)
    divisions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["player", "country"], name="uniq_player_country_profile")]
        indexes = [models.Index(fields=["player"])]


class DiplomaticRelation(models.Model):
    """🤝 رابطه دیپلماتیک جهت‌دار بین دو کشور (Player صاحب کشور) — Source of Truth روابط.
    relationScore/trust/tension همه server-side تکامل می‌یابند.
    """
    source = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="relations_out")
    target = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="relations_in")
    relation_score = models.IntegerField(default=0)   # -100..100
    trust = models.IntegerField(default=0)            # 0..100
    tension = models.IntegerField(default=0)          # 0..100
    last_interaction_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["source", "target"], name="uniq_diplo_pair")]
        indexes = [models.Index(fields=["source", "relation_score"])]


class Agreement(models.Model):
    """📜 توافق بین دو کشور — پیمان عدم تجاوز / اتحاد / ترانزیت / تجارت.
    state transitions فقط server-side؛ اجرای تجارت در diplomacy.execute_trade_tick.
    """
    TYPES = [
        ("non_aggression", "پیمان عدم تجاوز"), ("alliance", "اتحاد نظامی"),
        ("transit", "توافق ترانزیت"), ("trade", "توافق تجاری"),
    ]
    STATUS = [("active", "فعال"), ("terminated", "خاتمه‌یافته"), ("expired", "منقضی")]
    akey = models.CharField(max_length=80, unique=True, blank=True)  # idempotency: نوع+طرفین+روز
    type = models.CharField(max_length=20, choices=TYPES)
    initiator = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="agreements_init")
    partner = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="agreements_part")
    status = models.CharField(max_length=12, choices=STATUS, default="active")
    # trade terms: {item_key, qty, price, duration_days} — کالا از موجودی واقعی PlayerItem
    terms = models.JSONField(default=dict, blank=True)
    deliveries_done = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["initiator", "status"]), models.Index(fields=["partner", "status"])]

    def country_ids(self):
        return {self.initiator_id, self.partner_id}


class DiplomaticProposal(models.Model):
    """✉️ پیشنهاد دیپلماتیک — state machine: sent→pending→accepted/rejected/expired/cancelled.
    counter_term نبود = پیشنهاد اصلی؛ بودن = counter-offer (نسخه جدید، history حفظ).
    """
    STATUS = [
        ("sent", "ارسال‌شده"), ("pending", "در انتظار پاسخ"),
        ("accepted", "پذیرفته‌شده"), ("rejected", "رد‌شده"),
        ("expired", "منقضی"), ("cancelled", "لغوشده"),
    ]
    akey = models.CharField(max_length=80, unique=True, blank=True)  # idempotency فرمان
    type = models.CharField(max_length=20, choices=Agreement.TYPES)
    from_country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="proposals_out")
    to_country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="proposals_in")
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    terms = models.JSONField(default=dict, blank=True)
    counter_terms = models.JSONField(null=True, blank=True)  # counter proposal — نسخه جدید
    ai_review = models.JSONField(default=dict, blank=True)   # تصمیم AI + دلایل
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=["to_country", "status"]), models.Index(fields=["-created_at"])]


class Alert(models.Model):
    """🚨 هشدار تولیدی backend از وضعیت واقعی — dedup با akey، lifecycle کامل.
    فرمول اولویت configurable در settings.GAME["ALERT_WEIGHTS"].
    """
    TYPES = [
        ("resource_shortage", "کمبود منابع"), ("treasury_low", "خزانه کم"),
        ("supply_disruption", "اختلال تأمین"), ("equipment_shortage", "کمبود تجهیزات"),
        ("military_readiness", "آمادگی نظامی"), ("production_failure", "شکست تولید"),
        ("diplomatic_change", "تغییر دیپلماتیک"), ("trade_disruption", "اختلال تجارت"),
        ("infrastructure_capacity", "ظرفیت زیرساخت"), ("construction_delay", "تأخیر ساخت"),
    ]
    SEVERITIES = [("critical", "بحرانی"), ("warning", "هشدار"), ("info", "اطلاع")]
    STATUS = [("active", "فعال"), ("acknowledged", "تأیید‌شده"), ("resolved", "حل‌شده")]
    akey = models.CharField(max_length=120, db_index=True)  # TYPE:key:scope — dedup
    country = models.ForeignKey(Country, null=True, on_delete=models.CASCADE, related_name="alerts")
    player = models.ForeignKey(Player, null=True, on_delete=models.CASCADE, related_name="alerts")
    type = models.CharField(max_length=28, choices=TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITIES, default="warning")
    priority = models.IntegerField(default=0)
    title = models.CharField(max_length=128)
    description = models.TextField(blank=True, default="")
    cause = models.CharField(max_length=256, blank=True, default="")
    recommended_action = models.CharField(max_length=256, blank=True, default="")
    meta = models.JSONField(default=dict, blank=True)   # عدد/لینک entity برای Map focus
    status = models.CharField(max_length=12, choices=STATUS, default="active")
    acked_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["player", "status"]), models.Index(fields=["-priority"])]


class AdminAuditLog(models.Model):
    """Audit لاگ اکشن‌های ادمین (بند ۱۲ داشبورد: Audit Logging)"""
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="admin_actions")
    admin_name = models.CharField(max_length=64, blank=True, default="")
    action = models.CharField(max_length=64)
    target = models.CharField(max_length=128, blank=True, default="")
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["-created_at"])]


class ActivityLog(models.Model):
    """Activity Feed عمومی — ثبت یک‌خطی eventهای مهم (بند ۸ داشبورد)
    actor: Player یا None (سیستم) | kind: types زیر"""
    KINDS = [
        ("register", "ثبت‌نام"), ("login", "ورود"), ("battle_start", "شروع نبرد"),
        ("battle_end", "پایان نبرد"), ("alliance_created", "ساخت اتحاد"),
        ("large_transaction", "تراکنش بزرگ"), ("suspicious", "فعالیت مشکوک"),
        ("admin_action", "اکشن ادمین"), ("system_warning", "هشدار سیستم"),
        ("achievement", "دستاورد"), ("base_built", "ساخت پایگاه"),
        ("union_join", "عضویت در اتحاد"),
    ]
    kind = models.CharField(max_length=24, choices=KINDS)
    actor = models.ForeignKey(Player, null=True, blank=True, on_delete=models.SET_NULL, related_name="activities")
    actor_name = models.CharField(max_length=32, blank=True, default="")
    text = models.CharField(max_length=256)
    target_id = models.IntegerField(null=True, blank=True)  # drill-down: player/battle id
    target_kind = models.CharField(max_length=16, blank=True, default="")  # player|battle|union
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["-created_at"]), models.Index(fields=["kind"])]


class Notification(models.Model):
    KINDS = [
        ("battle", "نبرد"), ("bomb", "بمب"), ("hack", "هک"), ("assassination", "ترور"),
        ("union", "اتحاد"), ("base", "پایگاه"), ("virus", "ویروس"), ("reward", "جایزه"),
        ("war", "جنگ"), ("system", "سیستم"), ("payment", "پرداخت"), ("sanction", "تحریم"),
    ]
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=16, choices=KINDS, default="system")
    title = models.CharField(max_length=128)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["player", "-created_at"])]
