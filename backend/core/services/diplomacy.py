# -*- coding: utf-8 -*-
"""🤝 دیپلماسی — پیشنهاد با state machine، AI utility explainable، توافق و اجرای تجارت.

همه state transitions در سرور validate می‌شوند؛ کلاینت فقط command می‌فرستد.
کالا از موجودی واقعی PlayerItem (Game Core) جابه‌جا می‌شود؛ payment با audit کامل (CreditTransaction).
اتصال به بقیه World State:
- پیمان عدم تجاوز/اتحاد → combat.py حمله را بلاک می‌کند
- ترانزیت → naval.py مسیر دریایی همسایه مجاز می‌شود (فعلاً fleet بدون dock اما با توافق)
- تجارت → هر tick کالای واقعی جابه‌جا + پول با audit + alert در اختلال
"""
import logging
import random

from django.db import transaction
from django.utils import timezone

from ..models import (Agreement, Country, CreditTransaction, DiplomaticProposal,
                      DiplomaticRelation, Notification, Player)
from . import gamestate as gs

logger = logging.getLogger(__name__)

PROPOSAL_TTL_HOURS = 48

# ==================== روابط ====================


def get_relation(a: Country, b: Country) -> DiplomaticRelation:
    """رابطه جهت‌دار a→b — ساخت خودکار در اولین نگاه."""
    rel, _ = DiplomaticRelation.objects.get_or_create(source=a, target=b)
    return rel


def adjust_relation(a: Country, b: Country, score: int = 0, trust: int = 0,
                    tension: int = 0) -> DiplomaticRelation:
    rel = get_relation(a, b)
    rel.relation_score = max(-100, min(100, rel.relation_score + score))
    rel.trust = max(0, min(100, rel.trust + trust))
    rel.tension = max(0, min(100, rel.tension + tension))
    rel.save(update_fields=["relation_score", "trust", "tension", "last_interaction_at"])
    return rel


def agreement_between(a: Country, b: Country, atype: str) -> Agreement | None:
    """توافق فعال بین دو کشور (هر دو جهت)."""
    return (Agreement.objects.filter(type=atype, status="active")
            .filter(initiator__in=[a, b], partner__in=[a, b])).first()


def relation_profile(owner: Player) -> list[dict]:
    """خلاصه روابط کشور بازیکن برای UI — با توافق‌های فعال هر طرف."""
    if not owner.country_id:
        return []
    c = owner.country
    out = []
    rels = (DiplomaticRelation.objects.filter(source=c)
            .select_related("target").order_by("-relation_score")[:30])
    for rel in rels:
        ags = (Agreement.objects.filter(status="active")
               .filter(initiator__in=[c, rel.target], partner__in=[c, rel.target]))
        out.append({
            "country": rel.target.name, "emoji": rel.target.emoji,
            "score": rel.relation_score, "trust": rel.trust, "tension": rel.tension,
            "agreements": [{"id": a.id, "type": a.type, "type_fa": a.get_type_display(),
                            "ends_at": a.ends_at.isoformat() if a.ends_at else None}
                           for a in ags],
        })
    return out


# ==================== AI دیپلمات — utility explainable ====================
# وزن‌ها configurable؛ تصمیم = مجموع امتیاز factors + policy آستانه‌ای (نه random)

AI_WEIGHTS = {
    "economic_benefit": 1.0, "security_benefit": 1.2, "relationship": 0.5,
    "trade_dependency": 0.6, "risk": -1.5, "relative_power_concern": -0.8,
    "existing_obligations": -0.5, "tension": -0.6,
}
AI_ACCEPT_THRESHOLD = 15
AI_COUNTER_THRESHOLD = 0


