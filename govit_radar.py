import streamlit as st
import requests
import json
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
    .cat-heading {
        font-size: 13px;
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
        font-size: 15px;
        font-weight: 600;
        color: #1a2a3a;
        margin-bottom: 3px;
    }
    .job-org {
        font-size: 12px;
        color: #64748b;
        margin-bottom: 6px;
    }
    .job-role {
        font-size: 13px;
        color: #334155;
        margin-bottom: 8px;
        line-height: 1.5;
    }
    .job-meta {
        display: flex;
        gap: 16px;
        font-size: 12px;
        flex-wrap: wrap;
        align-items: center;
    }
    .job-date { color: #dc2626; font-weight: 500; }
    .job-date-ok { color: #16a34a; font-weight: 500; }
    .job-link a {
        color: #1a6ef5;
        text-decoration: none;
        font-weight: 500;
    }
    .no-results {
        color: #94a3b8;
        font-size: 13px;
        padding: 8px 0;
        font-style: italic;
    }
    .summary-bar {
        background: #f0f7ff;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 10px 16px;
        font-size: 13px;
        color: #1e40af;
        margin-bottom: 8px;
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
        f"BPSC Bihar NIC MeitY UPSC SSC DRDO ISRO BEL BSNL C-DAC "
        f"government IT civil services recruitment vacancy notification "
        f"{month} {yr} apply online"
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
                "employment.gov.in", "ncs.gov.in",
                "thehindu.com", "timesofindia.com",
                "ndtv.com", "livemint.com", "jagran.com",
                "digitalindia.gov.in", "cdac.in",
                "drdo.gov.in", "isro.gov.in",
                "freejobalert.com", "rojgarresult.com",
                "indgovtjobs.in"
            ]
        )
        return res.get("results", [])
    except:
        return []


def deduplicate(raw):
    seen_urls, seen_titles, unique = set(), set(), []
    for r in raw:
        url       = r.get("url", "")
        title_key = re.sub(r'\s+', ' ', r.get("title", "").lower())[:60]
        if url in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(url)
        seen_titles.add(title_key)
        unique.append(r)
    return unique


def compress(raw):
    """
    Heavily compress raw data before sending to Sarvam.
    Reasoning model needs spare tokens for thinking.
    Keep only title, url, last_date hint from content.
    """
    items = []
    for r in raw:
        title   = r.get("title", "")[:80]
        url     = r.get("url", "")[:100]
        # Extract just first 150 chars of content — enough to find date + role
        content = r.get("content", "")[:150].replace("\n", " ")
        items.append(f"{title} | {content} | {url}")
    return "\n".join(items)


def call_sarvam(messages):
    try:
        resp = requests.post(
            SARVAM_URL,
            headers={
                "api-subscription-key": get_key("SARVAM_API_KEY"),
                "Content-Type": "application/json"
            },
            json={
                "model":       SARVAM_MODEL,
                "messages":    messages,
                "max_tokens":  4096,   # High — reasoning model needs headroom
                "temperature": 0.1
            },
            timeout=60
        )

        try:
            rj = resp.json()
        except:
            return None, f"Cannot parse response. HTTP {resp.status_code}."

        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}: {str(rj)[:300]}"

        choices = rj.get("choices")
        if not choices:
            return None, f"No choices: {str(rj)[:300]}"

        msg = choices[0].get("message", {})
        content = msg.get("content")

        if content is None:
            fr = choices[0].get("finish_reason", "unknown")
            # Try reasoning_content as fallback info
            rc = msg.get("reasoning_content", "")[:200]
            return None, (
                f"Content is None. finish_reason={fr}.\n"
                f"Reasoning preview: {rc}"
            )

        return content.strip(), None

    except requests.exceptions.Timeout:
        return None, "Timed out after 60s. Try again."
    except Exception as e:
        return None, f"Error: {str(e)}"


def refine(raw, today):
    today_fmt = today.strftime("%d %B %Y")
    today_iso = today.strftime("%Y-%m-%d")

    # Compress heavily — reasoning model needs token headroom
    compressed = compress(raw)

    # Hard limit on input
    if len(compressed) > 3500:
        compressed = compressed[:3500]

    system = (
        f"You extract Indian government job data. Today={today_fmt}. "
        f"Output valid JSON only. No text before or after JSON. "
        f"Exclude jobs with deadline before {today_fmt}."
    )

    prompt = f"""Today: {today_fmt} ({today_iso})

Data (format: title | details | url):
{compressed}

Return this JSON — nothing else:
{{
  "bihar_state": [
    {{"title":"","org":"","role":"","last_date":"","url":""}}
  ],
  "central_it": [
    {{"title":"","org":"","role":"","last_date":"","url":""}}
  ],
  "civil_services": [
    {{"title":"","org":"","role":"","last_date":"","url":""}}
  ],
  "public_sector": [
    {{"title":"","org":"","role":"","last_date":"","url":""}}
  ]
}}

Rules:
- bihar_state = BPSC, Bihar govt, BSEDC, BELTRON
- central_it = NIC, MeitY, C-DAC, Digital India
- civil_services = UPSC IAS/IPS, lateral entry
- public_sector = DRDO, ISRO, BEL, BSNL, SSC technical, HAL, ONGC
- last_date: use date from content if found, else "Check official site"
- Skip expired jobs (deadline before {today_fmt})
- Empty array if nothing valid for a category
- JSON only, no explanation"""

    return call_sarvam([
        {"role": "system", "content": system},
        {"role": "user",   "content": prompt}
    ])


