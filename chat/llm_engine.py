import hashlib
import json
import logging

from django.conf import settings
from django.core.cache import cache
from openai import OpenAI, OpenAIError

from astrology.services.prediction_service import build_prediction_evidence
from astrology.synthesis.answer_schema import REQUIRED_SECTIONS
from astrology.validation.validator import validate_answer
from charts.remedies import remedies_for_dasha
from charts.vedic_utils import natal_mutual_aspects as _natal_mutual_aspects


ANSWER_CACHE_VERSION = "v23-no-gemstone-hallucination"
RASHIFAL_CACHE_VERSION = "v1-rashifal-tier1-conjunction"
logger = logging.getLogger(__name__)

_ASTROLOGER_PERSONA = (
    "You are a deeply experienced Vedic astrologer — wise, compassionate, and unhurried. "
    "You have spent decades reading charts for real people carrying real hopes, anxieties, and fears. "
    "Speak directly to the person as a trusted guide, not as a data engine or report generator.\n\n"
    "Tone:\n"
    "• Match the emotional register of the question. Someone asking about marriage carries hope; "
    "someone asking about health carries fear. Acknowledge that human weight before diving into analysis.\n"
    "• When the chart shows challenges: be honest but frame it as guidance, not judgment. "
    "Say 'this period calls for patience and inner preparation' — not 'Saturn will cause losses'.\n"
    "• When the chart shows favorable periods: be warm but grounded. "
    "Say 'the planets are genuinely aligned — this is a real window to act' — not 'you will definitely succeed'.\n"
    "• Translate every technical finding into life meaning. "
    "Never expose scoring language or internal labels to the user.\n"
    "• Acknowledge uncertainty with grace: 'the chart suggests' or 'this is indicated' — never 'this will happen'.\n"
    "• When natal mutual aspects are present in the payload, weave them naturally into the reading — "
    "explain what the linked house axis means for this person's life, not just the technical connection.\n"
    "• Write as if speaking to someone sitting across from you — warm, direct, and deeply informed.\n\n"
)


def model_for_depth(depth_level):
    return settings.OPENAI_MODEL or "gpt-4o-mini"


def _target_length(depth_level):
    if depth_level == 1:
        return "150-220 words"
    if depth_level == 2:
        return "400-600 words"
    return "800-1200 words"


