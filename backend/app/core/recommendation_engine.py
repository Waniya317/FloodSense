"""
FloodSense AI — Emergency Recommendation Engine
Maps risk levels to specific, actionable NDMA-aligned emergency protocols.
Every recommendation is bilingual (English + Urdu).
"""

from dataclasses import dataclass, field
from typing import Optional
import math

# ── Risk thresholds (must match train.py) ─────────────────────────────────────
RISK_LEVELS = {
    "Low":      (0.00, 0.25),
    "Medium":   (0.25, 0.50),
    "High":     (0.50, 0.75),
    "Critical": (0.75, 1.01),
}

RISK_COLORS = {
    "Low":      "#22c55e",
    "Medium":   "#f59e0b",
    "High":     "#f97316",
    "Critical": "#dc2626",
}

BADGE_COLOR = {
    "Low":      "Green",
    "Medium":   "Yellow",
    "High":     "Orange",
    "Critical": "Red",
}

RISK_URDU = {
    "Low":      "کم خطرہ",
    "Medium":   "درمیانہ خطرہ",
    "High":     "زیادہ خطرہ",
    "Critical": "انتہائی خطرناک",
}

# Population estimates per district (2023 census approximations, thousands)
DISTRICT_POPULATION = {
    "buner":       900,
    "swat":       2300,
    "nowshera":   1600,
    "charsadda":  1500,
    "peshawar":   4300,
    "mardan":     2400,
    "abbottabad": 1300,
    "mansehra":   1500,
    "kohistan":    700,
    "shangla":     750,
    "dir lower":  1000,
    "dir upper":   700,
    "chitral":     450,
    "dera ismail khan": 1800,
    "tank":        700,
    "lakki marwat": 950,
    "bannu":      1200,
    "karak":       700,
    "hangu":       550,
    "kohat":      1100,
    "kurram":      850,
    "orakzai":     500,
    "khyber":     1000,
    "bajaur":     1100,
    "mohmand":     650,
    # Punjab
    "dera ghazi khan": 3200,
    "rajanpur":   2200,
    "muzaffargarh": 4200,
    "multan":     4700,
    "bahawalnagar": 3200,
    "bahawalpur": 3800,
    "rahim yar khan": 4700,
    "jhang":      3600,
    # Sindh
    "larkana":    2000,
    "jacobabad":  1200,
    "kashmore":    950,
    "shikarpur":  1300,
    "sukkur":     1600,
    "khairpur":   2500,
    "dadu":       1700,
    "qambar shahdadkot": 1200,
    "balochistan": 500,  # generic fallback
}

DEFAULT_POPULATION = 1000  # thousands


@dataclass
class Recommendation:
    risk_level: str
    risk_level_urdu: str
    color: str
    badge_color: str
    probability: float
    confidence_pct: int
    affected_population: int        # estimated people
    affected_population_display: str
    immediate_actions: list[str]
    immediate_actions_urdu: list[str]
    agency_notifications: list[str]
    agency_notifications_urdu: list[str]
    preparation_timeline: str
    preparation_timeline_urdu: str
    evacuation_priority: str
    evacuation_priority_urdu: str
    alert_level_code: str           # e.g. "NDMA-RED"
    summary_en: str
    summary_ur: str


def probability_to_risk(prob: float) -> str:
    if prob < 0.25:
        return "Low"
    elif prob < 0.50:
        return "Medium"
    elif prob < 0.75:
        return "High"
    return "Critical"


def estimate_population(district: str, risk_level: str, probability: float) -> tuple[int, str]:
    """Return (raw_count, formatted_string) of estimated affected population."""
    district_key = district.strip().lower()
    base_pop_k = DISTRICT_POPULATION.get(district_key, DEFAULT_POPULATION)
    base_pop = base_pop_k * 1000

    # Exposure fraction by risk level
    exposure = {
        "Low":      0.05,
        "Medium":   0.18,
        "High":     0.40,
        "Critical": 0.72,
    }
    affected = int(base_pop * exposure[risk_level] * (0.7 + probability * 0.3))

    if affected >= 1_000_000:
        display = f"{affected / 1_000_000:.1f}M"
    elif affected >= 1000:
        display = f"{affected // 1000:,}K"
    else:
        display = str(affected)

    return affected, display


