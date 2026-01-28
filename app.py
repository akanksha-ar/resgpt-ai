from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import pandas as pd
import os
import requests

from ingest import ingest_file
from pdf_chunks import chunk_text
from vector_store import add_chunks, search


# =================================================
# CONFIG
# =================================================
st.set_page_config(page_title="RESGPT.AI", page_icon="🤖", layout="wide")
CHUNK_SIZE = 2000


# =================================================
# SESSION STATE
# =================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "dataframes" not in st.session_state:
    st.session_state.dataframes = {}   # filename -> DataFrame

if "text_chunks" not in st.session_state:
    st.session_state.text_chunks = {}  # filename -> list of chunks

if "processed_files" not in st.session_state:
    st.session_state.processed_files = set()


# =================================================
# UI
# =================================================
st.title("🤖 RESGPT.AI")
st.markdown("💡 Upload CSV / Excel / PDF / TXT and ask **fact-correct questions**")


# =================================================
# SIDEBAR – FILE UPLOAD
# =================================================
with st.sidebar:
    st.header("📁 Upload Documents")

    files = st.file_uploader(
        "Choose file(s)",
        type=["csv", "xlsx", "pdf", "txt"],
        accept_multiple_files=True
    )

    if files:
        with st.spinner("Processing files..."):
            for f in files:
                if f.name in st.session_state.processed_files:
                    continue

                content, error = ingest_file(f)
                if error:
                    st.error(f"❌ {f.name}: {error}")
                    continue

                # ---------- CSV / XLSX ----------
                if content["type"] == "table":
                    df = content["df"]
                    st.session_state.dataframes[f.name] = df

                    st.success(
                        f"📊 {f.name}: {len(df)} rows, {len(df.columns)} columns"
                    )

                # ---------- PDF / TXT ----------
                elif content["type"] == "document":
                    chunks = chunk_text(content["text"], CHUNK_SIZE)
                    st.session_state.text_chunks[f.name] = chunks
                    add_chunks(chunks)

                    st.success(
                        f"📄 {f.name}: indexed {len(chunks)} chunks"
                    )

                st.session_state.processed_files.add(f.name)

        st.success(f"✅ {len(st.session_state.processed_files)} file(s) processed")

    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.session_state.dataframes = {}
        st.session_state.text_chunks = {}
        st.session_state.processed_files = set()
        st.rerun()


# =================================================
# CHAT HISTORY
# =================================================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# =================================================
# CHAT INPUT
# =================================================
if prompt := st.chat_input("Ask a question about your files..."):

    if not st.session_state.processed_files:
        st.warning("⚠️ Upload a file first")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    prompt_lower = prompt.lower()

    # =================================================
    # ✅ CSV / XLSX — FACT-SAFE ANSWERS (NO AI)
    # =================================================
    if st.session_state.dataframes:
        df = list(st.session_state.dataframes.values())[0]

        # ---- COUNT ----
        if "count" in prompt_lower or "total" in prompt_lower:
            answer = f"✅ Total number of records: **{len(df)}**"
            st.markdown(answer)
            st.session_state.messages.append(
                {"role": "assistant", "content": answer}
            )
            st.stop()

        # ---- COLUMN VALUES ----
        for col in df.columns:
            if col.lower() in prompt_lower:
                values = df[col].dropna().astype(str).tolist()

                answer = (
                    f"✅ Column `{col}` has **{len(values)}** values:\n\n"
                    + "\n".join(f"- {v}" for v in values[:200])
                )

                st.markdown(answer)
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer}
                )
                st.stop()


    # =================================================
    # 📄 PDF / TXT — VECTOR SEARCH + CLAUDE
    # =================================================
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        st.error("❌ CLAUDE_API_KEY not set")
        st.stop()

    context_chunks = search(prompt)
    context = "\n\n".join(context_chunks)

    full_prompt = f"""
Use ONLY the information below.
Do NOT invent facts.

<context>
{context}
</context>

Question:
{prompt}
"""

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }

            payload = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 800,
                "messages": [{"role": "user", "content": full_prompt}]
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
                st.error(response.text)


# =================================================
# FOOTER
# =================================================
st.markdown("---")
st.markdown("🚀 **RESGPT.AI** – Document-aware Q&A powered by AI")

