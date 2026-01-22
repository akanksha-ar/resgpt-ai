from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import requests
import os
from ingest import ingest_file



# -------------------------------------------------
# Page config
# -------------------------------------------------
st.set_page_config(page_title="RESGPT.AI", page_icon="🤖", layout="wide")

# -------------------------------------------------
# Session state
# -------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_file_content" not in st.session_state:
    st.session_state.uploaded_file_content = None

if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None


# -------------------------------------------------
# Title
# -------------------------------------------------
st.title("🤖 RESGPT.AI")
st.markdown("💡 *Upload a document first, then ask questions about its content*")


# -------------------------------------------------
# Sidebar – File Upload & Ingestion
# -------------------------------------------------
with st.sidebar:
    st.header("📁 Upload Document")

    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "csv", "xlsx", "txt", "docx"],
        help="Upload a document to analyze"
    )

# 🔍 TEMP DEBUG — ADD EXACTLY HERE
    st.sidebar.caption(
        f"Using API key ending with: {os.getenv('CLAUDE_API_KEY')[-6:]}"
    )
    
    if uploaded_file is not None:
        with st.spinner("Processing file..."):
            content, error = ingest_file(uploaded_file)

        if error:
            st.error(f"❌ {error}")
            st.session_state.uploaded_file_content = None
            st.session_state.uploaded_file_name = None
        else:
            st.success(f"✅ File uploaded & processed: {uploaded_file.name}")
            st.session_state.uploaded_file_content = content
            st.session_state.uploaded_file_name = uploaded_file.name

            # 🔍 TEMP DEBUG (remove later)
            st.text_area(
                "Extracted Content (debug)",
                content[:3000],
                height=300
            )

    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.session_state.uploaded_file_content = None
        st.session_state.uploaded_file_name = None
        st.rerun()


# -------------------------------------------------
# Chat History
# -------------------------------------------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# -------------------------------------------------
# Chat Input + Claude API Call
# -------------------------------------------------
if prompt := st.chat_input("Ask a question about your document..."):

    # Safety check
    if not st.session_state.uploaded_file_content or len(st.session_state.uploaded_file_content.strip()) == 0:
        st.warning("⚠️ Please upload and process a document first.")
        st.stop()

    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):

            try:
                api_key = os.getenv("CLAUDE_API_KEY")
                if not api_key:
                    st.error("❌ CLAUDE_API_KEY not found in environment variables")
                    st.stop()

                # Build prompt
                full_prompt = f"""
You are answering questions strictly based on the following document.

<document>
{st.session_state.uploaded_file_content[:12000]}
</document>

Question:
{prompt}
"""

                # -------------------------
                # ✅ CLAUDE API CALL (CORRECT)
                # -------------------------
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }

                payload = {
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 800,
                    "messages": [
                        {
                            "role": "user",
                            "content": full_prompt
                        }
                    ]
                }

                response = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=60
                )

                if response.status_code == 200:
                    answer = response.json()["content"][0]["text"]
                    st.markdown(answer)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer}
                    )
                else:
                    error_msg = f"❌ Claude API Error {response.status_code}: {response.text}"
                    st.error(error_msg)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_msg}
                    )

            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )


# -------------------------------------------------
# Footer
# -------------------------------------------------
st.markdown("---")
st.markdown("🚀 **RESGPT.AI** – Document-aware Q&A powered by AI")
