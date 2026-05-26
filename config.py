"""Server configuration loaded from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()

API_TOKEN: str = os.environ.get("CLICKUP_API_TOKEN", "")
TEAM_ID: str = os.environ.get("CLICKUP_TEAM_ID", "")
BASE_URL: str = "https://api.clickup.com/api/v2"
CACHE_TTL: int = int(os.environ.get("CACHE_TTL_SECONDS", "300"))

if not API_TOKEN:
    raise ValueError("CLICKUP_API_TOKEN environment variable is required")
if not TEAM_ID:
    raise ValueError("CLICKUP_TEAM_ID environment variable is required")
