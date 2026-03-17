import streamlit as st
import requests
from datetime import datetime, timezone, timedelta
from tavily import TavilyClient

IST = timezone(timedelta(hours=5, minutes=30))
def now_ist():
    return datetime.now(IST)

SARVAM_URL   = "https://api.sarvam.ai/v1/chat/completions"
SARVAM_MODEL = "sarvam-105b"

st.set_page_config(
    page_title="GovIT Radar",
    page_icon="📡",
    layout="centered"
)

# Minimal CSS — no dark colors anywhere
st.markdown("""
<style>
    .stApp {
        background-color: #ffffff !important;
        font-family: 'Segoe UI', sans-serif;
    }
    [data-testid="stAppViewContainer"] {
        background-color: #ffffff !important;
    }
    [data-testid="stHeader"] {
        background-color: #ffffff !important;
    }
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    #MainMenu, footer { visibility: hidden; }

    .result-block {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 20px 24px;
        margin-top: 16px;
        font-size: 14px;
        color: #1e2d3d;
        line-height: 1.9;
    }
    .ts {
        font-size: 11px;
        color: #94a3b8;
        margin-top: 12px;
        text-align: right;
    }
</style>
""", unsafe_allow_html=True)


def get_key(k):
    try:
        return st.secrets[k]
    except:
        return ""


def fetch_raw():
    yr     = now_ist().year
    client = TavilyClient(api_key=get_key("TAVILY_API_KEY"))
    seen, results = set(), []

    queries = [
        f"BPSC Bihar Public Service Commission recruitment notification {yr}",
        f"NIC National Informatics Centre IT officer recruitment {yr}",
        f"MeitY Digital India C-DAC IT jobs vacancy {yr}",
        f"UPSC lateral entry IT technology specialist {yr}",
        f"Bihar IT e-governance BSEDC BELTRON recruitment {yr}",
        f"SSC CGL technical IT officer government recruitment {yr}",
        f"BEL BSNL DRDO ISRO engineer IT recruitment {yr}",
    ]

    for q in queries:
        try:
            res = client.search(
                query=q,
                search_depth="advanced",
                max_results=4,
                include_domains=[
                    "upsc.gov.in", "ssc.nic.in", "nic.in",
                    "meity.gov.in", "bpsc.bih.nic.in",
                    "sarkariresult.com", "sarkariexam.com",
                    "thehindu.com", "timesofindia.com",
                    "ndtv.com", "livemint.com"
                ]
            )
            for r in res.get("results", []):
                url = r.get("url", "")
                if url and url not in seen:
                    seen.add(url)
                    results.append({
                        "title":   r.get("title", ""),
                        "url":     url,
                        "content": r.get("content", "")[:350]
                    })
        except:
            continue

    return results


def refine(raw):
    text = "\n".join(
        f"Title: {r['title']}\nURL: {r['url']}\nInfo: {r['content']}\n---"
        for r in raw
    )

    prompt = f"""You have raw search data about current Indian government job openings, focused on Bihar and national IT roles.

RAW DATA:
{text}

From this data, extract ONLY real current job openings and present them as clean bullet points.

Format — for each real opening write exactly:
• [Job Title] — [Organization]
  [One line: what the role is and key requirement]
  Apply: [URL]

Group bullets under these plain headings only if real openings exist:
Bihar & State Level
Central Government IT
Civil Services
Public Sector

Important:
- Only include openings actually present in the raw data
- Skip any group with no real openings
- No preparation advice, no strategy, no tips
- No invented details
- Be concise — 3 lines max per bullet"""

    try:
        resp = requests.post(
            SARVAM_URL,
            headers={
                "api-subscription-key": get_key("SARVAM_API_KEY"),
                "Content-Type": "application/json"
            },
            json={
                "model": SARVAM_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "Extract and present only verified current Indian government job openings from provided search data. Be factual and concise. Never add advice or invented details."
                    },
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1000,
                "temperature": 0.1
            },
            timeout=40
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return f"Could not process (Error {resp.status_code})"
    except Exception as e:
        return f"Error: {str(e)[:80]}"


# ── UI ────────────────────────────────────────────────────────────
st.markdown("## 📡 GovIT Radar")
st.markdown("Current government IT & civil services openings — Bihar & India")
st.markdown("")

if st.button("🔍 Fetch Latest Openings", type="primary"):

    if not get_key("TAVILY_API_KEY") or not get_key("SARVAM_API_KEY"):
        st.error("API keys missing in secrets.toml")
    else:
        with st.spinner("Fetching latest notifications…"):
            raw = fetch_raw()

        if not raw:
            st.warning("No results found. Try again.")
        else:
            with st.spinner("Refining results…"):
                output = refine(raw)

            st.markdown(
                f'<div class="result-block">{output}</div>',
                unsafe_allow_html=True
            )
            st.markdown(
                f'<div class="ts">Updated: '
                f'{now_ist().strftime("%d %b %Y, %I:%M %p")} IST</div>',
                unsafe_allow_html=True
            )
