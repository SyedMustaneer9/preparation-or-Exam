import os
import streamlit as st
from groq import Groq
import PyPDF2

# Page Configuration
st.set_paged_config(
    page_title="PakStudy AI Exam Prep",
    page_icon="📚",
    layout="wide"
)

# Custom Styling for Urdu/Roman Urdu friendliness and clean UI
st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; color: #1E3A8A; font-weight: 700; }
    .subtitle { font-size: 1.1krem; color: #4B5563; }
    .urdu-text { font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', serif; direction: rtl; font-size: 1.3rem; text-align: right; }
    .card { background-color: #F9FAFB; padding: 20px; border-radius: 10px; border: 1px solid #E5E7EB; }
    </style>
""", unsafe_allow_html=True)

# Sidebar for API Key & Settings
with st.sidebar:
    st.header("⚙️ Configuration")
    groq_api_key = st.text_input("Enter Groq API Key", type="password", value=os.environ.get("GROQ_API_KEY", ""))
    
    st.markdown("---")
    st.markdown("### 🎯 Exam Settings")
    board_level = st.selectbox("Select Level / Board", ["Matric (9th/10th - BISE)", "Intermediate (11th/12th - FA/FSc/ICS)"])
    language = st.selectbox("Explanation Language", ["English", "Roman Urdu", "Urdu (اردو)"])
    
    st.markdown("---")
    st.info("💡 **Tip:** Upload your FBISE, Punjab, Sindh, KPK, or Balochistan textbook chapter PDF or text notes to get started!")

# Main Header
st.markdown('<p class="main-title">🇵🇰 PakStudy AI Exam Prep</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Upload your textbook chapter, test your knowledge with board-style exam questions, and get instant evaluations in your preferred language.</p>', unsafe_allow_html=True)
st.markdown("---")

# Initialize Session State
if "chapter_text" not in st.session_state:
    st.session_state.chapter_text = ""
if "questions" not in st.session_state:
    st.session_state.questions = []
if "current_q_idx" not in st.session_state:
    st.session_state.current_q_idx = 0
if "quiz_started" not in st.session_state:
    st.session_state.quiz_started = False

# Step 1: File Upload
st.subheader("Step 1: Upload Your Textbook Chapter")
uploaded_file = st.file_uploader("Upload chapter file (PDF or TXT)", type=["pdf", "txt"])

if uploaded_file is not None:
    if not st.session_state.chapter_text:
        with st.spinner("Reading and parsing chapter..."):
            text = ""
            if uploaded_file.type == "application/pdf":
                reader = PyPDF2.PdfReader(uploaded_file)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            else:
                text = uploaded_file.read().decode("utf-8")
            
            st.session_state.chapter_text = text
            st.success(f"Successfully loaded chapter! ({len(text)} characters)")

# Step 2: Generate Questions
if st.session_state.chapter_text:
    st.markdown("---")
    st.subheader("Step 2: Generate Practice Questions")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        num_questions = st.number_input("Number of Questions", min_value=1, max_value=10, value=5)
        q_type = st.selectbox("Question Type", ["Short Questions (Board Style)", "Long/Detailed Questions", "Multiple Choice Questions (MCQs)"])
    
    with col2:
        st.write("")
        st.write("")
        generate_btn = st.button("🚀 Generate Exam Questions", type="primary")

    if generate_btn:
        if not groq_api_key:
            st.error("Please enter your Groq API Key in the sidebar.")
        else:
            with st.spinner("Generating board-pattern exam questions from your textbook..."):
                client = Groq(api_key=groq_api_key)
                
                prompt = f"""
                You are an expert Pakistani board exam paper setter for {board_level}. 
                Based strictly on the following textbook chapter text, generate exactly {num_questions} {q_type}.
                Make sure the questions match the style of Pakistani board exams (conceptual yet based on the text).
                
                Chapter Text:
                {st.session_state.chapter_text[:12000]}  # Truncate to fit token limits safely
                
                Return ONLY a valid Python list of strings containing the questions, formatted cleanly without extra commentary. Example format:
                ["Question 1...", "Question 2..."]
                """
                
                try:
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7
                    )
                    
                    content = response.choices[0].message.content.strip()
                    # Safe eval or parsing for list
                    import ast
                    # Find bracket bounds
                    start_idx = content.find("[")
                    end_idx = content.rfind("]")
                    if start_idx != -1 and end_idx != -1:
                        st.session_state.questions = ast.literal_eval(content[start_idx:end_idx+1])
                        st.session_state.current_q_idx = 0
                        st.session_state.quiz_started = True
                        st.rerun()
                    else:
                        st.error("Failed to parse generated questions. Try generating again.")
                except Exception as e:
                    st.error(f"Error generating questions: {e}")

# Step 3: Interactive Practice & Evaluation
if st.session_state.quiz_started and st.session_state.questions:
    st.markdown("---")
    st.subheader("Step 3: Answer & Get Evaluated")
    
    q_idx = st.session_state.current_q_idx
    questions = st.session_state.questions
    
    if q_idx < len(questions):
        st.markdown(f"**Question {q_idx + 1} of {len(questions)}:**")
        st.info(questions[q_idx])
        
        user_answer = st.text_area("Your Answer:", key=f"ans_{q_idx}")
        
        col_prev, col_eval, col_next = st.columns([1, 2, 1])
        
        with col_eval:
            evaluate_btn = st.button("📝 Check & Evaluate Answer", type="primary", key=f"eval_btn_{q_idx}")
            
        if evaluate_btn:
            if not user_answer.strip():
                st.warning("Please write an answer before checking.")
            else:
                with st.spinner("Evaluating your answer against the textbook..."):
                    client = Groq(api_key=groq_api_key)
                    
                    eval_prompt = f"""
                    You are an expert board examiner for {board_level} in Pakistan. 
                    Evaluate the student's answer based strictly on the provided chapter excerpt.
                    
                    Target Language for Explanation: {language}
                    (If language is Urdu, write the explanation in Urdu script/Nastaliq. If Roman Urdu, write in conversational Roman Urdu. If English, write in clear academic English.)
                    
                    Textbook Chapter Context:
                    {st.session_state.chapter_text[:10000]}
                    
                    Question: {questions[q_idx]}
                    Student's Answer: {user_answer}
                    
                    Provide your feedback in the following format:
                    1. **Score/Rating:** (e.g., Excellent / Good / Needs Improvement / Incorrect)
                    2. **Feedback & Corrections:** Point out what was correct, what was missing, or any conceptual mistakes based on the book.
                    3. **Model Answer:** Provide a concise, board-exam-ready ideal answer.
                    """
                    
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": eval_prompt}],
                        temperature=0.3
                    )
                    
                    evaluation_result = response.choices[0].message.content
                    
                    st.markdown("### 📊 Examiner Evaluation")
                    if language == "Urdu (اردو)":
                        st.markdown(f'<div class="card"><p class="urdu-text">{evaluation_result}</p></div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="card">{evaluation_result}</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        nav_cols = st.columns(2)
        with nav_cols[0]:
            if q_idx > 0:
                if st.button("⬅️ Previous Question"):
                    st.session_state.current_q_idx -= 1
                    st.rerun()
        with nav_cols[1]:
            if q_idx < len(questions) - 1:
                if st.button("Next Question ➡️"):
                    st.session_state.current_q_idx += 1
                    st.rerun()
            else:
                if st.button("🎉 Finish Practice Session"):
                    st.success("You have completed all questions in this session! Great job preparing for your exams.")
    else:
        st.success("You have finished all questions!")
