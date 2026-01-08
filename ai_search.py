"""
AI-powered search module for unknown steel grades
Uses OpenAI GPT-4 to find information about steel grades not in the database
"""

import os
import json
import time
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from database_schema import get_connection

# Add utils directory to path
sys.path.append(str(Path(__file__).parent / 'utils'))

try:
    from utils.pdf_parser import PDFParser, find_pdf_urls_in_text
    PDF_PARSER_AVAILABLE = True
except ImportError:
    PDF_PARSER_AVAILABLE = False
    print("WARNING: PDF parser not available. Install pdfplumber: pip install pdfplumber PyPDF2")


class AISearch:
    """AI-powered search for steel grades using OpenAI API"""

    def __init__(self, api_key: Optional[str] = None, perplexity_key: Optional[str] = None):
        """
        Initialize AI search with OpenAI and Perplexity API keys

        Args:
            api_key: OpenAI API key (if None, will try to get from environment)
            perplexity_key: Perplexity API key (if None, will try to get from environment)
        """
        # OpenAI configuration
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4')
        self.max_tokens = int(os.getenv('OPENAI_MAX_TOKENS', '2000'))
        self.temperature = float(os.getenv('OPENAI_TEMPERATURE', '0.3'))

        # Perplexity configuration
        self.perplexity_key = perplexity_key or os.getenv('PERPLEXITY_API_KEY')
        self.perplexity_model = os.getenv('PERPLEXITY_MODEL', 'sonar-pro')

        # Common settings
        self.cache_ttl = int(os.getenv('AI_CACHE_TTL', '86400'))  # 24 hours
        self.enabled = os.getenv('ENABLE_AI_FALLBACK', 'True').lower() == 'true'

        # Check if at least one API is available
        if self.enabled and not self.api_key and not self.perplexity_key:
            print("WARNING: No AI API keys found. AI search will be disabled.")
            print("Set OPENAI_API_KEY or PERPLEXITY_API_KEY in .env file")
            self.enabled = False

        # Initialize PDF parser
        self.pdf_parser = PDFParser() if PDF_PARSER_AVAILABLE else None

    def search_steel(self, grade_name: str) -> Optional[Dict[str, Any]]:
        """
        Search for steel grade information using AI with cascade fallback:
        1. Check cache
        2. Try Perplexity (PRIORITY - internet access, more accurate)
        3. Try OpenAI GPT-4 (if Perplexity failed)

        Args:
            grade_name: Name of the steel grade to search

        Returns:
            Dictionary with steel information or None if not found
        """
        if not self.enabled:
            return None

        # Check cache first
        cached_result = self._get_from_cache(grade_name)
        if cached_result:
            return cached_result

        result = None

        # Try Perplexity FIRST (PRIORITY - has internet access)
        if self.perplexity_key:
            try:
                print(f"[Perplexity] Searching for '{grade_name}' with internet access...")
                result = self._search_with_perplexity(grade_name)
                if result:
                    result['ai_source'] = 'perplexity'
                    print(f"[Perplexity] Found result for '{grade_name}'")
            except Exception as e:
                print(f"[Perplexity] Search error for '{grade_name}': {e}")

        # If Perplexity failed or not available, try OpenAI as fallback
        if not result and self.api_key:
            try:
                print(f"[OpenAI] Fallback search for '{grade_name}'...")
                result = self._search_with_openai(grade_name)
                if result:
                    result['ai_source'] = 'openai'
                    print(f"[OpenAI] Found result for '{grade_name}'")
            except Exception as e:
                print(f"[OpenAI] Search error for '{grade_name}': {e}")

        # If nothing found, return clear message
        if not result:
            print(f"[AI Search] Марка '{grade_name}' не найдена ни в одном источнике")
            return None

        # Strict validation before caching - MANDATORY chemical composition
        is_valid = self._validate_composition(result)
        result['validated'] = is_valid

        if not is_valid:
            print(f"[REJECTED] AI result for '{grade_name}' - химический состав не найден или некорректен")
            print(f"[INFO] Марка НЕ будет добавлена в базу данных (требуется химический состав)")
            # REJECT: Do not return invalid results (no chemical composition = no add to database)
            return None
        else:
            # Only save to cache if validated
            self._save_to_cache(grade_name, result)
            print(f"[OK] Результат проверен и сохранен в кеш для '{grade_name}'")

        return result

    def _search_with_openai(self, grade_name: str) -> Optional[Dict[str, Any]]:
        """
        Search for steel using OpenAI API

        Args:
            grade_name: Steel grade name

        Returns:
            Dictionary with steel information
        """
        try:
            # Import OpenAI only when needed
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            # Create prompt
            prompt = self._create_prompt(grade_name)

            # Call OpenAI API
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert metallurgist and steel database specialist. "
                                   "Provide accurate, factual information about steel grades. "
                                   "Return information in valid JSON format only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            # Parse response
            content = response.choices[0].message.content

            # Extract JSON from response
            result = self._parse_ai_response(content, grade_name)

            return result

        except ImportError:
            print("ERROR: openai package not installed. Run: pip install openai")
            self.enabled = False
            return None
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return None

    def _search_with_perplexity(self, grade_name: str) -> Optional[Dict[str, Any]]:
        """
        Search for steel using Perplexity API (with internet access)

        Args:
            grade_name: Steel grade name

        Returns:
            Dictionary with steel information
        """
        try:
            # Import OpenAI (Perplexity uses compatible API)
            from openai import OpenAI

            # Create Perplexity client
            client = OpenAI(
                api_key=self.perplexity_key,
                base_url="https://api.perplexity.ai"
            )

            # Create prompt
            prompt = self._create_prompt(grade_name)

            # Add instruction to search the internet with strict verification
            system_message = (
                "You are an expert metallurgist and steel database specialist. "
                "CRITICAL REQUIREMENTS:\n"
                "1. Search MULTIPLE sources (manufacturer datasheets, MatWeb, steelnumber.com, standards)\n"
                "2. Cross-verify chemical composition from AT LEAST 2 different reliable sources\n"
                "3. NEVER invent, estimate or guess values - only use verified factual data\n"
                "4. If chemical composition differs between sources, use manufacturer datasheet as primary\n"
                "5. If analogues not confirmed in standards - set to null\n"
                "6. If information not found or uncertain - set 'found': false\n"
                "7. Return information in valid JSON format only.\n"
                "8. Prefer manufacturer PDF datasheets over general databases"
            )

            # Call Perplexity API
            response = client.chat.completions.create(
                model=self.perplexity_model,
                messages=[
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            # Parse response
            content = response.choices[0].message.content

            # Extract JSON from response
            result = self._parse_ai_response(content, grade_name)

            # Try to enhance with PDF data if available
            if result and self.pdf_parser:
                result = self._enhance_with_pdf(result, content, grade_name)

            return result

        except ImportError:
            print("ERROR: openai package not installed. Run: pip install openai")
            return None
        except Exception as e:
            print(f"Perplexity API error: {e}")
            return None

    def _enhance_with_pdf(self, result: Dict[str, Any], full_content: str, grade_name: str) -> Dict[str, Any]:
        """
        Enhance AI result with data from PDF datasheets

        Args:
            result: AI search result dictionary
            full_content: Full AI response text
            grade_name: Steel grade name

        Returns:
            Enhanced result dictionary
        """
        if not self.pdf_parser:
            return result

        try:
            # Check if PDF URL is in result
            pdf_url = result.get('pdf_url')

            # If not, try to find PDF URLs in the full response text
            if not pdf_url:
                pdf_urls = find_pdf_urls_in_text(full_content)
                if pdf_urls:
                    pdf_url = pdf_urls[0]  # Take first PDF

            if not pdf_url:
                return result

            print(f"Found PDF datasheet: {pdf_url}")
            print("Downloading and parsing PDF...")

            # Parse PDF
            pdf_data = self.pdf_parser.parse_pdf_from_url(pdf_url)

            if not pdf_data:
                print("Failed to parse PDF")
                return result

            # Try to extract composition using AI (more accurate)
            composition = None
            if self.api_key and 'text' in pdf_data:
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=self.api_key)
                    composition = self.pdf_parser.extract_composition_with_ai(pdf_data['text'], client)
                    if composition:
                        print("Extracted chemical composition from PDF using AI")
                except Exception as e:
                    print(f"AI extraction error: {e}")

            # Fallback to regex extraction
            if not composition and 'composition' in pdf_data:
                composition = pdf_data['composition']
                if composition:
                    print("Extracted chemical composition from PDF using regex")

            # Update result with PDF data
            if composition:
                # Update chemical elements with more accurate PDF data
                for element in ['c', 'cr', 'mo', 'v', 'w', 'co', 'ni', 'mn', 'si', 's', 'p', 'cu', 'nb', 'n', 'ti', 'al']:
                    if element in composition and composition[element]:
                        result[element] = composition[element]
                        print(f"  Updated {element.upper()}: {composition[element]}")

                # Add metadata
                result['pdf_source'] = pdf_url
                result['pdf_extracted'] = True

            return result

        except Exception as e:
            print(f"Error enhancing with PDF: {e}")
            return result

    def _validate_composition(self, result: Dict[str, Any]) -> bool:
        """
        Validate chemical composition values
        REQUIRES at least one valid chemical element to be present

        Args:
            result: AI search result

        Returns:
            True if composition is valid, False otherwise
        """
        elements = ['c', 'cr', 'mo', 'v', 'w', 'co', 'ni', 'mn', 'si', 's', 'p', 'cu', 'nb', 'n']

        valid_elements_found = 0

        for element in elements:
            value = result.get(element)
            if value is None or value == '':
                continue

            # Convert to string for validation
            value_str = str(value).strip().lower()

            # Skip if null/none/n/a
            if value_str in ['null', 'none', 'n/a', '-', '']:
                continue

            try:
                # Check if it's a range (e.g., "0.40-0.50")
                if '-' in value_str:
                    parts = value_str.replace(',', '.').split('-')
                    if len(parts) == 2:
                        min_val = float(parts[0].strip())
                        max_val = float(parts[1].strip())

                        # Validate ranges
                        if min_val > max_val:
                            print(f"Invalid range for {element}: {value} (min > max)")
                            return False

                        # Check reasonable limits
                        if element == 'c' and (max_val > 5.0 or min_val < 0):
                            print(f"Invalid carbon range: {value} (should be 0-5%)")
                            return False

                        if max_val > 100 or min_val < 0:
                            print(f"Invalid {element} range: {value} (should be 0-100%)")
                            return False

                        valid_elements_found += 1
                else:
                    # Single value
                    val = float(value_str.replace(',', '.'))

                    # Check reasonable limits
                    if element == 'c' and (val > 5.0 or val < 0):
                        print(f"Invalid carbon: {value} (should be 0-5%)")
                        return False

                    if val > 100 or val < 0:
                        print(f"Invalid {element}: {value} (should be 0-100%)")
                        return False

                    valid_elements_found += 1

            except (ValueError, AttributeError) as e:
                print(f"Cannot parse {element} value: {value}")
                return False

        # MANDATORY: At least one valid chemical element must be present
        if valid_elements_found == 0:
            print(f"VALIDATION FAILED: No valid chemical composition found")
            return False

        print(f"[OK] Found {valid_elements_found} valid chemical elements")
        return True

    def _normalize_analogues(self, analogues: Any) -> str:
        """
        Normalize analogues field

        Args:
            analogues: Analogues value from AI

        Returns:
            Normalized string or indication that none found
        """
        if analogues is None or str(analogues).strip().lower() in ['none', 'null', 'n/a', '-', '']:
            return "Аналоги не найдены (уникальная марка)"

        return str(analogues).strip()

    def _create_prompt(self, grade_name: str) -> str:
        """Create prompt for OpenAI"""
        return f"""Find detailed information about steel grade "{grade_name}".

CRITICAL INSTRUCTIONS:
1. Search multiple reliable sources (manufacturer websites, MatWeb, steelnumber.com, etc.)
2. Chemical composition is MANDATORY - if you cannot find verified chemical composition, set "found": false
3. Cross-check chemical composition from at least 2 sources if possible
4. NEVER invent or estimate values - only use data from verified sources
5. For analogues, provide only confirmed equivalents from standards (AISI, DIN, JIS, etc.)
6. If no analogues found, set analogues to null (NOT empty string)
7. Chemical composition must be realistic (C: 0-5%, other elements: 0-100%)
8. MANDATORY: Provide source URL with the following priority:
   a) If found on official manufacturer website -> provide manufacturer product page URL
   b) If found in standard document -> provide standard document URL
   c) If found in PDF datasheet -> provide PDF URL
   d) Otherwise -> provide the most reliable source URL you found
9. Include manufacturer name and country for proprietary grades

Provide the following information in JSON format:
{{
    "grade": "{grade_name}",
    "found": true/false,
    "analogues": "space-separated list of equivalent grades from different standards",
    "base": "base element (Fe, Ni, Co, or Ti)",
    "c": "carbon content range (e.g. 0.40-0.50)",
    "cr": "chromium content",
    "mo": "molybdenum content",
    "v": "vanadium content",
    "w": "tungsten content",
    "co": "cobalt content",
    "ni": "nickel content",
    "mn": "manganese content",
    "si": "silicon content",
    "s": "sulfur content (max)",
    "p": "phosphorus content (max)",
    "cu": "copper content",
    "nb": "niobium content",
    "n": "nitrogen content",
    "standard": "standard (AISI, DIN, GOST, JIS, etc.) or null if proprietary",
    "application": "typical applications",
    "properties": "key properties (hardness, corrosion resistance, etc.)",
    "manufacturer": "manufacturer name if it's a proprietary grade",
    "manufacturer_country": "manufacturer country (e.g., Австрия, США, Германия, Франция, Швеция, Япония, Россия)",
    "source_url": "MANDATORY: URL to the source (manufacturer website > standard > PDF > other reliable source)"
}}

CRITICAL REQUIREMENTS:
- If chemical composition is not found or cannot be verified, set "found": false
- source_url is MANDATORY - always provide the most reliable source URL
- For proprietary grades, include both manufacturer name and country
- Only provide factual data from reliable sources. Never invent or estimate values.

Example for proprietary grade K888:
- manufacturer: "Bohler Edelstahl"
- manufacturer_country: "Австрия"
- source_url: "https://www.bohler-edelstahl.com/en/products/k888-matrix/" or "https://www.bohler-edelstahl.com/app/uploads/sites/248/productdb/api/k888-matrix_en_gb.pdf"
"""

    def _parse_ai_response(self, content: str, grade_name: str) -> Optional[Dict[str, Any]]:
        """
        Parse OpenAI response and extract steel data

        Args:
            content: OpenAI response text
            grade_name: Original grade name

        Returns:
            Parsed steel data dictionary
        """
        try:
            # Try to find JSON in response
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                data = json.loads(json_str)

                # Validate required fields
                if not data.get('found', False):
                    return None

                # Ensure grade name is set
                data['grade'] = data.get('grade', grade_name)

                # Extract and map source_url to link field
                source_url = data.get('source_url') or data.get('pdf_url')
                if source_url and source_url not in ['null', None, '']:
                    data['link'] = source_url
                    print(f"[SOURCE] Extracted link: {source_url}")
                else:
                    print(f"[WARNING] No source URL found for '{grade_name}'")

                # Handle manufacturer country
                manufacturer = data.get('manufacturer')
                manufacturer_country = data.get('manufacturer_country')

                # If we have manufacturer and country, combine them for standard field if no standard exists
                if manufacturer and manufacturer_country:
                    # Format: "Manufacturer, Country"
                    manufacturer_info = f"{manufacturer}, {manufacturer_country}"

                    # If no standard specified, use manufacturer info as standard
                    if not data.get('standard') or data.get('standard') in ['null', None, '']:
                        data['standard'] = manufacturer_info
                        print(f"[INFO] Set standard to manufacturer info: {manufacturer_info}")

                # Normalize analogues
                if 'analogues' in data:
                    data['analogues'] = self._normalize_analogues(data['analogues'])

                # Add metadata (ai_source will be set by caller)
                data['ai_timestamp'] = datetime.now().isoformat()

                return data
            else:
                print(f"No valid JSON found in AI response for '{grade_name}'")
                return None

        except json.JSONDecodeError as e:
            print(f"Failed to parse AI response as JSON: {e}")
            print(f"Response: {content[:200]}...")
            return None

    def _get_from_cache(self, grade_name: str) -> Optional[Dict[str, Any]]:
        """
        Get cached AI search result from database

        Args:
            grade_name: Steel grade name

        Returns:
            Cached result or None
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Check if ai_searches table exists
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='ai_searches'
            """)

            if not cursor.fetchone():
                # Create table if it doesn't exist
                self._create_cache_table()

            # Get cached result
            cursor.execute("""
                SELECT result, created_at
                FROM ai_searches
                WHERE grade_name = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (grade_name,))

            row = cursor.fetchone()
            conn.close()

            if row:
                result_json, created_at = row
                created_time = datetime.fromisoformat(created_at)

                # Check if cache is still valid
                if datetime.now() - created_time < timedelta(seconds=self.cache_ttl):
                    result = json.loads(result_json)
                    result['cached'] = True
                    result['cache_age'] = (datetime.now() - created_time).total_seconds()
                    return result

            return None

        except Exception as e:
            print(f"Cache read error: {e}")
            return None

    def _save_to_cache(self, grade_name: str, result: Dict[str, Any]) -> None:
        """
        Save AI search result to cache

        Args:
            grade_name: Steel grade name
            result: Search result dictionary
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Ensure table exists
            self._create_cache_table()

            # Save result
            result_json = json.dumps(result)
            created_at = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO ai_searches (grade_name, result, created_at)
                VALUES (?, ?, ?)
            """, (grade_name, result_json, created_at))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Cache save error: {e}")

    def _create_cache_table(self) -> None:
        """Create ai_searches cache table"""
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    grade_name TEXT NOT NULL,
                    result TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_grade
                ON ai_searches(grade_name)
            """)

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Failed to create cache table: {e}")


# Singleton instance
_ai_search_instance = None


def get_ai_search() -> AISearch:
    """Get or create AISearch singleton instance"""
    global _ai_search_instance

    if _ai_search_instance is None:
        _ai_search_instance = AISearch()

    return _ai_search_instance


if __name__ == "__main__":
    # Test AI search
    print("Testing AI Search...")

    ai = AISearch()

    if not ai.enabled:
        print("AI search is disabled. Please set OPENAI_API_KEY in .env file")
    else:
        # Test with a known steel grade
        test_grade = "Bohler K340"
        print(f"\nSearching for: {test_grade}")

        result = ai.search_steel(test_grade)

        if result:
            print("\nResult:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("No result found")