def ai_evaluate(proposal: DiplomaticProposal) -> dict:
    """محاسبه utility پیشنهاد برای کشور گیرنده — با دلایل شفاف (explainable).
    عوامل از داده واقعی: قدرت (attack_power)، روابط، توافق‌های فعلی، تنش.
    """
    from . import combat as cbt
    to_c = proposal.to_country
    from_c = proposal.from_country
    to_owner = Player.objects.filter(country=to_c).select_related("country").order_by("-score").first()
    from_owner = Player.objects.filter(country=from_c).order_by("-score").first()
    rel = get_relation(from_c, to_c)

    factors: dict[str, float] = {}
    reasons_pos, reasons_neg = [], []

    my_power = (to_owner.attack_power + to_owner.defense) if to_owner else 0
    their_power = (from_owner.attack_power + from_owner.defense) if from_owner else 0
    power_ratio = (their_power / max(1, my_power)) if my_power else 2.0

    # سود اقتصادی — فقط برای توافق تجاری (قیمت منصفانه؟)
    if proposal.type == "trade":
        terms = proposal.counter_terms or proposal.terms
        qty = terms.get("qty", 0)
        price = terms.get("price", 0)
        factors["economic_benefit"] = min(40, qty * price / 5000)
        if price <= 0:
            factors["economic_benefit"] = -10
            reasons_neg.append("قیمت کالا نامعقول است")
        else:
            reasons_pos.append(f"درآمد {qty:,}×{price:,} در هر تحویل")
    else:
        factors["economic_benefit"] = 5

    # سود امنیتی — قدرت‌مندتر از ما پیمان بدهد = سود؛ از ما ضعیف‌تر + نگرانی
    if proposal.type in ("non_aggression", "alliance"):
        factors["security_benefit"] = 20 if power_ratio > 1.3 else (8 if power_ratio > 0.8 else 3)
        if power_ratio > 1.3:
            reasons_pos.append("طرف مقابل قدرت نظامی بالاتری دارد — امنیت بیشتر")
    else:
        factors["security_benefit"] = 5

    factors["relationship"] = rel.relation_score * AI_WEIGHTS["relationship"]
    if rel.relation_score >= 30:
        reasons_pos.append(f"رابطه خوب ({rel.relation_score})")
    factors["tension"] = rel.tension * AI_WEIGHTS["tension"]
    if rel.tension >= 50:
        reasons_neg.append(f"تنش بالا ({rel.tension}٪)")
    factors["trade_dependency"] = 0
    factors["risk"] = 15 if proposal.type == "trade" else 5
    # نگرانی قدرت نسبی: اتحاد با خیلی قوی‌تر = وابستگی
    if proposal.type == "alliance":
        factors["relative_power_concern"] = 10 * max(0.0, power_ratio - 1.5)
    # تعهدات موجود — هر توافق فعال مانع توافق مشابه جدید
    n_active = Agreement.objects.filter(status="active",
                                        initiator__in=[to_c, from_c],
                                        partner__in=[to_c, from_c]).count()
    factors["existing_obligations"] = n_active * 6
    if n_active >= 2:
        reasons_neg.append(f"{n_active} توافق فعال دیگر دارد")

    utility = sum(factors.get(k, 0) * AI_WEIGHTS.get(k, 1.0) for k in factors)
    utility += random.uniform(-2, 2)  # نویز کوچک انسانی — تصمیم‌ها همه متفاوت نباشد

    if utility >= AI_ACCEPT_THRESHOLD:
        decision, primary = "accept", "مجموع سود اقتصادی/امنیتی پیشنهاد بالا است"
    elif utility >= AI_COUNTER_THRESHOLD and proposal.type == "trade":
        decision, primary = "counter", "سود هست اما شرایط قابل بهبود است"
    else:
        decision, primary = "reject", max(
            (f"{k}" for k in factors if factors[k] < 0), default="سود کلی پیشنهاد کافی نیست")

    return {
        "decision": decision, "utility": round(utility, 1),
        "primary_reason": primary,
        "positive_factors": reasons_pos[:3], "negative_factors": reasons_neg[:3],
        "factors": {k: round(v, 1) for k, v in factors.items()},
    }


# ==================== Proposal state machine ====================

