# ================================================================
# GovIT Radar — Simple Government IT & Civil Services Dashboard
# - Tavily: fetches latest job openings per category
# - Sarvam-105b: generates prep strategy per category
# - Each tab = one category = jobs + prep strategy
# ================================================================

import streamlit as st
import requests
import json
import time
from datetime import datetime, timezone, timedelta
from tavily import TavilyClient

# ── IST ──────────────────────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))
def now_ist():
    return datetime.now(IST)

# ── Constants ────────────────────────────────────────────────────
SARVAM_MODEL = "sarvam-105b"
SARVAM_URL   = "https://api.sarvam.ai/v1/chat/completions"

# ── Page config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="GovIT Radar",
    page_icon="📡",
    layout="wide"
)

# ── Simple clean styling ─────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background: #0f1117; color: #e0e6f0; }
    
    .job-item {
        background: #1a1f2e;
        border: 1px solid #2a3a4e;
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 10px;
    }
    .job-title {
        font-size: 15px;
        font-weight: 600;
        color: #e0e6f0;
        margin-bottom: 6px;
    }
    .job-snippet {
        font-size: 12px;
        color: #6a8aaa;
        line-height: 1.6;
        margin-bottom: 8px;
    }
    .job-link {
        font-size: 11px;
        color: #4a9eff;
    }
    .strategy-box {
        background: #111827;
        border: 1px solid #1e3a5a;
        border-left: 3px solid #00cc66;
        border-radius: 8px;
        padding: 16px 20px;
        font-size: 13px;
        color: #8ab4cc;
        line-height: 1.8;
        white-space: pre-wrap;
    }
    .section-label {
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: #00cc66;
        margin: 16px 0 8px 0;
    }
    .no-results {
        color: #3a5a7a;
        font-size: 13px;
        padding: 12px 0;
    }
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Get API keys (secrets first, sidebar fallback) ───────────────
def get_key(name):
    try:
        return st.secrets[name]
    except:
        return ""


