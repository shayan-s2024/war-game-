# -*- coding: utf-8 -*-
"""اسکریپت smoke test یک‌باره — کل جریان بازی از auth تا حمله.

اجرا (از backend/):
    python manage.py shell < smoke_test.py
"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import json as _json

import django, os, random
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

RUN = str(random.randint(1000, 9999))  # پسوند یکتا برای اجراهای مکرر

from django.test import Client
from django.contrib.auth import get_user_model
from core.models import (Player, UsedCountry, WarEvent, PlayerItem, Notification,
                         Union, CreditTransaction)
from core.gamedata import TANKS
from core.services import gamestate as gs

User = get_user_model()

OK, FAIL = 0, 0
def check(label, cond, extra=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label} {extra}")

def j(r):
    return _json.loads(r.content.decode("utf-8"))

def register_and_login(username):
    c = Client(HTTP_HOST="localhost")
    r = c.post("/api/auth/register/", {"username": f"{username}{RUN}", "password": "pass12345"},
               content_type="application/json")
    assert r.status_code == 201, f"register failed: {r.status_code} {r.content[:200]}"
    tok = j(r)["tokens"]["access"]
    c = Client(HTTP_HOST="localhost", HTTP_AUTHORIZATION=f"Bearer {tok}")
    return c, tok

print("== 1) Auth ==")
c1, tok1 = register_and_login("smoke1")
c2, tok2 = register_and_login("smoke2")
r = c1.post("/api/auth/login/", {"username": f"smoke1{RUN}", "password": "pass12345"},
            content_type="application/json")
check("login", r.status_code == 200)

print("== 2) Registration flow ==")
r = c1.get("/api/registration/status/")
check("registration status", r.status_code == 200 and j(r)["remaining"] > 0)
# بازیکن ۲ اول کشورش را می‌گیرد (برای تست تداخل رزرو)
r = c2.post("/api/registration/name/", {"name": f"فرمانده دوم {RUN}"}, content_type="application/json")
check("register name p2", r.status_code == 200, r.content[:120])
countries = j(c1.get("/api/countries/"))["countries"]
first_cont = list(countries.keys())[0]
free2 = [c for c in countries[first_cont] if not c["taken"]]
r = c2.post("/api/registration/country/", {"country": free2[0]["name"]}, content_type="application/json")
check("register country p2", r.status_code == 200, r.content[:200])
# کابینه بازیکن ۲ هم کامل شود (برای تست هک/ترور)
for k, v in {"diplomat": "د", "leader": "ل", "defense": "ف", "economy": "ا", "intelligence": "ط"}.items():
    c2.post("/api/cabinet/set/", {"key": k, "value": v}, content_type="application/json")
c2.post("/api/cabinet/finish/", content_type="application/json")
free = [c for c in countries[first_cont] if not c["taken"] and c["name"] != free2[0]["name"]]
r = c1.post("/api/registration/name/", {"name": f"فرمانده دود {RUN}"}, content_type="application/json")
check("register name", r.status_code == 200, r.content[:120])
r = c1.post("/api/registration/country/", {"country": free2[0]["name"]}, content_type="application/json")
check("duplicate country rejected", r.status_code == 409)
r = c1.post("/api/registration/country/", {"country": free[0]["name"]}, content_type="application/json")
check("register country", r.status_code == 200, r.content[:200])
for k, v in {"diplomat": "دیپلمات۱۲۳۴۵", "leader": "رهبر بزرگ", "defense": "وزیر دفاع",
             "economy": "وزیر اقتصاد", "intelligence": "اطلاعات"}.items():
    c1.post("/api/cabinet/set/", {"key": k, "value": v}, content_type="application/json")
r = c1.post("/api/cabinet/finish/", content_type="application/json")
check("cabinet finish + codes", r.status_code == 200 and r.json().get("ok"))
r = c1.get("/api/cabinet/")
codes = j(r)["codes"]
check("codes generated (5)", len(codes) == 5, str(codes))

print("== 3) Dashboard ==")
r = c1.get("/api/dashboard/")
d = j(r)
check("dashboard", r.status_code == 200 and "دود" in (d.get("player", {}).get("name") or ""))
check("dashboard next_step null", d.get("next_step") is None, str(d.get("next_step")))

print("== 4) Shop ==")
r = c1.get("/api/shop/catalog/")
check("shop catalog", r.status_code == 200 and "tank" in j(r)["categories"])
# پول بده
p1 = Player.objects.get(user__username=f"smoke1{RUN}")
p1.credit = 1_000_000
p1.save(update_fields=["credit"])
r = c1.post("/api/shop/buy/", {"category": "tank", "item": "simple", "count": 2},
            content_type="application/json")  # ۲ بسته ۱۰۰تایی = ۲۰۰ عدد (سقف ۴۰۰)
buy = j(r)
check("buy tanks", buy.get("ok") is True, str(buy)[:200])
check("audit trail", CreditTransaction.objects.filter(player=p1, reason="purchase").exists())
r = c1.post("/api/shop/buy/", {"category": "mine", "item": "emerald", "count": 5},
            content_type="application/json")
check("buy mines (profit)", j(r).get("ok") is True, str(j(r))[:200])
r = c1.post("/api/shop/buy/", {"category": "tank", "item": "simple", "count": 10**9},
            content_type="application/json")
check("insufficient funds rejected", r.status_code == 400)

print("== 5) Combat ==")
p2 = Player.objects.get(user__username=f"smoke2{RUN}")
r = c1.get("/api/attack/targets/", {"weapon": "tank"})
check("attack targets (same continent only or empty)", r.status_code == 200)

WarEvent.objects.create(active=True)  # جنگ را روشن کن
r = c1.post("/api/attack/", {"target_id": p2.id, "weapon": "tank", "count": 5},
            content_type="application/json")
res = j(r)
check("attack executed", res.get("ok") is True, str(res)[:250])
check("attack consumed quota", Player.objects.get(id=p1.id).attack_records.count() >= 1)
check("defender notified", Notification.objects.filter(player=p2, kind="battle").exists())
r = c1.get("/api/attack/status/")
check("attack status remaining", j(r)["remaining"] == 3, str(j(r)))

print("== 6) Spy ==")
gs.add_item_qty(p1, "hacker_count", "strong", 10)
r = c1.post("/api/spy/hack/", {"target_id": p2.id, "level": "strong", "count": 3},
            content_type="application/json")
hack = j(r)
check("hack steals codes", hack.get("ok") and hack.get("success") is True, str(hack)[:250])
r = c1.get("/api/spy/")
intel = j(r)["intel"]
check("intel available", len(intel) > 0)
if intel:
    it = intel[0]
    gs.add_item_qty(p1, "ground_count", "commando", 5)  # کماندو برای ترور
    r = c1.post("/api/spy/assassinate/",
                {"target_id": it["target_id"], "member_key": it["member_key"],
                 "method": "commando", "code": it["code"]},
                content_type="application/json")
    check("assassinate request valid", r.status_code == 200 and j(r).get("ok"), str(j(r))[:200])

print("== 7) Unions ==")
r = c1.post("/api/unions/", {"action": "create", "name": f"اتحاد دود {RUN}"}, content_type="application/json")
check("create union", j(r).get("ok"), str(j(r))[:200])
u_id = j(r)["union"]["id"]  # اتحاد تازه‌ساخته‌شده (نه اولین اتحاد DB)
r = c2.post("/api/unions/", {"action": "join_request", "union_id": u_id}, content_type="application/json")
check("join request", j(r).get("ok"), str(j(r))[:200])
r = c1.get("/api/unions/")
pending = j(r)["pending_requests"]
check("owner sees pending", len(pending) == 1)
r = c1.post("/api/unions/", {"action": "approve", "request_id": pending[0]["id"]},
            content_type="application/json")
check("approve join", j(r).get("ok"), str(j(r))[:200])
p2.refresh_from_db()
check("member linked", p2.union_id == u_id)
r = c1.post("/api/unions/", {"action": "deposit", "union_id": u_id, "amount": 50000},
            content_type="application/json")
check("treasury deposit", j(r).get("ok") and Union.objects.get(id=u_id).treasury == 50000, str(j(r))[:200])
# اهدای تجهیز (مسیر UI جدید) — ۵ تانک به بازیکن ۲
r = c1.post("/api/unions/", {"action": "donate_item", "union_id": u_id, "recipient_id": p2.id,
                             "category": "tank", "item": "simple", "count": 5},
            content_type="application/json")
check("donate item to member", j(r).get("ok"), str(j(r))[:200])

print("== 8) Bases + achievements + notifications + guide ==")
r = c1.get("/api/bases/")
check("bases list", r.status_code == 200)
r = c1.get("/api/achievements/")
ach = j(r)
check("achievements endpoint", r.status_code == 200 and ach.get("total_count", 0) >= 10)
# بعد از خرید ۱۰۰ تانک + نبرد + سرقت کد، حداقل یک دستاورد باز شده باشد
check("achievement unlocked", ach.get("unlocked_count", 0) >= 1,
      f"unlocked={ach.get('unlocked_count')}")
r = c1.get("/api/equipment/")
equip = j(r)
tank_total = sum(i["qty"] for i in equip["categories"].get("tank", []))
check("equipment shows tanks", tank_total >= 100, f"tank={tank_total}")
r = c1.get("/api/notifications/")
check("notifications list", r.status_code == 200 and j(r)["unread_count"] > 0)
r = c1.get("/api/guide/")
check("guide sections", len(j(r)["sections"]) >= 5)
r = c1.get("/api/leaderboard/", {"metric": "score"})
check("leaderboard", r.status_code == 200 and len(j(r)["leaderboard"]) >= 2)

print(f"\n{'='*40}\nRESULT: {OK} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
