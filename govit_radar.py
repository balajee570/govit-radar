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
        padding: 22px 28px;
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


def fetch_raw():
    """
    Single Tavily call — 1 credit per fetch.
    Broad query covering all categories discussed.
    """
    yr    = now_ist().year
    month = now_ist().strftime("%B")

    query = (
        f"BPSC Bihar NIC MeitY UPSC SSC DRDO ISRO BEL BSNL C-DAC "
        f"government IT civil services recruitment vacancy notification "
        f"{month} {yr} apply online"
    )

    client = TavilyClient(api_key=get_key("TAVILY_API_KEY"))

    try:
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


def call_sarvam(messages, max_tokens=1800):
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
            timeout=50
        )

        try:
            raw_json = resp.json()
        except Exception:
            return None, f"Could not parse response. HTTP {resp.status_code}."

        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}: {str(raw_json)[:300]}"

        choices = raw_json.get("choices")
        if not choices or len(choices) == 0:
            return None, f"No choices in response: {str(raw_json)[:300]}"

        message = choices[0].get("message")
        if not message:
            return None, f"No message in choices[0]: {str(raw_json)[:300]}"

        content = message.get("content")
        if content is None:
            return None, (
                f"Content is None. "
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
        f"DETAILS: {r.get('content', '')[:300]}\n---"
        for r in raw
    )

    if len(text) > 6000:
        text = text[:6000]

    system = f"""You are a government job intelligence assistant.
Today is {today_fmt} ({today_iso}).

STRICT RULES:
1. Discard any opening whose application deadline has passed before {today_fmt}
2. Discard anything published more than 60 days before {today_fmt}
3. Only include real active job openings — not results, news, or opinions
4. Never show template text, placeholders, or format examples in output
5. Never invent details not present in the data"""

    prompt = f"""Today is {today_fmt}.

Raw data:
{text}

Filter strictly. For each valid active opening write:

Name of post — Organization
Role and key qualification in one line
Last date: [date if known, else: Check official site]
Link: [URL]

Blank line between entries.

Group under these headings only if entries exist for them:
BIHAR & STATE LEVEL
CENTRAL GOVERNMENT IT
CIVIL SERVICES & UPSC
PUBLIC SECTOR

No other text. No commentary. No expired openings."""

    return call_sarvam(
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt}
        ],
        max_tokens=1800
    )


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
        st.warning("No results returned. Check Tavily key or try again.")
        st.stop()

    st.caption(f"Found {len(raw)} items — filtering active openings…")

    today = now_ist()

    with st.spinner("Filtering and refining…"):
        output, error = refine(raw, today)

    if error:
        st.error("AI filtering failed.")
        st.markdown(
            f'<div class="debug-box">{error}</div>',
            unsafe_allow_html=True
        )
    elif not output:
        st.warning("No active openings found. Try again tomorrow.")
    else:
        st.markdown(
            f'<div class="result-block">{output}</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div class="ts">'
            f'Updated: {today.strftime("%d %b %Y, %I:%M %p")} IST'
            f' &nbsp;·&nbsp; Active openings only'
            f'</div>',
            unsafe_allow_html=True
        )
