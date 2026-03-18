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
    .cat-heading {
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: #1a6ef5;
        margin: 28px 0 12px 0;
        padding-bottom: 6px;
        border-bottom: 2px solid #e2e8f0;
    }
    .job-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 10px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .job-title {
        font-size: 14px;
        font-weight: 600;
        color: #1a2a3a;
        margin-bottom: 4px;
        line-height: 1.4;
    }
    .job-summary {
        font-size: 12px;
        color: #475569;
        line-height: 1.6;
        margin-bottom: 8px;
    }
    .job-link a {
        color: #1a6ef5;
        text-decoration: none;
        font-size: 12px;
        font-weight: 500;
    }
    .no-results {
        color: #94a3b8;
        font-size: 13px;
        padding: 8px 0;
        font-style: italic;
    }
    .ts {
        font-size: 11px;
        color: #94a3b8;
        margin-top: 20px;
        text-align: right;
    }
    .stButton > button {
        background-color: #1a6ef5 !important;
        color: white !important;
        border: none !important;
        padding: 10px 28px !important;
        border-radius: 6px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
    }
    .debug-box {
        background: #fff8f0;
        border: 1px solid #fcd0a0;
        border-radius: 8px;
        padding: 14px 18px;
        font-size: 12px;
        color: #7a4010;
        margin-top: 12px;
        white-space: pre-wrap;
        word-break: break-word;
    }
    .summary-bar {
        background: #f0f7ff;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 10px 16px;
        font-size: 13px;
        color: #1e40af;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)


def get_key(k):
    try:
        return st.secrets[k]
    except:
        return ""


# ── Single Tavily call ────────────────────────────────────────────
def fetch_raw():
    yr    = now_ist().year
    month = now_ist().strftime("%B")

    query = (
        f"BPSC Bihar NIC MeitY UPSC SSC DRDO ISRO BEL C-DAC "
        f"government IT civil services recruitment vacancy {month} {yr}"
    )

    try:
        client = TavilyClient(api_key=get_key("TAVILY_API_KEY"))
        res = client.search(
            query=query,
            search_depth="advanced",
            max_results=20,
            days=60,
            include_domains=[
                "upsc.gov.in", "ssc.nic.in", "nic.in",
                "meity.gov.in", "bpsc.bih.nic.in",
                "sarkariresult.com", "sarkariexam.com",
                "employment.gov.in", "freejobalert.com",
                "rojgarresult.com", "indgovtjobs.in",
                "thehindu.com", "timesofindia.com",
                "ndtv.com", "jagran.com",
                "digitalindia.gov.in", "cdac.in",
                "drdo.gov.in", "isro.gov.in",
            ]
        )
        return res.get("results", [])
    except Exception as e:
        return []


# ── Sarvam-105b: summarise each result, 1 at a time ──────────────
# Instead of sending all results at once (token overflow),
# we send each result individually for a 1-line summary.
# Short prompt = minimal reasoning tokens used.
def summarise_one(sarvam_key, title, content):
    prompt = (
        f"Summarise this Indian government job opening in exactly 2 sentences. "
        f"Mention post, organisation, key eligibility, and last date if found. "
        f"Be factual, use only info given.\n\n"
        f"Title: {title}\nDetails: {content}"
    )
    try:
        resp = requests.post(
            SARVAM_URL,
            headers={
                "api-subscription-key": sarvam_key,
                "Content-Type": "application/json"
            },
            json={
                "model":       SARVAM_MODEL,
                "messages":    [{"role": "user", "content": prompt}],
                "max_tokens":  300,
                "temperature": 0.1
            },
            timeout=30
        )
        if resp.status_code == 200:
            rj      = resp.json()
            choices = rj.get("choices", [])
            if choices:
                content_out = choices[0].get("message", {}).get("content")
                if content_out:
                    return content_out.strip()
        return None
    except:
        return None


# ── Categorise results without AI ────────────────────────────────
# Simple keyword match — fast and reliable
def categorise(results):
    cats = {
        "BPSC & Bihar Civil Services":       [],
        "Bihar State IT — BSEDC / BELTRON":  [],
        "NIC — National Informatics Centre": [],
        "MeitY / Digital India / C-DAC":     [],
        "UPSC — Civil Services & Lateral":   [],
        "SSC — Technical & IT Posts":        [],
        "Public Sector — DRDO / ISRO / PSU": [],
        "Other Government Openings":         [],
    }

    for r in results:
        text = (r.get("title", "") + " " + r.get("content", "")).lower()
        url  = r.get("url", "").lower()
        combined = text + " " + url

        if any(k in combined for k in ["bpsc", "bihar public service", "bihar psc"]):
            cats["BPSC & Bihar Civil Services"].append(r)
        elif any(k in combined for k in ["bsedc", "beltron", "bihar e-gov", "bihar it dept", "bihar electronics"]):
            cats["Bihar State IT — BSEDC / BELTRON"].append(r)
        elif any(k in combined for k in ["nic ", "national informatics", "nic.in"]):
            cats["NIC — National Informatics Centre"].append(r)
        elif any(k in combined for k in ["meity", "digital india", "c-dac", "cdac", "stpi"]):
            cats["MeitY / Digital India / C-DAC"].append(r)
        elif any(k in combined for k in ["upsc", "ias", "ips", "lateral entry", "civil services"]):
            cats["UPSC — Civil Services & Lateral"].append(r)
        elif any(k in combined for k in ["ssc", "staff selection", "cgl", "chsl"]):
            cats["SSC — Technical & IT Posts"].append(r)
        elif any(k in combined for k in ["drdo", "isro", "bel ", "bsnl", "hal ", "ongc", "bhel", "psu", "public sector"]):
            cats["Public Sector — DRDO / ISRO / PSU"].append(r)
        else:
            cats["Other Government Openings"].append(r)

    # Remove empty categories
    return {k: v for k, v in cats.items() if v}


def render_card(r, summary):
    title = r.get("title", "—")
    url   = r.get("url", "")
    pub   = r.get("published_date", "")

    date_str = ""
    if pub:
        try:
            d = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            date_str = d.strftime("%d %b %Y")
        except:
            date_str = str(pub)[:10]

    display_summary = summary if summary else r.get("content", "")[:200]

    link_html = (
        f'<a href="{url}" target="_blank">View / Apply ↗</a>'
        if url else ""
    )

    st.markdown(f"""
    <div class="job-card">
        <div class="job-title">{title}</div>
        <div class="job-summary">{display_summary}</div>
        <div style="display:flex; gap:16px; align-items:center; flex-wrap:wrap;">
            {"<span style='font-size:11px;color:#64748b;'>📅 " + date_str + "</span>" if date_str else ""}
            <span class="job-link">{link_html}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── UI ─────────────────────────────────────────────────────────────
st.markdown("## 📡 GovIT Radar")
st.markdown(
    f"Latest government IT & civil services openings — Bihar & India"
    f" &nbsp;·&nbsp; *{now_ist().strftime('%d %b %Y')}*"
)
st.markdown("")

if st.button("🔍 Fetch Latest Openings", type="primary"):

    if not get_key("TAVILY_API_KEY"):
        st.error("TAVILY_API_KEY missing from secrets.toml")
        st.stop()

    sv_key = get_key("SARVAM_API_KEY")

    # Step 1 — single Tavily call
    with st.spinner("Fetching latest notifications…"):
        raw = fetch_raw()

    if not raw:
        st.warning("No results returned. Check Tavily key or try again.")
        st.stop()

    # Step 2 — categorise by keyword (no AI needed for this)
    categorised = categorise(raw)
    total       = sum(len(v) for v in categorised.values())

    st.markdown(
        f'<div class="summary-bar">'
        f'✅ Found <strong>{total} openings</strong> across '
        f'<strong>{len(categorised)} categories</strong>'
        f'{"  ·  AI summaries enabled" if sv_key else "  ·  Add SARVAM_API_KEY for AI summaries"}'
        f'</div>',
        unsafe_allow_html=True
    )

    today = now_ist()

    # Step 3 — render each category
    # Sarvam called per-card (short prompt = no token overflow)
    for cat_label, results in categorised.items():
        st.markdown(
            f'<div class="cat-heading">{cat_label} ({len(results)})</div>',
            unsafe_allow_html=True
        )

        for r in results:
            summary = None
            if sv_key:
                title   = r.get("title", "")
                content = r.get("content", "")[:300]
                with st.spinner(f"Summarising: {title[:50]}…"):
                    summary = summarise_one(sv_key, title, content)

            render_card(r, summary)

    st.markdown(
        f'<div class="ts">'
        f'Updated: {today.strftime("%d %b %Y, %I:%M %p")} IST'
        f'</div>',
        unsafe_allow_html=True
    )
