# ================================================================
# GovIT Radar — Government IT & Civil Services Dashboard
# ================================================================

import streamlit as st
import requests
import time
from datetime import datetime, timezone, timedelta
from tavily import TavilyClient

IST = timezone(timedelta(hours=5, minutes=30))
def now_ist():
    return datetime.now(IST)

SARVAM_MODEL = "sarvam-105b"
SARVAM_URL   = "https://api.sarvam.ai/v1/chat/completions"

st.set_page_config(page_title="GovIT Radar", page_icon="📡", layout="wide")

st.markdown("""
<style>
    .stApp { background: #0f1117; }
    .job-item {
        background: #1a1f2e;
        border: 1px solid #2a3a4e;
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 10px;
    }
    .job-title { font-size: 15px; font-weight: 600; color: #e0e6f0; margin-bottom: 6px; }
    .job-snippet { font-size: 12px; color: #6a8aaa; line-height: 1.6; margin-bottom: 8px; }
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
        font-size: 11px; font-weight: 600;
        letter-spacing: 1.5px; text-transform: uppercase;
        color: #00cc66; margin: 16px 0 8px 0;
    }
    #MainMenu, footer, header { visibility: hidden; }
    section[data-testid="stSidebar"] { display: none; }
</style>
""", unsafe_allow_html=True)


def get_key(name):
    try:
        return st.secrets[name]
    except:
        return ""


def fetch_jobs(tavily_key, query, n=5):
    try:
        client = TavilyClient(api_key=tavily_key)
        result = client.search(
            query=query,
            search_depth="advanced",
            max_results=n,
            include_domains=[
                "upsc.gov.in", "ssc.nic.in", "nic.in",
                "meity.gov.in", "bpsc.bih.nic.in",
                "sarkariresult.com", "sarkariexam.com",
                "thehindu.com", "timesofindia.com",
                "ndtv.com", "livemint.com",
                "employment.gov.in", "ncs.gov.in"
            ]
        )
        return result.get("results", [])
    except Exception as e:
        return []


def get_prep_strategy(sarvam_key, category, jobs_text, state):
    if not sarvam_key:
        return "API key not configured."

    prompt = f"""You are a career advisor for Indian government jobs.

Category of jobs: {category}
State focus: {state}

Recent openings found:
{jobs_text}

Write a clear preparation strategy for someone interested in these openings. Include:
1. Overview of what these roles offer
2. Eligibility and key requirements
3. Step-by-step preparation plan
4. Key resources and study material
5. How and where to apply
6. Realistic timeline

Keep it practical and India-specific. No bullet symbol formatting, use plain numbered steps."""

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
                        "content": "You are a career advisor specializing in Indian government and IT sector jobs. Give specific, actionable guidance."
                    },
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 900,
                "temperature": 0.3
            },
            timeout=30
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return f"Could not generate strategy (Error {resp.status_code})."
    except Exception as e:
        return f"Could not generate strategy: {str(e)[:80]}"


def get_categories(state, yr):
    sq = f"{state} " if state != "All India" else ""
    return {
        "🏛️ BPSC / Bihar Civil Services": {
            "query": f"BPSC Bihar Public Service Commission combined competitive exam notification {yr}",
            "desc": "Bihar state gazetted officer posts — SDO, DSP, BAS and other services"
        },
        "🇮🇳 UPSC Civil Services": {
            "query": f"UPSC civil services IAS IPS IFS examination notification {yr}",
            "desc": "Central government all-India services — IAS, IPS, IFS"
        },
        "💻 NIC — IT Officer": {
            "query": f"NIC National Informatics Centre scientist engineer recruitment {yr}",
            "desc": "Government IT infrastructure and e-governance technical roles"
        },
        "🌐 MeitY / Digital India": {
            "query": f"MeitY Digital India C-DAC STPI IT recruitment vacancy notification {yr}",
            "desc": "Central IT ministry, digital policy and implementation roles"
        },
        "🏢 State IT Department": {
            "query": f"{sq}state electronics corporation IT department e-governance recruitment {yr}",
            "desc": f"State government IT, digitisation and technology roles"
        },
        "📋 SSC Technical Posts": {
            "query": f"SSC CGL CHSL scientific technical IT officer recruitment notification {yr}",
            "desc": "Central government technical officer posts via Staff Selection Commission"
        },
        "🔵 PSU — IT & Tech": {
            "query": f"BEL BSNL DRDO ISRO BHEL IT technology engineer recruitment {yr}",
            "desc": "Public sector undertakings with technology and IT openings"
        },
        "🎯 Lateral Entry": {
            "query": f"UPSC lateral entry joint secretary deputy director IT specialist recruitment {yr}",
            "desc": "Direct senior-level entry for experienced professionals"
        },
    }


