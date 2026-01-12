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
        self.cache_ttl = int(os.getenv('AI_CACHE_TTL', '604800'))  # 7 days (was 24 hours)
        self.enabled = os.getenv('ENABLE_AI_FALLBACK', 'True').lower() == 'true'

        # Check if Perplexity API is available (OpenAI removed for accuracy)
        if self.enabled and not self.perplexity_key:
            print("WARNING: Perplexity API key not found. AI search will be disabled.")
            print("Set PERPLEXITY_API_KEY in .env file")
            print("Note: OpenAI fallback removed to ensure 100% accuracy")
            self.enabled = False

        # Initialize PDF parser
        self.pdf_parser = PDFParser() if PDF_PARSER_AVAILABLE else None

    def search_steel(self, grade_name: str) -> Optional[Dict[str, Any]]:
        """
        Search for steel grade information using Perplexity AI ONLY.
        OpenAI removed as fallback to ensure 100% accuracy.

        Workflow:
        1. Check cache
        2. Try Perplexity (ONLY source - internet access, accurate)
        3. If not found - return None (better than false information)

        Args:
            grade_name: Name of the steel grade to search

        Returns:
            Dictionary with steel information or None if not found
        """
        if not self.enabled:
            return None

        # CACHE DISABLED - always fetch fresh results to avoid storing incorrect data
        # cached_result = self._get_from_cache(grade_name)
        # if cached_result:
        #     print(f"[CACHE] Found cached result for '{grade_name}' (age: {cached_result.get('cache_age', 0):.0f}s)")
        #     return cached_result

        result = None

        # Try Perplexity ONLY (no fallback to OpenAI for 100% accuracy)
        if self.perplexity_key:
            try:
                print(f"[Perplexity] Searching for '{grade_name}' with internet access...")
                result = self._search_with_perplexity(grade_name)
                if result:
                    result['ai_source'] = 'perplexity'
                    print(f"[Perplexity] Found result for '{grade_name}'")
            except Exception as e:
                print(f"[Perplexity] Search error for '{grade_name}': {e}")
        else:
            print(f"[WARNING] Perplexity API key not configured. AI search disabled.")

        # If nothing found, return None (no false information)
        if not result:
            print(f"[AI Search] Марка '{grade_name}' не найдена через Perplexity")
            print(f"[INFO] OpenAI fallback отключен для обеспечения достоверности на 100%")
            return None

        # Validation (SOFTENED: allow partial data with warning)
        is_valid = self._validate_composition(result)
        result['validated'] = is_valid

        # Calculate confidence score based on multiple factors
        confidence_score = self._calculate_confidence_score(result, is_valid)
        result['confidence'] = confidence_score['level']  # high, medium, or low
        result['confidence_score'] = confidence_score['score']  # 0-100
        result['confidence_reasons'] = confidence_score['reasons']

        if not is_valid:
            print(f"[WARNING] AI result for '{grade_name}' - неполный химический состав")
            print(f"[INFO] Confidence: {confidence_score['level']} ({confidence_score['score']}/100)")
            # SOFTENED: Return result with warning instead of rejecting completely
            result['warning'] = 'Неполные данные по химическому составу'
        else:
            print(f"[OK] Найдено {result.get('_valid_elements_count', 0)} валидных элементов")
            print(f"[INFO] Confidence: {confidence_score['level']} ({confidence_score['score']}/100)")

        # CACHE DISABLED - do not save AI results to avoid storing incorrect data
        # self._save_to_cache(grade_name, result)
        # print(f"[CACHE] Результат сохранен в кэш на 7 дней")

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
                "CRITICAL REQUIREMENTS:\n\n"
                "SOURCE PRIORITY (highest to lowest):\n"
                "1. TIER 1 (HIGHEST): Official manufacturer PDF datasheets (e.g., Bohler, SSAB, Hardox)\n"
                "2. TIER 2: International standards documents (AISI, DIN, EN, GOST, JIS, GB)\n"
                "3. TIER 3: Professional databases (MatWeb.com, steelnumber.com, key-to-steel.com)\n"
                "4. TIER 4 (LOWEST): General websites (Wikipedia, forums, blogs) - DO NOT USE for chemical composition\n\n"
                "VERIFICATION PROTOCOL:\n"
                "1. Search MULTIPLE sources (minimum 2-3 different sources)\n"
                "2. Cross-verify chemical composition from AT LEAST 2 reliable sources (Tier 1-3)\n"
                "3. NEVER invent, estimate, or guess values - only use verified factual data\n"
                "4. If chemical composition differs between sources:\n"
                "   a) Prefer manufacturer datasheet (Tier 1)\n"
                "   b) Then prefer standards (Tier 2)\n"
                "   c) Then professional databases (Tier 3)\n"
                "5. If you cannot find data in Tier 1-3 sources, set partial fields to null (don't use Tier 4)\n"
                "6. If analogues not confirmed in standards/manufacturer docs - set to null\n"
                "7. If information not found or uncertain - indicate in confidence level\n"
                "8. Return information in valid JSON format only\n\n"
                "SOURCE_URL CRITICAL REQUIREMENTS:\n"
                "- source_url MUST point to the page/PDF that contains CHEMICAL COMPOSITION\n"
                "- For manufacturer grades: Link to product datasheet page or direct PDF with composition\n"
                "- For standards: Link to standard document or official database entry\n"
                "- NEVER link to: welding materials, accessories, processing guides, certificates\n"
                "- VERIFY the URL actually contains chemical composition data before including it\n"
                "- Examples of CORRECT URLs:\n"
                "  ✓ https://www.ssab.com/brands-and-products/hardox/hardox-400 (product page with composition)\n"
                "  ✓ https://www.ssab.com/.../hardox-400-datasheet.pdf (direct datasheet PDF)\n"
                "  ✓ https://www.matweb.com/search/DataSheet.aspx?MatGUID=... (database entry)\n"
                "- Examples of WRONG URLs:\n"
                "  ✗ https://www.ssab.com/welding/hardox-400-welding-consumables (welding materials)\n"
                "  ✗ https://www.ssab.com/processing/hardox-400-cutting (processing guide)\n"
                "  ✗ https://www.ssab.com/certificates/hardox-400 (certificates, not composition)"
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

            # ENABLED: Enhanced PDF parsing with "Typical Composition" targeting
            # Now searches for "Typical Composition" table specifically
            # Validates values before replacing Perplexity data
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

            # Update result with PDF data (with validation)
            if composition:
                # Define realistic limits for each element
                element_limits = {
                    'c': (0, 5.0),      # Carbon: 0-5%
                    'n': (0, 1.0),      # Nitrogen: 0-1%
                    's': (0, 0.5),      # Sulfur: max 0.5%
                    'p': (0, 0.5),      # Phosphorus: max 0.5%
                    'cr': (0, 35),      # Chromium: 0-35%
                    'ni': (0, 30),      # Nickel: 0-30%
                    'mo': (0, 15),      # Molybdenum: 0-15%
                    'v': (0, 10),       # Vanadium: 0-10%
                    'w': (0, 20),       # Tungsten: 0-20%
                    'co': (0, 20),      # Cobalt: 0-20%
                }

                # Validate and update chemical elements
                updated_count = 0
                rejected_count = 0

                for element in ['c', 'cr', 'mo', 'v', 'w', 'co', 'ni', 'mn', 'si', 's', 'p', 'cu', 'nb', 'n', 'ti', 'al']:
                    if element in composition and composition[element]:
                        value_str = str(composition[element]).strip()

                        # Validate value
                        try:
                            # Handle ranges (take midpoint for validation)
                            if '-' in value_str:
                                parts = value_str.split('-')
                                val = (float(parts[0]) + float(parts[1])) / 2
                            else:
                                val = float(value_str.replace(',', '.'))

                            # Check against limits
                            min_limit, max_limit = element_limits.get(element, (0, 100))

                            if min_limit <= val <= max_limit:
                                # Value is valid - update
                                result[element] = composition[element]
                                print(f"  ✓ Updated {element.upper()}: {composition[element]} (validated)")
                                updated_count += 1
                            else:
                                # Value is suspicious - reject
                                print(f"  ✗ REJECTED {element.upper()}: {composition[element]} (outside {min_limit}-{max_limit}%, likely wrong units)")
                                rejected_count += 1

                        except (ValueError, TypeError) as e:
                            print(f"  ✗ REJECTED {element.upper()}: {composition[element]} (cannot parse)")
                            rejected_count += 1

                if updated_count > 0:
                    # Add metadata
                    result['pdf_source'] = pdf_url
                    result['pdf_extracted'] = True
                    print(f"PDF enhancement: {updated_count} values updated, {rejected_count} rejected")
                else:
                    print(f"PDF enhancement: All {rejected_count} values rejected (suspicious), keeping Perplexity data")

            return result

        except Exception as e:
            print(f"Error enhancing with PDF: {e}")
            return result

    def _calculate_confidence_score(self, result: Dict[str, Any], has_valid_composition: bool) -> Dict[str, Any]:
        """
        Calculate confidence score based on multiple factors

        Args:
            result: AI search result
            has_valid_composition: Whether composition validation passed

        Returns:
            Dictionary with level (high/medium/low), score (0-100), and reasons
        """
        score = 0
        reasons = []

        # Factor 1: Source tier (40 points max)
        source_tier = result.get('source_tier', '').lower()
        if source_tier == 'tier1':
            score += 40
            reasons.append('Tier 1 source (manufacturer datasheet)')
        elif source_tier == 'tier2':
            score += 30
            reasons.append('Tier 2 source (standards document)')
        elif source_tier == 'tier3':
            score += 20
            reasons.append('Tier 3 source (professional database)')
        else:
            # Try to infer tier from source_url
            source_url = result.get('source_url', '').lower()
            if any(x in source_url for x in ['.pdf', 'datasheet', 'bohler', 'ssab', 'hardox', 'ovako']):
                score += 35
                reasons.append('Tier 1 source inferred (manufacturer PDF)')
            elif any(x in source_url for x in ['standard', 'din', 'aisi', 'gost', 'jis', 'en10']):
                score += 25
                reasons.append('Tier 2 source inferred (standards)')
            elif any(x in source_url for x in ['matweb.com', 'steelnumber.com', 'key-to-steel']):
                score += 15
                reasons.append('Tier 3 source inferred (database)')
            else:
                reasons.append('Unknown source tier')

        # Factor 2: Verification sources (30 points max)
        verification_sources = result.get('verification_sources', [])
        if isinstance(verification_sources, list):
            source_count = len(verification_sources)
            if source_count >= 3:
                score += 30
                reasons.append(f'Cross-verified from {source_count} sources')
            elif source_count == 2:
                score += 20
                reasons.append('Verified from 2 sources')
            elif source_count == 1:
                score += 10
                reasons.append('Single source verification')

        # Factor 3: Chemical composition completeness (30 points max)
        if has_valid_composition:
            valid_count = result.get('_valid_elements_count', 0)
            if valid_count >= 7:
                score += 30
                reasons.append(f'{valid_count} chemical elements found')
            elif valid_count >= 4:
                score += 20
                reasons.append(f'{valid_count} chemical elements found')
            elif valid_count >= 1:
                score += 10
                reasons.append(f'{valid_count} chemical elements found')
        else:
            reasons.append('No valid chemical composition')

        # Determine level
        if score >= 75:
            level = 'high'
        elif score >= 45:
            level = 'medium'
        else:
            level = 'low'

        return {
            'level': level,
            'score': min(score, 100),
            'reasons': reasons
        }

    def _validate_composition(self, result: Dict[str, Any]) -> bool:
        """
        Validate chemical composition values
        SOFTENED: Allows results with partial or no composition (with warning)

        Args:
            result: AI search result

        Returns:
            True if composition is valid (at least 1 element), False if no valid elements
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
                            print(f"[WARNING] Invalid range for {element}: {value} (min > max) - skipping")
                            continue

                        # Check element-specific realistic limits
                        element_limits = {
                            'c': (0, 5.0),      # Carbon: 0-5%
                            'n': (0, 1.0),      # Nitrogen: 0-1% (NOT 200%!)
                            's': (0, 0.5),      # Sulfur: max 0.5%
                            'p': (0, 0.5),      # Phosphorus: max 0.5%
                            'cr': (0, 35),      # Chromium: 0-35%
                            'ni': (0, 30),      # Nickel: 0-30%
                            'mo': (0, 15),      # Molybdenum: 0-15%
                            'v': (0, 10),       # Vanadium: 0-10%
                            'w': (0, 20),       # Tungsten: 0-20%
                            'co': (0, 20),      # Cobalt: 0-20%
                        }

                        min_limit, max_limit = element_limits.get(element, (0, 100))

                        if max_val > max_limit or min_val < min_limit:
                            print(f"[WARNING] Suspicious {element} range: {value} (should be {min_limit}-{max_limit}%) - likely wrong units (ppm vs %)")
                            continue

                        valid_elements_found += 1
                else:
                    # Single value
                    val = float(value_str.replace(',', '.'))

                    # Check element-specific realistic limits (same as for ranges)
                    element_limits = {
                        'c': (0, 5.0),      # Carbon: 0-5%
                        'n': (0, 1.0),      # Nitrogen: 0-1% (NOT 200%!)
                        's': (0, 0.5),      # Sulfur: max 0.5%
                        'p': (0, 0.5),      # Phosphorus: max 0.5%
                        'cr': (0, 35),      # Chromium: 0-35%
                        'ni': (0, 30),      # Nickel: 0-30%
                        'mo': (0, 15),      # Molybdenum: 0-15%
                        'v': (0, 10),       # Vanadium: 0-10%
                        'w': (0, 20),       # Tungsten: 0-20%
                        'co': (0, 20),      # Cobalt: 0-20%
                    }

                    min_limit, max_limit = element_limits.get(element, (0, 100))

                    if val > max_limit or val < min_limit:
                        print(f"[WARNING] Suspicious {element}: {value} (should be {min_limit}-{max_limit}%) - likely wrong units (ppm vs %)")
                        continue

                    valid_elements_found += 1

            except (ValueError, AttributeError) as e:
                print(f"[WARNING] Cannot parse {element} value: {value} - skipping")
                continue

        # Store count for reporting
        result['_valid_elements_count'] = valid_elements_found

        # SOFTENED: At least one valid chemical element recommended but not mandatory
        if valid_elements_found == 0:
            print(f"[WARNING] No valid chemical composition found - result will be marked as low confidence")
            return False

        print(f"[OK] Found {valid_elements_found} valid chemical elements")
        return True

    def _clean_citation_references(self, text: str) -> str:
        """
        Remove citation references like [1], [2], [3] from text

        Args:
            text: Text with potential citation references

        Returns:
            Cleaned text without references
        """
        if not text or text in ['null', None, '']:
            return text

        import re
        # Remove patterns like [1], [2], [3], [1][2], etc.
        cleaned = re.sub(r'\[\d+\]', '', str(text))
        # Remove multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        # Remove trailing/leading spaces
        return cleaned.strip()

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

        return self._clean_citation_references(str(analogues).strip())

    def _create_prompt(self, grade_name: str) -> str:
        """Create prompt for AI with enhanced confidence tracking"""
        return f"""Find detailed information about steel grade "{grade_name}".