def parse_json_safe(text):
    if not text:
        return None
    text = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(text)
    except:
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except:
                pass
    return None


def render_category(jobs, today):
    if not jobs:
        st.markdown(
            '<div class="no-results">No active openings in this category right now.</div>',
            unsafe_allow_html=True
        )
        return

    today_dt = today.date()

    for j in jobs:
        title     = j.get("title", "—")
        org       = j.get("org", "")
        role      = j.get("role", "")
        last_date = j.get("last_date", "Check official site") or "Check official site"
        url       = j.get("url", "")

        # Date colour
        date_class = "job-date"
        date_display = last_date

        if last_date not in ("Check official site", "", "unknown"):
            for fmt in ("%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y"):
                try:
                    parsed = datetime.strptime(last_date, fmt).date()
                    if parsed >= today_dt:
                        date_class   = "job-date-ok"
                        date_display = parsed.strftime("%d %b %Y")
                    break
                except:
                    continue

        link_html = (
            f'<a href="{url}" target="_blank">Apply / View ↗</a>'
            if url else "—"
        )

        st.markdown(f"""
        <div class="job-card">
            <div class="job-title">{title}</div>
            {"<div class='job-org'>" + org + "</div>" if org else ""}
            {"<div class='job-role'>" + role + "</div>" if role else ""}
            <div class="job-meta">
                <span class="{date_class}">📅 {date_display}</span>
                <span class="job-link">{link_html}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ── UI ─────────────────────────────────────────────────────────────
st.markdown("## 📡 GovIT Radar")
st.markdown(
    f"Active government IT & civil services openings — Bihar & India"
    f" &nbsp;·&nbsp; *{now_ist().strftime('%d %b %Y')}*"
)
st.markdown("")

if st.button("🔍 Fetch Active Openings", type="primary"):

    if not get_key("TAVILY_API_KEY"):
        st.error("TAVILY_API_KEY missing from secrets.toml")
        st.stop()
    if not get_key("SARVAM_API_KEY"):
        st.error("SARVAM_API_KEY missing from secrets.toml")
        st.stop()

    with st.spinner("Fetching latest notifications…"):
        raw = fetch_raw()

    if not raw:
        st.warning("No results from search. Check Tavily key or try again.")
        st.stop()

    raw   = deduplicate(raw)
    today = now_ist()

    st.caption(f"Processing {len(raw)} unique items…")

    with st.spinner("Categorising and filtering…"):
        output, error = refine(raw, today)

    if error:
        st.error("Processing failed — see details below.")
        st.markdown(
            f'<div class="debug-box">{error}</div>',
            unsafe_allow_html=True
        )
        st.stop()

    data = parse_json_safe(output)

    if not data:
        st.warning("Could not parse AI response.")
        st.markdown(
            f'<div class="debug-box">{output[:800] if output else "Empty response"}</div>',
            unsafe_allow_html=True
        )
        st.stop()

    total = sum(
        len(data.get(k, []))
        for k in ("bihar_state", "central_it", "civil_services", "public_sector")
    )

    if total == 0:
        st.info("No active openings found right now. Try again tomorrow.")
        st.stop()

    st.markdown(
        f'<div class="summary-bar">'
        f'✅ <strong>{total} active openings</strong> found — '
        f'deadlines verified after {today.strftime("%d %b %Y")}'
        f'</div>',
        unsafe_allow_html=True
    )

    CATEGORIES = [
        ("bihar_state",    "Bihar & State Level"),
        ("central_it",     "Central Government IT"),
        ("civil_services", "Civil Services & UPSC"),
        ("public_sector",  "Public Sector"),
    ]

    for key, label in CATEGORIES:
        st.markdown(
            f'<div class="cat-heading">{label}</div>',
            unsafe_allow_html=True
        )
        render_category(data.get(key, []), today)

    st.markdown(
        f'<div class="ts">'
        f'Updated: {today.strftime("%d %b %Y, %I:%M %p")} IST'
        f' &nbsp;·&nbsp; Expired openings excluded'
        f'</div>',
        unsafe_allow_html=True
    )