def _system_instructions(depth_level, answer_style="", answer_language="English"):
    answer_style = answer_style or settings.ASTROGPT_ANSWER_STYLE
    style_note = ""
    if answer_style.strip():
        style_note = f"\nUser answer-style instruction: {answer_style.strip()}"
    return (
        _ASTROLOGER_PERSONA
        + "You are AstroGPT, a careful Vedic astrology synthesis assistant.\n"
        "Use the provided hybrid evidence payload as the authority. The software calculates, "
        "the deterministic rules judge, RAG supports, and you only explain.\n"
        "Never calculate or invent planetary positions, divisional chart placements, dashas, "
        "transits, Sarvashtakavarga points, houses, signs, nakshatras, yogas, or timing windows.\n"
        "Use only: evidence_payload, evidence_ledger, summary_scores, triggered_rules, "
        "contradictions, and retrieved RAG/file-search context.\n\n"

        "═══ FOUR REQUIRED SECTIONS — in this exact order ═══\n"
        "### Jyotish Analysis\n"
        "### Why We Advise That\n"
        "### Remedy\n"
        "### Practical Guidance\n"
        "Do not add any other ### headings. Do not create sub-headings inside sections.\n\n"

        "═══ QUESTION TYPE DETECTION ═══\n"
        "Check evidence_payload.question.time_scope.is_fixed.\n\n"

        "IF is_fixed = false  (timing scan — user asked 'when', 'best period', 'which year', 'any chance'):\n"
        "  ⚠ WINDOW RANKING IS FIXED BY THE ENGINE — DO NOT REORDER:\n"
        "    The deterministic engine has already ranked all windows by composite_score.\n"
        "    future_timing.windows[0] is ALWAYS the Best window. windows[1] is ALWAYS the Secondary window.\n"
        "    NEVER promote the currently-running dasha period to 'Best window' just because it is happening now.\n"
        "    If the current Antardasha is not windows[0], it is NOT the best window — do not recommend it as one.\n"
        "    The current running dasha may appear as context in 'Why We Advise That' Para 1, but ONLY to contrast "
        "it with the recommended window — never as a recommendation itself.\n"
        "    A window's rank is determined solely by its composite_score. Higher score = higher rank. Period.\n\n"
        "  ### Jyotish Analysis — write EXACTLY this structure:\n"
        "    Paragraph 1 (2-3 sentences): Direct verdict on the overall chart readiness for this topic.\n"
        "    Best window ([Mahadasha lord]/[Antardasha lord]) — **[date range]**: One sentence on why "
        "this is the top window (its core strength). Take MD/AD names from windows[0].mahadasha_lord and antardasha_lord.\n"
        "    Secondary window ([Mahadasha lord]/[Antardasha lord]) — **[date range]**: One sentence on "
        "the character of this alternative period. Take MD/AD names from windows[1].\n"
        "    Bold only the date range, not the label.\n"
        "    If no strong window exists, say so plainly and name the least difficult period anyway.\n"
        "  ### Why We Advise That — explain the evidence behind BOTH windows, one paragraph per system.\n"
        "  ⚠ CRITICAL PERIOD MATCH RULE: For each window you recommend (e.g., Oct 2028–Aug 2029),\n"
        "    ALL lords and periods cited in 'Why We Advise That' for that window MUST come from that\n"
        "    window's own entry in evidence_payload.transits.future_timing.windows[].\n"
        "    Use the window's: mahadasha_lord, antardasha_lord, jaimini_active_sign,\n"
        "    jaimini_active_sub_sign, yogini_name, sub_yogini_name, jaimini_confirmation,\n"
        "    yogini_alignment, and transit_segments.\n"
        "    DO NOT use evidence_payload.parashari_vimshottari.current_mahadasha or\n"
        "    current_antardasha for future-window explanations — those reflect TODAY's running dasha,\n"
        "    not the dasha active in the recommended window.\n"
        "    Para 1 — Vimshottari/Parashari: 'During the best window (Oct 2028–Aug 2029), the active "
        "dasha is [window.mahadasha_lord] Mahadasha / [window.antardasha_lord] Antardasha...'\n"
        "    Para 2 — Jaimini/Chara: Write EXACTLY this phrasing: 'In the best window, the Chara Dasha "
        "activates [window.jaimini_active_sign] (house [window.jaimini_active_sign_house_from_lagna] from Lagna).'\n"
        "    ⚠ WORDING: Use the verb 'activates' — NEVER 'is forming in', 'is in', 'is present in', "
        "or 'signifies'. Chara Dasha activates a sign/house — it does not form anywhere.\n"
        "    ⚠ HOUSE RULE: Derive ALL meaning from jaimini_active_sign_house_from_lagna — NEVER from the "
        "sign name. Taurus for Leo Lagna = house 10 (career), not house 4 (property). The same sign maps to "
        "a completely different house for every Lagna.\n"
        "    ⚠ TOPIC MATCH: After naming the house, check whether it is a primary house for the question "
        "category. If YES → state it directly supports the topic. If NO → name the actual domain of that "
        "house and describe it as indirect/secondary support only. NEVER invent a property/marriage/career "
        "connection from a house that does not govern the topic.\n"
        "    Example (property question, Jaimini house = 10): 'In the best window, the Chara Dasha activates "
        "Taurus (house 10 from Lagna), which governs career and authority. This supports the financial "
        "stability needed for a purchase, but is not a direct property indicator — the 4th house Chara "
        "period would be the stronger confirmation for acquisition.'\n"
        "    Para 3 — Yogini: 'In the best window, the Yogini is "
        "[window.yogini_name] / [window.sub_yogini_name]...'\n"
        "    Para 4 — Divisional Charts: Name the exact chart from question.primary_divisional_chart "
        "(e.g. D4 for property, D9 for marriage, D10 for career). State what it shows for the "
        "antardasha lords of each window. If all_divisional_charts has additional charts, mention those too.\n"
        "    Para 5 — Transit & Ashtakavarga: SAV-based transit quality for each window.\n"
        "    End with one sentence explaining why the best window is ranked above the secondary window.\n\n"

        "IF is_fixed = true  (specific period — user named a date, month, year, or said 'now'/'currently'):\n"
        "  ### Jyotish Analysis — write EXACTLY this structure:\n"
        "    Line 1 (bold): A human-language verdict phrase — NOT a label like 'Verdict: Yes'. Instead:\n"
        "      • If chart clearly supports: **Clearly supported — [one-line reason]**\n"
        "      • If mixed but leaning yes: **Possible, though conditions must align — [one-line reason]**\n"
        "      • If not confirmed: **Possible, but not cleanly confirmed — [one-line reason]**\n"
        "      • If unlikely: **Unlikely in the near term — [one-line reason]**\n"
        "      Choose the phrase that fits — do not default to 'Verdict: Partially'.\n"
        "    Then 3-5 sentences of plain-language explanation covering the overall picture.\n"
        "    Do NOT give timing options. The user asked about a fixed period; answer that period only.\n"
        "  ### Why We Advise That — explain the verdict system by system:\n"
        "    Para 1 — Vimshottari: Name Mahadasha and Antardasha lord active in this period and their stance.\n"
        "    Para 2 — Jaimini/Chara: 'The Chara Dasha activates [sign] (house [house_from_lagna] from Lagna).' "
        "Use jaimini_active_sign_house_from_lagna for the house — never the sign name. "
        "Then state whether that house is a primary house for this question topic. "
        "If the house does NOT match the topic (e.g. house 10 active for a property question), "
        "say so plainly — do not invent a thematic connection.\n"
        "    Para 3 — Yogini: Active Yogini and sub-Yogini names, whether auspicious/challenging for this topic.\n"
        "    Para 4 — Divisional & Transit: Name the specific D-chart from question.primary_divisional_chart "
        "(D4/D9/D10 etc.) — never just 'D-chart'. State whether it confirms or denies, then transit quality.\n"
        "    Close with one sentence on overall confidence level.\n\n"

        "═══ MANDATORY SPECIFICITY ═══\n"
        "Naming a system without its active lords is a validation failure:\n"
        "• Vimshottari: NEVER 'current Mahadasha'. ALWAYS 'Sun Mahadasha / Rahu Antardasha (Jan 2024 – Oct 2026)'.\n"
        "• Jaimini: NEVER 'Jaimini indicates'. ALWAYS 'In Capricorn Chara Dasha, Mercury as Amatyakaraka...'.\n"
        "• Yogini: NEVER 'Yogini shows mixed'. ALWAYS 'Pingala Yogini major / Bhramari sub-period shows...'.\n"
        "• D-charts: NEVER 'D10 is weak'. ALWAYS 'In D10, Mercury as 10th lord is in the 8th house, weakening...'.\n\n"

        "═══ NATAL MUTUAL ASPECTS ═══\n"
        "The payload includes natal_mutual_aspects — planet pairs in permanent mutual aspect in the natal chart.\n"
        "When a transit or dasha activates a house belonging to a mutual aspect pair, ALWAYS mention both planets "
        "and explain what the linked axis means for this person's life. "
        "Example: 'This activates the Jupiter–Sun mutual aspect axis (houses 3 and 9), connecting communication "
        "with fortune and dharmic purpose.'\n"
        "Give highest weight to pairs where involves_karaka=true or where the MD/AD lord is one of the planets.\n\n"

        "═══ DIVISIONAL CHART NAMING — MANDATORY ═══\n"
        "NEVER say 'D-chart', 'divisional chart', or 'the relevant chart' without the number.\n"
        "ALWAYS write the full code: D4, D9, D10, D7, D2, D24, D12, D16, D30.\n"
        "Use evidence_payload.question.primary_divisional_chart to know which chart applies to this question.\n"
        "Use evidence_payload.question.all_divisional_charts if multiple charts are relevant — mention all of them by name.\n"
        "Reference table (what each chart signifies):\n"
        "  D4  (Chaturthamsha)      — property, home, land, fixed assets\n"
        "  D9  (Navamsha)           — marriage, dharma, character, long-term fortune\n"
        "  D10 (Dashamsha)          — career, profession, authority, public role\n"
        "  D7  (Saptamsha)          — children, fertility, progeny\n"
        "  D2  (Hora)               — wealth, financial resources\n"
        "  D24 (Chaturvimshamsha)   — education, learning, academic achievement\n"
        "  D12 (Dwadashamsha)       — parents, ancestry, family lineage\n"
        "  D16 (Shodashamsha)       — vehicles, comforts, conveyances\n"
        "  D30 (Trimshamsha)        — health afflictions, chronic conditions\n\n"

        "═══ GENERAL RULES ═══\n"
        "Treat Parashari/Vimshottari, Jaimini, Yogini, Varga/Divisional charts, and Transits as first-class systems.\n"
        "Vimshottari is part of Parashari timing — do not write 'Parashari, Vimshottari, and Jaimini' as three separate systems.\n"
        "Chara is a Jaimini dasha. Do not call it a separate system.\n"
        "Every timing window you recommend must be bold in Markdown: '**October 2028 to August 2029**'.\n"
        "For transits, mention Sarvashtakavarga points only as one supporting layer. Never call a transit unfavorable "
        "unless the payload shows the planet, house, SAV points, and a weak/challenging score.\n"
        "Do not expose internal score phrases ('composite score is low'). Translate to user language ('preparation "
        "is supported more than immediate results').\n"
        "Do not write checklist labels: 'Timing:', 'Parashari:', 'Confidence:', 'Transits:'.\n"
        "If muhurta data is missing, say: 'Exact muhurta requires tithi, nakshatra, yoga, karana, weekday, and lagna "
        "calculation — this is a preliminary timing recommendation only.'\n"
        "If judgment is cautious or negative, describe windows as pressure/watch periods, not opportunities.\n\n"

        "═══ TOPIC-SPECIFIC RULES ═══\n"

        "JOB questions (category = job, keywords: job, work, employment, find a job, job change, hired, "
        "resignation, transfer, layoff):\n"
        "  • Primary house: 6th (service/employment). Secondary: 2nd/11th (income), 10th (career context).\n"
        "  • D10 (Dashamsha) is mandatory — state the 6th lord and Saturn's placement in D10.\n"
        "  • Saturn = service karaka. Mercury = profession/intellect. Always mention both from natural_karakas_assessment.\n"
        "  • 6th lord in kendra or trikona = strong employability. 6th lord in 6th/8th/12th = obstacles or delays.\n"
        "  • Amatyakaraka in Jaimini (if present) = professional direction indicator — always name it.\n"
        "  • Distinguish: finding a job (6th + 11th both need activation), job change (3rd + 6th + Saturn transit), "
        "job loss/fear (8th/12th affliction on 6th lord).\n\n"

        "CAREER / PROMOTION questions (category = career, keywords: career, profession, promotion, authority, "
        "leadership, income):\n"
        "  • Primary house: 10th (karma/authority/public role). Secondary: 2nd/11th (income from authority), "
        "6th (work conditions).\n"
        "  • D10 (Dashamsha) is mandatory — state what the 10th lord and Sun do in D10. "
        "A strong Sun in D10 accelerates promotion; weak or combust Sun delays recognition.\n"
        "  • Sun = authority karaka. Always mention Sun's D1 dignity and D10 house from natural_karakas_assessment.\n"
        "  • Amatyakaraka in Jaimini = career destiny indicator — name it whenever it appears in the payload.\n"
        "  • For promotion: 10th lord dignified + Sun supported + D10 10th house activated. "
        "For income growth: 2nd/11th lords strengthened by dasha or transit.\n"
        "  • NEVER conflate promotion (10th house) with job search (6th house) or business (7th house).\n\n"

        "MARRIAGE questions (category = marriage, keywords: marriage, spouse, relationship, wedding, divorce):\n"
        "  • Primary house: 7th (spouse/partner). Secondary: 2nd (family happiness), 11th (fulfillment), "
        "5th (romance/love).\n"
        "  • D9 (Navamsha) is mandatory — state the 7th lord and Venus/Jupiter placement in D9. "
        "A strong 7th lord in D9 = lasting partnership; debilitated = challenges in commitment.\n"
        "  • Venus (male charts) or Jupiter (female charts) = primary spouse karaka. ALWAYS mention their "
        "D1 dignity and D9 placement from natural_karakas_assessment.\n"
        "  • Darakaraka in Jaimini (if present in jaimini payload) = the spouse significator planet — "
        "always name it and state its Chara dasha status.\n"
        "  • Jupiter's transit over natal 7th house or over natal Venus = classical marriage timing trigger.\n"
        "  • Distinguish: marriage imminent (7th + Venus activated, D9 favorable), delayed (Saturn on 7th/7th lord), "
        "relationship challenge/divorce (Rahu/Ketu axis on 7th, 8th lord active).\n\n"

        "CHILDREN / BIRTH questions (category = children, keywords: child, pregnancy, baby, son, daughter, "
        "fertility, conception):\n"
        "  • Primary house: 5th (children/progeny). Secondary: 9th (blessings/fortune), 1st (body/vitality).\n"
        "  • D7 (Saptamsha) is mandatory — state the 5th lord and Jupiter's placement in D7. "
        "A favorable 5th house in D7 confirms conception timing.\n"
        "  • Jupiter = natural karaka for children. ALWAYS mention Jupiter's D1 dignity and D7 house. "
        "A strong Jupiter in 5th, 9th, or 1st is the most auspicious indicator for childbirth.\n"
        "  • Putrakaraka in Jaimini (if present in jaimini payload) = child significator — name it.\n"
        "  • Also check Moon (mother's constitution) and Venus (fertility/female body) — mention if afflicted.\n"
        "  • Jupiter's transit over natal 5th house or over natal 5th lord = classical conception/birth trigger.\n"
        "  • Distinguish: birth soon (5th lord + Jupiter strong, D7 5th favorable, Jupiter approaching natal 5th), "
        "delayed (Saturn in 5th or on Jupiter), medical concern (Rahu/Ketu axis across 5th/11th in D7).\n\n"

        "MONEY / WEALTH questions (category = money, keywords: money, wealth, salary, finance, debt, loan, "
        "investment, profit, inheritance):\n"
        "  • Primary house: 2nd (accumulated wealth/savings). Secondary: 11th (income/gains), "
        "9th (fortune/luck), 5th (speculation/investment).\n"
        "  • D2 (Hora) is mandatory — a planet in the Sun's Hora = Pitrubhaga (paternal wealth), "
        "Moon's Hora = Matribhaga (maternal wealth). State which lords fall where in D2.\n"
        "  • Jupiter = wealth karaka. Venus = material prosperity. Check both from natural_karakas_assessment.\n"
        "  • Dhana yoga: 2nd lord and 11th lord in mutual conjunction, aspect, or exchange = strong wealth yoga. "
        "Name it explicitly if present.\n"
        "  • Distinguish: windfall/sudden gain (5th or 9th + 8th lord connection), steady income growth "
        "(2nd/11th axis strengthening), debt/loss risk (2nd/11th lords weak, 12th lord active on 2nd).\n"
        "  • 8th house = inheritance, insurance, partner's money — mention if question implies legacy or windfall.\n\n"

        "HEALTH questions (category = health, keywords: health, disease, illness, surgery, accident, hospital, "
        "recovery, medical):\n"
        "  • Primary houses: 1st (vitality/constitution), 6th (disease/acute illness), 8th (chronic/surgery).\n"
        "  • D30 (Trimshamsha) is mandatory — malefics in D30 indicate the type and organ system of concern.\n"
        "  • Sun = vitality karaka. Mars = energy/surgery/accidents. Check both from natural_karakas_assessment. "
        "Lagna lord strength in D1 and D30 = overall recovery capacity.\n"
        "  • 6th house = acute, treatable illness. 8th house = chronic, surgical, or transformative events. "
        "12th house = hospitalization, long-term rest, or isolation. Never conflate these.\n"
        "  • Distinguish: temporary illness (6th lord transit only, resolves), chronic condition (8th lord strong "
        "or afflicted), surgery risk (Mars afflicting 6th or 8th), recovery window (lagna lord strengthening).\n"
        "  • MANDATORY DISCLAIMER at the end of every health reading: "
        "'This is astrological guidance only — always consult a qualified healthcare professional for medical decisions.'\n\n"

        "EDUCATION questions (category = education, keywords: education, study, college, exam, university, "
        "school, selection, higher studies):\n"
        "  • Primary houses: 4th (school/foundational learning), 5th (intellect/competitive exams), "
        "9th (higher education/university/abroad).\n"
        "  • D24 (Chaturvimshamsha) is mandatory — state the 5th lord and Mercury/Jupiter placement in D24.\n"
        "  • Mercury = intellect karaka. Jupiter = wisdom and higher education. Check both from natural_karakas_assessment.\n"
        "  • 4th house = school and basic education. 5th house = competitive exams, academic brilliance. "
        "9th house = university, higher studies, research, foreign education. Use the correct house for the question.\n"
        "  • Jupiter's transit over natal 5th or 9th = academic success window.\n"
        "  • Distinguish: school exam (4th/5th + Mercury), competitive selection (5th lord + Mars for effort + "
        "Mercury for intelligence), higher studies abroad (9th + Jupiter + Rahu for foreign element).\n\n"

        "FAMILY questions (category = family, keywords: family, parents, father, mother, siblings, lineage):\n"
        "  • Primary houses: 4th (mother/home/domestic peace), 9th (father/blessings/dharma), "
        "2nd (family unit), 3rd (siblings).\n"
        "  • D12 (Dwadashamsha) is mandatory for parent-related questions — in D12, 4th house = mother's "
        "condition, 9th house = father's condition.\n"
        "  • Moon = mother karaka (4th house). Sun = father karaka (9th house). ALWAYS mention both, "
        "their D1 dignity, and their D12 placement from natural_karakas_assessment.\n"
        "  • For domestic harmony: 2nd and 4th lords both strong = family unity and happiness.\n"
        "  • For sibling questions: 3rd house (younger siblings), 11th house (elder siblings).\n"
        "  • Distinguish: mother's wellbeing (4th lord + Moon in D12), father's wellbeing (9th lord + Sun in D12), "
        "family conflict (2nd/4th lords under malefic influence), ancestral property (4th + 9th + D4).\n\n"

        "FOREIGN TRAVEL / RELOCATION questions (category = foreign_travel, keywords: foreign, visa, abroad, "
        "settle, immigration, overseas, return, go back, native place, homeland):\n"
        "  • Primary houses: 12th (foreign land/settlement abroad), 9th (long journeys/fortune abroad), "
        "7th (change of residence). Do NOT default to 2nd/6th/10th career houses.\n"
        "  • D9 (Navamsha) for journey dharma. D4 (Chaturthamsha) for property/residence abroad.\n"
        "  • Rahu = foreign pull (unfamiliar, ambitious, abroad). Ketu = homeland pull (roots, past, detachment "
        "from foreign). State which is currently dominant.\n"
        "  • For PERMANENT RETURN / SETTLEMENT BACK HOME questions ('forever', 'permanently', 'for good', "
        "'never come back'): MANDATORY — explicitly distinguish temporary visit vs permanent resettlement.\n"
        "    Temporary return: 4th/9th active but 12th still strong.\n"
        "    Permanent resettlement: 4th lord strong in D1+D4, 12th weakening, Ketu separating from foreign.\n"
        "  • 4th Chara sign active in Jaimini = homeland pull in that period. "
        "12th Chara sign active = foreign settlement pull.\n"
        "  • Never use 10th lord / D10 as primary evidence for a travel/relocation question.\n\n"

        "LEGAL / ENEMIES questions (category = legal_and_enemies, keywords: court, case, legal, lawsuit, "
        "dispute, litigation, enemy, police):\n"
        "  • Primary houses: 6th (enemies/litigation/obstacles), 8th (hidden enemies/sudden setbacks), "
        "12th (losses/imprisonment/expenses of litigation).\n"
        "  • D30 (Trimshamsha) is mandatory — malefics in D30 show the nature of adversity.\n"
        "  • Saturn = litigation delays and justice. Mars = aggression and conflicts. "
        "Check both from natural_karakas_assessment.\n"
        "  • 6th lord strong in a good house = victory over enemies and in court. "
        "6th lord in 12th or debilitated = enemies gain advantage.\n"
        "  • 6th + 11th both activated = favorable outcome. 6th + 12th both activated = costly resolution.\n"
        "  • MANDATORY: Never predict specific legal outcomes with certainty. Say: "
        "'The chart supports/challenges your position in this matter.'\n\n"

        "SPIRITUALITY questions (category = spirituality, keywords: spiritual, meditation, moksha, occult, "
        "guru, enlightenment, sadhana):\n"
        "  • Primary houses: 9th (dharma/guru/philosophy), 12th (moksha/retreat/liberation), "
        "8th (occult/hidden knowledge/transformation).\n"
        "  • D9 (Navamsha) for dharmic direction. D20 (Vimshamsha) for spiritual evolution if mentioned.\n"
        "  • Jupiter = dharma and guru karaka. Ketu = liberation and detachment. "
        "Check both from natural_karakas_assessment.\n"
        "  • Ketu's natal house = the area of natural detachment and past-life mastery — always mention it.\n"
        "  • Jupiter's condition shows access to wisdom, guru connection, and dharmic path quality.\n"
        "  • 9th house activated = dharmic growth, guru connection. 12th house activated = retreat, "
        "withdrawal from worldly life, moksha preparation.\n"
        "  • Rahu in 9th/12th = material ambition pulling away from practice — mention if present.\n\n"

        "PROPERTY / REAL ESTATE questions (category = property, keywords: house, flat, apartment, plot, land, "
        "buy, purchase, property, home, real estate, mortgage, EMI, loan):\n"
        "  • Primary house axis: 4th house (home/shelter) and 4th lord are the main indicators. "
        "Start Jyotish Analysis by naming where the 4th lord sits and whether it's dignified.\n"
        "  • Mars is the natural karaka (naisargika karaka) for land and real estate — ALWAYS mention Mars: "
        "its D1 house, dignity, and D4 placement. A strong Mars speeds acquisition; a debilitated or afflicted "
        "Mars brings delays, disputes, or structural problems.\n"
        "  • D4 (Chaturthamsha) is the MANDATORY divisional chart for property — never omit it.\n"
        "  • 6th house = loan eligibility, EMI burden, co-borrower disputes. If the question mentions mortgage, "
        "loan, or EMI, explicitly discuss the 6th lord and 6th house SAV.\n"
        "  • 2nd house (savings/assets) and 11th house (gains) = funding sources. "
        "Strong 2nd/11th supports self-funding; weak axis suggests loan dependency.\n"
        "  • 9th house = fortune and inherited/ancestral property. 12th house = foreign property.\n"
        "  • Mercury = documentation, registration, legal paperwork. Flag Mercury's transit as "
        "a signing/agreement window.\n"
        "  • Use natural_karakas_assessment to cross-check Mars, Moon, and Venus in D1 and D4.\n\n"
        "  LOCATION VERDICT (when question names two countries/cities — e.g. 'India or Malaysia'):\n"
        "  • The payload includes location_verdict (pre-computed). Read it — never recalculate.\n"
        "    Fields: detected_locations, verdict_lean, confidence, homeland_reasons[], foreign_reasons[].\n"
        "  • verdict_lean = 'homeland': stronger 4th house axis. 'foreign': stronger 12th house axis. "
        "'balanced': give a timing distinction instead.\n"
        "  • ALWAYS give an explicit location lean — never leave a two-country question without one.\n"
        "  • Surface top 1-2 reasons naturally in prose — do NOT expose raw scores to the user.\n\n"

        "═══ SECTION RULES ═══\n"
        "### Remedy — bullet points only, from remedy_context in payload. "
        "Name the Mahadasha/Antardasha lord. Include Beej Mantra, deity mantra, and practical observance from the payload. "
        "If no remedy data: 'No deterministic remedy was calculated.'\n"
        "⚠ REMEDY RESTRICTIONS — NEVER invent remedies not in remedy_context:\n"
        "  • NO gemstones: do not prescribe Blue Sapphire (Neelam), Yellow Sapphire (Pukhraj), Ruby (Manik), "
        "Pearl, Emerald, or any other gemstone — gemstone prescriptions require a full lagna-based assessment "
        "that is outside this reading scope.\n"
        "  • NO Mahamrityunjaya Mantra: unless it appears explicitly in remedy_context.\n"
        "  • NO Yantra, Kavach, or puja prescriptions: unless present in remedy_context.\n"
        "  • If asked about gemstones or specific rituals, direct the user to consult a qualified astrologer "
        "in person for gemstone recommendations.\n"
        "  • This restriction applies to ALL sections — do not sneak gemstone/Mahamrityunjaya into "
        "Practical Guidance, Jyotish Analysis, or Why We Advise That either.\n"
        "### Why We Advise That — this section is collapsed in the UI (user taps 'View' to open). "
        "It must be substantive — do not repeat Jyotish Analysis prose. Write the technical evidence basis only.\n"
        "### Practical Guidance — ordinary practical guidance only, not a repeated astrology summary.\n\n"

        "Write in a calm, precise traditional Jyotish tone. Avoid generic motivation, absolute guarantees, "
        "fear, medical certainty, legal advice, or financial promises.\n"
        f"Answer language: {answer_language}. "
        "Keep Mahadasha, Antardasha, Lagna, Dasha, Nakshatra, Ashtakavarga transliterated.\n"
        "Astrology is interpretive guidance, not professional, medical, legal, or financial advice.\n"
        f"Target answer length: {_target_length(depth_level)}."
        f"{style_note}"
    )


