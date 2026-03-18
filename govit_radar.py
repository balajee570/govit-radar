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
        margin-bottom: 4px;
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
    }
    .job-date {
        color: #dc2626;
        font-weight: 500;
    }
    .job-date.safe {
        color: #16a34a;
        font-weight: 500;
    }
    .job-link a {
        color: #1a6ef5;
        text-decoration: none;
        font-weight: 500;
    }
    .job-link a:hover {
        text-decoration: underline;
    }
    .no-results {
        color: #94a3b8;
        font-size: 13px;
        padding: 10px 0;
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
    .stButton > button:hover {
        background-color: #1558d0 !important;
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
    except Exception as e:
        return []


def deduplicate(raw):
    """Remove duplicate URLs and very similar titles."""
    seen_urls   = set()
    seen_titles = set()
    unique      = []

    for r in raw:
        url   = r.get("url", "")
        title = r.get("title", "").lower().strip()

        # Normalise title to catch near-duplicates
        title_key = re.sub(r'\s+', ' ', title)[:60]

        if url in seen_urls:
            continue
        if title_key in seen_titles:
            continue

        seen_urls.add(url)
        seen_titles.add(title_key)
        unique.append(r)

    return unique


def call_sarvam(messages, max_tokens=2000):
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
                "max_tokens":  max_tokens,
                "temperature": 0.1
            },
            timeout=55
        )

        try:
            raw_json = resp.json()
        except Exception:
            return None, f"Could not parse response. HTTP {resp.status_code}."

        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}: {str(raw_json)[:300]}"

        choices = raw_json.get("choices")
        if not choices or len(choices) == 0:
            return None, f"No choices: {str(raw_json)[:300]}"

        message = choices[0].get("message")
        if not message:
            return None, f"No message: {str(raw_json)[:300]}"

        content = message.get("content")
        if content is None:
            return None, (
                f"Content None. "
                f"Finish reason: {choices[0].get('finish_reason')}. "
                f"Response: {str(raw_json)[:300]}"
            )

        return content.strip(), None

    except requests.exceptions.Timeout:
        return None, "Timed out. Try again."
    except Exception as e:
        return None, f"Error: {str(e)}"


def refine(raw, today):
    today_fmt = today.strftime("%d %B %Y")
    today_iso = today.strftime("%Y-%m-%d")

    text = "\n".join(
        f"TITLE: {r.get('title', '')}\n"
        f"PUBLISHED: {r.get('published_date', '')}\n"
        f"URL: {r.get('url', '')}\n"
        f"DETAILS: {r.get('content', '')[:280]}\n---"
        for r in raw
    )

    if len(text) > 6000:
        text = text[:6000]

    system = f"""You are a government job data extractor.
Today is {today_fmt} ({today_iso}).

Rules:
1. Any opening with last date before {today_fmt} is EXPIRED — exclude it completely
2. Only include real active job notifications — not news, not results
3. Output must be valid JSON only — no extra text before or after
4. Never invent data not present in the input"""

    prompt = f"""Today is {today_fmt}.

Input data:
{text}

Extract all currently active job openings (deadline not yet passed as of {today_fmt}).

Return a JSON object in this exact structure:
{{
  "bihar_state": [
    {{
      "title": "post name",
      "org": "organization name",
      "role": "what the role is and key qualification",
      "last_date": "DD Month YYYY or unknown",
      "url": "application link"
    }}
  ],
  "central_it": [ same structure ],
  "civil_services": [ same structure ],
  "public_sector": [ same structure ]
}}

Category guide:
- bihar_state: BPSC, Bihar government posts, BSEDC, BELTRON, Bihar IT
- central_it: NIC, MeitY, C-DAC, Digital India, STPI
- civil_services: UPSC civil services, UPSC lateral entry, engineering services
- public_sector: DRDO, ISRO, BEL, BSNL, HAL, ONGC, BHEL, SSC technical posts

If a category has no valid entries, return empty array for it.
If last date is unknown from the data, set it to "unknown".
Return ONLY the JSON object. No text before or after."""

    return call_sarvam(
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt}
        ],
        max_tokens=2000
    )


