import streamlit as st
import psycopg2
import graphviz
import os
import time
import json
import hashlib
import google.generativeai as genai

# ============================
# Gemini Config
# ============================
# Make sure to set GOOGLE_API_KEY in your environment variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# Using gemini-1.5-flash for speed and efficiency
MODEL_NAME = "gemini-3-flash-preview"

# ============================
# Database Connection
# ============================
def get_connection():
    try:
        return psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "erd_database"),
            user=os.getenv("DB_USER", "user"),
            password=os.getenv("DB_PASS", "password"),
            connect_timeout=5
        )
    except Exception as e:
        st.error(f"DB Error: {e}")
        return None

# ============================
# Auth Helpers
# ============================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(email, password):
    conn = get_connection()
    if not conn:
        return None
    with conn.cursor() as cur:
        cur.execute("SELECT id, password_hash FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
    conn.close()
    if row and row[1] == hash_password(password):
        return row[0]
    return None

def create_user(email, password):
    conn = get_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id",
                (email, hash_password(password))
            )
            user_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO projects (user_id, name, description) VALUES (%s, %s, %s)",
                (user_id, "My First ERD Project", "Default workspace")
            )
            conn.commit()
        return True
    except Exception as e:
        print(e)
        return False
    finally:
        conn.close()

# ============================
# Gemini Caller (Cached)
# ============================
@st.cache_data(ttl=3600, show_spinner=False)
def call_gemini_for_dot(prompt_text):
    system_instruction = (
        "You are a senior database architect. "
        "Convert the user's description into a VALID Graphviz DOT string "
        "for an ER diagram. "
        "Use box shapes for entities. "
        "No markdown. No explanations. "
        "Return ONLY raw DOT code."
    )

    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system_instruction
    )

    start = time.time()
    # Using generation_config to keep output strictly code-focused
    response = model.generate_content(
        prompt_text,
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
        )
    )
    duration = time.time() - start

    if not response.text:
        raise Exception("Gemini returned an empty response.")

    content = response.text.strip()
    
    # Clean up markdown if the model ignores the "no markdown" instruction
    if "```" in content:
        content = content.split("```")[1]
        if content.startswith("dot"):
            content = content[3:]
    
    return content.strip(), duration

# ============================
# UI Setup
# ============================
st.set_page_config(page_title="AutoERGen Gemini v1", layout="wide")
for key in ["logged_in", "user_id", "last_dot"]:
    st.session_state.setdefault(key, None)

# ============================
# Sidebar (Login / Signup)
# ============================
with st.sidebar:
    st.title("🛡️ AutoERGen (Gemini Edition)")

    if st.session_state.logged_in:
        st.success("Logged in")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.last_dot = None
            st.rerun() 

    else:
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
        with tab1:
            with st.form("login"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login")
                if submit:
                    uid = authenticate_user(email, password)
                    if uid:
                        st.session_state.logged_in = True
                        st.session_state.user_id = uid
                        st.rerun()
                    else:
                        st.error("Invalid credentials")

        with tab2:
            with st.form("signup"):
                email = st.text_input("Email", key="s_email")
                password = st.text_input("Password", type="password", key="s_pw")
                submit = st.form_submit_button("Create Account")
                if submit:
                    if create_user(email, password):
                        st.success("Account created. Please log in.")
                    else:
                        st.error("Email already exists")

# ============================
# Main App
# ============================
if st.session_state.logged_in:
    st.header("ER Diagram Architect (Text → DOT via Gemini)")
    user_input = st.text_area("Describe your tables and relationships:", height=150)

    if st.button("🚀 Generate Diagram") and user_input.strip():
        with st.spinner("Gemini is designing your ER diagram..."):
            try:
                dot, exec_time = call_gemini_for_dot(user_input)
                st.session_state.last_dot = dot

                # Log to DB
                conn = get_connection()
                if conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO logs (project_id, user_prompt, llm_response, execution_time)
                            SELECT id, %s, %s, %s
                            FROM projects
                            WHERE user_id = %s
                            ORDER BY created_at
                            LIMIT 1
                            """,
                            (user_input, json.dumps(dot), exec_time, st.session_state.user_id)
                        )
                        conn.commit()
                    conn.close()
            except Exception as e:
                st.error(f"Error calling Gemini: {e}")

    if st.session_state.last_dot:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("DOT Source")
            edited = st.text_area("Edit DOT", st.session_state.last_dot, height=400)
            if st.button("Update Diagram"):
                st.session_state.last_dot = edited
        with col2:
            st.subheader("Visual ERD")
            try:
                st.graphviz_chart(st.session_state.last_dot)
            except Exception as e:
                st.error(f"Graphviz rendering error: {e}")
else:
    st.title("Welcome to AutoERGen")
    st.write("Please log in to continue.")