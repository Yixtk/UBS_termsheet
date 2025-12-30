"""
Simple PDF document loading utilities with artifact cleaning
"""
from pypdf import PdfReader
from typing import List
import re


def clean_pdf_artifacts(text: str) -> str:
    """
    Clean common PDF artifacts: headers, footers, page numbers, excessive whitespace
    
    Args:
        text: Raw text extracted from PDF
        
    Returns:
        Cleaned text with artifacts removed
    """
    lines = text.split('\n')
    cleaned_lines = []
    
    # Patterns to identify and remove
    footer_patterns = [
        r'^\s*page\s+\d+\s*$',  # "Page 1"
        r'^\s*\d+\s*$',  # Standalone page numbers
        r'^\s*\d+\s*/\s*\d+\s*$',  # "1/10"
        r'confidential',
        r'proprietary',
        r'©.*\d{4}',  # Copyright notices
        r'all rights reserved',
        r'^\s*\d{4}\s*$',  # Year only
        r'^\s*\[?\s*\d+\s*\]?\s*$',  # [1], (1), etc.
    ]
    
    for line in lines:
        line_lower = line.lower().strip()
        
        # Skip empty lines
        if not line_lower:
            continue
        
        # Skip lines matching footer patterns
        if any(re.search(pattern, line_lower) for pattern in footer_patterns):
            continue
        
        # Skip very short lines that are likely artifacts (but keep normal punctuation)
        if len(line_lower) <= 2 and line_lower not in ['-', '•', '–']:
            continue
        
        cleaned_lines.append(line)
    
    # Join lines and clean excessive whitespace
    cleaned_text = '\n'.join(cleaned_lines)
    
    # Remove multiple consecutive blank lines
    cleaned_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_text)
    
    # Remove excessive spaces
    cleaned_text = re.sub(r' {2,}', ' ', cleaned_text)
    
    return cleaned_text.strip()


def load_pdf_text(pdf_path: str) -> str:
    """
    Load PDF document, extract text, and clean artifacts
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted and cleaned text as a single string
    """
    reader = PdfReader(pdf_path)
    text_parts = []
    
    for page in reader.pages:
        text = page.extract_text()
        if text:
            # Clean artifacts from each page
            cleaned_text = clean_pdf_artifacts(text)
            if cleaned_text:
                text_parts.append(cleaned_text)
    
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