# ── Sarvam-105b: generate prep strategy ─────────────────────────
def get_prep_strategy(sarvam_key, category, jobs_text, exp_level, state):
    if not sarvam_key:
        return "⚠ Add SARVAM_API_KEY to secrets.toml to generate strategy."

    prompt = f"""You are a career advisor for Indian government jobs.

Category: {category}
Candidate: {exp_level}, targeting {state}
Recent openings found:
{jobs_text}

Write a focused preparation strategy for this category. Include:
1. What this category offers (2-3 lines)
2. Eligibility & key requirements
3. Step-by-step preparation plan (4-5 steps)
4. Key resources to use
5. Timeline estimate
6. Application process & where to apply

Be specific, practical, and India-focused. Plain text, no markdown symbols."""

    try:
        resp = requests.post(
            SARVAM_URL,
            headers={
                "api-subscription-key": sarvam_key,
                "Content-Type": "application/json"
            },
            json={
                "model": SARVAM_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a precise career advisor for Indian government and IT jobs. Give actionable, specific advice."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 800,
                "temperature": 0.3
            },
            timeout=30
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return f"Sarvam error: HTTP {resp.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"


# ── Tavily: fetch jobs for a category ───────────────────────────
def fetch_jobs(tavily_key, query, n=5):
    try:
        client = TavilyClient(api_key=tavily_key)
        result = client.search(
            query=query,
            search_depth="advanced",
            max_results=n,
            include_answer=False,
            include_domains=[
                "upsc.gov.in", "ssc.nic.in", "nic.in",
                "meity.gov.in", "bpsc.bih.nic.in",
                "sarkariresult.com", "sarkariexam.com",
                "thehindu.com", "timesofindia.com",
                "ndtv.com", "livemint.com"
            ]
        )
        return result.get("results", [])
    except Exception as e:
        return []


# ── Define categories ────────────────────────────────────────────
# Each has a display name, search query, and description
def get_categories(exp_level, state, yr):
    sq = f"{state} " if state != "All India" else ""
    return {
        "🏛️ BPSC / State PSC": {
            "query": f"BPSC Bihar Public Service Commission CCE notification recruitment {yr}",
            "desc":  "Bihar & state civil services — SDO, BAS, DSP and other gazetted posts"
        },
        "🏢 UPSC Civil Services": {
            "query": f"UPSC civil services IAS IPS IFS recruitment notification {yr}",
            "desc":  "Central government cadre — India's premier civil services examination"
        },
        "💻 NIC — IT Officer": {
            "query": f"NIC National Informatics Centre scientist engineer IT officer recruitment {yr}",
            "desc":  "Direct technical contribution to national e-governance infrastructure"
        },
        "🌐 MeitY / Digital India": {
            "query": f"MeitY Digital India Corporation C-DAC STPI IT recruitment vacancy {yr}",
            "desc":  "Central IT ministry, digital policy, and implementation bodies"
        },
        "🏢 State IT / BSEDC": {
            "query": f"{sq}state electronics development corporation IT department e-governance recruitment {yr}",
            "desc":  f"{state} state government IT and digitisation roles"
        },
        "📋 SSC Technical Posts": {
            "query": f"SSC CGL CHSL scientific technical IT officer government recruitment {yr}",
            "desc":  "Central govt technical officer posts via Staff Selection Commission"
        },
        "🔵 PSU — IT & Tech": {
            "query": f"BEL BSNL DRDO ISRO BHEL IT technology engineer officer recruitment {yr}",
            "desc":  "Public sector undertakings with IT and technology openings"
        },
        "🎯 Lateral Entry": {
            "query": f"UPSC lateral entry joint secretary deputy director IT technology specialist {yr}",
            "desc":  "Senior specialist entry for experienced professionals (7+ years)"
        },
    }


# ────────────────────────────────────────────────────────────────
# SIDEBAR
# ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📡 GovIT Radar")
    st.markdown(
        f"*{now_ist().strftime('%d %b %Y  %I:%M %p')} IST*",
    )
    st.divider()

    # API keys
    st.markdown("### 🔑 API Keys")

    _tv = get_key("TAVILY_API_KEY")
    _sv = get_key("SARVAM_API_KEY")

    if _tv:
        st.success("Tavily key loaded ✓", icon="✅")
        tavily_key = _tv
    else:
        tavily_key = st.text_input(
            "Tavily API Key", type="password",
            help="Get free key at tavily.com"
        )

    if _sv:
        st.success("Sarvam key loaded ✓", icon="✅")
        sarvam_key = _sv
    else:
        sarvam_key = st.text_input(
            "Sarvam API Key", type="password",
            help="Get key at sarvam.ai"
        )

    st.caption(f"AI Model: `{SARVAM_MODEL}`")
    st.divider()

    # Profile
    st.markdown("### 👤 Your Profile")
    exp_level = st.selectbox(
        "Experience Level",
        [
            "Fresher (0–1 yr)",
            "Junior (1–3 yrs)",
            "Mid-Level (3–7 yrs)",
            "Senior (7–12 yrs)",
            "Leadership (12+ yrs)"
        ],
        index=3
    )
    state = st.selectbox(
        "State Focus",
        ["All India", "Bihar", "Uttar Pradesh", "Madhya Pradesh",
         "Rajasthan", "Maharashtra", "Karnataka", "Tamil Nadu",
         "West Bengal", "Delhi", "Gujarat", "Odisha", "Jharkhand"],
        index=1
    )
    n_jobs = st.slider("Jobs to fetch per category", 3, 8, 5)

    st.divider()
    fetch_btn = st.button(
        "🔍 Fetch All Openings",
        use_container_width=True,
        type="primary"
    )


# ────────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────────
st.markdown(
    f"## 📡 Government IT & Civil Services Radar"
)
st.markdown(
    f"**{state}** · **{exp_level}** · "
    f"AI-powered openings + prep strategies via `{SARVAM_MODEL}`"
)
st.divider()

if not fetch_btn:
    st.info(
        "👈 Configure your profile in the sidebar, then click "
        "**Fetch All Openings** to load latest government job notifications.",
        icon="💡"
    )
    st.markdown("""
    **What you'll get per category:**
    - 📋 Latest job openings with titles, descriptions, and direct application links
    - 🤖 AI-generated preparation strategy tailored to your experience level and state
    - ⏱ Timeline, eligibility notes, and step-by-step action plan
    """)

elif not tavily_key:
    st.error("Please add your Tavily API key to fetch job openings.", icon="🔑")

else:
    yr         = now_ist().year
    categories = get_categories(exp_level, state, yr)
    tab_names  = list(categories.keys())
    tabs       = st.tabs(tab_names)

    for tab, (cat_name, cat_info) in zip(tabs, categories.items()):
        with tab:

            # ── Fetch jobs ───────────────────────────────────────
            with st.spinner(f"Fetching latest {cat_name} openings…"):
                jobs = fetch_jobs(tavily_key, cat_info["query"], n_jobs)

            # ── Category description ─────────────────────────────
            st.markdown(f"*{cat_info['desc']}*")
            st.markdown("")

            # ── Job listings ─────────────────────────────────────
            st.markdown(
                '<div class="section-label">Latest Openings</div>',
                unsafe_allow_html=True
            )

            if not jobs:
                st.markdown(
                    '<div class="no-results">No results found. '
                    'Try refreshing or check your Tavily key.</div>',
                    unsafe_allow_html=True
                )
                jobs_text = "No openings found at this time."
            else:
                jobs_text_lines = []
                for job in jobs:
                    title   = job.get("title", "Untitled")
                    url     = job.get("url", "")
                    snippet = job.get("content", "")[:280]

                    st.markdown(f"""
                    <div class="job-item">
                        <div class="job-title">{title}</div>
                        <div class="job-snippet">{snippet}</div>
                        <div class="job-link">
                            🔗 <a href="{url}" target="_blank"
                               style="color:#4a9eff;">{url}</a>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    jobs_text_lines.append(f"- {title}: {snippet[:120]}")

                jobs_text = "\n".join(jobs_text_lines)

            st.divider()

            # ── AI Prep Strategy ─────────────────────────────────
            st.markdown(
                '<div class="section-label">🤖 AI Preparation Strategy (sarvam-105b)</div>',
                unsafe_allow_html=True
            )

            if not sarvam_key:
                st.warning(
                    "Add SARVAM_API_KEY to secrets.toml to get "
                    "AI-powered preparation strategies.",
                    icon="🔑"
                )
            else:
                with st.spinner(f"Generating prep strategy with {SARVAM_MODEL}…"):
                    strategy = get_prep_strategy(
                        sarvam_key,
                        cat_name,
                        jobs_text,
                        exp_level,
                        state
                    )

                st.markdown(
                    f'<div class="strategy-box">{strategy}</div>',
                    unsafe_allow_html=True
                )

    st.divider()
    st.caption(
        f"Last fetched: {now_ist().strftime('%d %b %Y %I:%M %p')} IST · "
        f"Search by Tavily · Strategies by {SARVAM_MODEL}"
    )
