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
</style>
""", unsafe_allow_html=True)


def get_key(k):
    try:
        return st.secrets[k]
    except:
        return ""


def get_queries():
    yr    = now_ist().year
    month = now_ist().strftime("%B")
    return [
        f"BPSC combined competitive examination notification {month} {yr}",
        f"BPSC 72nd 73rd CCE prelims mains date apply {yr}",
        f"Bihar Public Service Commission new vacancy {yr}",
        f"BSEDC BELTRON Bihar IT recruitment {month} {yr}",
        f"Bihar e-governance IT officer vacancy {yr}",
        f"NIC National Informatics Centre scientist engineer recruitment {month} {yr}",
        f"NIC IT officer vacancy notification apply online {yr}",
        f"MeitY Digital India Corporation recruitment {month} {yr}",
        f"C-DAC STPI IT jobs vacancy notification {yr}",
        f"UPSC lateral entry joint secretary IT technology {yr}",
        f"SSC CGL technical scientific IT officer {month} {yr}",
        f"BEL BSNL DRDO ISRO IT engineer recruitment {month} {yr}",
        f"PSU technology officer vacancy notification {yr}",
    ]


def fetch_raw():
    client      = TavilyClient(api_key=get_key("TAVILY_API_KEY"))
    seen, found = set(), []

    for q in get_queries():
        try:
            res = client.search(
                query=q,
                search_depth="advanced",
                max_results=4,
                days=60,
                include_domains=[
                    "upsc.gov.in", "ssc.nic.in", "nic.in",
                    "meity.gov.in", "bpsc.bih.nic.in",
                    "sarkariresult.com", "sarkariexam.com",
                    "employment.gov.in", "ncs.gov.in",
                    "thehindu.com", "timesofindia.com",
                    "ndtv.com", "livemint.com",
                    "jagran.com", "digitalindia.gov.in", "cdac.in"
                ]
            )
            for r in res.get("results", []):
                url = r.get("url", "")
                if url and url not in seen:
                    seen.add(url)
                    found.append({
                        "title":     r.get("title", ""),
                        "url":       url,
                        "content":   r.get("content", "")[:400],
                        "published": r.get("published_date", "unknown"),
                    })
        except:
            continue

    return found


def call_sarvam(sarvam_key, messages, max_tokens=1200):
    """
    Single Sarvam-105b call with full error handling.
    Returns (text, error_message).
    text is None if call failed.
    """
    try:
        resp = requests.post(
            SARVAM_URL,
            headers={
                "api-subscription-key": sarvam_key,
                "Content-Type": "application/json"
            },
            json={
                "model":       SARVAM_MODEL,
                "messages":    messages,
                "max_tokens":  max_tokens,
                "temperature": 0.1
            },
            timeout=45
        )

        # Log full response for debugging
        raw_json = {}
        try:
            raw_json = resp.json()
        except Exception:
            return None, f"Could not parse Sarvam response. HTTP {resp.status_code}. Body: {resp.text[:300]}"

        if resp.status_code != 200:
            return None, (
                f"Sarvam returned HTTP {resp.status_code}.\n"
                f"Response: {str(raw_json)[:400]}"
            )

        # Safe extraction — check every level
        choices = raw_json.get("choices")
        if not choices or not isinstance(choices, list) or len(choices) == 0:
            return None, f"Sarvam response had no choices.\nFull response: {str(raw_json)[:400]}"

        message = choices[0].get("message")
        if not message:
            return None, f"Sarvam choices[0] had no message.\nFull response: {str(raw_json)[:400]}"

        content = message.get("content")
        if content is None:
            return None, (
                f"Sarvam message content was None.\n"
                f"Finish reason: {choices[0].get('finish_reason')}\n"
                f"Full response: {str(raw_json)[:400]}"
            )

        return content.strip(), None

    except requests.exceptions.Timeout:
        return None, "Request timed out after 45 seconds. Try again."
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


def refine(raw, today_str):
    text = "\n".join(
        f"Title: {r['title']}\n"
        f"Published: {r['published']}\n"
        f"URL: {r['url']}\n"
        f"Info: {r['content']}\n---"
        for r in raw
    )

    # Split into two calls if raw text is very long
    # to avoid token overflow causing empty content
    max_chars = 6000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n[...truncated for length]"

    prompt = f"""Today's date: {today_str}

Raw search data about Indian government job openings (Bihar + national IT/civil services):

{text}

Filter and present ONLY currently active openings.

DISCARD if any of these are true:
- Application deadline already passed before {today_str}
- Published more than 2 months before {today_str}
- Is a result, news article, or opinion — not an active opening
- No specific post name or organization
- Duplicate of another entry

FOR EACH VALID OPENING write:
• [Post Name] — [Organization]
  [Role description + key qualification, one line]
  [Last date if mentioned, else: Check official site]
  Apply: [URL]

Group under these headings only if valid entries exist:
Bihar & State Level
Central Government IT
Civil Services & UPSC
Public Sector Units

Skip any group with no valid openings.
No commentary, no tips, no strategy — just the openings."""

    messages = [
        {
            "role": "system",
            "content": (
                f"Today is {today_str}. "
                "You filter Indian government job data and show only currently active openings. "
                "Expired or irrelevant items are silently discarded. "
                "Never invent details not present in the data."
            )
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    return call_sarvam(get_key("SARVAM_API_KEY"), messages, max_tokens=1200)


# ── UI ─────────────────────────────────────────────────────────────
st.markdown("## 📡 GovIT Radar")
st.markdown(
    "Active government IT & civil services openings — Bihar & India &nbsp;·&nbsp; "
    f"*{now_ist().strftime('%d %b %Y')}*"
)
st.markdown("")

if st.button("🔍 Fetch Active Openings", type="primary"):

    tv_key = get_key("TAVILY_API_KEY")
    sv_key = get_key("SARVAM_API_KEY")

    if not tv_key:
        st.error("TAVILY_API_KEY missing from secrets.toml")
        st.stop()

    if not sv_key:
        st.error("SARVAM_API_KEY missing from secrets.toml")
        st.stop()

    with st.spinner("Scanning recent notifications…"):
        raw = fetch_raw()

    if not raw:
        st.warning("No results returned from search. Check your Tavily key or try again.")
        st.stop()

    st.caption(f"Fetched {len(raw)} raw items — filtering now…")

    today_str = now_ist().strftime("%d %B %Y")

    with st.spinner("Filtering and refining with AI…"):
        output, error = refine(raw, today_str)

    if error:
        # Show full debug info so we can diagnose
        st.error("AI filtering failed. See details below.")
        st.markdown(
            f'<div class="debug-box">DEBUG INFO:\n{error}</div>',
            unsafe_allow_html=True
        )
    elif not output:
        st.warning("AI returned an empty response. Try again.")
    else:
        st.markdown(
            f'<div class="result-block">{output}</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div class="ts">'
            f'Fetched: {now_ist().strftime("%d %b %Y, %I:%M %p")} IST &nbsp;·&nbsp;'
            f' Active openings only — last 60 days'
            f'</div>',
            unsafe_allow_html=True
        )