CRITICAL INSTRUCTIONS:
1. Search multiple reliable sources (manufacturer websites, MatWeb, steelnumber.com, etc.)
2. Chemical composition is MANDATORY - if you cannot find verified chemical composition, set "found": false
3. Cross-check chemical composition from at least 2 sources if possible
4. NEVER invent or estimate values - only use data from verified sources
5. For analogues, provide only confirmed equivalents from standards (AISI, DIN, JIS, etc.)
6. If no analogues found, set analogues to null (NOT empty string)
7. Chemical composition must be realistic (C: 0-5%, other elements: 0-100%)
8. CRITICAL: All composition values must be in PERCENT (%), NOT ppm or mg/kg
9. CRITICAL: Verify units before extracting - common errors:
   - 0.30% is CORRECT (not 30% or 300 ppm)
   - 0.002% is CORRECT (not 2% or 200% or 20 ppm)
   - Typical ranges: C: 0.01-3.0%, Cr: 0.1-30%, Ni: 0.1-25%, Mo: 0.1-10%, V: 0.01-5%, N: 0.001-0.5%
   - If you see C > 5% or N > 1% - you likely misinterpreted units (check if it's ppm/mg/kg, not %)
10. Include manufacturer name and country for proprietary grades
11. IMPORTANT: Provide "application" and "properties" fields in RUSSIAN language (На русском языке)
12. Do NOT include citation references like [1], [2], [3] in your response - provide clean text only

SOURCE_URL REQUIREMENTS (VERY IMPORTANT):
13. source_url MUST be the EXACT page (HTML or PDF) where you FOUND THE CHEMICAL COMPOSITION
14. Acceptable: manufacturer datasheet PDF, product HTML page with composition table, database entry
15. NOT acceptable: welding materials, processing guides, certificates, accessories, general info pages
16. VERIFY the URL you provide actually shows chemical composition when opened
17. If multiple URLs have composition, choose: manufacturer datasheet PDF > product page HTML > database
18. Provide source_tier (tier1/tier2/tier3) and verification_sources array for transparency

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
    "application": "typical applications IN RUSSIAN (e.g., Износостойкие детали горнодобывающего оборудования, ковши экскаваторов, кузова самосвалов)",
    "properties": "key properties IN RUSSIAN (e.g., Низкоуглеродистая сталь с твердостью около 500 HBW; изгибаемая и свариваемая; высокая износостойкость)",
    "manufacturer": "manufacturer name if it's a proprietary grade",
    "manufacturer_country": "manufacturer country (e.g., Австрия, США, Германия, Франция, Швеция, Япония, Россия)",
    "source_url": "MANDATORY: URL to the source (manufacturer website > standard > PDF > other reliable source)",
    "source_tier": "tier level of primary source: tier1|tier2|tier3 (tier1=manufacturer PDF, tier2=standards, tier3=databases)",
    "verification_sources": [
        {{"url": "source1_url", "type": "manufacturer_pdf|standard|database", "verified_fields": ["c", "cr", "mo"]}},
        {{"url": "source2_url", "type": "manufacturer_pdf|standard|database", "verified_fields": ["c", "cr", "ni"]}}
    ]
}}

