"""
PDF Parser for Steel Datasheets
Парсинг PDF файлов с техническими данными о сталях
"""

import os
import re
import requests
import tempfile
from typing import Optional, Dict, Any, List
from pathlib import Path

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("WARNING: pdfplumber not installed. PDF parsing will be limited.")

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False


class PDFParser:
    """Парсер PDF файлов с техническими характеристиками сталей"""

    def __init__(self):
        self.temp_dir = tempfile.gettempdir()

    def download_pdf(self, url: str, timeout: int = 30) -> Optional[str]:
        """
        Download PDF from URL to temporary file

        Args:
            url: URL of PDF file
            timeout: Request timeout in seconds

        Returns:
            Path to downloaded PDF file, or None if failed
        """
        try:
            # Check if URL looks like a PDF
            if not url.lower().endswith('.pdf') and 'pdf' not in url.lower():
                return None

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, timeout=timeout, headers=headers, stream=True)
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower():
                # Some servers don't set correct content-type, try anyway
                pass

            # Save to temp file
            temp_path = os.path.join(self.temp_dir, f"steel_datasheet_{hash(url)}.pdf")

            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return temp_path

        except Exception as e:
            print(f"Error downloading PDF from {url}: {e}")
            return None

    def extract_text_pdfplumber(self, pdf_path: str) -> Optional[str]:
        """
        Extract text from PDF using pdfplumber (best quality)

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text or None
        """
        if not PDF_AVAILABLE:
            return None

        try:
            with pdfplumber.open(pdf_path) as pdf:
                text_parts = []
                # Extract from first 5 pages (chemical composition usually on first pages)
                for page in pdf.pages[:5]:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)

                return '\n\n'.join(text_parts)

        except Exception as e:
            print(f"Error extracting text with pdfplumber: {e}")
            return None

    def extract_text_pypdf2(self, pdf_path: str) -> Optional[str]:
        """
        Extract text from PDF using PyPDF2 (fallback)

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text or None
        """
        if not PYPDF2_AVAILABLE:
            return None

        try:
            reader = PdfReader(pdf_path)
            text_parts = []

            # Extract from first 5 pages
            for page_num in range(min(5, len(reader.pages))):
                page = reader.pages[page_num]
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            return '\n\n'.join(text_parts)

        except Exception as e:
            print(f"Error extracting text with PyPDF2: {e}")
            return None

    def extract_text(self, pdf_path: str) -> Optional[str]:
        """
        Extract text from PDF (tries multiple methods)

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text or None
        """
        # Try pdfplumber first (better quality)
        text = self.extract_text_pdfplumber(pdf_path)
        if text:
            return text

        # Fallback to PyPDF2
        text = self.extract_text_pypdf2(pdf_path)
        if text:
            return text

        return None

    def extract_chemical_composition_regex(self, text: str) -> Dict[str, Any]:
        """
        Extract chemical composition using regex patterns

        Args:
            text: PDF text content

        Returns:
            Dictionary with chemical elements
        """
        composition = {}

        # Common elements in steel
        elements = ['C', 'Cr', 'Mo', 'V', 'W', 'Co', 'Ni', 'Mn', 'Si', 'S', 'P', 'Cu', 'Nb', 'N', 'Ti', 'Al']

        for element in elements:
            # Patterns like:
            # C: 0.65%
            # C 0.65
            # Carbon (C): 0.65%
            # C: 0.60-0.70%
            patterns = [
                rf'{element}\s*[:\-]\s*([\d.,]+(?:\s*-\s*[\d.,]+)?)\s*%?',
                rf'{element}\s+([\d.,]+(?:\s*-\s*[\d.,]+)?)\s*%?',
                rf'{element.lower()}\s*[:\-]\s*([\d.,]+(?:\s*-\s*[\d.,]+)?)\s*%?',
            ]

            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    value = match.group(1).strip()
                    # Clean value
                    value = value.replace(',', '.')
                    composition[element.lower()] = value
                    break

                if element.lower() in composition:
                    break

        return composition

    def parse_pdf_from_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Download and parse PDF from URL

        Args:
            url: URL of PDF file

        Returns:
            Dictionary with extracted data (text, composition)
        """
        # Download PDF
        pdf_path = self.download_pdf(url)
        if not pdf_path:
            return None

        try:
            # Extract text
            text = self.extract_text(pdf_path)
            if not text:
                return None

            # Extract chemical composition
            composition = self.extract_chemical_composition_regex(text)

            return {
                'text': text,
                'composition': composition,
                'source': 'pdf',
                'url': url
            }

        finally:
            # Clean up temp file
            try:
                if pdf_path and os.path.exists(pdf_path):
                    os.remove(pdf_path)
            except:
                pass

    def extract_composition_with_ai(self, text: str, openai_client) -> Optional[Dict[str, Any]]:
        """
        Extract chemical composition using OpenAI (more accurate)

        Args:
            text: PDF text content
            openai_client: OpenAI client instance

        Returns:
            Dictionary with chemical elements
        """
        try:
            # Limit text to first 3000 chars to save tokens
            text_sample = text[:3000]

            prompt = f"""Extract the chemical composition of this steel grade from the following datasheet text.
Return ONLY the chemical composition in this exact JSON format:
{{"c": "value", "cr": "value", "mo": "value", "ni": "value", "mn": "value", "si": "value", ...}}

Use lowercase element symbols. Include only elements that are explicitly mentioned.
For ranges like "0.60-0.70", keep as is. Use decimal notation (0.65 not 0,65).

Datasheet text:
{text_sample}

JSON response:"""

            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a metallurgical data extraction expert. Extract only factual data from datasheets. Never invent or estimate values."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=500
            )

            result = response.choices[0].message.content.strip()

            # Try to parse JSON
            import json
            # Remove markdown code blocks if present
            result = result.replace('```json', '').replace('```', '').strip()
            composition = json.loads(result)

            return composition

        except Exception as e:
            print(f"Error extracting composition with AI: {e}")
            return None


def find_pdf_urls_in_text(text: str) -> List[str]:
    """
    Find PDF URLs in text (e.g., from Perplexity search results)

    Args:
        text: Text to search for PDF URLs

    Returns:
        List of PDF URLs found
    """
    # Pattern for URLs ending in .pdf
    pdf_pattern = r'https?://[^\s<>"]+\.pdf'
    urls = re.findall(pdf_pattern, text, re.IGNORECASE)

    # Also look for common datasheet patterns
    datasheet_patterns = [
        r'https?://[^\s<>"]*bohler[^\s<>"]*\.pdf',
        r'https?://[^\s<>"]*uddeholm[^\s<>"]*\.pdf',
        r'https?://[^\s<>"]*voestalpine[^\s<>"]*\.pdf',
        r'https?://[^\s<>"]*datasheet[^\s<>"]*\.pdf',
    ]

    for pattern in datasheet_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        urls.extend(matches)

    # Remove duplicates
    return list(set(urls))
