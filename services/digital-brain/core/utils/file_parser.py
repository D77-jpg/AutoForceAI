import tempfile
import os
import shutil
from typing import Optional
from fastapi import UploadFile

# Try to import optional dependencies
try:
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None

class FileParser:
    @staticmethod
    async def parse_upload_file(file: UploadFile) -> str:
        """
        Parses an uploaded file and returns its text content.
        Supports: .txt, .md, .csv, .pdf, .docx
        """
        filename = file.filename.lower()
        content = ""

        # Create a temp file to read from
        suffix = os.path.splitext(filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        try:
            if filename.endswith(".pdf"):
                if PdfReader:
                    reader = PdfReader(tmp_path)
                    for page in reader.pages:
                        content += page.extract_text() + "\n"
                else:
                    content = "[Server Error] PyPDF2 not installed. Cannot parse PDF."
            
            elif filename.endswith(".docx"):
                if Document:
                    doc = Document(tmp_path)
                    for para in doc.paragraphs:
                        content += para.text + "\n"
                else:
                    content = "[Server Error] python-docx not installed. Cannot parse DOCX."

            elif filename.endswith((".txt", ".md", ".csv", ".json", ".py", ".js", ".ts", ".html", ".css")):
                with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            
            else:
                content = f"[System] Unsupported file type: {filename}. Please upload PDF, DOCX, or Text files."

        except Exception as e:
            content = f"[System] Error parsing file {filename}: {str(e)}"
        finally:
            # Cleanup temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        
        return content.strip()