CRITICAL REQUIREMENTS:
- If chemical composition is not found or cannot be verified, set "found": false
- source_url is MANDATORY - always provide URL to the page/PDF with CHEMICAL COMPOSITION
- source_tier is MANDATORY - indicate tier1/tier2/tier3 based on source quality
- verification_sources is OPTIONAL but RECOMMENDED - list all sources used for cross-verification
- For proprietary grades, include both manufacturer name and country
- Only provide factual data from reliable sources. Never invent or estimate values
- application and properties MUST be in RUSSIAN language
- Do NOT include citation references [1], [2], [3] etc. - clean text only

Examples of CORRECT source_url (page/PDF with composition):
✓ "https://www.ssab.com/en/brands-and-products/hardox/hardox-400" (product page with composition table)
✓ "https://www.ssab.com/.../hardox-400-datasheet.pdf" (direct PDF with composition)
✓ "https://www.bohler-edelstahl.com/en/products/k888-matrix/" (product page with composition)
✓ "https://www.matweb.com/search/DataSheet.aspx?MatGUID=..." (database with composition)

Examples of WRONG source_url (no composition on these pages):
✗ "https://www.ssab.com/welding/hardox-400-consumables" (welding materials, not steel composition)
✗ "https://www.ssab.com/processing/hardox-400-cutting" (processing guide, not composition)
✗ "https://www.ssab.com/certificates" (certificates, not datasheet)

Example result for proprietary grade K888:
- manufacturer: "Bohler Edelstahl"
- manufacturer_country: "Австрия"
- application: "Износостойкие детали для горнодобывающей промышленности, металлургии, переработки отходов"
- properties: "Мартенситная износостойкая сталь с высокой твердостью и хорошей свариваемостью"
- source_url: "https://www.bohler-edelstahl.com/en/products/k888-matrix/" (page with composition table)
- source_tier: "tier1"
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

                # Clean citation references from text fields
                if 'application' in data and data['application']:
                    data['application'] = self._clean_citation_references(data['application'])
                if 'properties' in data and data['properties']:
                    data['properties'] = self._clean_citation_references(data['properties'])
                if 'standard' in data and data['standard']:
                    data['standard'] = self._clean_citation_references(data['standard'])

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
