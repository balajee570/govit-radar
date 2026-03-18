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
        margin-bottom: 6px;
        line-height: 1.4;
    }
    .job-summary {
        font-size: 13px;
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
                "upsc.gov.in",
                "ssc.nic.in",
                "nic.in",
                "meity.gov.in",
                "bpsc.bih.nic.in",
                "sarkariresult.com",
                "sarkariexam.com",
                "employment.gov.in",
                "freejobalert.com",
                "rojgarresult.com",
                "indgovtjobs.in",       # ← back in
                "thehindu.com",
                "timesofindia.com",
                "ndtv.com",
                "jagran.com",
                "digitalindia.gov.in",
                "cdac.in",
                "drdo.gov.in",
                "isro.gov.in",
            ]
        )
        return res.get("results", [])
    except:
        return []


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
        t = (
            r.get("title",   "") + " " +
            r.get("content", "") + " " +
            r.get("url",     "")
        ).lower()

        if any(k in t for k in ["bpsc", "bihar public service", "bihar psc"]):
            cats["BPSC & Bihar Civil Services"].append(r)
        elif any(k in t for k in ["bsedc", "beltron", "bihar e-gov", "bihar electronics"]):
            cats["Bihar State IT — BSEDC / BELTRON"].append(r)
        elif any(k in t for k in ["nic ", "national informatics", "nic.in"]):
            cats["NIC — National Informatics Centre"].append(r)
        elif any(k in t for k in ["meity", "digital india", "c-dac", "cdac", "stpi"]):
            cats["MeitY / Digital India / C-DAC"].append(r)
        elif any(k in t for k in ["upsc", "lateral entry", "civil services", "ias ", "ips "]):
            cats["UPSC — Civil Services & Lateral"].append(r)
        elif any(k in t for k in ["ssc ", "staff selection", "cgl", "chsl"]):
            cats["SSC — Technical & IT Posts"].append(r)
        elif any(k in t for k in ["drdo", "isro", "bel ", "bsnl", "hal ", "ongc", "bhel"]):
            cats["Public Sector — DRDO / ISRO / PSU"].append(r)
        else:
            cats["Other Government Openings"].append(r)

    return {k: v for k, v in cats.items() if v}


def summarise(sv_key, title, content):
    """
    Sarvam-105b is a reasoning model.
    ~500 tokens used internally for reasoning.
    max_tokens=800 ensures output is never cut off.
    Prompt kept to 1 line — less reasoning needed.
    """
    try:
        resp = requests.post(
            SARVAM_URL,
            headers={
                "api-subscription-key": sv_key,
                "Content-Type": "application/json"
            },
            json={
                "model": SARVAM_MODEL,
                "messages": [{
                    "role": "user",
                    "content": (
                        f"In 2 sentences summarise this Indian govt job opening. "
                        f"Include post, organisation, eligibility, last date if found. "
                        f"Title: {title}. Details: {content[:200]}"
                    )
                }],
                "max_tokens":  800,
                "temperature": 0.1
            },
            timeout=30
        )
        if resp.status_code == 200:
            c = (
                resp.json()
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content")
            )
            return c.strip() if c else None
        return None
    except:
        return None


def render_card(r, summary):
    title = r.get("title",   "—")
    url   = r.get("url",     "")
    pub   = r.get("published_date", "")

    date_str = ""
    if pub:
        try:
            d = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            date_str = d.strftime("%d %b %Y")
        except:
            date_str = str(pub)[:10]

    # AI badge — clearly shows whether Sarvam summarised this card
    if summary:
        badge   = (
            "<span style='font-size:10px;background:#dcfce7;color:#16a34a;"
            "padding:2px 8px;border-radius:4px;font-weight:600;'>✦ AI Summary</span>"
        )
        display = summary
    else:
        badge   = (
            "<span style='font-size:10px;background:#f1f5f9;color:#94a3b8;"
            "padding:2px 8px;border-radius:4px;'>Raw</span>"
        )
        display = r.get("content", "")[:220]

    link_html = (
        f'<a href="{url}" target="_blank">View / Apply ↗</a>' if url else ""
    )

    st.markdown(f"""
    <div class="job-card">
        <div style="display:flex;justify-content:space-between;
                    align-items:flex-start;gap:8px;margin-bottom:6px;">
            <div class="job-title">{title}</div>
            {badge}
        </div>
        <div class="job-summary">{display}</div>
        <div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap;">
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

    with st.spinner("Fetching latest notifications…"):
        raw = fetch_raw()

    if not raw:
        st.warning("No results. Check Tavily key or try again.")
        st.stop()

    categorised = categorise(raw)
    total       = sum(len(v) for v in categorised.values())
    ai_note     = "✦ AI summaries enabled" if sv_key else "Add SARVAM_API_KEY for AI summaries"

    st.markdown(
        f'<div class="summary-bar">'
        f'✅ <strong>{total} openings</strong> across '
        f'<strong>{len(categorised)} categories</strong>'
        f' &nbsp;·&nbsp; {ai_note}'
        f'</div>',
        unsafe_allow_html=True
    )

    ai_count  = 0
    raw_count = 0
    today     = now_ist()

    for cat_label, results in categorised.items():
        st.markdown(
            f'<div class="cat-heading">{cat_label} — {len(results)}</div>',
            unsafe_allow_html=True
        )
        for r in results:
            s = None
            if sv_key:
                with st.spinner(f"Summarising…"):
                    s = summarise(sv_key, r.get("title",""), r.get("content",""))
            if s:
                ai_count  += 1
            else:
                raw_count += 1
            render_card(r, s)

    st.markdown(
        f'<div class="ts">'
        f'Updated: {today.strftime("%d %b %Y, %I:%M %p")} IST'
        f' &nbsp;·&nbsp; ✦ {ai_count} AI summarised'
        f' &nbsp;·&nbsp; {raw_count} raw'
        f'</div>',
        unsafe_allow_html=True
    )
