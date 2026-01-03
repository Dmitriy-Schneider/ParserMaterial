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
2. "analogues" - user wants to find equivalent/analogue grades
3. "stats" - user wants database statistics
4. "help" - user needs help or unclear request
5. "unknown" - cannot determine intent

If intent is "search" or "analogues", extract the steel grade name mentioned.

Examples:
- "найди 420" → intent: search, grade: 420
- "аналоги D2" → intent: analogues, grade: D2
- "что такое Bohler K340" → intent: search, grade: Bohler K340
- "сколько марок в базе" → intent: stats
- "помощь" → intent: help
- "хим состав 1.2379" → intent: search, grade: 1.2379

Return ONLY valid JSON:
{{
    "intent": "search|analogues|stats|help|unknown",
    "grade": "extracted grade name or null",
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

        # Check for stats keywords
        if any(word in message_lower for word in ['статистика', 'stats', 'сколько', 'количество', 'count']):
            return {
                'intent': 'stats',
                'grade': None,
                'confidence': 0.8
            }

        # Check for help keywords
        if any(word in message_lower for word in ['помощь', 'help', 'как', 'что делать', 'команды']):
            return {
                'intent': 'help',
                'grade': None,
                'confidence': 0.8
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
                            'confidence': 0.6
                        }

        # Default: assume search intent
        # The message itself is likely the grade name
        return {
            'intent': 'search',
            'grade': message_text.strip(),
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
