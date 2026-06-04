"""This module extracts the text from the files (pdf/txt)"""
import io
import pdfplumber
from fastapi import UploadFile, HTTPException
# from pydantic import str


class TextExtractorService:
    @staticmethod
    async def extract_text(file: UploadFile) -> str:
        """extracts the text data from the uploaded file

        Args:
            file (UploadFile): uploads a file (pdf/txt)

        Returns:
            str: text
        """
        filename = file.filename
        if not filename:
            raise HTTPException(
                status_code=400, detail="Uploaded file must have a filename")

        filename = filename.lower()

        if filename.endswith(".txt"):
            try:
                content = await file.read()
                return content.decode('utf-8')
            except Exception as err:
                print(f"Error while reading the file: {err}")
                raise HTTPException(
                    status_code=400, detail=f"Failed to decode txt file: {err}")

        elif filename.endswith(".pdf"):
            try:
                content = await file.read()
                text_content = []
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_content.append(page_text)

                extracted_text = "\n".join(text_content).strip()
                if not extracted_text:
                    raise HTTPException(
                        status_code=400, detail="PDF file is empty")

                return extracted_text

            except Exception as err:
                print(f"Error while reading the file: {err}")
                raise HTTPException(
                    status_code=400, detail=f"Failed to decode pdf file: {err}")

        else:
            raise HTTPException(
                status_code=400, detail="Uploaded file's format is not supported.")
