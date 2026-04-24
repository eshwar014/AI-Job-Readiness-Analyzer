import streamlit as st
from groq import Groq
import os
import PyPDF2
import docx
from dotenv import load_dotenv
import io
import json

# ── Load environment variables ──────────────────────────────────────────────
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Job Readiness AI",
    page_icon="🎯",
    layout="wide"
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); }
    h1 { color: #38bdf8 !important; font-family: Georgia, serif; }
    h2, h3 { color: #e2e8f0 !important; }
    .stTextArea textarea { background: #1e293b; color: #e2e8f0; border: 1px solid #334155; }
    div[data-testid="stMarkdownContainer"] p { color: #cbd5e1; }
    .score-box {
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        color: white;
        font-size: 2rem;
        font-weight: bold;
        margin: 10px 0;
    }
    .section-card {
        background: #1e293b;
        border-left: 4px solid #38bdf8;
        border-radius: 8px;
        padding: 16px;
        margin: 12px 0;
        color: #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# ── Helper: extract text ─────────────────────────────────────────────────────
def extract_text(uploaded_file) -> str:
    if uploaded_file is None:
        return ""
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif name.endswith(".docx"):
        doc = docx.Document(io.BytesIO(uploaded_file.read()))
        return "\n".join(para.text for para in doc.paragraphs)
    elif name.endswith((".txt", ".md")):
        return uploaded_file.read().decode("utf-8", errors="ignore")
    return ""

# ── Core AI analysis using Groq ──────────────────────────────────────────────
def analyze_job_readiness(resume_text: str, jd_text: str) -> dict:
    client = Groq(api_key=api_key)

    prompt = f"""
You are an expert career coach and hiring consultant. Analyze the resume against the job description and provide a detailed job readiness assessment.

## RESUME:
{resume_text}

## JOB DESCRIPTION:
{jd_text}

Respond ONLY in valid JSON format with no extra text, no markdown, no backticks:
{{
  "match_score": <integer 0-100>,
  "verdict": "<Ready to Apply | Needs Minor Improvements | Needs Significant Work | Not a Good Fit>",
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill1", "skill2"],
  "strengths": ["strength1", "strength2"],
  "gaps": ["gap1", "gap2"],
  "recommendations": ["action1", "action2"],
  "suggested_resume_edits": ["edit1", "edit2"],
  "interview_topics": ["topic1", "topic2"],
  "summary": "<2-3 sentence overall assessment>"
}}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw.strip())

# ── UI Layout ─────────────────────────────────────────────────────────────────
st.markdown("# 🎯 AI Job Readiness Analyzer")
st.markdown("#### Upload your resume and job description for an instant AI-powered fit analysis.")
st.divider()

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📄 Your Resume")
    resume_file = st.file_uploader(
        "Upload Resume (PDF, DOCX, or TXT)",
        type=["pdf", "docx", "txt"],
        key="resume"
    )
    if resume_file:
        st.success(f"✅ Loaded: {resume_file.name}")

with col2:
    st.markdown("### 📋 Job Description")
    jd_file = st.file_uploader(
        "Upload JD (PDF, DOCX, or TXT)",
        type=["pdf", "docx", "txt"],
        key="jd"
    )
    jd_text_input = st.text_area(
        "Or paste the Job Description here",
        height=200,
        placeholder="Paste the full job description text..."
    )

st.divider()

# ── Analyze Button ────────────────────────────────────────────────────────────
analyze_btn = st.button("🚀 Analyze Job Readiness", use_container_width=True, type="primary")

if analyze_btn:
    if not api_key:
        st.error("❌ GROQ_API_KEY not found in .env file. Please add it and restart.")
        st.stop()

    resume_text = extract_text(resume_file) if resume_file else ""
    jd_text = extract_text(jd_file) if jd_file else jd_text_input.strip()

    if not resume_text:
        st.warning("⚠️ Please upload a resume file.")
        st.stop()
    if not jd_text:
        st.warning("⚠️ Please upload or paste a job description.")
        st.stop()

    with st.spinner("🤖 Analyzing with Groq AI... Please wait..."):
        try:
            result = analyze_job_readiness(resume_text, jd_text)
        except Exception as e:
            st.error(f"❌ Analysis failed: {e}")
            st.stop()

    # ── Results ──────────────────────────────────────────────────────────────
    st.markdown("## 📊 Analysis Results")

    score = result.get("match_score", 0)
    verdict = result.get("verdict", "N/A")
    color = "#22c55e" if score >= 75 else "#f59e0b" if score >= 50 else "#ef4444"

    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(f"""
        <div class="score-box" style="background: {color};">
            {score}/100<br>
            <span style="font-size:1rem; font-weight:400;">{verdict}</span>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="section-card">
            <strong>Overall Assessment</strong><br><br>
            {result.get('summary', '')}
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown("### ✅ Matched Skills")
        for s in result.get("matched_skills", []):
            st.markdown(f"- 🟢 {s}")
    with sc2:
        st.markdown("### ❌ Missing Skills")
        for s in result.get("missing_skills", []):
            st.markdown(f"- 🔴 {s}")

    st.divider()

    sg1, sg2 = st.columns(2)
    with sg1:
        st.markdown("### 💪 Strengths")
        for s in result.get("strengths", []):
            st.markdown(f"- ✨ {s}")
    with sg2:
        st.markdown("### 🔧 Gaps to Address")
        for g in result.get("gaps", []):
            st.markdown(f"- ⚠️ {g}")

    st.divider()

    st.markdown("### 🎯 Action Recommendations")
    for i, r in enumerate(result.get("recommendations", []), 1):
        st.markdown(f"**{i}.** {r}")

    st.divider()

    st.markdown("### ✍️ Suggested Resume Edits")
    for e in result.get("suggested_resume_edits", []):
        st.markdown(f"- 📝 {e}")

    st.divider()

    st.markdown("### 🎤 Likely Interview Topics")
    cols = st.columns(3)
    for i, topic in enumerate(result.get("interview_topics", [])):
        cols[i % 3].markdown(f"🔹 {topic}")

    st.success("✅ Analysis complete! Use these insights to strengthen your application.")