def parse_json(text):
    """Safely extract JSON from Sarvam response."""
    if not text:
        return None

    # Strip any accidental markdown fences
    text = re.sub(r"```json|```", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object within the text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
    return None


def render_jobs(jobs, today):
    """Render a list of job dicts as HTML cards."""
    if not jobs:
        st.markdown(
            '<div class="no-results">No active openings found in this category.</div>',
            unsafe_allow_html=True
        )
        return

    today_dt = today.date()

    for j in jobs:
        title     = j.get("title", "")
        org       = j.get("org", "")
        role      = j.get("role", "")
        last_date = j.get("last_date", "unknown")
        url       = j.get("url", "")

        # Determine date styling
        date_class = "job-date safe"
        date_label = last_date

        if last_date and last_date.lower() not in ("unknown", "check official site", ""):
            try:
                # Try parsing the date
                for fmt in ("%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y"):
                    try:
                        parsed = datetime.strptime(last_date, fmt).date()
                        if parsed < today_dt:
                            # Skip expired — shouldn't reach here but safety net
                            continue
                        date_label = parsed.strftime("%d %b %Y")
                        date_class = "job-date safe"
                        break
                    except:
                        continue
            except:
                pass
        else:
            date_label = "Check official site"
            date_class = "job-date"

        link_html = (
            f'<a href="{url}" target="_blank">Apply / View Details ↗</a>'
            if url else "Link not available"
        )

        st.markdown(f"""
        <div class="job-card">
            <div class="job-title">{title}</div>
            <div class="job-org">{org}</div>
            <div class="job-role">{role}</div>
            <div class="job-meta">
                <span class="{date_class}">📅 Last Date: {date_label}</span>
                <span class="job-link">{link_html}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ── UI ─────────────────────────────────────────────────────────────
st.markdown("## 📡 GovIT Radar")
st.markdown(
    f"Active government IT & civil services openings — Bihar & India "
    f"&nbsp;·&nbsp; *{now_ist().strftime('%d %b %Y')}*"
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
        st.warning("No results returned. Check your Tavily key or try again.")
        st.stop()

    # Deduplicate before sending to Sarvam
    raw = deduplicate(raw)
    st.caption(f"Found {len(raw)} unique items — filtering and categorising…")

    today = now_ist()

    with st.spinner("Analysing and categorising…"):
        output, error = refine(raw, today)

    if error:
        st.error("AI processing failed.")
        st.markdown(f'<div class="debug-box">{error}</div>', unsafe_allow_html=True)
        st.stop()

    data = parse_json(output)

    if not data:
        st.warning("Could not parse results. Raw output below:")
        st.markdown(f'<div class="debug-box">{output}</div>', unsafe_allow_html=True)
        st.stop()

    # Count total valid jobs
    total = sum(
        len(data.get(k, []))
        for k in ("bihar_state", "central_it", "civil_services", "public_sector")
    )

    if total == 0:
        st.info("No active openings found at this time. Try again tomorrow.")
        st.stop()

    st.markdown(
        f'<div class="summary-bar">✅ Found <strong>{total} active openings</strong> '
        f'across all categories — all deadlines are after {today.strftime("%d %b %Y")}</div>',
        unsafe_allow_html=True
    )

    # ── Bihar & State Level ──────────────────────────────────────
    st.markdown(
        '<div class="cat-heading">Bihar & State Level</div>',
        unsafe_allow_html=True
    )
    render_jobs(data.get("bihar_state", []), today)

    # ── Central Government IT ────────────────────────────────────
    st.markdown(
        '<div class="cat-heading">Central Government IT</div>',
        unsafe_allow_html=True
    )
    render_jobs(data.get("central_it", []), today)

    # ── Civil Services & UPSC ────────────────────────────────────
    st.markdown(
        '<div class="cat-heading">Civil Services & UPSC</div>',
        unsafe_allow_html=True
    )
    render_jobs(data.get("civil_services", []), today)

    # ── Public Sector ────────────────────────────────────────────
    st.markdown(
        '<div class="cat-heading">Public Sector</div>',
        unsafe_allow_html=True
    )
    render_jobs(data.get("public_sector", []), today)

    st.markdown(
        f'<div class="ts">'
        f'Updated: {today.strftime("%d %b %Y, %I:%M %p")} IST'
        f' &nbsp;·&nbsp; Expired openings removed'
        f'</div>',
        unsafe_allow_html=True
    )
