import streamlit as st
import requests
import re
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

    .job-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 10px;
    }
    .job-title {
        font-size: 14px;
        font-weight: 600;
        color: #1a2a3a;
        margin-bottom: 4px;
    }
    .job-meta {
        font-size: 12px;
        color: #64748b;
        margin-bottom: 6px;
    }
    .job-link a {
        color: #1a6ef5;
        font-size: 12px;
        font-weight: 500;
        text-decoration: none;
    }
    .cat-insight {
        background: #f0fdf4;
        border-left: 3px solid #16a34a;
        border-radius: 4px;
        padding: 10px 14px;
        font-size: 13px;
        color: #166534;
        margin-bottom: 14px;
        line-height: 1.6;
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
    .ts {
        font-size: 11px;
        color: #94a3b8;
        margin-top: 16px;
        text-align: right;
    }
</style>
""", unsafe_allow_html=True)


def get_key(k):
    try:
        return st.secrets[k]
    except:
        return ""


def clean(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'[#*`\[\]|\\]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


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
        out = []
        for r in res.get("results", []):
            out.append({
                "title":   clean(r.get("title",   "")),
                "url":     r.get("url", ""),
                "content": clean(r.get("content", ""))[:300],
                "date":    r.get("published_date", ""),
            })
        return out
    except Exception as e:
        st.error(f"Tavily error: {e}")
        return []


# ── Keyword categorise ────────────────────────────────────────────
CATEGORY_KEYS = [
    ("BPSC & Bihar Civil Services",       ["bpsc", "bihar public service", "bihar psc"]),
    ("Bihar State IT — BSEDC / BELTRON",  ["bsedc", "beltron", "bihar e-gov", "bihar electronics"]),
    ("NIC — National Informatics Centre", ["nic ", "national informatics", "nic.in"]),
    ("MeitY / Digital India / C-DAC",     ["meity", "digital india", "c-dac", "cdac", "stpi"]),
    ("UPSC — Civil Services & Lateral",   ["upsc", "lateral entry", "ias ", "ips ", "civil services"]),
    ("SSC — Technical & IT Posts",        ["ssc ", "staff selection", "cgl", "chsl"]),
    ("Public Sector — DRDO / ISRO / PSU", ["drdo", "isro", "bel ", "bsnl", "hal ", "ongc", "bhel"]),
]

def categorise(results):
    cats = {name: [] for name, _ in CATEGORY_KEYS}
    cats["Other"] = []

    for r in results:
        t = (r["title"] + " " + r["content"] + " " + r["url"]).lower()
        matched = False
        for name, keys in CATEGORY_KEYS:
            if any(k in t for k in keys):
                cats[name].append(r)
                matched = True
                break
        if not matched:
            cats["Other"].append(r)

    return {k: v for k, v in cats.items() if v}


# ── Sarvam: ONE call per category ────────────────────────────────
# Fast because it's just one call per category, not per card.
# max_tokens=8192 so reasoning model never runs out.
def get_category_insight(sv_key, cat_name, jobs):
    if not sv_key:
        return None

    # Build compact job list
    job_lines = "\n".join(
        f"- {j['title']} | {j['content'][:120]}"
        for j in jobs
    )

    prompt = (
        f"These are government job openings in category: {cat_name}.\n"
        f"{job_lines}\n\n"
        f"Write 2-3 sentences summarising what opportunities are available "
        f"in this category right now. Be specific and factual."
    )

    try:
        resp = requests.post(
            SARVAM_URL,
            headers={
                "api-subscription-key": sv_key,
                "Content-Type": "application/json"
            },
            json={
                "model":       SARVAM_MODEL,
                "messages":    [{"role": "user", "content": prompt}],
                "max_tokens":  8192,
                "temperature": 0.1
            },
            timeout=45
        )
        if resp.status_code == 200:
            c = (
                resp.json()
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content")
            )
            if c:
                return clean(c.strip())
        return None
    except:
        return None


def format_date(pub):
    if not pub:
        return ""
    try:
        d = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        return d.strftime("%d %b %Y")
    except:
        return str(pub)[:10]


def render_jobs(jobs):
    for j in jobs:
        date_str  = format_date(j["date"])
        link_html = (
            f'<a href="{j["url"]}" target="_blank">View / Apply ↗</a>'
            if j["url"] else ""
        )
        st.markdown(f"""
        <div class="job-card">
            <div class="job-title">{j['title']}</div>
            <div class="job-meta">
                {('📅 ' + date_str + ' &nbsp;·&nbsp; ') if date_str else ''}
                {link_html}
            </div>
            <div style="font-size:12px;color:#64748b;line-height:1.6;">
                {j['content']}
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

    # Step 1 — fetch
    with st.spinner("Fetching…"):
        raw = fetch_raw()

    if not raw:
        st.warning("No results. Check Tavily key.")
        st.stop()

    # Step 2 — categorise
    categorised = categorise(raw)
    total = sum(len(v) for v in categorised.values())

    st.success(f"✅ {total} openings across {len(categorised)} categories")

    # Step 3 — render as expanders
    # Click to open = fast initial load
    for cat_label, jobs in categorised.items():
        with st.expander(f"**{cat_label}** — {len(jobs)} openings", expanded=False):

            # Sarvam insight for this category (1 call per category)
            if sv_key:
                with st.spinner("Getting AI insight…"):
                    insight = get_category_insight(sv_key, cat_label, jobs)
                if insight:
                    st.markdown(
                        f'<div class="cat-insight">✦ {insight}</div>',
                        unsafe_allow_html=True
                    )

            render_jobs(jobs)

    st.markdown(
        f'<div class="ts">'
        f'Updated: {now_ist().strftime("%d %b %Y, %I:%M %p")} IST'
        f'</div>',
        unsafe_allow_html=True
    )