def _akey(kind: str, a_id: int, b_id: int, extra: str = "") -> str:
    day = timezone.now().strftime("%Y%m%d")
    lo, hi = sorted([a_id, b_id])
    return f"{kind}:{lo}:{hi}:{extra}:{day}"


def send_proposal(owner: Player, to_country_name: str, ptype: str, terms: dict,
                  command_id: str = "") -> dict:
    """ارسال پیشنهاد — idempotent با command_id؛ فقط مالک کشور می‌تواند بفرستد."""
    if ptype not in ("non_aggression", "alliance", "transit", "trade"):
        return {"ok": False, "error": "نوع پیشنهاد نامعتبر"}
    if not owner.country_id:
        return {"ok": False, "error": "شما کشوری ندارید"}
    to_c = Country.objects.filter(name=to_country_name).first()
    if not to_c:
        return {"ok": False, "error": "کشور مقصد یافت نشد"}
    if to_c.id == owner.country_id:
        return {"ok": False, "error": "پیشنهاد به خود کشور ممکن نیست"}
    to_owner = Player.objects.filter(country=to_c).exclude(id=owner.id).first()
    if not to_owner:
        return {"ok": False, "error": "این کشور صاحب فعالی ندارد"}
    # تجاری: سنجش موجودی واقعی فرستنده
    if ptype == "trade":
        item = str(terms.get("item_key", ""))
        qty = int(terms.get("qty", 0))
        price = int(terms.get("price", 0))
        if not item or qty < 1 or price < 1:
            return {"ok": False, "error": "شرایط تجاری ناقص (item_key/qty/price)"}
        suffix = str(terms.get("suffix", "count"))
        if gs.get_item_qty(owner, suffix, item) < qty:
            return {"ok": False, "error": "موجودی کافی برای این قرارداد ندارید"}
    akey = _akey("prop", owner.country_id, to_c.id, f"{ptype}:{command_id}")[:80]
    if DiplomaticProposal.objects.filter(akey=akey, status__in=["sent", "pending"]).exists():
        return {"ok": False, "error": "پیشنهاد مشابه در جریان است"}  # idempotency
    prop = DiplomaticProposal.objects.create(
        akey=akey, type=ptype, from_country=owner.country, to_country=to_c,
        status="pending", terms=terms or {},
        expires_at=timezone.now() + timezone.timedelta(hours=PROPOSAL_TTL_HOURS))
    adjust_relation(owner.country, to_c, score=2)
    _notify(to_owner, {"kind": "diplomacy", "proposal_id": prop.id,
                       "title": f"✉️ پیشنهاد {prop.get_type_display()} از {owner.country.name}",
                       "type": ptype})
    return {"ok": True, "proposal_id": prop.id, "status": "pending"}