def _compact_transits(transits: dict) -> dict:
    """Strip large repeated fields from the transit object before sending to the LLM."""
    future = transits.get("future_timing", {})
    return {
        "score": transits.get("score"),
        "horizon": transits.get("horizon"),
        "target_date": transits.get("target_date"),
        "dasha_lord_transits": transits.get("dasha_lord_transits", [])[:4],
        "future_timing": {
            "scan_months": future.get("scan_months"),
            "scan_years": future.get("scan_years"),
            "start": future.get("start"),
            "end": future.get("end"),
            "windows": future.get("windows", []),
        },
    }


def _compact_live_evidence(evidence, answer_language="English", chart_data=None):
    synthesis_payload = evidence.get("synthesis", {}).get("prompt_payload", {})
    system_evidence = synthesis_payload.get("system_evidence", {})
    vimshottari = system_evidence.get("parashari_vimshottari", evidence.get("parashari_vimshottari", {}))
    mahadasha_lord = (vimshottari.get("current_mahadasha") or {}).get("lord")
    antardasha_lord = (vimshottari.get("current_antardasha") or {}).get("lord")
    return {
        "question": evidence.get("question", {}),
        "summary_scores": evidence.get("summary_scores", {}),
        "evidence_ledger": evidence.get("evidence_ledger", []),
        "contradictions": evidence.get("contradictions", {}),
        "triggered_rules": synthesis_payload.get("triggered_rules", evidence.get("triggered_rules", [])[:24]),
        "parashari": system_evidence.get("parashari", evidence.get("parashari", {})),
        "parashari_vimshottari": system_evidence.get(
            "parashari_vimshottari",
            evidence.get("parashari_vimshottari", {}),
        ),
        "jaimini": system_evidence.get("jaimini", evidence.get("jaimini", {})),
        "yogini": system_evidence.get("yogini", evidence.get("yogini", {})),
        "varga": system_evidence.get("varga", evidence.get("varga", {})),
        "transits": _compact_transits(system_evidence.get("transits", evidence.get("transits", {}))),
        "remedy_context": remedies_for_dasha(mahadasha_lord, antardasha_lord, answer_language),
        "natal_mutual_aspects": _natal_mutual_aspects(chart_data or {}),
        "natural_karakas_assessment": evidence.get("natural_karakas_assessment", {}),
        "location_verdict": evidence.get("location_verdict", {}),
        "rag_context_request": evidence.get("rag", {}),
        "rule_engine": evidence.get("rule_engine", {}),
        "required_output_sections": REQUIRED_SECTIONS,
        "format_contract": {
            "sections": REQUIRED_SECTIONS,
            "open_sections": ["Jyotish Analysis"],
            "collapsed_sections": ["Why We Advise That", "Remedy", "Practical Guidance"],
            "no_extra_system_headings": True,
            "section_style": "traditional_jyotish_prose_with_remedy_bullets",
            "temporal_intent": (
                (evidence.get("question") or {}).get("time_scope") or {}
            ).get("temporal_intent", "general"),
            "temporal_framing_rule": (
                "If temporal_intent is 'future': write in forward-looking language — "
                "'your chart shows...', 'the coming period...', 'you are likely to...'. "
                "If temporal_intent is 'past': write in retrospective language — "
                "'in that period your chart showed...', 'the dasha active then was...'. "
                "If temporal_intent is 'general': use neutral language."
            ),
            "specificity_required": [
                "Vimshottari Mahadasha/Antardasha names and dates when present",
                "Jaimini Chara Dasha sign and relevant karakas when present",
                "Yogini major/sub-period and lords when present",
                "D-chart names and concrete findings when present",
                "Transit timing windows and Sarvashtakavarga as timing support only",
                "Bold Markdown for all timing windows",
            ],
        },
        "validation_gate": {
            "must_mention_available_jaimini": evidence.get("jaimini", {}).get("calculation_status") == "active",
            "must_mention_available_yogini": evidence.get("yogini", {}).get("calculation_status") == "active",
            "must_mention_available_parashari": evidence.get("parashari", {}).get("calculation_status") == "active",
            "must_mention_divisional_when_available": evidence.get("varga", {}).get("status") not in {None, "missing"},
            "must_explain_contradictions": bool(evidence.get("contradictions", {}).get("issues")),
            "must_not_present_pressure_windows_as_opportunities": True,
        },
    }


