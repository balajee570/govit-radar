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

def format_date(pub):
    if not pub:
        return None
    try:
        d = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        return d.strftime("%d %b %Y")
    except:
        return str(pub)[:10]

def do_search(client, query, domains, n=15, days=60):
    try:
        res = client.search(
            query=query,
            search_depth="advanced",
            max_results=n,
            days=days,
            include_domains=domains
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
        st.error(f"Search error: {e}")
        return []


# ── Call 1 — BPSC + Civil Services + PSU ─────────────────────────
def fetch_civil(client, yr, month):
    return do_search(
        client,
        query=(
            f"BPSC Bihar civil services UPSC SSC DRDO ISRO BEL BSNL "
            f"PSU government recruitment vacancy {month} {yr}"
        ),
        domains=[
            "upsc.gov.in", "ssc.nic.in",
            "bpsc.bih.nic.in", "sarkariresult.com",
            "sarkariexam.com", "employment.gov.in",
            "freejobalert.com", "rojgarresult.com",
            "indgovtjobs.in", "thehindu.com",
            "timesofindia.com", "ndtv.com",
            "jagran.com", "drdo.gov.in", "isro.gov.in",
        ],
        n=15
    )


# ── Call 2 — Government IT jobs specifically ──────────────────────
def fetch_it(client, yr, month):
    return do_search(
        client,
        query=(
            f"government IT jobs {month} {yr} NIC MeitY C-DAC BSEDC "
            f"BELTRON software engineer IT officer developer recruitment "
            f"Bihar India apply online"
        ),
        domains=[
            "nic.in", "meity.gov.in",
            "digitalindia.gov.in", "cdac.in",
            "indgovtjobs.in", "sarkariresult.com",
            "sarkariexam.com", "freejobalert.com",
            "rojgarresult.com", "employment.gov.in",
            "bpsc.bih.nic.in", "timesofindia.com",
            "ndtv.com", "jagran.com",
        ],
        n=15
    )


# ── Categorise civil results ──────────────────────────────────────
CIVIL_CATS = [
    ("🏛️ BPSC & Bihar Civil Services",
     ["bpsc", "bihar public service", "bihar psc"]),
    ("📜 UPSC — Civil Services & Lateral Entry",
     ["upsc", "lateral entry", "ias ", "ips ", "civil services"]),
    ("📋 SSC — Technical & IT Posts",
     ["ssc ", "staff selection", "cgl", "chsl"]),
    ("🔬 Public Sector — DRDO / ISRO / PSU",
     ["drdo", "isro", "bel ", "bsnl", "hal ", "ongc", "bhel"]),
]

def categorise_civil(results):
    cats = {name: [] for name, _ in CIVIL_CATS}
    cats["📌 Other Government"] = []
    seen = set()
    for r in results:
        if r["url"] in seen:
            continue
        seen.add(r["url"])
        t = (r["title"] + " " + r["content"] + " " + r["url"]).lower()
        matched = False
        for name, keys in CIVIL_CATS:
            if any(k in t for k in keys):
                cats[name].append(r)
                matched = True
                break
        if not matched:
            cats["📌 Other Government"].append(r)
    return {k: v for k, v in cats.items() if v}


# ── Categorise IT results ─────────────────────────────────────────
IT_CATS = [
    ("💻 NIC — National Informatics Centre",
     ["nic ", "national informatics", "nic.in"]),
    ("🌐 MeitY / Digital India / C-DAC",
     ["meity", "digital india", "c-dac", "cdac", "stpi"]),
    ("🏢 Bihar IT — BSEDC / BELTRON",
     ["bsedc", "beltron", "bihar e-gov", "bihar electronics", "bihar it"]),
]

def categorise_it(results):
    cats = {name: [] for name, _ in IT_CATS}
    cats["🖥️ Other Government IT"] = []
    seen = set()
    for r in results:
        if r["url"] in seen:
            continue
        seen.add(r["url"])
        t = (r["title"] + " " + r["content"] + " " + r["url"]).lower()
        matched = False
        for name, keys in IT_CATS:
            if any(k in t for k in keys):
                cats[name].append(r)
                matched = True
                break
        if not matched:
            cats["🖥️ Other Government IT"].append(r)
    return {k: v for k, v in cats.items() if v}


# ── Sarvam — 1 call per category ─────────────────────────────────
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


# ── Render jobs — pure Streamlit ──────────────────────────────────
def render_section(label, categorised, sv_key):
    st.subheader(label)
    for cat_label, jobs in categorised.items():
        with st.expander(
            f"{cat_label}  —  {len(jobs)} openings",
            expanded=True       # all open by default
        ):
            if sv_key:
                with st.spinner("AI insight…"):
                    insight = get_insight(sv_key, cat_label, jobs)
                if insight:
                    st.info(f"✦ {insight}")

            st.divider()

            for j in jobs:
                st.markdown(f"**{j['title']}**")
                if j["content"]:
                    st.caption(j["content"])
                c1, c2 = st.columns([2, 3])
                with c1:
                    d = format_date(j["date"])
                    if d:
                        st.caption(f"📅 {d}")
                with c2:
                    if j["url"]:
                        st.markdown(f"[View / Apply ↗]({j['url']})")
                st.divider()


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
    client = TavilyClient(api_key=get_key("TAVILY_API_KEY"))
    yr     = now_ist().year
    month  = now_ist().strftime("%B")

    # ── 2 Tavily calls ────────────────────────────────────────────
    with st.spinner("Fetching civil services & PSU openings…"):
        civil_raw = fetch_civil(client, yr, month)

    with st.spinner("Fetching government IT openings…"):
        it_raw = fetch_it(client, yr, month)

    if not civil_raw and not it_raw:
        st.warning("No results. Check Tavily key.")
        st.stop()

    civil_cats = categorise_civil(civil_raw)
    it_cats    = categorise_it(it_raw)

    civil_total = sum(len(v) for v in civil_cats.values())
    it_total    = sum(len(v) for v in it_cats.values())

    st.success(
        f"✅ {civil_total + it_total} openings — "
        f"{it_total} IT · {civil_total} Civil/PSU"
    )
    st.divider()

    # ── Section 1 — IT jobs (primary) ────────────────────────────
    if it_cats:
        render_section("💻 Government IT Opportunities", it_cats, sv_key)
        st.divider()

    # ── Section 2 — Civil services + PSU ─────────────────────────
    if civil_cats:
        render_section("🏛️ Civil Services & Public Sector", civil_cats, sv_key)

    st.caption(
        f"Updated: {now_ist().strftime('%d %b %Y, %I:%M %p')} IST"
        f" · 2 searches · AI insights by Sarvam-105b"
    )
