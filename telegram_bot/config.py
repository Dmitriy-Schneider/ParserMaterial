"""Telegram bot configuration"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# ParserSteel API Configuration
API_BASE_URL = os.getenv('PARSERSTEEL_API_URL', 'http://localhost:5001')

# API Endpoints
SEARCH_ENDPOINT = f"{API_BASE_URL}/api/steels"
AI_SEARCH_ENDPOINT = f"{API_BASE_URL}/api/steels/ai-search"
STATS_ENDPOINT = f"{API_BASE_URL}/api/stats"

# Bot settings
MAX_RESULTS_PER_MESSAGE = 5
CACHE_TTL = 3600  # 1 hour