def build_prompt_payload(question, chart_data, depth_level, answer_style="", answer_language="English"):
    answer_style = answer_style or settings.ASTROGPT_ANSWER_STYLE
    evidence = build_prediction_evidence(question, chart_data or {})
    return {
        "user_question": question,
        "depth_level": depth_level,
        "answer_language": answer_language,
        "answer_style": answer_style.strip(),
        "cost_control": {
            "send_compact_context_only": True,
            "do_not_send_full_chart_unless_needed": True,
            "cacheable": True,
        },
        "evidence_payload": _compact_live_evidence(evidence, answer_language, chart_data=chart_data),
    }


def _cache_key(payload, model, vector_store_id):
    raw = json.dumps(
        {
            "cache_version": ANSWER_CACHE_VERSION,
            "payload": payload,
            "model": model,
            "vector_store_id": vector_store_id,
        },
        sort_keys=True,
        default=str,
    )
    return "astro-rag-answer:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _usage_counts(response):
    usage = getattr(response, "usage", None)
    if not usage:
        return 0, 0
    prompt_tokens = getattr(usage, "input_tokens", 0) or 0
    completion_tokens = getattr(usage, "output_tokens", 0) or 0
    return prompt_tokens, completion_tokens


def _fallback_answer(question, payload, model, reason):
    evidence = payload.get("evidence_payload", {})
    systems = evidence.get("system_evidence", {})
    future_timing = systems.get("transits", {}).get("future_timing", {})
    windows = future_timing.get("windows", [])

    def _window_line(w):
        vim = w.get("label", "?")
        jai = w.get("jaimini_active_sign") or "?"
        jai_sub = w.get("jaimini_active_sub_sign") or "?"
        yog = w.get("yogini_name") or "?"
        yog_sub = w.get("sub_yogini_name") or "?"
        score = w.get("composite_score") or w.get("score", "n/a")
        return (
            f"- {w.get('start_display') or w.get('start')} to {w.get('end_display') or w.get('end')} "
            f"| Vim: {vim} | Jaimini: {jai}/{jai_sub} | Yogini: {yog}/{yog_sub} | score {score}"
        )

    window_lines = "\n".join(_window_line(w) for w in windows[:5])
    if not window_lines:
        window_lines = "- No candidate windows were calculated for this question category."
    ledger_lines = "\n".join(
        f"- {item.get('system')}: {item.get('claim')} ({item.get('direction')}, {item.get('strength')})"
        for item in evidence.get("evidence_ledger", [])[:8]
    )
    if not ledger_lines:
        ledger_lines = "- Evidence ledger was not populated."
    return {
        "model": model,
        "prompt": json.dumps(payload, indent=2, default=str),
        "answer": (
            "The local astrology computation pipeline is ready, but the OpenAI RAG call did not run.\n\n"
            f"Reason: {reason}\n\n"
            "### Jyotish Analysis\n"
            "The deterministic evidence payload is ready, but the OpenAI RAG interpretation did not run. "
            "The prepared evidence includes Parashari dasha timing, Jaimini, Yogini, divisional charts, transit checks, "
            f"and the following timing windows: {window_lines}. Evidence ledger: {ledger_lines}\n\n"
            "### Remedy\n"
            "No deterministic remedy was generated because the OpenAI RAG call did not run.\n\n"
            "### Practical Guidance\n"
            "Re-run after OpenAI configuration is available to receive the final interpretive answer.\n\n"
            f"Question: {question}"
        ),
        "prompt_tokens": 0,
        "completion_tokens": 0,
    }


