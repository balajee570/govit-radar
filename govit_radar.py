# ================================================================
# GovIT Radar — Bihar & India Government IT Career Opportunities
# Tavily fetches raw data → Sarvam-105b refines into clean output
# ================================================================

import streamlit as st
import requests
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

    .stApp {
        background: #f5f7fa;
        font-family: 'Inter', sans-serif;
    }
    .main-title {
        font-size: 26px;
        font-weight: 600;
        color: #1a2a3a;
        margin-bottom: 4px;
    }
    .subtitle {
        font-size: 13px;
        color: #6a8aaa;
        margin-bottom: 24px;
    }
    .result-card {
        background: #ffffff;
        border: 1px solid #dde3ec;
        border-radius: 10px;
        padding: 24px 28px;
        margin-bottom: 16px;
        line-height: 1.9;
        font-size: 14px;
        color: #2a3a4a;
        white-space: pre-wrap;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .timestamp {
        font-size: 11px;
        color: #aab8c8;
        text-align: right;
        margin-top: 10px;
    }
    #MainMenu, footer, header { visibility: hidden; }
    section[data-testid="stSidebar"] { display: none; }
    .stButton > button {
        background: #1a6ef5;
        border: none;
        color: #ffffff;
        font-size: 14px;
        font-weight: 500;
        padding: 10px 32px;
        border-radius: 6px;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background: #1558d0;
        box-shadow: 0 4px 12px rgba(26,110,245,0.3);
    }
    .hint-text {
        color: #aab8c8;
        font-size: 13px;
        padding: 16px 0;
        line-height: 2;
    }
</style>
""", unsafe_allow_html=True)


# ── Keys from secrets ─────────────────────────────────────────────
def get_key(name):
    try:
        return st.secrets[name]
    except:
        return ""

tavily_key = get_key("TAVILY_API_KEY")
sarvam_key = get_key("SARVAM_API_KEY")


# ── Search queries ────────────────────────────────────────────────
def get_queries():
    yr = now_ist().year
    return [
        f"BPSC Bihar Public Service Commission latest notification recruitment {yr}",
        f"NIC National Informatics Centre IT officer recruitment {yr}",
        f"MeitY Digital India C-DAC government IT jobs {yr}",
        f"UPSC lateral entry IT technology specialist recruitment {yr}",
        f"Bihar government IT e-governance jobs vacancy {yr}",
        f"SSC CGL technical IT officer central government {yr}",
        f"BSEDC BELTRON Bihar IT recruitment notification {yr}",
        f"PSU BEL BSNL DRDO technology engineer recruitment {yr}",
    ]


# ── Fetch raw results ─────────────────────────────────────────────
def fetch_all_raw(tavily_key):
    client = TavilyClient(api_key=tavily_key)
    all_results = []
    seen_urls = set()

    for query in get_queries():
        try:
            res = client.search(
                query=query,
                search_depth="advanced",
                max_results=4,
                include_domains=[
                    "upsc.gov.in", "ssc.nic.in", "nic.in",
                    "meity.gov.in", "bpsc.bih.nic.in",
                    "sarkariresult.com", "sarkariexam.com",
                    "employment.gov.in", "thehindu.com",
                    "timesofindia.com", "ndtv.com", "livemint.com",
                    "jagran.com", "bhaskar.com"
                ]
            )
            for r in res.get("results", []):
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append({
                        "title":   r.get("title", ""),
                        "url":     url,
                        "content": r.get("content", "")[:400]
                    })
        except:
            continue

    return all_results


# ── Sarvam-105b refinement ────────────────────────────────────────
def refine_with_sarvam(sarvam_key, raw_results):
    if not sarvam_key:
        return "Sarvam API key not configured."

    raw_text = ""
    for r in raw_results:
        raw_text += f"\nTitle: {r['title']}\nURL: {r['url']}\nDetails: {r['content']}\n---"

    prompt = f"""You are an expert career advisor for Indian government and IT sector jobs.

Below is raw search data about current government job openings in India, with focus on Bihar.

RAW DATA:
{raw_text}

Your task: Read all the above carefully and produce a clean, well-organized summary of ONLY the most relevant and actionable current job opportunities.

For each genuine opportunity, write:
- Job title and organization
- Key eligibility (1 line)
- Why it is relevant (1 line)
- Application link

Group under these headings only if real results exist:
BIHAR STATE OPPORTUNITIES
CENTRAL GOVERNMENT IT ROLES
CIVIL SERVICES & UPSC
PUBLIC SECTOR (PSU)

Rules:
- Only include real, specific openings from the data
- Skip any heading with no current openings
- Max 4 lines per entry
- Precise and factual — only what is in the raw data
- Do not invent or assume any details"""

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
                        "content": "You are a precise career intelligence assistant. Extract and present only verified, actionable government job opportunities from provided data. Never invent details."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1200,
                "temperature": 0.2
            },
            timeout=40
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return f"Could not process results (Error {resp.status_code})."
    except Exception as e:
        return f"Error: {str(e)[:100]}"


# ── UI ────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">📡 GovIT Radar</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">'
    'Latest government IT &amp; civil services opportunities — Bihar &amp; India'
    '</div>',
    unsafe_allow_html=True
)

fetch_btn = st.button("🔍 Find Latest Opportunities")

st.markdown("")

if fetch_btn:
    if not tavily_key:
        st.error("TAVILY_API_KEY not found in secrets.", icon="🔑")
    elif not sarvam_key:
        st.error("SARVAM_API_KEY not found in secrets.", icon="🔑")
    else:
        with st.spinner("Scanning latest notifications across all sources…"):
            raw = fetch_all_raw(tavily_key)

        if not raw:
            st.warning("No results found. Please try again.")
        else:
            with st.spinner("Analysing and refining results…"):
                refined = refine_with_sarvam(sarvam_key, raw)

            st.markdown(
                f'<div class="result-card">{refined}</div>',
                unsafe_allow_html=True
            )
            st.markdown(
                f'<div class="timestamp">'
                f'Last updated: {now_ist().strftime("%d %b %Y, %I:%M %p")} IST'
                f'</div>',
                unsafe_allow_html=True
            )
else:
    st.markdown("""
    <div class="hint-text">
    Click the button above to load the latest opportunities across:<br>
    BPSC &nbsp;·&nbsp; NIC &nbsp;·&nbsp; MeitY &nbsp;·&nbsp;
    Digital India &nbsp;·&nbsp; UPSC Lateral Entry &nbsp;·&nbsp;
    SSC Technical &nbsp;·&nbsp; Bihar IT Dept &nbsp;·&nbsp; PSU
    </div>
    """, unsafe_allow_html=True)
