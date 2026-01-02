# Configuration file for Steel Parser
import os

# URL of the steel chart to parse
STEEL_CHART_URL = "https://zknives.com/knives/steels/steelchart.php"

# Database configuration
DB_FOLDER = "database"
DB_FILE = os.path.join(DB_FOLDER, "steel_database.db")

# Retry configuration
RETRY_COUNT = 3
REQUEST_TIMEOUT = 30
DELAY_BETWEEN_REQUESTS = 1  # seconds