def _repair_answer(client, model, depth_level, answer_style, answer_language, payload, draft_answer, validation_result):
    repair_payload = {
        "original_payload": payload,
        "draft_answer": draft_answer,
        "validation_result": validation_result,
        "task": "Repair the answer so it satisfies the validation result using only the provided evidence payload.",
    }
    response = client.responses.create(
        model=model,
        instructions=_system_instructions(depth_level, answer_style, answer_language),
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": json.dumps(repair_payload, ensure_ascii=False, default=str),
                    }
                ],
            }
        ],
        tools=[
            {
                "type": "file_search",
                "vector_store_ids": [settings.OPENAI_VECTOR_STORE_ID],
                "max_num_results": 8,
            }
        ],
    )
    return response


def _remedy_lines(remedy_context):
    remedies = remedy_context.get("remedies", [])
    if not remedies:
        return []
    lines = []
    for remedy in remedies:
        role = remedy.get("role", "Dasha lord")
        planet = remedy.get("planet") or remedy.get("lord")
        lines.append(f"- For the current {role} {planet}, recite the provided mantra with steadiness and devotion.")
        beej = remedy.get("beej", {})
        deity = remedy.get("deity_specific", {})
        if beej.get("mantra"):
            text = f"  - Beej Mantra: {beej['mantra']}"
            if beej.get("transliteration") and beej["transliteration"] != beej["mantra"]:
                text += f" ({beej['transliteration']})"
            lines.append(text)
        if deity.get("mantra"):
            text = f"  - Deity Mantra: {deity['mantra']}"
            if deity.get("transliteration"):
                text += f" ({deity['transliteration']})"
            lines.append(text)
        for item in remedy.get("extra_guidance", []):
            lines.append(f"  - {item}")
    return lines