# ── Keys ─────────────────────────────────────────────────────────
tavily_key = get_key("TAVILY_API_KEY")
sarvam_key = get_key("SARVAM_API_KEY")

# ── Header ───────────────────────────────────────────────────────
st.markdown("## 📡 Government IT & Civil Services — Latest Openings")
st.markdown(
    f"*Updated: {now_ist().strftime('%d %b %Y, %I:%M %p')} IST*"
)
st.divider()

# ── Controls ─────────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    state = st.selectbox(
        "State Focus",
        ["All India", "Bihar", "Uttar Pradesh", "Madhya Pradesh",
         "Rajasthan", "Maharashtra", "Karnataka", "Tamil Nadu",
         "West Bengal", "Delhi", "Gujarat", "Odisha", "Jharkhand"],
        index=1,
        label_visibility="visible"
    )

with col2:
    n_jobs = st.selectbox(
        "Results per category",
        [3, 5, 8],
        index=1
    )

with col3:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    fetch_btn = st.button("🔍 Fetch Openings", type="primary", use_container_width=True)

st.divider()

# ── Main content ─────────────────────────────────────────────────
if not fetch_btn:
    st.markdown("""
    ### How it works

    Click **Fetch Openings** above to load the latest government job notifications.

    Each section below will show:
    - **Latest openings** with titles, descriptions and direct application links
    - **Preparation strategy** — what to study, how to apply, timeline

    Sections covered:
    - BPSC / Bihar Civil Services
    - UPSC Civil Services
    - NIC IT Officer Roles
    - MeitY / Digital India
    - State IT Department
    - SSC Technical Posts
    - PSU IT & Tech
    - Lateral Entry
    """)

elif not tavily_key:
    st.error(
        "Tavily API key not found. "
        "Add TAVILY_API_KEY to your Streamlit secrets.",
        icon="🔑"
    )

else:
    yr         = now_ist().year
    categories = get_categories(state, yr)
    tab_labels = list(categories.keys())
    tabs       = st.tabs(tab_labels)

    for tab, (cat_name, cat_info) in zip(tabs, categories.items()):
        with tab:

            st.markdown(f"*{cat_info['desc']}*")
            st.markdown("")

            # ── Jobs ─────────────────────────────────────────────
            st.markdown(
                '<div class="section-label">Latest Openings</div>',
                unsafe_allow_html=True
            )

            with st.spinner("Fetching latest openings…"):
                jobs = fetch_jobs(tavily_key, cat_info["query"], n_jobs)

            if not jobs:
                st.markdown(
                    "No recent notifications found for this category.",
                )
                jobs_summary = "No openings found currently."
            else:
                jobs_summary_lines = []
                for job in jobs:
                    title   = job.get("title", "")
                    url     = job.get("url", "")
                    snippet = job.get("content", "")[:300]

                    st.markdown(f"""
                    <div class="job-item">
                        <div class="job-title">{title}</div>
                        <div class="job-snippet">{snippet}</div>
                        <div class="job-link">
                            🔗 <a href="{url}" target="_blank"
                               style="color:#4a9eff; font-size:12px;">{url}</a>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    jobs_summary_lines.append(
                        f"- {title}: {snippet[:120]}"
                    )

                jobs_summary = "\n".join(jobs_summary_lines)

            st.divider()

            # ── Prep Strategy ─────────────────────────────────────
            st.markdown(
                '<div class="section-label">Preparation Strategy</div>',
                unsafe_allow_html=True
            )

            if not sarvam_key:
                st.warning(
                    "Add SARVAM_API_KEY to secrets to get preparation strategies.",
                    icon="🔑"
                )
            else:
                with st.spinner("Generating preparation strategy…"):
                    strategy = get_prep_strategy(
                        sarvam_key,
                        cat_name,
                        jobs_summary,
                        state
                    )

                st.markdown(
                    f'<div class="strategy-box">{strategy}</div>',
                    unsafe_allow_html=True
                )

    st.divider()
    st.caption(
        f"Data fetched: {now_ist().strftime('%d %b %Y %I:%M %p')} IST"
    )