ACTIONS = {
    "Low": {
        "immediate_en": [
            "Monitor local rainfall levels every 6 hours",
            "Verify all drainage channels are unobstructed",
            "Review emergency contact lists with local officials",
            "Check that flood shelters are accessible",
        ],
        "immediate_ur": [
            "ہر 6 گھنٹے میں بارش کی سطح کی نگرانی کریں",
            "تمام نکاسی آب کے راستے صاف کریں",
            "مقامی عہدیداروں کے ساتھ ہنگامی رابطہ فہرست کی تصدیق کریں",
            "سیلابی پناہ گاہوں تک رسائی یقینی بنائیں",
        ],
        "agencies_en": ["District Administration", "PDMA (monitoring)"],
        "agencies_ur": ["ضلعی انتظامیہ", "پی ڈی ایم اے (نگرانی)"],
        "timeline_en": "72 hours — Standard readiness",
        "timeline_ur": "72 گھنٹے — معیاری تیاری",
        "evacuation_en": "Not required — standby",
        "evacuation_ur": "ضروری نہیں — تیار رہیں",
        "code": "NDMA-GREEN",
        "summary_en": "Low flood probability. Continue routine monitoring and ensure drainage systems are clear.",
        "summary_ur": "سیلاب کا امکان کم ہے۔ معمول کی نگرانی جاری رکھیں اور نکاسی کا نظام صاف رکھیں۔",
    },
    "Medium": {
        "immediate_en": [
            "Issue precautionary flood advisory to all union councils",
            "Pre-position rescue boats and life jackets at river crossings",
            "Alert hospitals to increase emergency capacity by 30%",
            "Activate district-level Emergency Operations Center (EOC)",
            "Notify PDMA and request standby rescue teams",
        ],
        "immediate_ur": [
            "تمام یونین کونسلوں کو احتیاطی سیلاب مشاورت جاری کریں",
            "دریائی گزرگاہوں پر کشتیاں اور لائف جیکٹس پہلے سے رکھیں",
            "ہسپتالوں کو ہنگامی صلاحیت 30 فیصد بڑھانے کا الرٹ دیں",
            "ضلعی ایمرجنسی آپریشن سنٹر (EOC) فعال کریں",
            "پی ڈی ایم اے کو مطلع کریں اور امدادی ٹیمیں طلب کریں",
        ],
        "agencies_en": ["PDMA", "District EOC", "Pakistan Army (on notice)", "1122 Rescue"],
        "agencies_ur": ["پی ڈی ایم اے", "ضلعی EOC", "پاک فوج (الرٹ پر)", "1122 ریسکیو"],
        "timeline_en": "48 hours — Enhanced monitoring mode",
        "timeline_ur": "48 گھنٹے — بہتر نگرانی موڈ",
        "evacuation_en": "Flood plains and riverbanks — voluntary evacuation",
        "evacuation_ur": "سیلابی میدانوں اور دریائی کناروں سے رضاکارانہ انخلاء",
        "code": "NDMA-YELLOW",
        "summary_en": "Moderate flood risk detected. Activate EOC, pre-position rescue assets, and issue public advisories.",
        "summary_ur": "معتدل سیلاب خطرہ محسوس ہوا۔ EOC فعال کریں، امدادی وسائل تیار کریں اور عوامی اطلاع جاری کریں۔",
    },
    "High": {
        "immediate_en": [
            "Issue FLOOD WARNING — mandatory evacuation of high-risk zones",
            "Deploy Pakistan Army and FC rescue teams immediately",
            "Open all 72+ designated flood relief camps in district",
            "Notify NDMA Islamabad — escalate to federal response",
            "Broadcast emergency alerts on PTV, Radio Pakistan, and SMS",
            "Shut down river crossings and low-lying road access points",
            "Evacuate livestock and essential assets from flood plains",
        ],
        "immediate_ur": [
            "سیلاب وارننگ جاری کریں — خطرناک علاقوں سے لازمی انخلاء",
            "پاک فوج اور ایف سی کی امدادی ٹیمیں فوری طور پر تعینات کریں",
            "ضلع کے تمام 72+ نامزد سیلابی ریلیف کیمپ کھولیں",
            "این ڈی ایم اے اسلام آباد کو مطلع کریں — وفاقی ردعمل تک پہنچائیں",
            "پی ٹی وی، ریڈیو پاکستان اور ایس ایم ایس پر ہنگامی الرٹ نشر کریں",
            "دریائی گزرگاہیں اور نچلے علاقوں تک سڑک بند کریں",
            "سیلابی میدانوں سے مویشی اور ضروری سامان نکالیں",
        ],
        "agencies_en": [
            "NDMA (federal)", "PDMA", "Pakistan Army", "FC",
            "1122 Rescue", "Civil Aviation (helicopter prep)", "FFC"
        ],
        "agencies_ur": [
            "این ڈی ایم اے (وفاقی)", "پی ڈی ایم اے", "پاک فوج", "ایف سی",
            "1122 ریسکیو", "سول ایوی ایشن (ہیلی کاپٹر)", "ایف ایف سی"
        ],
        "timeline_en": "12–24 hours — IMMEDIATE ACTION REQUIRED",
        "timeline_ur": "12–24 گھنٹے — فوری کارروائی ضروری ہے",
        "evacuation_en": "MANDATORY — all low-elevation zones within 3km of waterways",
        "evacuation_ur": "لازمی — آبی گزرگاہوں سے 3 کلومیٹر کے اندر تمام نچلے علاقے",
        "code": "NDMA-ORANGE",
        "summary_en": "HIGH FLOOD RISK. Mandatory evacuation order. Deploy all federal and provincial rescue assets immediately.",
        "summary_ur": "زیادہ سیلاب خطرہ۔ لازمی انخلاء کا حکم۔ تمام وفاقی اور صوبائی امدادی وسائل فوری تعینات کریں۔",
    },
    "Critical": {
        "immediate_en": [
            "CATASTROPHIC FLOOD IMMINENT — evacuate entire district NOW",
            "Activate National Disaster Response Force (NDRF) deployment",
            "Request international humanitarian aid (UN OCHA, UNICEF)",
            "Establish forward command post at district headquarters",
            "Deploy all available helicopters for stranded population rescue",
            "Block all roads into flood zones — enforce police/army cordon",
            "Pre-position field hospitals at high-elevation assembly points",
            "Activate satellite communication for rural area coordination",
            "Coordinate with WAPDA for emergency reservoir releases schedule",
        ],
        "immediate_ur": [
            "تباہ کن سیلاب آنے والا ہے — ابھی پورے ضلع کا انخلاء کریں",
            "نیشنل ڈیزاسٹر رسپانس فورس (NDRF) تعینات کریں",
            "بین الاقوامی امداد کی درخواست کریں (UN OCHA، UNICEF)",
            "ضلعی ہیڈکوارٹر میں فارورڈ کمانڈ پوسٹ قائم کریں",
            "پھنسی ہوئی آبادی کو نکالنے کے لیے تمام دستیاب ہیلی کاپٹر تعینات کریں",
            "سیلابی علاقوں میں تمام سڑکیں بند کریں — پولیس/فوجی کورڈن نافذ کریں",
            "اونچے مقامات پر فیلڈ ہسپتال تعینات کریں",
            "دیہی علاقوں کی ہم آہنگی کے لیے سیٹلائٹ مواصلات فعال کریں",
            "ہنگامی آبی ذخائر کے اخراج کے شیڈول کے لیے واپڈا سے ہم آہنگی کریں",
        ],
        "agencies_en": [
            "NDMA (Prime Minister briefed)", "All armed forces",
            "PDMA + all divisional administrations", "UN OCHA",
            "UNICEF Pakistan", "WFP Pakistan", "FFC Emergency Cell",
            "Ministry of Interior", "Aviation Division"
        ],
        "agencies_ur": [
            "این ڈی ایم اے (وزیر اعظم کو بریفنگ)", "تمام مسلح افواج",
            "پی ڈی ایم اے + تمام ڈویژنل انتظامیہ", "UN OCHA",
            "UNICEF پاکستان", "WFP پاکستان", "FFC ایمرجنسی سیل",
            "وزارت داخلہ", "ایوی ایشن ڈویژن"
        ],
        "timeline_en": "0–6 hours — CATASTROPHIC RESPONSE REQUIRED",
        "timeline_ur": "0–6 گھنٹے — تباہ کن ردعمل کی ضرورت ہے",
        "evacuation_en": "TOTAL DISTRICT EVACUATION — no exceptions",
        "evacuation_ur": "مکمل ضلع کا انخلاء — کوئی استثناء نہیں",
        "code": "NDMA-RED",
        "summary_en": "CRITICAL: Catastrophic flood event imminent. Full district evacuation. Prime Minister and NDMA briefed. International aid requested.",
        "summary_ur": "انتہائی خطرناک: تباہ کن سیلاب آنے والا ہے۔ مکمل ضلعی انخلاء۔ وزیر اعظم اور این ڈی ایم اے کو بریفنگ۔ بین الاقوامی امداد طلب کی گئی۔",
    },
}


