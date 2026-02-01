import streamlit as st
from graphviz import Digraph
from google import genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

# --- Configure Gemini client ---
# It will automatically look for GEMINI_API_KEY in your .env
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# --- Function: Generate ER entities and relationships from text ---
def generate_er_spec(prompt_text):
    """
    Uses Gemini to generate structured ER info from text description
    """
    system_instruction = "You are an expert database architect. Always return output in valid JSON format."
    
    er_prompt = f"""
    Extract entities and relationships from the following database description:
    "{prompt_text}"

    Return as JSON with this exact structure:
    {{
        "entities": ["Entity1", "Entity2"],
        "relationships": [
            {{"from": "Entity1", "to": "Entity2", "relation": "description"}}
        ]
    }}
    """
    
    try:
        # Using Gemini 2.0 Flash for speed and high context window
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=er_prompt,
            config={'system_instruction': system_instruction}
        )
        
        # Clean the response text (remove markdown backticks if present)
        raw_text = response.text.strip().replace("```json", "").replace("```", "")
        er_data = json.loads(raw_text)
        return er_data
    except Exception as e:
        st.error(f"Failed to process with Gemini: {e}")
        return {"entities": [], "relationships": []}

# --- Function: Generate ER Diagram ---
def create_er_diagram(er_data):
    dot = Digraph(comment="ER Diagram")
    dot.attr(rankdir='LR') # Left to Right layout
    
    # Add entities
    for entity in er_data.get("entities", []):
        dot.node(entity, entity, shape="box", style="filled", color="lightblue")
    
    # Add relationships
    for rel in er_data.get("relationships", []):
        dot.edge(rel["from"], rel["to"], label=rel.get("relation", ""))
    return dot

# --- Function: Suggest SQL Schema ---
def generate_sql_schema(er_data):
    sql_statements = []
    for entity in er_data.get("entities", []):
        stmt = f"CREATE TABLE {entity} (\n    id INT PRIMARY KEY,\n    name VARCHAR(100)\n);"
        sql_statements.append(stmt)
    
    for rel in er_data.get("relationships", []):
        stmt = (
            f"-- {rel['from']} {rel['relation']} {rel['to']}\n"
            f"ALTER TABLE {rel['from']} ADD COLUMN {rel['to'].lower()}_id INT REFERENCES {rel['to']}(id);"
        )
        sql_statements.append(stmt)
    return "\n\n".join(sql_statements)

# --- Streamlit Interface ---
st.set_page_config(page_title="AutoERGen", layout="wide")
st.title("🧬 AutoERGen: Gemini-Powered ER Diagram Generator")

st.markdown("Enter your database requirements below to visualize your schema.")

user_input = st.text_area("Database Description:", placeholder="e.g., An e-commerce system where customers place orders for products...")

if st.button("Generate Visualization"):
    if not user_input.strip():
        st.warning("Please enter a description.")
    else:
        with st.spinner("Gemini is thinking..."):
            er_data = generate_er_spec(user_input)
            
            if er_data["entities"]:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.subheader("ER Diagram")
                    dot = create_er_diagram(er_data)
                    st.graphviz_chart(dot)
                
                with col2:
                    st.subheader("SQL Schema")
                    st.code(generate_sql_schema(er_data), language="sql")
            else:
                st.error("Could not extract data. Try more descriptive text.")