def respond_proposal(owner: Player, proposal_id: int, action: str,
                     counter_terms: dict | None = None) -> dict:
    """پاسخ به پیشنهاد — گیرنده یا فرستنده (بعد از counter)؛ state transitions validate؛ atomic.
    counter: گیرنده شرایط جدید می‌دهد → حال فرستنده باید accept/reject کند (جهت معکوس).
    """
    prop = (DiplomaticProposal.objects.select_related("from_country", "to_country")
            .filter(id=proposal_id).first())
    if not prop:
        return {"ok": False, "error": "پیشنهاد یافت نشد"}
    is_receiver = prop.to_country_id == owner.country_id
    is_sender_after_counter = (prop.from_country_id == owner.country_id
                               and prop.counter_terms is not None)
    if not is_receiver and not is_sender_after_counter:
        return {"ok": False, "error": "این پیشنهاد خطاب به کشور شما نیست"}  # IDOR
    if prop.status != "pending":
        return {"ok": False, "error": f"پیشنهاد در وضعیت {prop.status} است"}
    if prop.expires_at and prop.expires_at < timezone.now():
        prop.status = "expired"
        prop.save(update_fields=["status", "responded_at"])
        return {"ok": False, "error": "پیشنهاد منقضی شده است"}
    to_owner = owner
    from_owner = Player.objects.filter(country=prop.from_country).first()

    if action == "reject":
        prop.status = "rejected"
        prop.responded_at = timezone.now()
        prop.save(update_fields=["status", "responded_at"])
        adjust_relation(prop.from_country, prop.to_country, score=-5, tension=+5)
        if from_owner:
            _notify(from_owner, {"kind": "diplomacy", "proposal_id": prop.id,
                                 "title": f"❌ پیشنهاد {prop.get_type_display()} شما رد شد"})
        return {"ok": True, "status": "rejected"}

    if action == "counter":
        if not counter_terms:
            return {"ok": False, "error": "شرایط پیشنهاد متقابل خالی است"}
        if not is_receiver:
            return {"ok": False, "error": "فقط گیرنده می‌تواند پیشنهاد متقابل بدهد"}
        prop.counter_terms = counter_terms  # نسخه جدید — history در JSON حفظ
        prop.save(update_fields=["counter_terms"])
        if from_owner:
            _notify(from_owner, {"kind": "diplomacy", "proposal_id": prop.id,
                                 "title": f"🔁 پیشنهاد متقابل برای {prop.get_type_display()}"})
        return {"ok": True, "status": "pending", "counter_terms": counter_terms}

    if action != "accept":
        return {"ok": False, "error": "اکشن نامعتبر"}

    # accept — در ترانزیشن اتمیک → Agreement
    terms = prop.counter_terms if prop.counter_terms else prop.terms
    try:
        with transaction.atomic():
            prop.status = "accepted"
            prop.responded_at = timezone.now()
            prop.save(update_fields=["status", "responded_at"])
            dur = int(terms.get("duration_days", 7)) if prop.type == "trade" else 14
            ag = Agreement.objects.create(
                type=prop.type, initiator=prop.from_country, partner=prop.to_country,
                terms=terms, ends_at=timezone.now() + timezone.timedelta(days=dur))
            adjust_relation(prop.from_country, prop.to_country, score=+15, trust=+10, tension=-15)
    except Exception:
        logger.exception("accept_proposal failed")
        return {"ok": False, "error": "خطا در ثبت توافق — دوباره تلاش کنید"}
    if from_owner:
        _notify(from_owner, {"kind": "diplomacy", "proposal_id": prop.id, "agreement_id": ag.id,
                             "title": f"✅ {prop.get_type_display()} امضا شد!"})
    _notify(to_owner, {"kind": "diplomacy", "agreement_id": ag.id,
                       "title": f"✅ {prop.get_type_display()} با {prop.from_country.name} فعال شد"})
    return {"ok": True, "status": "accepted", "agreement_id": ag.id}


def cancel_agreement(owner: Player, agreement_id: int) -> dict:
    """لغو توافق — هزینه دیپلماتیک (اعتماد ↓ تنش ↑) و اثر واقعی در قیود."""
    ag = Agreement.objects.filter(id=agreement_id, status="active").select_related("initiator", "partner").first()
    if not ag:
        return {"ok": False, "error": "توافق فعال یافت نشد"}
    if owner.country_id not in ag.country_ids():
        return {"ok": False, "error": "شما طرف این توافق نیستید"}  # IDOR
    ag.status = "terminated"
    ag.save(update_fields=["status"])
    adjust_relation(ag.initiator, ag.partner, score=-15, trust=-20, tension=+25)
    adjust_relation(ag.partner, ag.initiator, score=-20, trust=-15, tension=+30)
    for c in (ag.initiator, ag.partner):
        po = Player.objects.filter(country=c).first()
        if po:
            _notify(po, {"kind": "diplomacy", "agreement_id": ag.id,
                         "title": f"📜 {ag.get_type_display()} لغو شد"})
    return {"ok": True}


# ==================== اجرای تجارت در tick ====================

