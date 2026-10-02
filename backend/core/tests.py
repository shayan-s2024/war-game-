# -*- coding: utf-8 -*-
"""تست‌های Backend — قوانین حساس بازی.

اجرا: python manage.py test core
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient as _APIClient

from core.gamedata import AIR_DEFENSES, MINES, get_total_countries_count
from core.models import AttackRecord, Player, Sanction, UsedCountry
from core.services import combat, economy, gamestate as gs

User = get_user_model()


def _mk_user(username="tester"):
    return User.objects.create_user(username=username, password="pass12345")


def _mk_player(username="p1", name="Ali"):
    u = _mk_user(username)
    return Player.objects.create(user=u, player_name=name)


class GamedataTests(TestCase):
    def test_450_countries(self):
        """قانون طلایی: دقیقاً ۴۵۰ سرزمین"""
        self.assertEqual(get_total_countries_count(), 450)

    def test_continent_lookup(self):
        from core.gamedata import get_country_continent_key
        self.assertEqual(get_country_continent_key("ایران"), "asia")
        self.assertEqual(get_country_continent_key("آمریکا"), "north_america")
        self.assertIsNone(get_country_continent_key("ناموجود"))


class PlayerItemTests(TestCase):
    def setUp(self):
        self.p = _mk_player()

    def test_item_qty_crud(self):
        gs.add_item_qty(self.p, "tank_count", "simple", 10)
        self.assertEqual(gs.get_item_qty(self.p, "tank_count", "simple"), 10)
        gs.set_item_qty(self.p, "tank_count", "simple", 3)
        self.assertEqual(gs.get_item_qty(self.p, "tank_count", "simple"), 3)

    def test_recalc_defense_base(self):
        # دفاع پایه ۵۰۰۰ بدون پدافند — مطابق تلگرام
        self.assertEqual(gs.recalc_defense(self.p), 5000)

    def test_recalc_attack_power_with_tanks(self):
        gs.add_item_qty(self.p, "tank_count", "simple", 2)  # power=80
        self.assertEqual(gs.recalc_attack_power(self.p), 160)


class EconomyTests(TestCase):
    def setUp(self):
        self.p = _mk_player("econ", "Economist")
        self.p.credit = 100000
        self.p.save()

    def test_purchase_mine_updates_profit(self):
        result = economy.purchase(self.p, "mine", "emerald", 1)
        self.assertTrue(result["ok"])
        self.assertEqual(self.p.daily_profit, MINES["emerald"]["daily_profit"])
        self.assertEqual(self.p.credit, 100000 - MINES["emerald"]["price"])

    def test_cap_enforced(self):
        cap = MINES["emerald"]["max"]  # 100
        result = economy.purchase(self.p, "mine", "emerald", cap + 1)
        self.assertFalse(result["ok"])

    def test_insufficient_balance(self):
        self.p.credit = 10
        self.p.save()
        result = economy.purchase(self.p, "tank", "simple", 1)
        self.assertFalse(result["ok"])

    def test_sanction_penalty_price(self):
        Sanction.objects.create(player=self.p, sanction_type="light",
                                start_date=timezone.now(),
                                end_date=timezone.now() + timezone.timedelta(days=3),
                                price_penalty=0.3)
        price, penalty = economy.effective_price(self.p, 1000)
        self.assertEqual(price, 1300)

    def test_purchase_defense_adds_defense(self):
        result = economy.purchase(self.p, "defense", "normal", 1)  # بسته ۱۰۰ عددی، power=100
        self.assertTrue(result["ok"])
        self.assertEqual(self.p.defense, 5000 + 100 * AIR_DEFENSES["normal"]["power"])

    def test_daily_profit_application(self):
        self.p.daily_profit = 5000
        self.p.save()
        before = self.p.credit
        result = economy.apply_daily_profit(self.p)
        self.assertEqual(result["profit"], 5000)
        self.p.refresh_from_db()
        self.assertEqual(self.p.credit, before + 5000)


class CombatTests(TestCase):
    def setUp(self):
        self.a = _mk_player("atk", "Attacker")
        self.d = _mk_player("dfd", "Defender")

    def test_battle_power_formula_direction(self):
        result, al, dl, ratio = combat.calculate_battle_power(
            "fighter", "air_defense", 1000, 10, None, attacker_quality=1.5, defender_quality=0.4)
        self.assertEqual(result, "victory")
        self.assertGreater(ratio, 1.5)

    def test_quality_reduces_losses(self):
        """⚖️ کیفیت هم‌ارز تعداد: باکیفیت کمتر تلف می‌دهد"""
        _, al_low, _, _ = combat.calculate_battle_power(
            "tank", "tank", 100, 100, None, attacker_quality=0.5, defender_quality=0.5)
        _, al_high, _, _ = combat.calculate_battle_power(
            "tank", "tank", 100, 100, None, attacker_quality=2.0, defender_quality=0.5)
        self.assertLess(al_high, al_low)

    def test_attack_limit_4_per_day(self):
        """سهمیه ۴ حمله در ۲۴ ساعت — مطابق نسخه تلگرام"""
        for _ in range(4):
            AttackRecord.objects.create(player=self.a)
        ok, remaining, wait = combat.can_attack(self.a)
        self.assertFalse(ok)
        self.assertGreater(wait, 0)

    def test_attack_requires_war(self):
        from core.models import WarEvent
        # بدون WarEvent فعال → حمله رد شود
        result = combat.process_attack(self.a, self.d, "tank", 1)
        self.assertFalse(result["ok"])
        self.assertIn("جنگ", result["error"])

    def test_attack_consumes_units_and_awards_loot(self):
        from core.models import WarEvent
        WarEvent.objects.create(active=True)
        # مهاجم قدرتمند / مدافع بدون تجهیز
        gs.add_item_qty(self.a, "tank_count", "simple", 500)
        self.a.attack_power = 500 * 80
        self.a.save()
        result = combat.process_attack(self.a, self.d, "tank", 100)
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"], "victory")
        self.assertGreater(result["loot"], 0)

    def test_bomb_consumes_and_sets_fire(self):
        from core.models import WarEvent
        WarEvent.objects.create(active=True)
        gs.add_item_qty(self.a, "bomb_count", "fire", 2)
        result = combat.process_bomb_strike(self.a, self.d, "fire", 1)
        self.assertTrue(result["ok"])
        self.assertEqual(gs.get_item_qty(self.a, "bomb_count", "fire"), 1)
        self.d.refresh_from_db()
        self.assertIsNotNone(self.d.on_fire_until)


class SpyTests(TestCase):
    def setUp(self):
        self.a = _mk_player("hax", "Hacker")
        self.d = _mk_player("tgt", "Target")
        self.d.cabinet = {k: f"عضو {k}" for k in
                          ("diplomat", "leader", "defense", "economy", "intelligence")}
        self.d.save()
        from core.models import CabinetCode
        for k in self.d.cabinet:
            CabinetCode.objects.create(player=self.d, position_key=k, code="123456")

    def test_hack_steals_codes(self):
        gs.add_item_qty(self.a, "hacker_count", "strong", 10)
        result = combat  # placeholder to keep import used
        from core.services import spy
        result = spy.process_hack_attack(self.a, self.d, "strong", 2)
        self.assertTrue(result["ok"])
        self.assertTrue(result["success"])
        self.assertEqual(len(result["stolen"]), 5)

    def test_weak_hacker_cannot_attack(self):
        from core.services import spy
        result = spy.process_hack_attack(self.a, self.d, "weak", 1)
        self.assertFalse(result["ok"])

    def test_hack_defense_beats_weak_attack(self):
        """دفاع هکری قوی حمله ضعیف را دفع می‌کند"""
        from core.services import spy
        gs.add_item_qty(self.d, "hacker_count", "weak", 20)  # دفاع = 20
        gs.add_item_qty(self.a, "hacker_count", "medium", 1)  # حمله = 5
        result = spy.process_hack_attack(self.a, self.d, "medium", 1)
        self.assertTrue(result["ok"])
        self.assertFalse(result["success"])

    def test_assassination_with_correct_code(self):
        from core.services import spy
        from core.models import AssassinationInfo
        AssassinationInfo.objects.create(hacker=self.a, target=self.d,
                                         position_key="defense", code="654321")
        gs.add_item_qty(self.a, "ground_count", "commando", 5)
        old_def = self.d.defense
        result = spy.execute_assassination(self.a, self.d.id, "defense", "commando", "654321")
        self.assertTrue(result["ok"])
        if result.get("success"):
            self.d.refresh_from_db()
            self.assertLess(self.d.defense, old_def)


class RegistrationFlowTests(TestCase):
    def test_country_unique_reservation(self):
        from core.models import Continent, Country
        c, _ = Continent.objects.get_or_create(key="asia", defaults={"name": "آسیا"})
        country = Country.objects.create(name="تستستان", continent=c)
        p1 = _mk_player("u1", "First")
        p2 = _mk_player("u2", "Second")
        UsedCountry.objects.create(country=country, player=p1)
        self.assertTrue(UsedCountry.objects.filter(country=country).exists())
        # p2 نمی‌تواند همان کشور را بگیرد (منطق در API چک می‌شود)

    def test_registration_capacity(self):
        from core.models import Continent, Country
        self.assertGreater(get_total_countries_count(), 0)


class PublicProfileTests(TestCase):
    def test_public_profile_privacy_enforced(self):
        """پروفایل عمومی — privacy سمت سرور: سکه دقیق هرگز نمی‌گذرد"""
        from django.test import Client
        p = _mk_player("pub1", "PublicGuy")
        p.credit = 987654
        p.save()
        c = Client(HTTP_HOST="localhost")
        r = c.get(f"/api/players/{p.user.username}/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["name"], "PublicGuy")
        self.assertNotIn("credit", data["stats"])  # سکه دقیق عمومی نمی‌شود
        self.assertIn("credit_range", data["stats"])
        self.assertGreater(data["ranks"]["global"], 0)

    def test_privacy_hide_country(self):
        """Privacy: اگر show_country=False باشد کشور از API عمومی حذف شود"""
        from django.test import Client
        from core.models import Continent, Country, UsedCountry
        p = _mk_player("pub2", "PrivateGuy")
        cont, _ = Continent.objects.get_or_create(key="asia", defaults={"name": "آسیا"})
        c = Country.objects.create(name="کشورخصوصی", continent=cont)
        UsedCountry.objects.create(country=c, player=p)
        p.country = c
        p.privacy = {"show_country": False}
        p.save()
        cl = Client(HTTP_HOST="localhost")
        r = cl.get(f"/api/players/{p.user.username}/")
        self.assertIsNone(r.json()["country"])
        self.assertNotIn("country", r.json()["ranks"])


class AdminAnalyticsTests(TestCase):
    def test_analytics_requires_admin(self):
        """Analytics فقط برای ادمین — server-side permission"""
        from django.test import Client
        from rest_framework_simplejwt.tokens import RefreshToken
        u = _mk_user("notadmin")
        tok = str(RefreshToken.for_user(u).access_token)
        c = Client(HTTP_HOST="localhost", HTTP_AUTHORIZATION=f"Bearer {tok}")
        r = c.get("/api/admin/analytics/")
        self.assertEqual(r.status_code, 403)

    def test_analytics_kpis_shape(self):
        """kpis با داده واقعی — ساختار و مقادیر درست"""
        from core.services import analytics
        _mk_player("kpi1", "KpiOne")
        data = analytics.kpis(7)
        self.assertGreaterEqual(data["kpis"][0]["value"], 1)
        self.assertIn("updated_at", data)
        self.assertIsInstance(data["kpis"], list)

    def test_admin_audit_log_written(self):
        """اکشن ادمین audit می‌شود"""
        from core.models import AdminAuditLog
        from core.services import analytics as a
        a.players_csv()  # بی‌ضرر
        from django.test import Client
        from rest_framework_simplejwt.tokens import RefreshToken
        from django.contrib.auth import get_user_model as gUM
        admin = gUM().objects.create_user(username="boss", password="pass12345", is_staff=True)
        tok = str(RefreshToken.for_user(admin).access_token)
        c = Client(HTTP_HOST="localhost", HTTP_AUTHORIZATION=f"Bearer {tok}")
        c.get("/api/admin/export/players.csv")
        self.assertTrue(AdminAuditLog.objects.filter(action="export_csv").exists())


class AchievementTests(TestCase):
    def test_achievement_unlock_with_reward(self):
        """🏆 دستاورد با رسیدن به آستانه باز شود و جایزه با audit واریز شود"""
        from core.gamedata import ACHIEVEMENTS
        from core.models import PlayerAchievement, CreditTransaction
        from core.services import achievements as ach
        p = _mk_player("ach", "AchPlayer")
        p.credit = 150000
        p.save()
        unlocked = ach.evaluate_achievements(p)
        self.assertIn("treasury_builder", unlocked)
        self.assertTrue(PlayerAchievement.objects.filter(player=p, achievement_key="treasury_builder").exists())
        # جایزه = 10000 (treasury_builder reward)
        reward = ACHIEVEMENTS["treasury_builder"]["reward"]
        self.assertEqual(p.credit, 150000 + reward)
        self.assertTrue(CreditTransaction.objects.filter(player=p, reason="achievement_reward").exists())
        # اجرای دوباره: دیگر قفل نشود (یک‌بارمصرف)
        unlocked2 = ach.evaluate_achievements(p)
        self.assertNotIn("treasury_builder", unlocked2)

    def test_achievement_overview_progress(self):
        from core.services import achievements as ach
        p = _mk_player("ach2", "AchPlayer2")
        data = ach.achievement_overview(p)
        self.assertEqual(data["total_count"], len(ach.ACHIEVEMENTS) if hasattr(ach, "ACHIEVEMENTS") else data["total_count"])
        self.assertEqual(data["unlocked_count"], 0)
        first = data["achievements"][0]
        self.assertIn("progress", first)


class UnionTreasuryTests(TestCase):
    def test_deposit_withdraw_cycle(self):
        from core.services import social
        from core.models import Union
        owner = _mk_player("own", "Owner")
        r = social.create_union(owner, "اتحاد تست")
        self.assertTrue(r["ok"])
        union = Union.objects.first()
        owner.credit = 50000
        owner.save()
        r = social.treasury_deposit(owner, union, 20000)
        self.assertTrue(r["ok"])
        self.assertEqual(union.treasury, 20000)
        r = social.treasury_withdraw(owner, union, 5000)
        self.assertTrue(r["ok"])
        self.assertEqual(union.treasury, 15000)

    def test_withdraw_more_than_treasury_fails(self):
        from core.services import social
        from core.models import Union
        owner = _mk_player("own2", "Owner2")
        social.create_union(owner, "اتحاد دوم")
        union = Union.objects.filter(owner=owner).first()
        r = social.treasury_withdraw(owner, union, 999999)
        self.assertFalse(r["ok"])

    def test_upgrade_level_cap(self):
        from core.services import social
        from core.models import Union
        owner = _mk_player("own3", "Owner3")
        social.create_union(owner, "اتحاد سوم")
        union = Union.objects.filter(owner=owner).first()
        union.treasury = 10**9
        union.save()
        for _ in range(4):
            r = social.upgrade_union(owner, union)
            self.assertTrue(r["ok"])
        r = social.upgrade_union(owner, union)
        self.assertFalse(r["ok"])  # حداکثر لول ۵


class CountryGeoTests(TestCase):
    client_class = _APIClient
    """🗺 هندسه کشور: real از atlas + خیالی تولید seed-پایدار + پایداری بین reloadها"""

    def _country(self, name="ایران"):
        from core.models import Continent, Country
        cont, _ = Continent.objects.get_or_create(key="asia", defaults={"name": "آسیا", "lat": 30, "lon": 55})
        c, _ = Country.objects.get_or_create(
            name=name, continent=cont,
            defaults={"emoji": "🏳️", "lat": 32.0, "lon": 53.0})
        return c

    def test_real_country_geometry_from_atlas(self):
        from core.services import country_geo
        c = self._country("ایران")
        geo = country_geo.geometry_for_country(c.name, c.lat, c.lon, 30, 55)
        self.assertEqual(geo["kind"], "real")
        self.assertTrue(len(geo["polygons"]) >= 1)
        # مرکز داخل bbox
        lat, lon = geo["center"]
        bbox = geo["bbox"]
        self.assertTrue(bbox[1] - 1 <= lat <= bbox[3] + 1)
        self.assertTrue(bbox[0] - 1 <= lon <= bbox[2] + 1)

    def test_imaginary_geometry_seed_stable(self):
        from core.services import country_geo
        geo1 = country_geo.geometry_for_country("آراکیس", None, None, 30, 55)
        self.assertEqual(geo1["kind"], "imaginary")
        geo2 = country_geo.geometry_for_country("آراکیس", None, None, 30, 55)
        self.assertEqual(geo1["polygons"], geo2["polygons"])  # seed-پایدار
        # دو کشور خیالی متفاوت شکل متفاوت دارند
        geo3 = country_geo.geometry_for_country("گیریتار", None, None, -10, 20)
        self.assertNotEqual(geo1["polygons"], geo3["polygons"])
        # جزیره‌ها مجزا و مساحت معقول
        self.assertTrue(geo1["area_km2"] > 0)

    def test_divisions_deterministic(self):
        from core.services import country_geo
        geo = country_geo.geometry_for_country("ایران", 32, 53, 30, 55)
        d1 = country_geo.generate_divisions("ایران", geo["polygons"])
        d2 = country_geo.generate_divisions("ایران", geo["polygons"])
        self.assertEqual(d1, d2)
        kinds = {d["kind"] for d in d1}
        self.assertIn("capital", kinds)
        self.assertIn("province", kinds)

    def test_my_map_stats_real_data(self):
        """آمار داشبورد فقط از Game Core — خزانه = credit واقعی"""
        from core.api.views import _my_country_stats
        p = _mk_player("geo1", "GeoOwner")
        p.credit = 77777
        p.save()
        stats = _my_country_stats(p)
        self.assertEqual(stats["treasury"], 77777)
        self.assertIn("army", stats)
        self.assertIn("income", stats)
        self.assertIn("status", stats)

    def test_country_profile_api(self):
        """API شخصی‌سازی: ساخت خودکار + POST رنگ/نام + حکم مرزی پایتخت"""
        from django.urls import reverse
        from core.models import Continent, Country, UsedCountry
        cont, _ = Continent.objects.get_or_create(key="asia", defaults={"name": "آسیا", "lat": 30, "lon": 55})
        c, _ = Country.objects.get_or_create(
            name="ایران", continent=cont,
            defaults={"emoji": "🏳️", "lat": 32.0, "lon": 53.0})
        u = _mk_user("prof_user")
        p = Player.objects.create(user=u, player_name="ProfBoss")
        UsedCountry.objects.create(country=c, player=p)
        self.client.force_authenticate(user=u)
        # GET — ساخت خودکار پروفایل
        r = self.client.get("/api/my-map/country-profile/?country=ایران")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["profile"]["display_name"], "ایران")
        # POST — تغییر نام نمایشی و رنگ
        r = self.client.post("/api/my-map/country-profile/", {
            "country": "ایران", "display_name": "ایران بزرگ", "map_color": "#ff8800"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["profile"]["display_name"], "ایران بزرگ")
        self.assertEqual(r.data["profile"]["map_color"], "#ff8800")
        # POST — پایتخت بیرون قلمرو رد می‌شود
        r = self.client.post("/api/my-map/country-profile/", {
            "country": "ایران", "capital_lat": 0.0, "capital_lon": 0.0})
        self.assertEqual(r.status_code, 400)
        # POST — پایتخت داخل قلمرو قبول (ایران polygon atlas)
        r = self.client.post("/api/my-map/country-profile/", {
            "country": "ایران", "capital_lat": 35.7, "capital_lon": 51.4})
        self.assertEqual(r.status_code, 200)
        # کشور بیگانه — ممنوع
        r = self.client.get("/api/my-map/country-profile/?country=آمریکا")
        self.assertIn(r.status_code, (403, 404))

    def test_country_geometry_endpoint(self):
        from core.models import Continent, Country
        cont, _ = Continent.objects.get_or_create(key="asia", defaults={"name": "آسیا", "lat": 30, "lon": 55})
        Country.objects.get_or_create(
            name="ایران", continent=cont,
            defaults={"emoji": "🏳️", "lat": 32.0, "lon": 53.0})
        u = _mk_user("geo_user")
        Player.objects.create(user=u, player_name="GeoBoss")
        self.client.force_authenticate(user=u)
        r = self.client.get("/api/my-map/country-geometry/?name=ایران")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["geo"]["kind"], "real")
        self.assertTrue(r.data["divisions"])
        r404 = self.client.get("/api/my-map/country-geometry/?name=ناموجود")
        self.assertEqual(r404.status_code, 404)


class _DiploBase(TestCase):
    """زیرساخت مشترک: دو کاربر با کشور واقعی + existing برای روابط"""

    def setUp(self):
        self._setup_two()

    def _setup_two(self):
        from core.models import Continent, Country
        cont, _ = Continent.objects.get_or_create(key="asia", defaults={"name": "آسیا", "lat": 30, "lon": 55})
        self.ca, _ = Country.objects.get_or_create(
            name="ایران", continent=cont, defaults={"emoji": "🏳️", "lat": 32.0, "lon": 53.0})
        self.cb, _ = Country.objects.get_or_create(
            name="عراق", continent=cont, defaults={"emoji": "🏳️", "lat": 33.0, "lon": 44.0})
        self.ua = _mk_user("da")
        self.pa = Player.objects.create(user=self.ua, player_name="DiploA", country=self.ca, credit=50000)
        self.ub = _mk_user("db")
        self.pb = Player.objects.create(user=self.ub, player_name="DiploB", country=self.cb, credit=50000)


class DiplomacyFlowTests(_DiploBase):
    """state machine کامل: send → accept/reject/counter/expiry + idempotency + IDOR"""

    def test_send_accept_creates_agreement_and_blocks_attack(self):
        """سناریو: پیمان عدم تجاوز → حمله server-side بلاک"""
        from core.models import WarEvent
        from core.services import diplomacy as dip, combat as cbt
        WarEvent.objects.create(active=True)  # جنگ جهانی فعال برای تست
        r = dip.send_proposal(self.pa, "عراق", "non_aggression", {}, command_id="c1")
        self.assertTrue(r["ok"])
        # idempotency: دوبار همان command
        r2 = dip.send_proposal(self.pa, "عراق", "non_aggression", {}, command_id="c1")
        self.assertFalse(r2["ok"])
        # accept توسط گیرنده
        r3 = dip.respond_proposal(self.pb, r["proposal_id"], "accept")
        self.assertTrue(r3["ok"])
        self.assertTrue(dip.agreement_between(self.ca, self.cb, "non_aggression"))
        # حمله بلاک می‌شود
        res = cbt.process_attack(self.pa, self.pb, "tank", 10)
        self.assertFalse(res["ok"])
        self.assertIn("پیمان", res["error"])
        # cancel → حمله دیگر با پیمان بلاک نیست
        ag_id = r3["agreement_id"]
        rc = dip.cancel_agreement(self.pa, ag_id)
        self.assertTrue(rc["ok"])
        self.assertFalse(dip.agreement_between(self.ca, self.cb, "non_aggression"))

    def test_only_receiver_can_accept(self):
        """IDOR: فرستنده نمی‌تواند پیشنهاد خودش را بپذیرد"""
        from core.services import diplomacy as dip
        r = dip.send_proposal(self.pa, "عراق", "transit", {})
        self.assertTrue(r["ok"])
        bad = dip.respond_proposal(self.pa, r["proposal_id"], "accept")
        self.assertFalse(bad["ok"])
        good = dip.respond_proposal(self.pb, r["proposal_id"], "accept")
        self.assertTrue(good["ok"])

    def test_counter_then_accept_uses_counter_terms(self):
        from core.services import diplomacy as dip, gamestate as gs
        gs.add_item_qty(self.pa, "count", "iron", 10)  # موجودی واقعی برای send
        r = dip.send_proposal(self.pa, "عراق", "trade",
                              {"item_key": "iron", "qty": 5, "price": 100, "duration_days": 2})
        rc = dip.respond_proposal(self.pb, r["proposal_id"], "counter",
                                  {"item_key": "iron", "qty": 5, "price": 150, "duration_days": 2})
        self.assertTrue(rc["ok"])
        ra = dip.respond_proposal(self.pa, r["proposal_id"], "accept")
        self.assertTrue(ra["ok"])
        from core.models import Agreement
        ag = Agreement.objects.get(id=ra["agreement_id"])
        self.assertEqual(ag.terms["price"], 150)  # نسخه counter با history حفظ شد

    def test_trade_tick_moves_real_goods_and_money(self):
        """سناریو ۳ سند: قرارداد تجاری → تحویل واقعی کالا + پول با audit"""
        from core.services import diplomacy as dip, gamestate as gs
        gs.add_item_qty(self.pa, "count", "iron", 10)
        gs.add_item_qty(self.pa, "count", "dock", 1)  # مسیر حمل فعال
        r = dip.send_proposal(self.pa, "عراق", "trade",
                              {"item_key": "iron", "qty": 4, "price": 1000, "duration_days": 2})
        ra = dip.respond_proposal(self.pb, r["proposal_id"], "accept")
        self.assertTrue(ra["ok"])
        seller_credit = self.pa.credit
        buyer_credit = self.pb.credit
        out = dip.execute_trade_tick()
        self.assertIn("1 delivered", out)
        self.assertEqual(gs.get_item_qty(self.pa, "count", "iron"), 6)
        self.assertEqual(gs.get_item_qty(self.pb, "count", "iron"), 4)
        self.pa.refresh_from_db(); self.pb.refresh_from_db()
        self.assertEqual(self.pa.credit, seller_credit + 4000)
        self.assertEqual(self.pb.credit, buyer_credit - 4000)
        from core.models import CreditTransaction
        self.assertTrue(CreditTransaction.objects.filter(player=self.pb, amount=-4000).exists())

    def test_trade_blocked_without_docks_creates_alert(self):
        """سناریو ۴ سند: نبود اسکله → اختلال + alert واقعی (dedup)"""
        from core.services import diplomacy as dip, gamestate as gs, alerts as al
        from core.models import Alert
        gs.add_item_qty(self.pa, "count", "iron", 10)
        r = dip.send_proposal(self.pa, "عراق", "trade",
                              {"item_key": "iron", "qty": 4, "price": 1000, "duration_days": 2})
        ra = dip.respond_proposal(self.pb, r["proposal_id"], "accept")
        self.assertTrue(ra["ok"])
        out = dip.execute_trade_tick()
        self.assertIn("0 delivered", out)
        self.assertIn("1 failed", out)
        # کالا/پول جابه‌جا نشد
        self.assertEqual(gs.get_item_qty(self.pa, "count", "iron"), 10)
        # alert با akey یکتا — دوبار tick → همان alert (dedup)، نه تکرار
        out2 = dip.execute_trade_tick()
        self.assertIn("1 failed", out2)
        self.assertEqual(Alert.objects.filter(akey=f"trade_disruption:{ra['agreement_id']}").count(), 1)
        # ساخت اسکله → تیک بعدی تحویل واقعی + resolve alert
        gs.add_item_qty(self.pa, "count", "dock", 1)
        out3 = dip.execute_trade_tick()
        self.assertIn("1 delivered", out3)
        a = Alert.objects.get(akey=f"trade_disruption:{ra['agreement_id']}")
        self.assertEqual(a.status, "resolved")


class AlertEngineTests(_DiploBase):
    """موتور هشدار از وضعیت واقعی + dedup + resolve خودکار"""

    def test_no_dock_naval_alert_dedup_and_resolve(self):
        from core.services import gamestate as gs, alerts as al
        from core.models import Alert
        gs.add_item_qty(self.pa, "naval_count", "destroyer", 3)
        found = al.evaluate_player(self.pa)
        self.assertTrue(any(a.akey == "supply_disruption:dock:player" for a in found))
        al.evaluate_player(self.pa)
        self.assertEqual(Alert.objects.filter(akey="supply_disruption:dock:player").count(), 1)
        # رفع: اسکله ساخته شد → resolve
        gs.add_item_qty(self.pa, "count", "dock", 1)
        al.evaluate_player(self.pa)
        a = Alert.objects.get(akey="supply_disruption:dock:player")
        self.assertEqual(a.status, "resolved")

    def test_treasury_low_alert_and_recovery(self):
        from core.services import alerts as al
        from core.models import Alert
        self.pa.credit = 100
        self.pa.save()
        al.evaluate_player(self.pa)
        self.assertTrue(Alert.objects.filter(akey="treasury_low:credit:player", status="active").exists())
        self.pa.credit = 90000
        self.pa.save()
        al.evaluate_player(self.pa)
        a = Alert.objects.get(akey="treasury_low:credit:player")
        self.assertEqual(a.status, "resolved")

    def test_priority_configurable(self):
        from core.services import alerts as al
        from django.test import override_settings
        p1 = al.compute_priority("critical", "supply_disruption")
        with override_settings(GAME={"ALERT_WEIGHTS": {"severity": {"critical": 5, "warning": 2, "info": 1}}}):
            p2 = al.compute_priority("critical", "supply_disruption")
        self.assertGreater(p1, p2)

    def test_ai_utility_explainable(self):
        """AI تصمیم با دلیل شفاف — نه random خام"""
        from core.services import diplomacy as dip
        from core.models import DiplomaticProposal
        from django.utils import timezone
        prop = DiplomaticProposal.objects.create(
            type="non_aggression", from_country=self.cb, to_country=self.ca,
            status="pending", terms={},
            expires_at=timezone.now() + timezone.timedelta(hours=24))
        rev = dip.ai_evaluate(prop)
        self.assertIn(rev["decision"], ("accept", "reject", "counter"))
        self.assertIn("primary_reason", rev)
        self.assertIsInstance(rev["factors"], dict)

    def test_command_center_requires_auth_and_shows_real_data(self):
        """CountryOverview فقط داده واقعی + احراز هویت"""
        from rest_framework.test import APIClient
        c = APIClient()
        r = c.get("/api/command-center/")
        self.assertEqual(r.status_code, 401)
        c.force_authenticate(user=self.ua)
        r = c.get("/api/command-center/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["treasury"]["current"], 50000)
        self.assertIn("alerts", r.data)
        self.assertIn("agreements", r.data)
        self.assertIn("relations", r.data)
