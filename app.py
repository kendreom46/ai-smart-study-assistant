"""
StudyMate AI - AI Smart Study Assistant
Second-Year B.Tech Class Project
Student: Kendre Om | College: Sreenidhi University | Section: B11

A functional, academic, and user-centric study assistant providing:
- AI Topic Explanations (Beginner, Intermediate, Advanced)
- Notes Summarizer & Exam Revision Points
- Interactive Practice Quiz Generator & Automated Grading
- Study Chat Assistant with PDF Grounding
- PDF Text Extraction & Safety Guardrails
- Local SQLite Study History & Persistence
"""

import json
import os
import streamlit as st
from dotenv import load_dotenv

# Load local environment configuration
load_dotenv()

from src.ai_service import AIService
from src.database import (
    clear_all_history,
    delete_history_entry,
    get_history,
    get_history_by_id,
    get_history_stats,
    init_db,
)
from src.pdf_service import extract_text_from_pdf, validate_pdf_size
from src.study_service import (
    format_quiz_markdown,
    grade_quiz,
    save_study_session,
    validate_input_length,
)

# ------------------------------------------------------------------------------
# Streamlit Page Setup
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="StudyMate AI | Smart Study Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize SQLite database
init_db()

# ------------------------------------------------------------------------------
# Academic Styling & Design System
# ------------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Global Academic Aesthetic */
    .stApp {
        background-color: #F8FAFC;
        color: #1E293B;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Academic Cards */
    .academic-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }

    /* Badges */
    .badge-primary {
        display: inline-block;
        background-color: #EFF6FF;
        color: #1D4ED8;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid #DBEAFE;
    }

    .badge-success {
        display: inline-block;
        background-color: #F0FDF4;
        color: #15803D;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid #DCFCE7;
    }

    .badge-neutral {
        display: inline-block;
        background-color: #F1F5F9;
        color: #475569;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
        border: 1px solid #E2E8F0;
    }

    /* Header styling */
    .project-header {
        border-bottom: 1px solid #E2E8F0;
        padding-bottom: 14px;
        margin-bottom: 22px;
    }

    .project-title {
        font-size: 1.75rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 4px;
    }

    .project-subtitle {
        font-size: 0.92rem;
        color: #64748B;
        line-height: 1.4;
    }

    /* Quiz Option Item */
    .quiz-question-box {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 18px;
        margin-bottom: 18px;
    }

    /* Metrics Bar */
    .stat-box {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px 18px;
        text-align: center;
    }
    .stat-number {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1D4ED8;
    }
    .stat-label {
        font-size: 0.8rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------------------
# Session State Initialization
# ------------------------------------------------------------------------------
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""
if "pdf_filename" not in st.session_state:
    st.session_state.pdf_filename = None
if "pdf_info" not in st.session_state:
    st.session_state.pdf_info = {}

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None
if "quiz_topic" not in st.session_state:
    st.session_state.quiz_topic = ""
if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}
if "quiz_graded" not in st.session_state:
    st.session_state.quiz_graded = None

if "api_key_override" not in st.session_state:
    st.session_state.api_key_override = ""

# ------------------------------------------------------------------------------
# AI Service Provider
# ------------------------------------------------------------------------------
def get_ai_service() -> AIService:
    """Return configured AI service instance."""
    api_key = st.session_state.api_key_override or os.getenv("GEMINI_API_KEY")
    # Streamlit secrets fallback if deployed
    if not api_key and hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    if hasattr(st, "secrets") and "GEMINI_MODEL" in st.secrets:
        model_name = st.secrets["GEMINI_MODEL"]

    return AIService(api_key=api_key, model_name=model_name)


ai_service = get_ai_service()

