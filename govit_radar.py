import streamlit as st
import requests
from datetime import datetime, timezone, timedelta
from tavily import TavilyClient

IST = timezone(timedelta(hours=5, minutes=30))
def now_ist():
    return datetime.now(IST)

SARVAM_URL   = "https://api.sarvam.ai/v1/chat/completions"
SARVAM_MODEL = "sarvam-105b"

st.set_page_config(page_title="GovIT Radar", page_icon="📡", layout="centered")

st.markdown("""
<style>
    .stApp, [data-testid="stAppViewContainer"],
    [data-testid="stHeader"], [data-testid="block-container"] {
        background-color: #ffffff !important;
        font-family: 'Segoe UI', sans-serif;
    }
    section[data-testid="stSidebar"] { display: none !important; }
    #MainMenu, footer { visibility: hidden; }

    .result-block {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 22px 26px;
        margin-top: 16px;
        font-size: 14px;
        color: #1e2d3d;
        line-height: 2;
        white-space: pre-wrap;
    }
    .ts {
        font-size: 11px;
        color: #94a3b8;
        margin-top: 10px;
        text-align: right;
    }
    .stButton > button {
        background-color: #1a6ef5 !important;
        color: white !important;
        border: none !important;
        padding: 10px 28px !important;
        border-radius: 6px !important;
        font-size: 14px !important;
    }
</style>
""", unsafe_allow_html=True)


def get_key(k):
    try:
        return st.secrets[k]
    except:
        return ""


# ── Queries covering all topics discussed ─────────────────────────
# BPSC civil services, NIC, MeitY, lateral entry,
# Bihar IT, SSC technical, PSU IT
def get_queries():
    now   = now_ist()
    yr    = now.year
    month = now.strftime("%B")
    prev  = (now - timedelta(days=30)).strftime("%B")

    return [
        # BPSC & Bihar civil services
        f"BPSC combined competitive examination notification {month} {yr}",
        f"BPSC 72nd 73rd CCE prelims mains date apply {yr}",
        f"Bihar Public Service Commission new vacancy {yr}",

        # Bihar state IT
        f"BSEDC BELTRON Bihar IT recruitment {month} {yr}",
        f"Bihar e-governance IT officer vacancy {yr}",
        f"Bihar government digital technology jobs {yr}",

        # NIC
        f"NIC National Informatics Centre scientist engineer recruitment {month} {yr}",
        f"NIC IT officer vacancy notification apply online {yr}",

        # MeitY / Digital India
        f"MeitY Digital India Corporation recruitment {month} {yr}",
        f"C-DAC STPI IT jobs vacancy notification {yr}",

        # UPSC lateral entry
        f"UPSC lateral entry joint secretary IT technology {yr}",
        f"DOPT lateral entry specialist director recruitment {yr}",

        # SSC technical
        f"SSC CGL technical scientific IT officer {month} {yr}",

        # PSU IT
        f"BEL BSNL DRDO ISRO IT engineer recruitment {month} {yr}",
        f"PSU technology officer vacancy notification {yr}",
    ]


def fetch_raw():
    client      = TavilyClient(api_key=get_key("TAVILY_API_KEY"))
    seen, found = set(), []
    now         = now_ist()
    cutoff      = now - timedelta(days=60)   # 2-month window

    for q in get_queries():
        try:
            res = client.search(
                query=q,
                search_depth="advanced",
                max_results=4,
                # Tavily days filter — last 60 days only
                days=60,
                include_domains=[
                    "upsc.gov.in", "ssc.nic.in", "nic.in",
                    "meity.gov.in", "bpsc.bih.nic.in",
                    "sarkariresult.com", "sarkariexam.com",
                    "employment.gov.in", "ncs.gov.in",
                    "thehindu.com", "timesofindia.com",
                    "ndtv.com", "livemint.com",
                    "jagran.com", "bhaskar.com",
                    "digitalindia.gov.in", "cdac.in"
                ]
            )
            for r in res.get("results", []):
                url = r.get("url", "")
                if url and url not in seen:
                    seen.add(url)
                    found.append({
                        "title":       r.get("title", ""),
                        "url":         url,
                        "content":     r.get("content", "")[:400],
                        "published":   r.get("published_date", "unknown"),
                    })
        except:
            continue

    return found


def refine(raw, today_str):
    text = "\n".join(
        f"Title: {r['title']}\n"
        f"Published: {r['published']}\n"
        f"URL: {r['url']}\n"
        f"Info: {r['content']}\n---"
        for r in raw
    )

    prompt = f"""Today's date: {today_str}

You have raw search data about Indian government job openings focused on Bihar and national IT/civil services roles.

RAW DATA:
{text}

Your job: Act as a strict filter and presenter.

FILTERING RULES — discard any item that:
- Has a last date / application deadline that has already passed before {today_str}
- Was published more than 2 months before {today_str}
- Is a news article, opinion, or result announcement (not an active opening)
- Is vague with no specific post, organization, or link
- Is a duplicate of another item

PRESENTATION — for each item that PASSES the filter, write exactly:
• [Post Name] — [Organization Name]
  [What the role is + key qualification in one line]
  [Last date to apply if mentioned, else say "Check official site"]
  Apply: [URL]

Group under these headings only if valid openings exist under them:
Bihar & State Level
Central Government IT
Civil Services & UPSC
Public Sector Units

If a group has zero valid openings after filtering, skip it entirely.
Do not add any commentary, advice, tips, or strategy.
Only show openings active as of {today_str}."""

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
                        "content": (
                            f"You are a strict career intelligence filter. "
                            f"Today is {today_str}. "
                            "Show ONLY currently active Indian government job openings. "
                            "Discard expired, old, or irrelevant items without mercy. "
                            "Never invent or assume any detail not in the data."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1200,
                "temperature": 0.1
            },
            timeout=45
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return f"Could not process results (Error {resp.status_code})"
    except Exception as e:
        return f"Error: {str(e)[:100]}"


# ── UI ─────────────────────────────────────────────────────────────
st.markdown("## 📡 GovIT Radar")
st.markdown(
    "Active government IT & civil services openings — Bihar & India &nbsp;·&nbsp; "
    f"*{now_ist().strftime('%d %b %Y')}*"
)
st.markdown("")

if st.button("🔍 Fetch Active Openings", type="primary"):

    if not get_key("TAVILY_API_KEY") or not get_key("SARVAM_API_KEY"):
        st.error("API keys missing. Add TAVILY_API_KEY and SARVAM_API_KEY to secrets.toml")
    else:
        with st.spinner("Scanning sources for recent notifications…"):
            raw = fetch_raw()

        if not raw:
            st.warning("No results returned. Check your Tavily key or try again.")
        else:
            today_str = now_ist().strftime("%d %B %Y")
            with st.spinner("Filtering active openings only…"):
                output = refine(raw, today_str)

            st.markdown(
                f'<div class="result-block">{output}</div>',
                unsafe_allow_html=True
            )
            st.markdown(
                f'<div class="ts">'
                f'Fetched: {now_ist().strftime("%d %b %Y, %I:%M %p")} IST &nbsp;·&nbsp; '
                f'Showing openings active as of today only'
                f'</div>',
                unsafe_allow_html=True
            )
