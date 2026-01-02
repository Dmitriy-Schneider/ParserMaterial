"""
AI-powered search module for unknown steel grades
Uses OpenAI GPT-4 to find information about steel grades not in the database
"""

import os
import json
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from database_schema import get_connection


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

    def search_steel(self, grade_name: str) -> Optional[Dict[str, Any]]:
        """
        Search for steel grade information using AI with cascade fallback:
        1. Check cache
        2. Try OpenAI GPT-4 (if available)
        3. Try Perplexity (if available and OpenAI failed)

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

        # Try OpenAI first (if available)
        if self.api_key:
            try:
                result = self._search_with_openai(grade_name)
                if result:
                    result['ai_source'] = 'openai'
            except Exception as e:
                print(f"OpenAI search error for '{grade_name}': {e}")

        # If OpenAI failed or not available, try Perplexity
        if not result and self.perplexity_key:
            try:
                result = self._search_with_perplexity(grade_name)
                if result:
                    result['ai_source'] = 'perplexity'
            except Exception as e:
                print(f"Perplexity search error for '{grade_name}': {e}")

        # Save to cache if found
        if result:
            self._save_to_cache(grade_name, result)

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

            # Add instruction to search the internet
            system_message = (
                "You are an expert metallurgist and steel database specialist. "
                "Search the internet for accurate, up-to-date information about the requested steel grade. "
                "Look for manufacturer specifications, datasheets, and technical documentation. "
                "Return information in valid JSON format only."
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

            return result

        except ImportError:
            print("ERROR: openai package not installed. Run: pip install openai")
            return None
        except Exception as e:
            print(f"Perplexity API error: {e}")
            return None

    def _create_prompt(self, grade_name: str) -> str:
        """Create prompt for OpenAI"""
        return f"""Find detailed information about steel grade "{grade_name}".

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
    "standard": "standard (AISI, DIN, GOST, JIS, etc.)",
    "application": "typical applications",
    "properties": "key properties (hardness, corrosion resistance, etc.)",
    "manufacturer": "manufacturer if it's a proprietary grade",
    "source": "information source"
}}

If the steel grade is not found or you're uncertain, set "found": false and provide as much information as possible.
Use null for unknown chemical elements.
Be precise with chemical composition ranges.
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