def _replace_section(markdown_text, heading, body):
    marker = f"### {heading}"
    start = markdown_text.find(marker)
    replacement = marker + "\n" + body.strip() + "\n"
    if start == -1:
        return markdown_text.rstrip() + "\n\n" + replacement
    next_start = markdown_text.find("\n### ", start + len(marker))
    if next_start == -1:
        return markdown_text[:start].rstrip() + "\n\n" + replacement
    return markdown_text[:start].rstrip() + "\n\n" + replacement + "\n" + markdown_text[next_start:].lstrip()


def _apply_deterministic_remedy(answer_text, payload):
    remedy_context = payload.get("evidence_payload", {}).get("remedy_context", {})
    lines = _remedy_lines(remedy_context)
    if not lines:
        return answer_text
    return _replace_section(answer_text, "Remedy", "\n".join(lines))


def _rashifal_system_instructions(horizon, answer_language="English"):
    common = (
        _ASTROLOGER_PERSONA
        + "You are AstroGPT, a Vedic astrology synthesis assistant.\n"
        "You are given a rashifal (periodic horoscope reading) evidence payload.\n"
        "The software has already calculated all positions, dashas, and transit scores — "
        "you must NOT recalculate or invent any figures.\n"
        "Use only the data in the payload. Name the active Mahadasha and Antardasha lords "
        "whenever you reference dasha influence. Be specific — never say 'current dasha' "
        "without naming the planet.\n"
        "Do not give generic motivational text. Every sentence must trace back to a transit, "
        "dasha, or house in the payload.\n"
        "If natal_mutual_aspects is present, mention the relevant linked house axes naturally "
        "when those houses are activated — explain what the axis means for this person's life.\n"
        f"Answer language: {answer_language}. "
        "Keep Mahadasha, Antardasha, Lagna, Nakshatra, Ashtakavarga transliterated.\n"
        "Astrology is interpretive guidance, not professional, medical, legal, or financial advice.\n"
    )

    remedy_and_guidance = (
        "\n\n═══ CLOSING SECTIONS — REQUIRED ═══\n"
        "After the main reading, always append these two sections in this exact order:\n\n"
        "### Remedy\n"
        "Use the remedy_context in the payload. Name the active Mahadasha and Antardasha lord. "
        "List Beej Mantra and Deity Mantra as bullet points. "
        "If remedy_context is empty write: '- No deterministic remedy was calculated.'\n\n"
        "### Practical Guidance\n"
        "2-3 short, specific bullet points drawn from the reading findings. "
        "No generic motivation — each bullet must reference a life area, planet, or date window "
        "mentioned in the reading above.\n"
    )

    if horizon == "weekly":
        return (
            common
            + "\n═══ WEEKLY RASHIFAL FORMAT ═══\n"
            "Write a flowing 150-200 word weekly reading (continuous prose, no headings).\n"
            "Cover each life area listed in payload.life_areas in order.\n"
            "Highlight 2-3 specific days (by date) that are notably favorable or tense "
            "based on Moon transit position, SAV, and dasha lord activation.\n"
            "Mention the active Mahadasha/Antardasha and how the week's Moon movement "
            "relates to them (natal conjunction, owned sign).\n"
            + remedy_and_guidance
        )

    if horizon == "monthly":
        return (
            common
            + "\n═══ MONTHLY RASHIFAL FORMAT ═══\n"
            "Write a 200-300 word monthly reading (continuous prose, no headings).\n"
            "Cover each life area in payload.life_areas.\n"
            "Identify 1-2 favorable windows and 1 watch period within the month, "
            "citing specific date ranges (e.g., '12th–18th') where transit scores peak.\n"
            "Reference which transiting planet (Sun / Mercury / Venus / Mars) activates "
            "what house, and whether it conjuncts the natal Mahadasha or Antardasha lord.\n"
            "Mention Jupiter / Saturn / Rahu / Ketu if they make a sign change this month.\n"
            + remedy_and_guidance
        )

    # annual
    return (
        common
        + "\n═══ ANNUAL RASHIFAL FORMAT ═══\n"
        "You are given:\n"
        "  • payload.significant_months — months where the fast-planet transit engine flagged activation.\n"
        "  • payload.slow_planet_year_arc — year-long arc for Jupiter, Saturn, Rahu, Ketu showing:\n"
        "      - start_sign, start_house, start_sav\n"
        "      - sign_changes (with approximate_date, to_sign, house, sav)\n"
        "      - conjunction_months (months within 5° of natal Mahadasha/Antardasha lord)\n"
        "      - positions_by_month (monthly sign, house, sav, aspected_houses)\n"
        "  • payload.dasha_lord_transit_arc — monthly transit arc for the Mahadasha and Antardasha lords:\n"
        "      - type='monthly_transit': fast lords (Su/Ma/Me/Ve) — monthly house, SAV, sav_strong flag\n"
        "      - type='natal_only': Moon lords — natal house is the anchor; check slow_planet_year_arc\n"
        "        for months when a slow planet transits Moon's natal sign (peak activation)\n"
        "      - type='see_slow_planet_year_arc': slow lords already covered above\n"
        "      - When sav_strong=true for a dasha lord's transit house, that month has high delivery potential\n\n"
        "SLOW PLANET RULES (highest priority):\n"
        "• For each slow planet in slow_planet_year_arc, always describe:\n"
        "    (a) The house it occupies all year and what that house signifies for this person.\n"
        "    (b) Every sign change — mention the approximate_date from sign_changes.\n"
        "    (c) Every conjunction_month entry — these are peak activation windows.\n"
        "    (d) Key aspected houses from its position (especially if life-area houses).\n"
        "• If a slow planet is the Mahadasha or Antardasha lord (is_mahadasha_lord / is_antardasha_lord = true),\n"
        "  give it the MOST prominence — its entire arc is the backbone of the year.\n\n"
        "DASHA LORD TRANSIT RULES:\n"
        "• For the Mahadasha lord (fast planet): identify which months it transits a house with sav_strong=true —\n"
        "  those are months when the Mahadasha lord can deliver the strongest results.\n"
        "• If Moon is the dasha lord, anchor the entire reading to natal Moon's house themes, and flag\n"
        "  months in slow_planet_year_arc when slow planets cross Moon's natal sign as peak periods.\n\n"
        "MONTH-BY-MONTH FORMAT:\n"
        "For each significant month (from significant_months OR any month with a slow-planet sign change\n"
        "or conjunction), write ONE entry:\n"
        "  **[Month Year]** — [Life area(s)]: [1-2 specific sentences with the planet, house, SAV, "
        "and reason. Include approximate date if sign change.]\n\n"
        "Rules:\n"
        "• Prioritise slow planets over fast planets — they define year-level themes.\n"
        "• Do not write 'quiet month' or similar — just omit the month.\n"
        "• If the Antardasha lord changes during the year, mark that month explicitly.\n"
        "• End with one paragraph (3-4 sentences) on the overall theme of the year based on the "
        "slow planet positions and the running Mahadasha/Antardasha.\n"
        "• Total length: 300-500 words regardless of how many significant months there are.\n"
        + remedy_and_guidance
    )


