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

st.set_page_config(
    page_title="GovIT Radar",
    page_icon="📡",
    layout="centered"
)

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

CATEGORY_KEYS = [
    ("🏛️ BPSC & Bihar Civil Services",
     ["bpsc", "bihar public service", "bihar psc"]),
    ("💻 Bihar State IT — BSEDC / BELTRON",
     ["bsedc", "beltron", "bihar e-gov", "bihar electronics"]),
    ("🖥️ NIC — National Informatics Centre",
     ["nic ", "national informatics", "nic.in"]),
    ("🌐 MeitY / Digital India / C-DAC",
     ["meity", "digital india", "c-dac", "cdac", "stpi"]),
    ("📜 UPSC — Civil Services & Lateral Entry",
     ["upsc", "lateral entry", "ias ", "ips ", "civil services"]),
    ("📋 SSC — Technical & IT Posts",
     ["ssc ", "staff selection", "cgl", "chsl"]),
    ("🔬 Public Sector — DRDO / ISRO / PSU",
     ["drdo", "isro", "bel ", "bsnl", "hal ", "ongc", "bhel"]),
]

def categorise(results):
    cats = {name: [] for name, _ in CATEGORY_KEYS}
    cats["📌 Other Government Openings"] = []
    for r in results:
        t = (r["title"] + " " + r["content"] + " " + r["url"]).lower()
        matched = False
        for name, keys in CATEGORY_KEYS:
            if any(k in t for k in keys):
                cats[name].append(r)
                matched = True
                break
        if not matched:
            cats["📌 Other Government Openings"].append(r)
    return {k: v for k, v in cats.items() if v}

def get_insight(sv_key, cat_name, jobs):
    if not sv_key:
        return None
    lines = "\n".join(
        f"- {j['title']}: {j['content'][:100]}"
        for j in jobs
    )
    prompt = (
        f"Category: {cat_name}\n"
        f"Jobs:\n{lines}\n\n"
        f"Write 2 sentences summarising current opportunities "
        f"in this category. Be specific and factual only."
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
            return clean(c.strip()) if c else None
        return None
    except:
        return None

def format_date(pub):
    if not pub:
        return None
    try:
        d = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        return d.strftime("%d %b %Y")
    except:
        return str(pub)[:10]


# ── UI ─────────────────────────────────────────────────────────────
st.title("📡 GovIT Radar")
st.caption(
    f"Latest government IT & civil services openings — Bihar & India"
    f" · {now_ist().strftime('%d %b %Y')}"
)
st.divider()

if st.button("🔍 Fetch Latest Openings", type="primary"):

    if not get_key("TAVILY_API_KEY"):
        st.error("TAVILY_API_KEY missing from secrets.toml")
        st.stop()

    sv_key = get_key("SARVAM_API_KEY")

    with st.spinner("Fetching latest notifications…"):
        raw = fetch_raw()

    if not raw:
        st.warning("No results. Check Tavily key.")
        st.stop()

    categorised = categorise(raw)
    total = sum(len(v) for v in categorised.values())
    st.success(f"✅ {total} openings found across {len(categorised)} categories")
    st.divider()

    for cat_label, jobs in categorised.items():
        with st.expander(f"{cat_label}  ({len(jobs)} openings)", expanded=False):

            # AI insight — 1 Sarvam call per category
            if sv_key:
                with st.spinner("Getting AI insight…"):
                    insight = get_insight(sv_key, cat_label, jobs)
                if insight:
                    st.info(f"✦ {insight}")

            st.divider()

            # Job cards — pure Streamlit, zero HTML
            for j in jobs:
                st.markdown(f"**{j['title']}**")

                if j["content"]:
                    st.caption(j["content"])

                cols = st.columns([2, 3])
                with cols[0]:
                    d = format_date(j["date"])
                    if d:
                        st.caption(f"📅 {d}")
                with cols[1]:
                    if j["url"]:
                        st.markdown(f"[View / Apply ↗]({j['url']})")

                st.divider()

    st.caption(
        f"Updated: {now_ist().strftime('%d %b %Y, %I:%M %p')} IST"
    )
