from __future__ import annotations

import html
import os
import re
from io import BytesIO

import streamlit as st
from dotenv import load_dotenv
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

load_dotenv()

STAGES = [
    ("research", "Web research"),
    ("scraping", "Source extraction"),
    ("writer", "Report writing"),
    ("critic", "Quality review"),
]


def _render_progress(states, placeholder):
    cards = []
    for key, title in STAGES:
        state, detail = states.get(key, ("pending", "Waiting"))
        icon = {
            "complete": "✓",
            "running": "◌",
            "error": "!",
            "pending": "·",
        }[state]
        cards.append(
            "<div class='step step-{state}'>"
            "<div class='step-icon'>{icon}</div>"
            "<div><div class='step-title'>{title}</div>"
            "<div class='step-detail'>{detail}</div></div></div>".format(
                state=state,
                icon=icon,
                title=html.escape(title),
                detail=html.escape(detail),
            )
        )
    placeholder.markdown(
        "<div class='progress-list'>{}</div>".format("".join(cards)),
        unsafe_allow_html=True,
    )


def _markdown_paragraphs(text, styles):
    elements = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            elements.append(Spacer(1, 5))
            continue
        if stripped.startswith("#"):
            heading_level = len(stripped) - len(stripped.lstrip("#"))
            heading = stripped.lstrip("#").strip()
            style = styles["Heading1"] if heading_level <= 2 else styles["Heading2"]
            elements.append(Paragraph(html.escape(heading), style))
            continue
        if stripped.startswith(("- ", "* ")):
            content = "– " + stripped[2:]
        else:
            content = stripped
        content = html.escape(content)
        content = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", content)
        content = re.sub(r"\*(.+?)\*", r"<i>\1</i>", content)
        elements.append(Paragraph(content, styles["BodyText"]))
        elements.append(Spacer(1, 4))
    return elements


def build_report_pdf(result):
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title=f"Research report - {result['research_question']}",
    )
    styles = getSampleStyleSheet()
    styles["Title"].alignment = TA_CENTER
    styles["Title"].textColor = colors.HexColor("#172554")
    styles["BodyText"].leading = 15
    styles["BodyText"].wordWrap = "CJK"
    story = [
        Paragraph("Research Report", styles["Title"]),
        Spacer(1, 8),
        Paragraph(html.escape(result["research_question"]), styles["Heading2"]),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1")),
        Spacer(1, 12),
    ]
    story.extend(_markdown_paragraphs(result["report"], styles))
    story.extend([
        Spacer(1, 12),
        Paragraph("Sources", styles["Heading1"]),
    ])
    if result["sources"]:
        for index, source in enumerate(result["sources"], start=1):
            title = html.escape(source["title"])
            url = html.escape(source["url"], quote=True)
            story.append(Paragraph(
                f'{index}. {title}<br/><link href="{url}" color="#2563eb">'
                f'{html.escape(source["url"])}</link>',
                styles["BodyText"],
            ))
            story.append(Spacer(1, 6))
    else:
        story.append(Paragraph("No source URLs were collected.", styles["BodyText"]))

    if result.get("review"):
        story.extend([
            Spacer(1, 12),
            Paragraph("Critic Review", styles["Heading1"]),
        ])
        story.extend(_markdown_paragraphs(result["review"], styles))

    document.build(story)
    return buffer.getvalue()