# ------------------------------------------------------------------------------
# Sidebar Navigation & Academic Credentials
# ------------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎓 **StudyMate AI**")
    st.caption("AI-Powered Academic Study Companion")

    # Navigation Menu
    nav_options = [
        "🏠 Dashboard",
        "💡 AI Topic Explainer",
        "📝 Notes Summarizer",
        "🎯 AI Quiz Generator",
        "💬 Study Chat Assistant",
        "📄 PDF Study Assistant",
        "📚 Study History",
    ]

    # Map current_page to index
    clean_current = st.session_state.current_page
    selected_index = 0
    for idx, opt in enumerate(nav_options):
        if clean_current in opt:
            selected_index = idx
            break

    nav_choice = st.radio(
        "Navigation",
        options=nav_options,
        index=selected_index,
        label_visibility="collapsed",
    )
    # Strip icon from chosen page name
    selected_page_name = nav_choice.split(" ", 1)[1]
    st.session_state.current_page = selected_page_name

    st.divider()

    # Active Document Indicator
    if st.session_state.pdf_filename:
        st.markdown(
            f"""
            <div style="background-color: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 6px; padding: 10px; font-size: 0.85rem;">
                <b style="color: #166534;">📄 Active PDF Loaded</b><br/>
                <span style="color: #374151;">{st.session_state.pdf_filename}</span><br/>
                <small style="color: #6B7280;">{st.session_state.pdf_info.get('total_pages', 0)} pages ({len(st.session_state.pdf_text):,} chars)</small>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Unload Document", use_container_width=True, key="unload_pdf_btn"):
            st.session_state.pdf_text = ""
            st.session_state.pdf_filename = None
            st.session_state.pdf_info = {}
            st.rerun()
    else:
        st.markdown(
            """
            <div style="background-color: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 6px; padding: 8px; font-size: 0.8rem; color: #64748B;">
                📄 No PDF active. Upload one under <b>PDF Study Assistant</b> to reference across tools.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    # Academic & Student Metadata
    with st.expander("👤 Project Information", expanded=False):
        st.markdown(
            """
            **Student:** Kendre Om  
            **College:** Sreenidhi University  
            **Section:** B11  
            **Course:** B.Tech Second Year  
            **Project:** AI Smart Study Assistant  
            **Model:** `{}`  
            """.format(ai_service.model)
        )

    # API Configuration Details
    with st.expander("⚙️ Gemini API Configuration", expanded=not ai_service.is_configured()):
        if ai_service.is_configured():
            st.success("✅ Gemini API Key Configured")
            st.caption(f"Using model: `{ai_service.model}`")
        else:
            st.warning("⚠️ API Key Missing")
            st.markdown(
                """
                1. Obtain a free key at [Google AI Studio](https://aistudio.google.com/).
                2. Set `GEMINI_API_KEY` in `.env`, or input below:
                """
            )

        api_input = st.text_input(
            "Session API Key",
            value=st.session_state.api_key_override,
            type="password",
            help="Overrides .env for this session only. Never saved to git.",
        )
        if api_input != st.session_state.api_key_override:
            st.session_state.api_key_override = api_input
            st.rerun()


# ------------------------------------------------------------------------------
# PAGE ROUTING
# ------------------------------------------------------------------------------
page = st.session_state.current_page


# ==============================================================================
# FEATURE A: DASHBOARD
# ==============================================================================
if page == "Dashboard":
    st.markdown(
        """
        <div class="project-header">
            <div class="project-title">Welcome to StudyMate AI</div>
            <div class="project-subtitle">
                An intelligent academic companion developed by <b>Kendre Om</b> (Sreenidhi University, Section B11).
                Master complex concepts, generate revision summaries, practice interactive quizzes, and explore study documents with genuine AI reasoning.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Status Notification if API key is unconfigured
    if not ai_service.is_configured():
        st.info(
            "💡 **Setup Reminder:** To unlock AI explanations, summaries, and quizzes, ensure you configure your "
            "Gemini API key in the `.env` file or in the sidebar **Gemini API Configuration** section."
        )

    # Quick Navigation Cards
    st.markdown("### 🛠️ Study Modules")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            <div class="academic-card">
                <span class="badge-primary">Concept Mastery</span>
                <h4 style="margin: 8px 0 4px 0; color: #0F172A;">💡 AI Topic Explainer</h4>
                <p style="color: #64748B; font-size: 0.9rem; margin-bottom: 12px;">
                    Demystify challenging academic topics tailored to your level (Beginner to Advanced) with clear real-world analogies and key takeaways.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Open Topic Explainer →", key="dash_btn_explainer", use_container_width=True):
            st.session_state.current_page = "AI Topic Explainer"
            st.rerun()

        st.markdown(
            """
            <div class="academic-card" style="margin-top: 14px;">
                <span class="badge-primary">Exam Preparation</span>
                <h4 style="margin: 8px 0 4px 0; color: #0F172A;">🎯 AI Quiz Generator</h4>
                <p style="color: #64748B; font-size: 0.9rem; margin-bottom: 12px;">
                    Generate structured multiple-choice questions with 4 options, automated grading, score calculation, and pedagogical rationales.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Generate Practice Quiz →", key="dash_btn_quiz", use_container_width=True):
            st.session_state.current_page = "AI Quiz Generator"
            st.rerun()

    with col2:
        st.markdown(
            """
            <div class="academic-card">
                <span class="badge-primary">Revision Aid</span>
                <h4 style="margin: 8px 0 4px 0; color: #0F172A;">📝 Notes Summarizer</h4>
                <p style="color: #64748B; font-size: 0.9rem; margin-bottom: 12px;">
                    Condense lecture notes into executive overviews, multi-section deep summaries, or high-yield bullet points for quick pre-exam review.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Open Notes Summarizer →", key="dash_btn_summarizer", use_container_width=True):
            st.session_state.current_page = "Notes Summarizer"
            st.rerun()

        st.markdown(
            """
            <div class="academic-card" style="margin-top: 14px;">
                <span class="badge-primary">Interactive & Multimodal</span>
                <h4 style="margin: 8px 0 4px 0; color: #0F172A;">💬 Chat & 📄 PDF Assistant</h4>
                <p style="color: #64748B; font-size: 0.9rem; margin-bottom: 12px;">
                    Upload course syllabus or lecture slides to ask grounded questions, inspect page text, and chat with your academic tutor.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        c_sub1, c_sub2 = st.columns(2)
        with c_sub1:
            if st.button("Study Chat →", key="dash_btn_chat", use_container_width=True):
                st.session_state.current_page = "Study Chat Assistant"
                st.rerun()
        with c_sub2:
            if st.button("Upload PDF →", key="dash_btn_pdf", use_container_width=True):
                st.session_state.current_page = "PDF Study Assistant"
                st.rerun()

    # Recent Study Activity (Real SQLite Queries)
    st.markdown("### 📊 Genuine Study Activity")
    stats = get_history_stats()
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.markdown(
            f"""<div class="stat-box"><div class="stat-number">{stats['total_sessions']}</div><div class="stat-label">Total Saved Sessions</div></div>""",
            unsafe_allow_html=True,
        )
    with m_col2:
        st.markdown(
            f"""<div class="stat-box"><div class="stat-number">{stats['type_counts'].get('topic_explainer', 0)}</div><div class="stat-label">Explanations</div></div>""",
            unsafe_allow_html=True,
        )
    with m_col3:
        st.markdown(
            f"""<div class="stat-box"><div class="stat-number">{stats['type_counts'].get('quiz', 0)}</div><div class="stat-label">Quizzes Completed</div></div>""",
            unsafe_allow_html=True,
        )
    with m_col4:
        st.markdown(
            f"""<div class="stat-box"><div class="stat-number">{stats['type_counts'].get('notes_summary', 0)}</div><div class="stat-label">Summaries</div></div>""",
            unsafe_allow_html=True,
        )

    st.markdown("#### 🕒 Recent Sessions")
    recent_records = get_history(limit=5)
    if not recent_records:
        st.markdown(
            """
            <div style="background-color: #FFFFFF; border: 1px dashed #CBD5E1; border-radius: 8px; padding: 30px; text-align: center; color: #64748B;">
                <p style="font-size: 1.1rem; font-weight: 500; margin-bottom: 6px;">No saved study sessions yet.</p>
                <p style="font-size: 0.85rem; margin-bottom: 0;">
                    Generate an explanation, summary, or quiz to start building your persistent revision library!
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        for item in recent_records:
            with st.container():
                st.markdown(
                    f"""
                    <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 12px 16px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span class="badge-neutral">{item['session_type'].replace('_', ' ').title()}</span>
                            <b style="color: #0F172A; margin-left: 8px;">{item['title']}</b>
                        </div>
                        <small style="color: #64748B;">{item['created_at']}</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# ==============================================================================
# FEATURE B: AI TOPIC EXPLAINER
# ==============================================================================
elif page == "AI Topic Explainer":
    st.markdown(
        """
        <div class="project-header">
            <div class="project-title">💡 AI Topic Explainer</div>
            <div class="project-subtitle">
                Generate pedagogical, multi-section explanations tailored to your academic comprehension level.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_in, col_opts = st.columns([3, 2])
    with col_in:
        topic_input = st.text_input(
            "Academic Topic or Concept",
            placeholder="e.g., Dijkstra's Algorithm, Amdahl's Law, TCP Handshake, Virtual Memory...",
        )
    with col_opts:
        sub_c1, sub_c2 = st.columns(2)
        with sub_c1:
            level_choice = st.selectbox(
                "Comprehension Level",
                options=["Beginner", "Intermediate", "Advanced"],
                index=1,
            )
        with sub_c2:
            length_choice = st.selectbox(
                "Detail & Length",
                options=["Detailed", "Concise"],
                index=0,
            )

    use_pdf_context = False
    context_text = ""
    if st.session_state.pdf_text:
        use_pdf_context = st.checkbox(
            f"Ground explanation in loaded PDF: '{st.session_state.pdf_filename}'",
            value=True,
        )
        if use_pdf_context:
            context_text = st.session_state.pdf_text[:8000]

    with st.expander("Optional: Paste additional reference text"):
        manual_context = st.text_area("Reference context", height=100)
        if manual_context.strip():
            context_text += "\n" + manual_context.strip()

    btn_explain = st.button("Generate Explanation", type="primary", use_container_width=False)

    if btn_explain:
        valid, err_msg = validate_input_length(topic_input, min_length=2, field_name="Topic")
        if not valid:
            st.error(f"❌ {err_msg}")
        elif not ai_service.is_configured():
            st.error("❌ Gemini API Key is missing. Please set GEMINI_API_KEY in .env or via the sidebar.")
        else:
            with st.spinner(f"StudyMate AI is analyzing '{topic_input}'..."):
                try:
                    explanation_result = ai_service.explain_topic(
                        topic=topic_input,
                        level=level_choice.lower(),
                        length=length_choice.lower(),
                        context=context_text,
                    )
                    st.session_state["last_explanation"] = explanation_result
                    st.session_state["last_explanation_topic"] = topic_input
                except Exception as e:
                    st.error(f"❌ {str(e)}")

    if "last_explanation" in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state["last_explanation"])

        st.markdown("---")
        act_c1, act_c2, _ = st.columns([1.5, 1.5, 3])
        with act_c1:
            if st.button("💾 Save to Study History", key="save_explainer_btn"):
                save_study_session(
                    session_type="topic_explainer",
                    title=f"Explanation: {st.session_state['last_explanation_topic']}",
                    content=st.session_state["last_explanation"],
                    input_excerpt=st.session_state["last_explanation_topic"],
                    metadata_dict={"level": level_choice, "length": length_choice},
                )
                st.success("✅ Saved to local study history!")
        with act_c2:
            st.download_button(
                "📥 Download Markdown",
                data=st.session_state["last_explanation"],
                file_name=f"{st.session_state['last_explanation_topic'].replace(' ', '_')}_explanation.md",
                mime="text/markdown",
            )


# ==============================================================================
# FEATURE C: NOTES SUMMARIZER
# ==============================================================================
elif page == "Notes Summarizer":
    st.markdown(
        """
        <div class="project-header">
            <div class="project-title">📝 Notes Summarizer</div>
            <div class="project-subtitle">
                Synthesize lecture transcripts, textbook chapters, or handwritten notes into high-yield summaries.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Pre-fill button from active PDF
    if st.session_state.pdf_text:
        if st.button(f"📥 Import text from active PDF ({st.session_state.pdf_filename})"):
            st.session_state["summarizer_input_text"] = st.session_state.pdf_text[:12000]
            st.rerun()

    input_text = st.text_area(
        "Paste Study Notes",
        value=st.session_state.get("summarizer_input_text", ""),
        height=220,
        placeholder="Paste your lecture notes, textbook passages, or technical summaries here...",
    )

    sum_col1, sum_col2 = st.columns([2, 1])
    with sum_col1:
        summary_format = st.selectbox(
            "Summary Format",
            options=[
                "Detailed Summary (Multi-section breakdown)",
                "Exam Revision Bullet Points (High-yield facts & terms)",
                "Short Summary (Executive overview)",
            ],
            index=0,
        )

    # Map format to internal key
    format_mapping = {
        "Short Summary (Executive overview)": "short",
        "Detailed Summary (Multi-section breakdown)": "detailed",
        "Exam Revision Bullet Points (High-yield facts & terms)": "exam_revision",
    }
    format_key = format_mapping[summary_format]

    btn_summarize = st.button("Summarize Notes", type="primary")

    if btn_summarize:
        valid, err_msg = validate_input_length(input_text, min_length=20, field_name="Notes")
        if not valid:
            st.error(f"❌ {err_msg}")
        elif not ai_service.is_configured():
            st.error("❌ Gemini API Key is missing. Please configure it in .env or the sidebar.")
        else:
            with st.spinner("Synthesizing notes with StudyMate AI..."):
                try:
                    summary_result = ai_service.summarize_notes(
                        notes=input_text,
                        summary_type=format_key,
                    )
                    st.session_state["last_summary"] = summary_result
                    st.session_state["last_summary_source"] = input_text[:200]
                except Exception as e:
                    st.error(f"❌ {str(e)}")

    if "last_summary" in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state["last_summary"])

        st.markdown("---")
        act_c1, act_c2, _ = st.columns([1.5, 1.5, 3])
        with act_c1:
            if st.button("💾 Save to Study History", key="save_summary_btn"):
                save_study_session(
                    session_type="notes_summary",
                    title="Summary: " + (input_text.splitlines()[0][:50] if input_text.splitlines() else "Study Notes"),
                    content=st.session_state["last_summary"],
                    input_excerpt=st.session_state.get("last_summary_source", ""),
                    metadata_dict={"format": format_key},
                )
                st.success("✅ Saved to study history!")
        with act_c2:
            st.download_button(
                "📥 Download Summary",
                data=st.session_state["last_summary"],
                file_name="study_notes_summary.md",
                mime="text/markdown",
            )


# ==============================================================================
# FEATURE D: AI QUIZ GENERATOR
# ==============================================================================
elif page == "AI Quiz Generator":
    st.markdown(
        """
        <div class="project-header">
            <div class="project-title">🎯 AI Quiz Generator</div>
            <div class="project-subtitle">
                Test your knowledge with authentic multiple-choice questions, instant scoring, and comprehensive explanations.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    q_col1, q_col2 = st.columns([3, 1])
    with q_col1:
        if st.session_state.pdf_text and st.button(f"📥 Fill with active PDF ({st.session_state.pdf_filename})"):
            st.session_state["quiz_source_text"] = st.session_state.pdf_text[:8000]
            st.rerun()

        quiz_source = st.text_area(
            "Topic or Study Material",
            value=st.session_state.get("quiz_source_text", ""),
            height=100,
            placeholder="e.g., Computer Networks Transport Layer, Normalization in DBMS, or paste notes...",
        )
    with q_col2:
        question_count = st.select_slider(
            "Number of Questions",
            options=[3, 5, 10, 15],
            value=5,
        )
        btn_generate_quiz = st.button("Generate Quiz", type="primary", use_container_width=True)

    if btn_generate_quiz:
        valid, err_msg = validate_input_length(quiz_source, min_length=3, field_name="Quiz Material")
        if not valid:
            st.error(f"❌ {err_msg}")
        elif not ai_service.is_configured():
            st.error("❌ Gemini API Key is missing. Please configure it in .env or the sidebar.")
        else:
            with st.spinner("Generating structured quiz questions via Gemini..."):
                try:
                    questions = ai_service.generate_quiz(
                        study_material=quiz_source,
                        num_questions=question_count,
                    )
                    st.session_state.quiz_data = questions
                    st.session_state.quiz_topic = quiz_source.splitlines()[0][:60]
                    st.session_state.quiz_answers = {}
                    st.session_state.quiz_graded = None
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ {str(e)}")

    # Render interactive quiz
    if st.session_state.quiz_data:
        st.markdown(f"### Practice Quiz: **{st.session_state.quiz_topic}**")
        st.caption(f"{len(st.session_state.quiz_data)} Questions Generated")

        # Answer Submission Form
        with st.form("quiz_form"):
            for q in st.session_state.quiz_data:
                q_id = str(q["id"])
                st.markdown(f"**Q{q_id}. {q['question']}**")

                opts = q["options"]
                opt_labels = [
                    f"A) {opts.get('A', '')}",
                    f"B) {opts.get('B', '')}",
                    f"C) {opts.get('C', '')}",
                    f"D) {opts.get('D', '')}",
                ]

                # Radio button selection
                chosen_opt_label = st.radio(
                    f"Select answer for Q{q_id}",
                    options=opt_labels,
                    index=None,
                    key=f"q_radio_{q_id}",
                    label_visibility="collapsed",
                )
                if chosen_opt_label:
                    # Extract letter from "A) Option"
                    st.session_state.quiz_answers[q_id] = chosen_opt_label[0]

                st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

            submit_quiz = st.form_submit_button("Submit Quiz for Grading", type="primary")

        if submit_quiz:
            graded = grade_quiz(st.session_state.quiz_data, st.session_state.quiz_answers)
            st.session_state.quiz_graded = graded

        # Display Grading Results
        if st.session_state.quiz_graded:
            results = st.session_state.quiz_graded
            score_pct = results["score_percentage"]
            score_color = "#15803D" if score_pct >= 70 else ("#B45309" if score_pct >= 40 else "#B91C1C")

            st.markdown(
                f"""
                <div style="background-color: #FFFFFF; border: 2px solid {score_color}; border-radius: 8px; padding: 18px; margin: 20px 0; text-align: center;">
                    <h3 style="margin: 0; color: {score_color};">Score: {results['correct_count']} / {results['total_questions']} ({score_pct}%)</h3>
                    <p style="color: #64748B; margin: 6px 0 0 0;">
                        {"🎉 Excellent work! Strong mastery of these concepts." if score_pct >= 70 else ("📖 Good effort. Review the explanations below to improve." if score_pct >= 40 else "💡 Study review recommended. Carefully read each question's explanation.")}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Detailed per-question review
            st.markdown("#### 🔍 Question-by-Question Review")
            for item in results["detailed_results"]:
                is_correct = item["is_correct"]
                border_col = "#22C55E" if is_correct else "#EF4444"
                bg_col = "#F0FDF4" if is_correct else "#FEF2F2"

                st.markdown(
                    f"""
                    <div style="background-color: {bg_col}; border-left: 4px solid {border_col}; border-radius: 4px; padding: 12px 16px; margin-bottom: 12px;">
                        <b>Q{item['id']}: {item['question']}</b><br/>
                        <span>{'✅ Correct' if is_correct else '❌ Incorrect'}</span> | 
                        <span><b>Your Answer:</b> {item['selected_option']}) {item['selected_text']}</span> | 
                        <span><b>Correct Answer:</b> {item['correct_option']}) {item['correct_text']}</span>
                        <div style="margin-top: 8px; font-size: 0.9rem; color: #374151;">
                            💡 <b>Explanation:</b> {item['explanation']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Actions: Save Quiz to SQLite
            act_col1, act_col2 = st.columns([2, 2])
            with act_col1:
                if st.button("💾 Save Quiz & Score to History", key="save_quiz_btn"):
                    md_report = format_quiz_markdown(st.session_state.quiz_topic, results)
                    save_study_session(
                        session_type="quiz",
                        title=f"Quiz: {st.session_state.quiz_topic} ({results['correct_count']}/{results['total_questions']})",
                        content=md_report,
                        input_excerpt=st.session_state.quiz_topic,
                        metadata_dict={"score": results["correct_count"], "total": results["total_questions"]},
                    )
                    st.success("✅ Quiz results saved to history!")
            with act_col2:
                if st.button("🔄 Clear & Generate New Quiz"):
                    st.session_state.quiz_data = None
                    st.session_state.quiz_answers = {}
                    st.session_state.quiz_graded = None
                    st.rerun()


# ==============================================================================
# FEATURE E: STUDY CHAT ASSISTANT
# ==============================================================================
elif page == "Study Chat Assistant":
    st.markdown(
        """
        <div class="project-header">
            <div class="project-title">💬 Study Chat Assistant</div>
            <div class="project-subtitle">
                Interactive dialogue with StudyMate AI. Ask conceptual questions, debug code, and analyze study materials.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Active PDF notification
    if st.session_state.pdf_filename:
        st.info(
            f"📄 **Grounded Mode:** The assistant has read `{st.session_state.pdf_filename}`. "
            "Questions will prioritize citations and facts from this document."
        )

    # Chat history controls
    col_c1, col_c2 = st.columns([6, 1])
    with col_c2:
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()

    # Render previous conversation turns
    for idx, msg in enumerate(st.session_state.chat_messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                if st.button("💾 Save to History", key=f"save_chat_{idx}", help="Save this explanation to SQLite"):
                    save_study_session(
                        session_type="chat",
                        title="Chat: " + (msg["content"].splitlines()[0][:50] if msg["content"].splitlines() else "Study Concept"),
                        content=msg["content"],
                        input_excerpt=st.session_state.chat_messages[idx - 1]["content"] if idx > 0 else "",
                    )
                    st.toast("Saved to study history!")

    # Chat input
    user_query = st.chat_input("Ask a question about your studies or the loaded document...")

    if user_query:
        if not ai_service.is_configured():
            st.error("❌ Gemini API Key is missing. Please configure it in .env or the sidebar.")
        else:
            # Display user turn
            st.session_state.chat_messages.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)

            # Generate assistant response
            with st.chat_message("assistant"):
                with st.spinner("StudyMate AI is thinking..."):
                    try:
                        ai_reply = ai_service.chat_response(
                            messages=st.session_state.chat_messages[:-1],
                            user_prompt=user_query,
                            pdf_context=st.session_state.pdf_text if st.session_state.pdf_text else "",
                        )
                        st.markdown(ai_reply)
                        st.session_state.chat_messages.append({"role": "assistant", "content": ai_reply})
                    except Exception as e:
                        st.error(f"❌ {str(e)}")


# ==============================================================================
# FEATURE F: PDF STUDY ASSISTANT
# ==============================================================================
elif page == "PDF Study Assistant":
    st.markdown(
        """
        <div class="project-header">
            <div class="project-title">📄 PDF Study Assistant</div>
            <div class="project-subtitle">
                Upload course syllabi, lecture slides, or textbook chapters (up to 15 MB) for automated text extraction.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Upload non-encrypted, machine-readable PDFs. Scanned/image-only PDFs require OCR which is not enabled.",
    )

    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)

        st.caption(f"File: **{uploaded_file.name}** | Size: **{file_size_mb:.2f} MB**")

        if st.button("Extract & Load Document", type="primary"):
            with st.spinner("Extracting text with PyMuPDF..."):
                extracted = extract_text_from_pdf(file_bytes)

                if not extracted["success"]:
                    st.error(f"❌ {extracted['error']}")
                else:
                    st.session_state.pdf_text = extracted["text"]
                    st.session_state.pdf_filename = uploaded_file.name
                    st.session_state.pdf_info = {
                        "total_pages": extracted["total_pages"],
                        "processed_pages": extracted["processed_pages"],
                        "char_count": len(extracted["text"]),
                    }

                    if extracted.get("warning"):
                        st.warning(f"⚠️ {extracted['warning']}")

                    st.success(
                        f"✅ Successfully extracted {extracted['processed_pages']} page(s) "
                        f"({len(extracted['text']):,} characters) from '{uploaded_file.name}'!"
                    )

    # Document details if currently loaded
    if st.session_state.pdf_filename and st.session_state.pdf_text:
        st.markdown("---")
        st.markdown(f"### 📋 Active Document: `{st.session_state.pdf_filename}`")

        doc_c1, doc_c2, doc_c3, doc_c4 = st.columns(4)
        with doc_c1:
            st.metric("Total Pages", st.session_state.pdf_info.get("total_pages", 0))
        with doc_c2:
            st.metric("Processed Pages", st.session_state.pdf_info.get("processed_pages", 0))
        with doc_c3:
            st.metric("Characters", f"{len(st.session_state.pdf_text):,}")
        with doc_c4:
            word_count = len(st.session_state.pdf_text.split())
            st.metric("Estimated Words", f"{word_count:,}")

        st.markdown("#### ⚡ Quick Actions with Document")
        act1, act2, act3 = st.columns(3)
        with act1:
            if st.button("📝 Summarize Document", use_container_width=True):
                st.session_state["summarizer_input_text"] = st.session_state.pdf_text[:12000]
                st.session_state.current_page = "Notes Summarizer"
                st.rerun()
        with act2:
            if st.button("🎯 Generate Quiz from PDF", use_container_width=True):
                st.session_state["quiz_source_text"] = st.session_state.pdf_text[:8000]
                st.session_state.current_page = "AI Quiz Generator"
                st.rerun()
        with act3:
            if st.button("💬 Chat about Document", use_container_width=True):
                st.session_state.current_page = "Study Chat Assistant"
                st.rerun()

        with st.expander("📖 Inspect Extracted Text Preview", expanded=False):
            st.text_area(
                "Document Text",
                value=st.session_state.pdf_text,
                height=300,
                disabled=True,
            )


# ==============================================================================
# FEATURE G: STUDY HISTORY
# ==============================================================================
elif page == "Study History":
    st.markdown(
        """
        <div class="project-header">
            <div class="project-title">📚 Study History & Archives</div>
            <div class="project-subtitle">
                Persistent local archive stored in SQLite. Filter, inspect, download, or manage past study sessions.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption("🔒 *Note: Study history is stored locally on this machine (`data/studymate.db`) and is not synced to external servers.*")

    # Filters and Search
    h_col1, h_col2, h_col3 = st.columns([3, 2, 1])
    with h_col1:
        search_kw = st.text_input("🔍 Search History", placeholder="Search by topic, keyword, or question...")
    with h_col2:
        type_filter = st.selectbox(
            "Filter by Session Type",
            options=["All", "topic_explainer", "notes_summary", "quiz", "chat"],
            index=0,
            format_func=lambda x: "All Categories" if x == "All" else x.replace("_", " ").title(),
        )
    with h_col3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        show_clear = st.button("Clear All", type="secondary", use_container_width=True)

    if show_clear:
        st.session_state["confirm_clear_history"] = True

    if st.session_state.get("confirm_clear_history", False):
        st.warning("⚠️ Are you sure you want to delete all saved study sessions? This cannot be undone.")
        y_col, n_col = st.columns(2)
        with y_col:
            if st.button("Yes, Clear Everything", type="primary"):
                clear_all_history()
                st.session_state["confirm_clear_history"] = False
                st.success("All history records cleared.")
                st.rerun()
        with n_col:
            if st.button("Cancel"):
                st.session_state["confirm_clear_history"] = False
                st.rerun()

    # Query records
    history_records = get_history(
        search_query=search_kw,
        session_type=type_filter,
    )

    if not history_records:
        st.markdown(
            """
            <div style="background-color: #FFFFFF; border: 1px dashed #CBD5E1; border-radius: 8px; padding: 40px; text-align: center; color: #64748B;">
                <p style="font-size: 1.1rem; font-weight: 500; margin-bottom: 6px;">No matching study sessions found.</p>
                <p style="font-size: 0.85rem; margin-bottom: 0;">Try adjusting your search terms or generate a new study session!</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.write(f"Showing **{len(history_records)}** session(s):")

        for item in history_records:
            item_id = item["id"]
            type_label = item["session_type"].replace("_", " ").title()

            with st.expander(f"📌 [{type_label}] {item['title']} — {item['created_at']}"):
                if item["input_excerpt"]:
                    st.caption(f"**Original Input:** {item['input_excerpt']}")

                st.markdown("---")
                st.markdown(item["content"])

                st.markdown("---")
                btn_d1, btn_d2, _ = st.columns([1.5, 1.5, 4])
                with btn_d1:
                    st.download_button(
                        "📥 Download",
                        data=item["content"],
                        file_name=f"studymate_{item['session_type']}_{item_id}.md",
                        mime="text/markdown",
                        key=f"dl_hist_{item_id}",
                    )
                with btn_d2:
                    if st.button("🗑️ Delete Entry", key=f"del_hist_{item_id}"):
                        delete_history_entry(item_id)
                        st.success("Entry deleted.")
                        st.rerun()

# ------------------------------------------------------------------------------
# Academic Footer
# ------------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #94A3B8; font-size: 0.8rem; padding: 10px 0;">
        <b>StudyMate AI</b> • Class Project by <b>Kendre Om</b> (Section B11, Sreenidhi University) • Built with Python, Streamlit & Google Gemini
    </div>
    """,
    unsafe_allow_html=True,
)
