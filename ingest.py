from pathlib import Path
import pdfplumber
import pandas as pd

print("✅ ingest.py LOADED")


def ingest_file(uploaded_file):
    """
    Returns:
    extracted_text (str | None),
    error_message (str | None)
    """

    print("📄 Ingesting file:", uploaded_file.name)

    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    file_path = upload_dir / uploaded_file.name

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
        filename = uploaded_file.name.lower()

        if filename.endswith(".txt"):
            return uploaded_file.getvalue().decode("utf-8"), None

        elif filename.endswith(".csv"):
            df = pd.read_csv(file_path)
            return df.to_string(index=False), None

        elif filename.endswith(".xlsx"):
            df = pd.read_excel(file_path, engine="openpyxl")
            return df.to_string(index=False), None

        elif filename.endswith(".pdf"):
            text = extract_pdf_text(file_path)
            if not text.strip():
                return None, "No readable text found in PDF"
            return text, None

        else:
            return None, "Unsupported file type"

    except Exception as e:
        return None, str(e)


def extract_pdf_text(path: Path) -> str:
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()