st.set_page_config(
    page_title="Research Studio",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { --bg:#080d19; --panel:#111a2b; --line:#25334b; --muted:#9aabc4; --text:#edf3ff; --blue:#78a9ff; }
    .stApp { background: radial-gradient(ellipse at 65% -10%, #1b3157 0, #080d19 46%); color:var(--text); font-family:Inter,ui-sans-serif,system-ui,sans-serif; }
    h1,h2,h3 { font-family:Inter,ui-sans-serif,system-ui,sans-serif !important; letter-spacing:-.035em; }
    [data-testid="stSidebar"] { background:#0a1120; border-right:1px solid #1b2940; }
    [data-testid="stSidebar"] * { color:#e9f0ff; }
    .hero-kicker { color:#91b9ff; text-transform:uppercase; letter-spacing:.17em; font-size:.75rem; font-weight:700; margin-bottom:.55rem; }
    .hero-title { font:800 clamp(2.5rem,5vw,4.3rem)/1.02 Inter,ui-sans-serif,system-ui,sans-serif; letter-spacing:-.07em; max-width:780px; }
    .hero-copy { color:#9aabc4; font-size:1.08rem; max-width:680px; line-height:1.7; margin-top:1rem; }
    .panel { background:linear-gradient(145deg,rgba(20,31,51,.96),rgba(13,21,36,.96)); border:1px solid #263650; border-radius:18px; padding:22px 24px; margin:14px 0; }
    .step { display:flex; gap:13px; align-items:flex-start; padding:13px 12px; border-bottom:1px solid #22314a; }
    .step:last-child { border-bottom:0; }
    .step-icon { display:grid; place-items:center; min-width:27px; height:27px; border-radius:50%; font-weight:800; }
    .step-pending .step-icon { color:#8090aa; background:#1b2639; }
    .step-running .step-icon { color:#07111f; background:#8ab4ff; box-shadow:0 0 20px #6797ff66; }
    .step-complete .step-icon { color:#b6f5d1; background:#123d35; }
    .step-error .step-icon { color:#ffd0c7; background:#49221f; }
    .step-title { color:#eff4ff; font-weight:700; }
    .step-detail { color:#95a5be; font-size:.88rem; line-height:1.5; margin-top:3px; overflow-wrap:anywhere; }
    .source-card { border:1px solid #263650; background:#111a2b; border-radius:13px; padding:15px 17px; margin:9px 0; }
    .source-card a { color:#9ac0ff; text-decoration:none; overflow-wrap:anywhere; }
    div.stButton > button, div[data-testid="stDownloadButton"] button { border-radius:10px; min-height:2.7rem; font-weight:700; }
    div[data-testid="stTextArea"] textarea { background:#0d1627; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## ✦ Research Studio")
    st.caption("Gemini · Tavily · source-backed reports")
    st.divider()
    with st.form("research_form"):
        question = st.text_area(
            "What should the agents research?",
            placeholder="e.g. How are cities reducing urban heat?",
            height=145,
        )
        source_text = st.text_area(
            "Add source URLs (optional)",
            placeholder="https://example.com/article\nOne URL per line",
            height=100,
            help="These URLs will be included alongside web-search sources.",
        )
        submitted = st.form_submit_button(
            "Start research  →",
            type="primary",
            use_container_width=True,
        )
    st.caption("Your API keys stay in your local environment / .env file.")

st.markdown("<div class='hero-kicker'>Multi-agent research</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-title'>From a question to a sourced report.</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='hero-copy'>A coordinated research team searches the web, "
    "reads source pages, writes a report, and reviews its evidence — with "
    "each agent’s progress visible as it works.</div>",
    unsafe_allow_html=True,
)

if submitted:
    st.session_state.pop("research_result", None)
    if not question.strip():
        st.error("Enter a research question to get started.")
    else:
        missing = []
        if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
            missing.append("GOOGLE_API_KEY or GEMINI_API_KEY")
        if not os.getenv("TAVILY_API_KEY"):
            missing.append("TAVILY_API_KEY")
        if missing:
            st.error("Missing required environment variable(s): " + ", ".join(missing))
        else:
            status_panel = st.container()
            with status_panel:
                st.markdown("### Agent activity")
                progress_placeholder = st.empty()
                progress_states = {
                    key: ("pending", "Waiting for previous agents")
                    for key, _ in STAGES
                }
                _render_progress(progress_states, progress_placeholder)

            def update_progress(stage, state, detail):
                progress_states[stage] = (state, detail)
                _render_progress(progress_states, progress_placeholder)

            user_sources = [
                line.strip()
                for line in source_text.splitlines()
                if line.strip()
            ]
            try:
                from main import run_research

                with st.spinner("Agents are working on your research…"):
                    result = run_research(
                        question,
                        extra_source_urls=user_sources,
                        on_progress=update_progress,
                    )
                st.session_state["research_result"] = result
                st.success("Research report is ready.")
            except Exception as error:
                st.error(f"Research could not be completed: {error}")

result = st.session_state.get("research_result")
if result:
    st.divider()
    top_left, top_right = st.columns([3, 1])
    with top_left:
        st.markdown("## Your report")
        st.caption(result["research_question"])
    with top_right:
        pdf_bytes = build_report_pdf(result)
        st.download_button(
            "↓  Download report PDF",
            data=pdf_bytes,
            file_name="research_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    report_tab, sources_tab, review_tab = st.tabs(
        ["Report", f"Sources · {len(result['sources'])}", "Critic review"]
    )
    with report_tab:
        st.markdown(result["report"])
    with sources_tab:
        if result["sources"]:
            for index, source in enumerate(result["sources"], start=1):
                st.markdown(
                    f"<div class='source-card'><strong>{index}. "
                    f"{html.escape(source['title'])}</strong><br>"
                    f"<a href='{html.escape(source['url'], quote=True)}' "
                    f"target='_blank'>{html.escape(source['url'])}</a></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("No source URLs were returned for this research run.")
    with review_tab:
        st.markdown(result["review"])
elif not submitted:
    st.markdown(
        "<div class='panel'><strong>How it works</strong><br><br>"
        "01 &nbsp; Research agent searches for evidence<br>"
        "02 &nbsp; Source agent reads relevant pages<br>"
        "03 &nbsp; Writer agent assembles the report<br>"
        "04 &nbsp; Critic agent checks quality and gaps</div>",
        unsafe_allow_html=True,
    )
