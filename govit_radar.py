# ============================================================
# GovIT Radar — Government IT & Civil Services Career Dashboard
# Deploy: Streamlit Cloud
# AI: Sarvam-105B (sarvam-105b) — Flagship 105B MoE Model
# Search: Tavily Advanced Search
# UX: Job list → Click job → Live AI roadmap + insights
# ============================================================

import streamlit as st
import requests
import json
import time
from datetime import datetime
from tavily import TavilyClient

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="GovIT Radar",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CSS — Minimal dark terminal, high contrast
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

.stApp {
    background: #07090f;
    font-family: 'IBM Plex Sans', sans-serif;
}

/* Dot-grid background */
.stApp::before {
    content: '';
    position: fixed; top: 0; left: 0;
    width: 100%; height: 100%;
    background-image: radial-gradient(circle, rgba(0,200,100,0.06) 1px, transparent 1px);
    background-size: 28px 28px;
    pointer-events: none; z-index: 0;
}

/* ── Job list cards ── */
.jcard {
    background: #0d1016;
    border: 1px solid #16202e;
    border-left: 3px solid var(--c, #00c864);
    border-radius: 6px;
    padding: 14px 16px;
    margin-bottom: 10px;
    cursor: pointer;
    transition: border-color .2s, background .2s;
}
.jcard:hover { background: #111620; border-color: #00c864; }
.jcard.selected {
    background: #0a1a10;
    border-color: #00c864;
    box-shadow: 0 0 16px rgba(0,200,100,0.08);
}

.jtitle {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 13px; font-weight: 600;
    color: #d0dce8; margin-bottom: 5px;
}
.jmeta {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px; color: #2a4a6a;
    letter-spacing: .4px;
}
.jsnippet {
    font-size: 11px; color: #2a4a6a;
    margin-top: 6px; line-height: 1.55;
}

/* ── Priority badges ── */
.badge {
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px; font-weight: 600;
    letter-spacing: .8px; text-transform: uppercase;
    padding: 2px 7px; border-radius: 3px;
    margin-right: 6px;
}
.badge-critical { background: rgba(255,65,65,.12); color: #ff4141; border: 1px solid #ff414130; }
.badge-high     { background: rgba(255,140,0,.12);  color: #ff8c00; border: 1px solid #ff8c0030; }
.badge-medium   { background: rgba(255,200,0,.12);  color: #ffc800; border: 1px solid #ffc80030; }
.badge-low      { background: rgba(0,200,100,.12);  color: #00c864; border: 1px solid #00c86430; }

/* ── Roadmap / Insight panel ── */
.insight-panel {
    background: linear-gradient(160deg, #080e14 0%, #0a1218 100%);
    border: 1px solid #1a3050;
    border-top: 2px solid #00c864;
    border-radius: 8px;
    padding: 22px 24px;
    margin-top: 4px;
}
.insight-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px; letter-spacing: 2.5px;
    text-transform: uppercase; color: #00c864;
    margin-bottom: 16px;
}
.insight-section {
    margin-bottom: 18px;
}
.insight-section-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px; letter-spacing: 1.5px;
    text-transform: uppercase; color: #1a5a8a;
    margin-bottom: 8px;
    border-bottom: 1px solid #101a24;
    padding-bottom: 4px;
}
.insight-body {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 12px; color: #6a8aaa;
    line-height: 1.7;
}

.phase-block {
    background: #0a0f18;
    border: 1px solid #101e2e;
    border-left: 2px solid var(--pc, #00c864);
    border-radius: 4px;
    padding: 10px 14px;
    margin-bottom: 8px;
}
.phase-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px; font-weight: 600;
    color: var(--pc, #00c864);
    margin-bottom: 6px;
}
.phase-items {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 11px; color: #3a6a8a;
    line-height: 1.8;
}

.skill-chip {
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px; padding: 2px 8px;
    border-radius: 3px; margin: 2px;
}
.skill-match { background: rgba(0,200,100,.1); color: #00c864; border: 1px solid #00c86420; }
.skill-gap   { background: rgba(255,140,0,.1);  color: #ff8c00; border: 1px solid #ff8c0020; }

.score-ring {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 28px; font-weight: 600;
    color: #00c864; text-align: center;
    padding: 12px;
}
.score-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px; letter-spacing: 1.5px;
    text-transform: uppercase; color: #1a4a2a;
    text-align: center;
}

/* ── Category section header ── */
.cat-sep {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px; letter-spacing: 2px;
    text-transform: uppercase; color: #1a3a5a;
    padding: 14px 0 8px 0;
    border-bottom: 1px solid #0f1820;
    margin-bottom: 10px;
    display: flex; justify-content: space-between;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #07090f;
    border-right: 1px solid #0f1820;
}

/* ── Empty / loading states ── */
.empty-hint {
    text-align: center; padding: 60px 20px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px; color: #0f2030;
    line-height: 2.2; letter-spacing: .5px;
}

/* ── Buttons ── */
.stButton > button[kind="primary"] {
    background: #001a0a;
    border: 1px solid #00c864;
    color: #00c864;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px; letter-spacing: 1.5px;
    text-transform: uppercase;
    border-radius: 4px;
    transition: all .2s;
}
.stButton > button[kind="primary"]:hover {
    background: #002a14;
    box-shadow: 0 0 18px rgba(0,200,100,.15);
}
.stButton > button:not([kind="primary"]) {
    background: #0a0e14;
    border: 1px solid #1a2a3a;
    color: #2a5a7a;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px; letter-spacing: 1px;
    border-radius: 4px;
}

/* ── Metrics ── */
.m-tile {
    background: #0a0e14;
    border: 1px solid #0f1820;
    border-radius: 6px; padding: 12px;
    text-align: center;
}
.m-val {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 20px; font-weight: 600;
    color: var(--mc, #00c864);
}
.m-lbl {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 8px; letter-spacing: 1.5px;
    text-transform: uppercase; color: #1a2a3a;
    margin-top: 3px;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #07090f;
    border-bottom: 1px solid #0f1820;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px; letter-spacing: 1.5px;
    text-transform: uppercase; color: #1a3a5a;
    padding: 10px 20px;
}
.stTabs [aria-selected="true"] {
    color: #00c864;
    border-bottom: 2px solid #00c864;
}

/* ── Input ── */
.stTextInput input {
    background: #0a0e14; border: 1px solid #1a2a3a;
    color: #4a7a9a; border-radius: 4px;
    font-family: 'IBM Plex Mono', monospace; font-size: 11px;
}
.stTextInput input:focus { border-color: #00c864; }

/* ── Misc ── */
#MainMenu, footer, header { visibility: hidden; }
.stProgress > div > div { background: linear-gradient(90deg, #00c864, #00aaff); }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────
if "jobs_store"      not in st.session_state: st.session_state.jobs_store = {}
if "selected_job"    not in st.session_state: st.session_state.selected_job = None
if "job_insights"    not in st.session_state: st.session_state.job_insights = {}
if "fetch_done"      not in st.session_state: st.session_state.fetch_done = False
if "total_found"     not in st.session_state: st.session_state.total_found = 0


# ─────────────────────────────────────────────
# SECRETS — Streamlit Cloud reads from
# .streamlit/secrets.toml automatically
# Falls back to sidebar text input
# ─────────────────────────────────────────────
def get_secret(key: str, fallback: str = "") -> str:
    try:
        return st.secrets[key]
    except Exception:
        return fallback


# ─────────────────────────────────────────────
# EXPERIENCE + DOMAIN CONFIGS
# ─────────────────────────────────────────────
EXP_PROFILES = {
    "Fresher  (0–1 yr)":    {"tag": "entry",  "kws": ["trainee", "junior", "assistant", "graduate"]},
    "Junior   (1–3 yrs)":   {"tag": "junior", "kws": ["assistant officer", "junior analyst", "grade B"]},
    "Mid-Level (3–7 yrs)":  {"tag": "mid",    "kws": ["officer", "analyst", "consultant", "specialist"]},
    "Senior   (7–12 yrs)":  {"tag": "senior", "kws": ["senior officer", "deputy director", "lateral entry specialist"]},
    "Leadership (12+ yrs)": {"tag": "lead",   "kws": ["director", "joint secretary", "principal advisor"]},
}

DOMAINS = {
    "IT / Software":       ["software engineer", "IT officer", "developer"],
    "Data & Analytics":    ["data analyst", "data scientist", "statistician"],
    "Cybersecurity":       ["cybersecurity officer", "information security"],
    "Project Management":  ["project manager", "program manager", "PMO"],
    "Policy & Governance": ["e-governance", "policy analyst", "digital governance"],
    "Networking / Infra":  ["network engineer", "system administrator"],
}

STATES = [
    "All India", "Bihar", "Uttar Pradesh", "Madhya Pradesh",
    "Rajasthan", "Maharashtra", "Karnataka", "Tamil Nadu",
    "West Bengal", "Delhi", "Gujarat", "Odisha", "Jharkhand",
]

PHASE_COLORS = ["#00c864", "#ff8c00", "#00aaff", "#a78bfa", "#ff4141"]


# ─────────────────────────────────────────────
# SEARCH QUERY BUILDER
# ─────────────────────────────────────────────
def build_categories(exp: str, domains: list, state: str,
                     civil: bool, central: bool, state_it: bool,
                     psu: bool, lateral: bool) -> dict:

    tag   = EXP_PROFILES[exp]["tag"]
    kw    = " ".join(domains[:2]) if domains else "IT technology"
    sq    = f"{state} " if state != "All India" else ""
    yr    = datetime.now().year
    cats  = {}

    if civil:
        if state == "Bihar" or state == "All India":
            cats["BPSC — Bihar Civil Services"] = {
                "priority": "CRITICAL", "badge": "badge-critical", "color": "#ff4141",
                "why": "Bihar state cadre civil services",
                "queries": [
                    f"BPSC combined competitive examination notification {yr}",
                    f"Bihar Public Service Commission CCE recruitment {yr} apply online",
                    f"BPSC 72nd 73rd prelims mains exam date {yr}",
                ]
            }
        cats["UPSC — Civil Services / Lateral"] = {
            "priority": "CRITICAL", "badge": "badge-critical", "color": "#ff4141",
            "why": "Central civil services and specialist entry",
            "queries": [
                f"UPSC civil services IAS IPS notification {yr}",
                f"UPSC lateral entry joint secretary technology IT {yr}",
            ]
        }
        if state != "All India":
            cats[f"{state} State PSC"] = {
                "priority": "HIGH", "badge": "badge-high", "color": "#ff8c00",
                "why": f"{state} state cadre",
                "queries": [
                    f"{state} Public Service Commission PSC recruitment {yr}",
                    f"{state} PSC combined state services exam {yr} notification",
                ]
            }

    if central:
        cats["NIC — National Informatics Centre"] = {
            "priority": "HIGH", "badge": "badge-high", "color": "#ff8c00",
            "why": "Direct e-governance IT work across all states",
            "queries": [
                f"NIC National Informatics Centre {kw} recruitment {yr}",
                f"NIC scientist engineer technical officer vacancy {yr}",
                f"NIC {sq}unit recruitment notification {yr}",
            ]
        }
        cats["MeitY / Digital India / C-DAC"] = {
            "priority": "HIGH", "badge": "badge-high", "color": "#ff8c00",
            "why": "Central IT ministry and implementation bodies",
            "queries": [
                f"MeitY ministry electronics information technology {kw} recruitment {yr}",
                f"Digital India Corporation vacancy {yr}",
                f"C-DAC CDAC scientist engineer recruitment {yr}",
            ]
        }
        cats["SSC — Technical IT Posts"] = {
            "priority": "MEDIUM", "badge": "badge-medium", "color": "#ffc800",
            "why": "Central govt technical officer via SSC",
            "queries": [
                f"SSC CGL scientific technical {kw} officer {yr}",
                f"SSC CHSL technical government IT recruitment {yr}",
            ]
        }

    if state_it and state != "All India":
        cats[f"{state} State IT / Electronics Dept"] = {
            "priority": "HIGH", "badge": "badge-high", "color": "#ff8c00",
            "why": f"Direct {state} state digital and IT roles",
            "queries": [
                f"{state} electronics development corporation recruitment {yr}",
                f"{state} IT department e-governance officer vacancy {yr}",
                f"{state} government {kw} jobs recruitment {yr}",
            ]
        }
    elif state_it:
        cats["State Govt IT / Electronics (All States)"] = {
            "priority": "HIGH", "badge": "badge-high", "color": "#ff8c00",
            "why": "State electronics corporations across India",
            "queries": [
                f"state electronics development corporation {kw} recruitment {yr}",
                f"state IT department e-governance vacancy {yr}",
            ]
        }

    if psu:
        cats["PSU — IT & Technology"] = {
            "priority": "MEDIUM", "badge": "badge-medium", "color": "#ffc800",
            "why": "BEL, BSNL, DRDO, ISRO and similar PSUs",
            "queries": [
                f"BEL BSNL DRDO ISRO BHEL {kw} recruitment {yr}",
                f"public sector undertaking PSU {kw} engineer officer {yr}",
            ]
        }

    if lateral and tag in ("mid", "senior", "lead"):
        cats["Lateral Entry — Senior Specialist"] = {
            "priority": "HIGH", "badge": "badge-high", "color": "#ff8c00",
            "why": "Senior direct entry for experienced professionals",
            "queries": [
                f"UPSC lateral entry {yr} specialist IT technology management",
                f"DOPT government lateral hire {kw} director {yr}",
            ]
        }

    cats["Research / Policy Advisory"] = {
        "priority": "LOW", "badge": "badge-low", "color": "#00c864",
        "why": "Think tanks, TRAI, regulatory bodies",
        "queries": [
            f"India government technology policy research {kw} vacancy {yr}",
            f"TRAI regulatory technology {kw} consultant officer {yr}",
        ]
    }

    return cats


# ─────────────────────────────────────────────
# TAVILY SEARCH
# ─────────────────────────────────────────────
TRUSTED = [
    "upsc.gov.in", "ssc.nic.in", "nic.in", "meity.gov.in",
    "digitalindia.gov.in", "bpsc.bih.nic.in", "sarkariresult.com",
    "thehindu.com", "timesofindia.com", "ndtv.com",
    "livemint.com", "hindustantimes.com", "jagran.com",
]


def tavily_search(client: TavilyClient, query: str, n: int = 4) -> list:
    try:
        r = client.search(
            query=query,
            search_depth="advanced",
            max_results=n,
            include_answer=False,
            include_raw_content=False,
            include_domains=TRUSTED,
        )
        return r.get("results", [])
    except Exception as e:
        return []


def fetch_category(client, cat_name, cat_data, n_per_q):
    all_r, raw = [], []
    for q in cat_data["queries"]:
        for r in tavily_search(client, q, n_per_q):
            all_r.append({
                "id":      f"{cat_name}_{len(all_r)}",
                "cat":     cat_name,
                "title":   r.get("title", "Untitled"),
                "url":     r.get("url", ""),
                "snippet": r.get("content", "")[:380],
                "score":   r.get("score", 0),
                "query":   q,
                "color":   cat_data["color"],
                "badge":   cat_data["badge"],
                "priority":cat_data["priority"],
            })
            raw.append(f"• {r.get('title','')}: {r.get('content','')[:160]}")

    seen, unique = set(), []
    for r in all_r:
        if r["url"] and r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)

    unique.sort(key=lambda x: x["score"], reverse=True)
    return unique[:8], "\n".join(raw[:10])


# ─────────────────────────────────────────────
# SARVAM 105B — JOB INSIGHT GENERATOR
# Model: sarvam-105b (flagship 105B MoE)
# Generates structured JSON roadmap per job
# ─────────────────────────────────────────────
SARVAM_URL = "https://api.sarvam.ai/v1/chat/completions"
SARVAM_MODEL = "sarvam-105b"   # Exact model ID — do not change


def generate_job_insight(
    api_key: str,
    job: dict,
    exp_level: str,
    domain_list: list,
    state: str,
) -> dict:
    """
    Call Sarvam-105B to generate structured career insight for a specific job.
    Returns parsed JSON with: summary, eligibility, skill_match, skill_gaps,
    roadmap phases, application_tips, timeline.
    """
    if not api_key:
        return {"error": "No Sarvam API key provided"}

    domain_str = ", ".join(domain_list) if domain_list else "IT / Technology"

    system_prompt = (
        "You are a precise career advisor for Indian government jobs. "
        "Always respond with ONLY valid JSON, no markdown fences, no preamble. "
        "Generate actionable, specific advice tailored to the job and candidate profile."
    )

    user_prompt = f"""
Analyze this government job opportunity and generate a career insight report.

CANDIDATE PROFILE:
- Experience Level: {exp_level}
- Domain Expertise: {domain_str}
- State Focus: {state}

JOB DETAILS:
- Title: {job.get('title', 'Unknown')}
- Category: {job.get('cat', 'Unknown')}
- Source URL: {job.get('url', '')}
- Description: {job.get('snippet', 'No description available')}

Generate a JSON response with EXACTLY this structure:
{{
  "quick_summary": "2-3 sentence summary of this opportunity and its relevance",
  "eligibility_score": <integer 0-100 representing fit percentage>,
  "eligibility_notes": "Why this score — specific reasons",
  "matched_skills": ["skill1", "skill2", "skill3"],
  "skill_gaps": ["gap1", "gap2", "gap3"],
  "preparation_roadmap": [
    {{
      "phase": "Phase 1 — Foundation",
      "duration": "Weeks 1-8",
      "actions": ["action1", "action2", "action3"]
    }},
    {{
      "phase": "Phase 2 — Core Preparation",
      "duration": "Weeks 9-20",
      "actions": ["action1", "action2", "action3"]
    }},
    {{
      "phase": "Phase 3 — Application & Test Prep",
      "duration": "Weeks 20-28",
      "actions": ["action1", "action2", "action3"]
    }}
  ],
  "application_tips": ["tip1", "tip2", "tip3", "tip4"],
  "estimated_timeline": "e.g. 6-8 months to be application-ready",
  "competition_level": "Low / Medium / High / Very High",
  "salary_range": "Approximate pay scale / grade pay if known, else estimate",
  "official_apply_hint": "Where to apply or check for notifications"
}}

Be specific to the Indian government context. If this is a state PSC exam include exam structure details.
Return ONLY the JSON object.
"""

    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "model": SARVAM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "max_tokens": 1200,
        "temperature": 0.2,
    }

    try:
        resp = requests.post(SARVAM_URL, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            raw_text = resp.json()["choices"][0]["message"]["content"].strip()
            # Strip any accidental markdown fences
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            return json.loads(raw_text)
        else:
            return {"error": f"Sarvam API error: HTTP {resp.status_code} — {resp.text[:200]}"}
    except json.JSONDecodeError as e:
        return {"error": f"JSON parse error: {str(e)[:100]}"}
    except Exception as e:
        return {"error": f"Request error: {str(e)[:100]}"}


# ─────────────────────────────────────────────
# RENDER — COMPACT JOB CARD (list view)
# ─────────────────────────────────────────────
def render_job_card_compact(job: dict, is_selected: bool, key_prefix: str):
    sel_class = "selected" if is_selected else ""
    rel = min(int(job["score"] * 100), 99) if job["score"] > 0 else 68
    bar = "█" * (rel // 10) + "░" * (10 - rel // 10)

    st.markdown(f"""
    <div class="jcard {sel_class}" style="--c: {job['color']};">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
            <div class="jtitle">{job['title']}</div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:9px;
                        color:{job['color']}; white-space:nowrap;">{bar} {rel}%</div>
        </div>
        <div class="jmeta">
            <span class="badge {job['badge']}">{job['priority']}</span>
            {job['cat']} &nbsp;·&nbsp;
            <a href="{job['url']}" target="_blank"
               style="color:#1a4a6a; text-decoration:none; font-size:9px;">
               ↗ {job['url'][:55]}{'…' if len(job['url'])>55 else ''}
            </a>
        </div>
        <div class="jsnippet">{job['snippet'][:200]}{'…' if len(job['snippet'])>200 else ''}</div>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b = st.columns([3, 1])
    with col_b:
        label = "▶ View Insight" if not is_selected else "✕ Close"
        if st.button(label, key=f"{key_prefix}_btn_{job['id']}", use_container_width=True):
            if is_selected:
                st.session_state.selected_job = None
            else:
                st.session_state.selected_job = job["id"]
            st.rerun()


# ─────────────────────────────────────────────
# RENDER — FULL INSIGHT PANEL (Sarvam 105B)
# ─────────────────────────────────────────────
def render_insight_panel(job: dict, insight: dict):
    if "error" in insight:
        st.markdown(f"""
        <div class="insight-panel">
            <div class="insight-header">◈ Sarvam-105B Insight — Error</div>
            <div style="color:#ff4141; font-family:'IBM Plex Mono',monospace; font-size:11px;">
                {insight['error']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Score + Summary row ──
    score = insight.get("eligibility_score", 0)
    score_color = "#00c864" if score >= 70 else "#ff8c00" if score >= 45 else "#ff4141"

    with st.container():
        st.markdown(f"""
        <div class="insight-panel">
            <div class="insight-header">
                ◈ Sarvam-105B Career Insight &nbsp;·&nbsp; {job['title'][:60]}
            </div>
        """, unsafe_allow_html=True)

        # Score + summary
        c_score, c_summary = st.columns([1, 4])
        with c_score:
            st.markdown(f"""
            <div style="text-align:center; padding:14px 0;">
                <div style="font-family:'IBM Plex Mono',monospace; font-size:36px;
                            font-weight:700; color:{score_color};">{score}</div>
                <div style="font-family:'IBM Plex Mono',monospace; font-size:8px;
                            letter-spacing:1.5px; text-transform:uppercase;
                            color:#1a3a2a; margin-top:4px;">Fit Score</div>
                <div style="font-family:'IBM Plex Mono',monospace; font-size:9px;
                            color:{score_color}; margin-top:6px;">/ 100</div>
            </div>
            """, unsafe_allow_html=True)

        with c_summary:
            st.markdown(f"""
            <div class="insight-section" style="padding-top:10px;">
                <div class="insight-section-title">Quick Summary</div>
                <div class="insight-body">{insight.get('quick_summary', '—')}</div>
                <div style="margin-top:8px; font-family:'IBM Plex Mono',monospace;
                            font-size:10px; color:#1a5a3a;">
                    {insight.get('eligibility_notes', '')}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Skills row ──
    c1, c2 = st.columns(2)
    with c1:
        matched = insight.get("matched_skills", [])
        chips = " ".join(f'<span class="skill-chip skill-match">✓ {s}</span>' for s in matched)
        st.markdown(f"""
        <div class="insight-section">
            <div class="insight-section-title">Matched Skills</div>
            <div>{chips if chips else '<span style="color:#1a3a2a;font-size:11px;">None identified</span>'}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        gaps = insight.get("skill_gaps", [])
        gchips = " ".join(f'<span class="skill-chip skill-gap">⚠ {g}</span>' for g in gaps)
        st.markdown(f"""
        <div class="insight-section">
            <div class="insight-section-title">Skill Gaps to Address</div>
            <div>{gchips if gchips else '<span style="color:#1a3a2a;font-size:11px;">None identified</span>'}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Roadmap phases ──
    st.markdown("""
    <div class="insight-section-title" style="margin-bottom:10px;">
        Preparation Roadmap
    </div>
    """, unsafe_allow_html=True)

    phases = insight.get("preparation_roadmap", [])
    for i, phase in enumerate(phases):
        pc = PHASE_COLORS[i % len(PHASE_COLORS)]
        actions = phase.get("actions", [])
        actions_html = "".join(f"<div>▸ {a}</div>" for a in actions)
        st.markdown(f"""
        <div class="phase-block" style="--pc: {pc};">
            <div class="phase-title">{phase.get('phase','Phase')}
                <span style="color:#1a3a5a; font-weight:400; margin-left:8px;">
                    {phase.get('duration','')}
                </span>
            </div>
            <div class="phase-items">{actions_html}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Tips + Meta row ──
    c3, c4 = st.columns([3, 2])
    with c3:
        tips = insight.get("application_tips", [])
        tips_html = "".join(f"<div>→ {t}</div>" for t in tips)
        st.markdown(f"""
        <div class="insight-section" style="margin-top:14px;">
            <div class="insight-section-title">Application Tips</div>
            <div class="insight-body">{tips_html if tips_html else '—'}</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        comp_colors = {
            "Low": "#00c864", "Medium": "#ffc800",
            "High": "#ff8c00", "Very High": "#ff4141"
        }
        comp = insight.get("competition_level", "Unknown")
        cc = comp_colors.get(comp, "#6a8aaa")
        st.markdown(f"""
        <div class="insight-section" style="margin-top:14px;">
            <div class="insight-section-title">At a Glance</div>
            <div class="insight-body" style="line-height:2.2;">
                <span style="color:#1a3a5a;">Timeline </span>
                {insight.get('estimated_timeline', '—')}<br>
                <span style="color:#1a3a5a;">Competition </span>
                <span style="color:{cc};">{comp}</span><br>
                <span style="color:#1a3a5a;">Pay Scale </span>
                {insight.get('salary_range', '—')}<br>
                <span style="color:#1a3a5a;">Apply Via </span>
                {insight.get('official_apply_hint', '—')}
            </div>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding:16px 0 10px;">
        <div style="font-family:'IBM Plex Mono',monospace; font-size:9px;
                    letter-spacing:3px; color:#003a1a; text-transform:uppercase;">
            System Active
        </div>
        <div style="font-family:'IBM Plex Sans',sans-serif; font-size:22px;
                    font-weight:700; color:#00c864; margin:6px 0 2px;">
            GovIT Radar
        </div>
        <div style="font-family:'IBM Plex Mono',monospace; font-size:9px;
                    color:#0f2a1a; letter-spacing:1px;">
            Govt Career Intelligence
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # API Keys — from secrets first, else sidebar input
    _tv_secret = get_secret("TAVILY_API_KEY")
    _sv_secret = get_secret("SARVAM_API_KEY")

    st.markdown("""
    <div style="font-family:'IBM Plex Mono',monospace; font-size:9px;
                letter-spacing:2px; color:#00c864; text-transform:uppercase;
                margin-bottom:8px;">◈ API Keys</div>
    """, unsafe_allow_html=True)

    if _tv_secret:
        st.markdown(
            '<div style="font-family:IBM Plex Mono,monospace;font-size:9px;'
            'color:#003a1a;">✓ Tavily key loaded from secrets</div>',
            unsafe_allow_html=True
        )
        tavily_key = _tv_secret
    else:
        tavily_key = st.text_input(
            "Tavily API Key", type="password",
            placeholder="tvly-xxxxxxxxxxxxxxxx",
            help="Free at tavily.com"
        )

    if _sv_secret:
        st.markdown(
            '<div style="font-family:IBM Plex Mono,monospace;font-size:9px;'
            'color:#003a1a;">✓ Sarvam key loaded from secrets</div>',
            unsafe_allow_html=True
        )
        sarvam_key = _sv_secret
    else:
        sarvam_key = st.text_input(
            "Sarvam API Key", type="password",
            placeholder="sarvam-xxxxxxxx",
            help="Free credits at sarvam.ai — powers roadmap insights"
        )

    st.markdown("""
    <div style="font-family:'IBM Plex Mono',monospace; font-size:8px;
                color:#0f1a0f; margin:4px 0 12px; letter-spacing:.5px;">
        Model: sarvam-105b (Flagship 105B MoE)
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Profile
    st.markdown("""
    <div style="font-family:'IBM Plex Mono',monospace; font-size:9px;
                letter-spacing:2px; color:#00c864; text-transform:uppercase;
                margin-bottom:8px;">◈ Your Profile</div>
    """, unsafe_allow_html=True)

    exp_level = st.selectbox(
        "Experience Level", list(EXP_PROFILES.keys()), index=3
    )
    domain_selected = st.multiselect(
        "Domain Focus", list(DOMAINS.keys()),
        default=["IT / Software", "Policy & Governance"]
    )
    state_selected = st.selectbox("State Focus", STATES, index=1)

    st.divider()

    # Scope
    st.markdown("""
    <div style="font-family:'IBM Plex Mono',monospace; font-size:9px;
                letter-spacing:2px; color:#00c864; text-transform:uppercase;
                margin-bottom:8px;">◈ Search Scope</div>
    """, unsafe_allow_html=True)

    inc_civil   = st.toggle("Civil Services",    value=True)
    inc_central = st.toggle("Central Govt IT",   value=True)
    inc_state   = st.toggle("State Govt IT",     value=True)
    inc_psu     = st.toggle("PSUs",              value=True)
    inc_lateral = st.toggle("Lateral Entry",     value=True)

    st.divider()

    n_results = st.slider("Results per query", 2, 5, 3)

    st.divider()

    fetch_btn = st.button(
        "⟫ FETCH OPPORTUNITIES",
        use_container_width=True,
        type="primary"
    )

    if st.button("✕ Clear Results", use_container_width=True):
        st.session_state.jobs_store   = {}
        st.session_state.selected_job = None
        st.session_state.job_insights = {}
        st.session_state.fetch_done   = False
        st.rerun()


# ─────────────────────────────────────────────
# MAIN HEADER
# ─────────────────────────────────────────────
st.markdown(f"""
<div style="padding:16px 0 8px;">
    <div style="font-family:'IBM Plex Mono',monospace; font-size:8px;
                letter-spacing:3px; color:#003a1a; text-transform:uppercase;
                margin-bottom:6px;">
        ▸ Live Govt Job Intelligence ▸ {datetime.now().strftime('%d %b %Y  %H:%M')} IST
    </div>
    <h1 style="font-family:'IBM Plex Sans',sans-serif; font-size:26px;
               font-weight:700; color:#c0d0e0; margin:0 0 4px; letter-spacing:-.3px;">
        Government IT &amp; Civil Services Radar
    </h1>
    <p style="font-family:'IBM Plex Mono',monospace; font-size:10px;
              color:#1a3a5a; letter-spacing:.5px; margin:0;">
        {state_selected} · {exp_level.strip()} ·
        {', '.join(domain_selected[:2]) if domain_selected else 'All Domains'} ·
        AI Roadmap powered by <span style="color:#00c864;">sarvam-105b</span>
    </p>
</div>
""", unsafe_allow_html=True)

# Metric strip
mc = st.columns(6)
tiles = [
    ("BPSC",  "Civil Svc",      "#ff4141"),
    ("NIC",   "Tech Roles",     "#ff8c00"),
    ("MeitY", "Digital India",  "#00aaff"),
    ("SSC",   "Tech Posts",     "#ffc800"),
    ("PSU",   "Public Sector",  "#a78bfa"),
    ("LAT",   "Lateral Entry",  "#00c864"),
]
for col, (val, lbl, color) in zip(mc, tiles):
    with col:
        st.markdown(f"""
        <div class="m-tile" style="--mc:{color};">
            <div class="m-val">{val}</div>
            <div class="m-lbl">{lbl}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FETCH LOGIC
# ─────────────────────────────────────────────
if fetch_btn:
    if not tavily_key:
        st.error("⚠  Tavily API key needed to search.", icon="🔑")
    else:
        # Collect domain keywords
        domain_kws = []
        for d in domain_selected:
            domain_kws.extend(DOMAINS.get(d, []))

        cats = build_categories(
            exp_level, domain_kws, state_selected,
            inc_civil, inc_central, inc_state, inc_psu, inc_lateral
        )

        try:
            tc = TavilyClient(api_key=tavily_key)
        except Exception as e:
            st.error(f"Tavily error: {e}")
            st.stop()

        bar    = st.progress(0, text="Initialising…")
        store  = {}
        n_cats = len(cats)

        for i, (cname, cdata) in enumerate(cats.items()):
            bar.progress(i / n_cats, text=f"Searching: {cname} ({i+1}/{n_cats})")
            results, _ = fetch_category(tc, cname, cdata, n_results)
            store[cname] = {"meta": cdata, "jobs": results}
            time.sleep(0.2)

        bar.progress(1.0, text="✅  Done")
        time.sleep(0.5)
        bar.empty()

        st.session_state.jobs_store   = store
        st.session_state.selected_job = None
        st.session_state.job_insights = {}
        st.session_state.fetch_done   = True
        st.rerun()


# ─────────────────────────────────────────────
# MAIN DISPLAY — Two-column: list + insight
# ─────────────────────────────────────────────
if not st.session_state.fetch_done:
    st.markdown("""
    <div class="empty-hint">
        <div style="font-size:48px; opacity:.15; margin-bottom:16px;">📡</div>
        AWAITING SIGNAL<br><br>
        1. Configure profile in sidebar<br>
        2. Add API keys (or set in secrets.toml)<br>
        3. Click  ⟫ FETCH OPPORTUNITIES<br><br>
        <span style="color:#071520; font-size:9px; letter-spacing:1px;">
            AI ROADMAP GENERATED PER JOB USING SARVAM-105B
        </span>
    </div>
    """, unsafe_allow_html=True)

else:
    store = st.session_state.jobs_store
    sel_id = st.session_state.selected_job

    # Find selected job object
    sel_job = None
    for _, cval in store.items():
        for j in cval["jobs"]:
            if j["id"] == sel_id:
                sel_job = j
                break

    # Layout: list always left; insight panel on right if job selected
    if sel_job:
        col_list, col_insight = st.columns([2, 3], gap="medium")
    else:
        col_list = st.container()
        col_insight = None

    # ── LEFT: Job List ──
    with col_list:
        total = sum(len(v["jobs"]) for v in store.values())
        st.markdown(f"""
        <div style="font-family:'IBM Plex Mono',monospace; font-size:9px;
                    letter-spacing:1.5px; color:#1a4a2a; margin-bottom:12px;">
            {total} OPPORTUNITIES · CLICK ANY JOB FOR AI ROADMAP
        </div>
        """, unsafe_allow_html=True)

        for cname, cval in store.items():
            jobs = cval["jobs"]
            if not jobs:
                continue

            meta = cval["meta"]
            st.markdown(f"""
            <div class="cat-sep">
                <span>{cname}</span>
                <span style="color:{meta['color']};">{meta['priority']} · {len(jobs)}</span>
            </div>
            """, unsafe_allow_html=True)

            for job in jobs:
                is_sel = (job["id"] == sel_id)
                render_job_card_compact(job, is_sel, f"cat_{cname[:8]}")

    # ── RIGHT: Insight Panel ──
    if sel_job and col_insight:
        with col_insight:
            st.markdown("""
            <div style="font-family:'IBM Plex Mono',monospace; font-size:9px;
                        letter-spacing:2px; color:#003a1a; text-transform:uppercase;
                        margin-bottom:10px; padding-bottom:6px;
                        border-bottom:1px solid #0a1a10;">
                ◈ Sarvam-105B Career Insight
            </div>
            """, unsafe_allow_html=True)

            jid = sel_job["id"]

            # Check cache
            if jid in st.session_state.job_insights:
                insight = st.session_state.job_insights[jid]
                render_insight_panel(sel_job, insight)

            else:
                if not sarvam_key:
                    st.warning(
                        "Add your Sarvam API key in the sidebar to generate "
                        "AI-powered roadmap insights using sarvam-105b.",
                        icon="🔑"
                    )
                else:
                    domain_kws_display = domain_selected if domain_selected else ["IT / Technology"]

                    with st.spinner(
                        "Generating roadmap with sarvam-105b — "
                        "105B parameter flagship model…"
                    ):
                        insight = generate_job_insight(
                            api_key=sarvam_key,
                            job=sel_job,
                            exp_level=exp_level,
                            domain_list=domain_kws_display,
                            state=state_selected,
                        )

                    st.session_state.job_insights[jid] = insight
                    render_insight_panel(sel_job, insight)


# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center; padding:28px 0 12px; margin-top:24px;
            border-top:1px solid #0a1018;">
    <div style="font-family:'IBM Plex Mono',monospace; font-size:8px;
                color:#0a1a0a; letter-spacing:2px; text-transform:uppercase;">
        GovIT Radar · Tavily Search + Sarvam-105B · {datetime.now().year}
    </div>
    <div style="font-family:'IBM Plex Mono',monospace; font-size:8px;
                color:#071510; margin-top:3px; letter-spacing:1px;">
        tavily.com/api · sarvam.ai · docs.sarvam.ai/api-reference-docs/getting-started/models/sarvam-105b
    </div>
</div>
""", unsafe_allow_html=True)
