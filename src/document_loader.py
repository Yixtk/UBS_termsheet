"""
Simple PDF document loading utilities
"""
from pypdf import PdfReader
from typing import List


def load_pdf_text(pdf_path: str) -> str:
    """
    Load PDF document and extract all text
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as a single string
    """
    reader = PdfReader(pdf_path)
    text_parts = []
    
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    
    return "\n\n".join(text_parts)


def load_pdf_by_pages(pdf_path: str) -> List[str]:
    """
    Load PDF document and return text by pages
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of text strings, one per page
    """
    reader = PdfReader(pdf_path)
    pages = []
    
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    
    return pages


def split_text(text: str, chunk_size: int = 4000, overlap: int = 200) -> List[str]:
    """
    Split text into chunks for processing
    
    Args:
        text: Text to split
        chunk_size: Maximum size of each chunk
        overlap: Overlap between chunks
        
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        
        if end >= len(text):
            break
        
        start = end - overlap
    
    return chunks

