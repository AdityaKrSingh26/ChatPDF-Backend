import PyPDF2
import io
import requests
from typing import List

async def process_pdf_file(url: str) -> str:
    """Download PDF from Cloudinary and extract text"""
    response = requests.get(url)
    pdf_file = io.BytesIO(response.content)
    
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    
    return text