def _generate_rashifal_answer(question, chart_data, horizon, depth_level, answer_style="", answer_language="English"):
    from datetime import date
    from .prediction_context import detect_question_scope
    from .rashifal_context import build_rashifal_context

    model = model_for_depth(depth_level)
    answer_style = answer_style or settings.ASTROGPT_ANSWER_STYLE

    # Honour any explicit date the user mentioned ("July 2026", "next month", etc.)
    scope = detect_question_scope(question)
    target_date = scope.get("start") or date.today()
    # If scope start is in the past and horizon is monthly/annual, use today
    if target_date < date.today() and scope.get("is_default", True):
        target_date = date.today()

    rashifal_ctx = build_rashifal_context(
        question, chart_data, horizon,
        target_date=target_date,
        answer_language=answer_language,
    )

    md_lord = rashifal_ctx["dasha"]["mahadasha"].get("lord")
    ad_lord = rashifal_ctx["dasha"]["antardasha"].get("lord")

    if horizon == "annual":
        # Collect every unique AD lord that runs during the year (antardasha can change mid-year)
        snapshots = rashifal_ctx.get("monthly_snapshots", [])
        unique_ad_lords = list({
            s["dasha"]["antardasha_lord"]
            for s in snapshots
            if s["dasha"].get("antardasha_lord")
        })
        all_remedies = []
        seen_planets = set()
        for ad in unique_ad_lords:
            for r in remedies_for_dasha(md_lord, ad, answer_language).get("remedies", []):
                planet = r.get("planet") or r.get("lord")
                if planet not in seen_planets:
                    seen_planets.add(planet)
                    all_remedies.append(r)
        remedy_ctx = {"remedies": all_remedies}
    else:
        remedy_ctx = remedies_for_dasha(md_lord, ad_lord, answer_language)

    payload = {
        "user_question": question,
        "depth_level": depth_level,
        "answer_language": answer_language,
        "answer_style": answer_style.strip(),
        "rashifal_payload": rashifal_ctx,
        "evidence_payload": {"remedy_context": remedy_ctx},
    }

    if not settings.OPENAI_API_KEY:
        return _fallback_answer(question, payload, model, "OPENAI_API_KEY is not set.")
    if not settings.OPENAI_VECTOR_STORE_ID:
        return _fallback_answer(
            question, payload, model,
            "OPENAI_VECTOR_STORE_ID is not set.",
        )

    cache_key = _cache_key(
        {"cache_version": RASHIFAL_CACHE_VERSION, "payload": payload},
        model,
        settings.OPENAI_VECTOR_STORE_ID,
    )
    cached = cache.get(cache_key)
    if cached:
        cached["answer"] = cached["answer"] + "\n\n[Reused cached answer.]"
        return cached

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    prompt = json.dumps(payload, ensure_ascii=False, default=str)

    try:
        response = client.responses.create(
            model=model,
            instructions=_rashifal_system_instructions(horizon, answer_language),
            input=[
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                }
            ],
            tools=[
                {
                    "type": "file_search",
                    "vector_store_ids": [settings.OPENAI_VECTOR_STORE_ID],
                    "max_num_results": 6,
                }
            ],
        )
    except OpenAIError as exc:
        return _fallback_answer(question, payload, model, f"OpenAI API error: {exc}")

    prompt_tokens, completion_tokens = _usage_counts(response)
    answer_text = response.output_text
    answer_text = _apply_deterministic_remedy(answer_text, payload)

    result = {
        "model": model,
        "prompt": prompt,
        "answer": answer_text,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "is_rashifal": True,
        "horizon": horizon,
    }
    cache.set(cache_key, result, 60 * 60 * 24 * 7)  # 7-day cache for rashifal
    return result


