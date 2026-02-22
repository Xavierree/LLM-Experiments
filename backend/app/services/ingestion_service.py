import os
from typing import List
from fastapi import UploadFile
from pypdf import PdfReader
from docx import Document
from io import BytesIO
from app.core import rag

class IngestionService:
    def __init__(self):
        pass

    async def process_file(self, file: UploadFile) -> dict:
        filename = file.filename
        content = await file.read()
        text = ""

        try:
            if filename.endswith(".pdf"):
                text = self._extract_pdf(content)
            elif filename.endswith(".docx"):
                text = self._extract_docx(content)
            elif filename.endswith(".txt"):
                text = content.decode("utf-8")
            else:
                return {"error": "Unsupported file format. Please upload PDF, DOCX, or TXT."}

            if not text:
                return {"error": "Could not extract text from file."}

            # Simple chunking by paragraph/lines for now
            # In production, use LangChain's RecursiveCharacterTextSplitter
            chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
            
            # Add to RAG system
            from app.core import rag
            rag.add_documents(chunks, filename)

            # Get total count (inefficient but okay for prototype)
            total_docs = len(rag.DOCUMENTS)

            return {
                "message": "File processed successfully",
                "chunks_added": len(chunks),
                "total_documents": total_docs
            }

        except Exception as e:
            return {"error": f"Failed to process file: {str(e)}"}

    def _extract_pdf(self, content: bytes) -> str:
        reader = PdfReader(BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text

    def _extract_docx(self, content: bytes) -> str:
        doc = Document(BytesIO(content))
        text = "\n".join([para.text for para in doc.paragraphs])
        return text

ingestion_service = IngestionService()
