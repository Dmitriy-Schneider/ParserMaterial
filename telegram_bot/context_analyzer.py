"""
Context Analyzer for Telegram Bot
Uses GPT-4 mini to automatically detect user intent and route to appropriate command
"""

import os
from typing import Dict, Any, Optional
from openai import OpenAI


class ContextAnalyzer:
    """Analyzes user messages to determine intent and extract parameters"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize context analyzer with OpenAI GPT-4 mini

        Args:
            api_key: OpenAI API key (if None, will try to get from environment)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = 'gpt-4o-mini'  # GPT-4 mini for fast, cheap inference
        self.enabled = bool(self.api_key)

        if not self.enabled:
            print("WARNING: Context analyzer disabled - OPENAI_API_KEY not found")

    def analyze_message(self, message_text: str) -> Dict[str, Any]:
        """
        Analyze user message to determine intent and extract parameters

        Args:
            message_text: User's message text

        Returns:
            Dictionary with:
            - intent: 'search', 'analogues', 'stats', 'help', or 'unknown'
            - grade: extracted steel grade name (if applicable)
            - confidence: confidence score 0-1
        """
        if not self.enabled:
            # Fallback to simple keyword matching
            return self._simple_analysis(message_text)

        try:
            client = OpenAI(api_key=self.api_key)

            prompt = f"""Analyze this user message and determine their intent.

User message: "{message_text}"

Possible intents:
1. "search" - user wants to search for a steel grade (by name or chemical composition)
2. "analogues" - user wants to find equivalent/analogue grades (official analogues from database)
3. "fuzzy_search" - user wants to find SIMILAR grades by chemical composition (похожая, схожая, найди похожую)
4. "compare" - user wants to compare multiple steel grades side-by-side (сравни, сравнить, compare)
5. "unknown" - cannot determine intent

For "fuzzy_search" intent, extract:
- grade: steel grade name
- tolerance: percentage value (if mentioned with %, otherwise null). Default is 50%.
- max_mismatched: number of elements allowed to exceed tolerance (if mentioned, otherwise null). Default is 3.

For "compare" intent, extract:
- grades: list of steel grade names to compare (2-5 grades)

Examples:
- "найди 420" → intent: search, grade: 420
- "аналоги D2" → intent: analogues, grade: D2
- "похожая марка HARDOX 500" → intent: fuzzy_search, grade: HARDOX 500, tolerance: null, max_mismatched: null
- "найди похожую HARDOX 500 30%" → intent: fuzzy_search, grade: HARDOX 500, tolerance: 30, max_mismatched: null
- "схожая 4140 50% 2" → intent: fuzzy_search, grade: 4140, tolerance: 50, max_mismatched: 2
- "похожие марки на D2 25% 3" → intent: fuzzy_search, grade: D2, tolerance: 25, max_mismatched: 3
- "сравни Х12МФ и D2" → intent: compare, grades: ["Х12МФ", "D2"]
- "compare 4140 with AISI 4140" → intent: compare, grades: ["4140", "AISI 4140"]
- "сравнить HARDOX 500 и AR500" → intent: compare, grades: ["HARDOX 500", "AR500"]
- "что такое Bohler K340" → intent: search, grade: Bohler K340