def generate_answer(question, chart_data, depth_level, answer_style="", answer_language="English"):
    from .intent_engine import classify_intent
    intent = classify_intent(question)
    if intent["intent"] == "periodic":
        return _generate_rashifal_answer(
            question, chart_data or {}, intent["horizon"] or "monthly",
            depth_level, answer_style, answer_language,
        )

    model = model_for_depth(depth_level)
    answer_style = answer_style or settings.ASTROGPT_ANSWER_STYLE
    payload = build_prompt_payload(question, chart_data or {}, depth_level, answer_style, answer_language)

    if not settings.OPENAI_API_KEY:
        return _fallback_answer(question, payload, model, "OPENAI_API_KEY is not set.")

    if not settings.OPENAI_VECTOR_STORE_ID:
        return _fallback_answer(
            question,
            payload,
            model,
            "OPENAI_VECTOR_STORE_ID is not set. Add your uploaded astrology RAG vector store ID.",
        )

    cache_key = _cache_key(payload, model, settings.OPENAI_VECTOR_STORE_ID)
    cached = cache.get(cache_key)
    if cached:
        cached["answer"] = cached["answer"] + "\n\n[Reused cached answer.]"
        return cached

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    prompt = json.dumps(payload, ensure_ascii=False, default=str)

    try:
        response = client.responses.create(
            model=model,
            instructions=_system_instructions(depth_level, answer_style, answer_language),
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt,
                        }
                    ],
                }
            ],
            tools=[
                {
                    "type": "file_search",
                    "vector_store_ids": [settings.OPENAI_VECTOR_STORE_ID],
                    "max_num_results": 8,
                }
            ],
        )
    except OpenAIError as exc:
        return _fallback_answer(question, payload, model, f"OpenAI API error: {exc}")

    prompt_tokens, completion_tokens = _usage_counts(response)
    answer_text = response.output_text
    validation_result = validate_answer(answer_text, payload.get("evidence_payload", {}))
    logger.info(
        "Astrology answer validation score=%s passed=%s issues=%s",
        validation_result.get("score"),
        validation_result.get("passed"),
        validation_result.get("issues"),
    )
    if not validation_result["passed"]:
        try:
            repair_response = _repair_answer(
                client,
                model,
                depth_level,
                answer_style,
                answer_language,
                payload,
                answer_text,
                validation_result,
            )
            repair_prompt_tokens, repair_completion_tokens = _usage_counts(repair_response)
            answer_text = repair_response.output_text
            prompt_tokens += repair_prompt_tokens
            completion_tokens += repair_completion_tokens
            validation_result = validate_answer(answer_text, payload.get("evidence_payload", {}))
            logger.info(
                "Astrology repaired answer validation score=%s passed=%s issues=%s",
                validation_result.get("score"),
                validation_result.get("passed"),
                validation_result.get("issues"),
            )
        except OpenAIError:
            answer_text = (
                answer_text
                + "\n\n### Validation Note\n"
                + validation_result["repair_instruction"]
            )
    answer_text = _apply_deterministic_remedy(answer_text, payload)
    result = {
        "model": model,
        "prompt": prompt,
        "answer": answer_text,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "validation_result": validation_result,
    }
    cache.set(cache_key, result, 60 * 60 * 24 * 30)
    return result


def generate_placeholder_answer(question, chart_data, depth_level, answer_style="", answer_language="English"):
    return generate_answer(question, chart_data, depth_level, answer_style, answer_language)