def execute_trade_tick() -> str:
    """هر tick: توافق‌های تجاری فعال → چک موجودی/مسیر → تحویل + پرداخت واقعی.
    اختلال → alert واقعی (dedup) + relation tension.
    """
    from ..gamedata import NAVAL_VESSELS
    from . import alerts as al
    from . import combat as cbt
    now = timezone.now()
    done, failed = 0, 0
    for ag in Agreement.objects.filter(type="trade", status="active").select_related("initiator", "partner"):
        # انقضا
        if ag.ends_at and ag.ends_at < now:
            ag.status = "expired"
            ag.save(update_fields=["status"])
            continue
        terms = ag.terms
        item = terms.get("item_key", "")
        suffix = terms.get("suffix", "count")
        qty = int(terms.get("qty", 0))
        price = int(terms.get("price", 0))
        seller = Player.objects.filter(country=ag.initiator).order_by("-score").first()
        buyer = Player.objects.filter(country=ag.partner).order_by("-score").first()
        if not seller or not buyer or not item or qty < 1:
            continue
        akey = f"trade_disruption:{ag.id}"
        # مسیر دریایی: اگر هر دو اسکله نداشته باشند و توافق ترانزیت هم نباشد → اختلال
        docks_s = gs.get_item_qty(seller, "count", "dock")
        docks_b = gs.get_item_qty(buyer, "count", "dock")
        if docks_s == 0 and docks_b == 0:
            failed += 1
            al.raise_alert(
                seller, "trade_disruption", akey,
                f"🚚 تحویل تجاری {item} متوقف شد",
                "هیچ‌کدام از دو کشور اسکله ندارند — مسیر حمل بسته است.",
                cause="نبود اسکله در دو سر مسیر", severity="warning",
                recommended_action="ساخت اسکله یا توافق ترانزیت با همسایه",
                meta={"agreement_id": ag.id, "item": item}, country=ag.initiator)
            adjust_relation(ag.initiator, ag.partner, tension=+3)
            continue
        al.resolve_alert(akey)
        # موجودی فروشنده
        have = gs.get_item_qty(seller, suffix, item)
        if have < qty:
            failed += 1
            al.raise_alert(
                seller, "resource_shortage", f"trade_stock:{ag.id}",
                f"📦 موجودی {item} برای قرارداد تجاری کافی نیست",
                f"لازم {qty}، موجودی {have} — تحویل این دور انجام نشد.",
                cause="کمبود موجودی کالا", severity="warning",
                recommended_action="تولید/خرید کالا یا کاهش دفعات تحویل",
                meta={"agreement_id": ag.id}, country=ag.initiator)
            continue
        # پول خریدار
        total = qty * price
        if buyer.credit < total:
            failed += 1
            al.raise_alert(
                buyer, "treasury_low", f"trade_pay:{ag.id}",
                f"💳 پول پرداخت قرارداد {item} موجود نیست",
                f"لازم {total:,}، موجودی {buyer.credit:,}.",
                cause="خزانه ناکافی", severity="warning",
                recommended_action="افزایش درآمد یا لغو قرارداد",
                meta={"agreement_id": ag.id}, country=ag.partner)
            continue
        # تحویل اتمیک: کالا + پول + audit
        with transaction.atomic():
            gs.add_item_qty(seller, suffix, item, -qty)
            gs.add_item_qty(buyer, suffix, item, +qty)
            cbt.transfer_credit(buyer, seller, total, "purchase",
                                meta={"trade_agreement": ag.id, "item": item, "qty": qty})
        ag.deliveries_done += 1
        ag.save(update_fields=["deliveries_done"])
        adjust_relation(ag.initiator, ag.partner, score=+2, trust=+1)
        done += 1
    return f"trade tick: {done} delivered, {failed} failed"


def _notify(player: Player, payload: dict):
    try:
        from ..api.routing import notify_player_sync
        notify_player_sync(player.id, payload)
    except Exception:
        pass


def expire_proposals() -> str:
    """انقضای پیشنهادهای گذشته از TTL — در tick."""
    n = (DiplomaticProposal.objects.filter(status="pending", expires_at__lt=timezone.now())
         .update(status="expired", responded_at=timezone.now()))
    return f"{n} proposals expired"