def build_recommendation(
    probability: float,
    district: str,
    confidence_band: str = "medium",
) -> Recommendation:
    """Assemble a full bilingual Recommendation for a given probability + district."""
    risk = probability_to_risk(probability)
    a = ACTIONS[risk]
    affected_count, affected_display = estimate_population(district, risk, probability)

    confidence_pct = {
        "high":   92 if risk in ("Low", "Critical") else 88,
        "medium": 78,
        "low":    65,
    }[confidence_band]

    return Recommendation(
        risk_level=risk,
        risk_level_urdu=RISK_URDU[risk],
        color=RISK_COLORS[risk],
        badge_color=BADGE_COLOR[risk],
        probability=round(probability, 4),
        confidence_pct=confidence_pct,
        affected_population=affected_count,
        affected_population_display=affected_display,
        immediate_actions=a["immediate_en"],
        immediate_actions_urdu=a["immediate_ur"],
        agency_notifications=a["agencies_en"],
        agency_notifications_urdu=a["agencies_ur"],
        preparation_timeline=a["timeline_en"],
        preparation_timeline_urdu=a["timeline_ur"],
        evacuation_priority=a["evacuation_en"],
        evacuation_priority_urdu=a["evacuation_ur"],
        alert_level_code=a["code"],
        summary_en=a["summary_en"],
        summary_ur=a["summary_ur"],
    )