Return ONLY valid JSON:
{{
    "intent": "search|analogues|fuzzy_search|compare|unknown",
    "grade": "extracted grade name or null",
    "grades": ["list of grades for compare"] or null,
    "tolerance": number or null,
    "max_results": number or null,
    "confidence": 0.0-1.0
}}"""

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a smart assistant that analyzes user intent for a steel database bot. "
                                   "Return ONLY valid JSON, no explanations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=200
            )

            # Parse response
            content = response.choices[0].message.content.strip()

            # Extract JSON
            import json
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1

            if start_idx >= 0 and end_idx > start_idx:
                result = json.loads(content[start_idx:end_idx])
                return result
            else:
                print(f"Invalid JSON from GPT-4 mini: {content}")
                return self._simple_analysis(message_text)

        except Exception as e:
            print(f"Context analysis error: {e}")
            return self._simple_analysis(message_text)

    def _simple_analysis(self, message_text: str) -> Dict[str, Any]:
        """
        Fallback: simple keyword-based analysis

        Args:
            message_text: User message

        Returns:
            Analysis result
        """
        message_lower = message_text.lower().strip()

        # Check for fuzzy search keywords
        fuzzy_keywords = ['похожая', 'похожий', 'похожую', 'схожая', 'схожий', 'схожую', 'similar', 'найди похож', 'найди схож']
        if any(keyword in message_lower for keyword in fuzzy_keywords):
            # Extract grade name and parameters
            import re
            # Remove fuzzy keywords
            text = message_lower
            for keyword in fuzzy_keywords:
                text = text.replace(keyword, ' ')
            text = text.replace('марк', '').replace('на', '').strip()

            # Extract tolerance (number with %)
            tolerance = None
            tolerance_match = re.search(r'(\d+)\s*%', text)
            if tolerance_match:
                tolerance = int(tolerance_match.group(1))
                text = text.replace(tolerance_match.group(0), '').strip()

            # Extract max_mismatched (number after tolerance)
            max_mismatched = None
            numbers = re.findall(r'\b(\d+)\b', text)
            if numbers:
                max_mismatched = int(numbers[-1]) if len(numbers) > 0 else None
                # Remove the last number from text
                if max_mismatched:
                    text = re.sub(r'\b' + str(max_mismatched) + r'\b', '', text, count=1).strip()

            # Remaining text is grade name
            grade = text.strip()

            return {
                'intent': 'fuzzy_search',
                'grade': grade if grade else None,
                'tolerance': tolerance,
                'max_mismatched': max_mismatched,
                'confidence': 0.7
            }

        # Check for analogues keywords
        if any(word in message_lower for word in ['аналог', 'analogue', 'equivalent', 'эквивалент', 'замена']):
            # Extract grade name (everything after the keyword)
            for keyword in ['аналог', 'analogue', 'equivalent', 'эквивалент', 'замена']:
                if keyword in message_lower:
                    parts = message_lower.split(keyword)
                    if len(parts) > 1:
                        grade = parts[1].strip()
                        return {
                            'intent': 'analogues',
                            'grade': grade if grade else None,
                            'grades': None,
                            'tolerance': None,
                            'max_results': None,
                            'confidence': 0.6
                        }

        # Check for compare keywords
        compare_keywords = ['сравни', 'сравнить', 'compare', 'сравнение']
        if any(keyword in message_lower for keyword in compare_keywords):
            # Extract grade names (separated by "и", "with", ",", etc.)
            import re
            text = message_lower
            for keyword in compare_keywords:
                text = text.replace(keyword, ' ')

            # Split by common separators
            separators = [' и ', ' with ', ',', ' vs ', ' versus ']
            grades = [text.strip()]
            for sep in separators:
                if sep in text:
                    grades = [g.strip() for g in text.split(sep) if g.strip()]
                    break

            # Filter out empty grades
            grades = [g for g in grades if g and len(g) > 0]

            return {
                'intent': 'compare',
                'grade': None,
                'grades': grades if len(grades) >= 2 else None,
                'tolerance': None,
                'max_results': None,
                'confidence': 0.7
            }

        # Default: assume search intent
        # The message itself is likely the grade name
        return {
            'intent': 'search',
            'grade': message_text.strip(),
            'grades': None,
            'tolerance': None,
            'max_results': None,
            'confidence': 0.5
        }


# Singleton instance
_context_analyzer_instance = None


def get_context_analyzer() -> ContextAnalyzer:
    """Get or create ContextAnalyzer singleton instance"""
    global _context_analyzer_instance

    if _context_analyzer_instance is None:
        _context_analyzer_instance = ContextAnalyzer()

    return _context_analyzer_instance
