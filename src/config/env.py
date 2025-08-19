from src.utils.infisical import getenv_or_action, mask_string
from loguru import logger

# Log environment configuration on import
logger.info("Loading environment configuration...")

QDRANT_URL = getenv_or_action("QDRANT_URL")
logger.info(f"QDRANT_URL: {QDRANT_URL}")

COLL = getenv_or_action("COLL")
logger.info(f"COLL: {COLL}")

CRAWL_URL = getenv_or_action("CRAWL_URL")
logger.info(f"CRAWL_URL: {CRAWL_URL}")

SEARX_URL = getenv_or_action("SEARX_URL")
logger.info(f"SEARX_URL: {SEARX_URL}")

GEMINI_API_KEY = getenv_or_action("GEMINI_API_KEY")
logger.info(f"GEMINI_API_KEY: {mask_string(GEMINI_API_KEY) if GEMINI_API_KEY else 'NOT SET'}")

SECRET_KEY_SEARXNG = getenv_or_action("SECRET_KEY_SEARXNG")
logger.info(f"SECRET_KEY_SEARXNG: {mask_string(SECRET_KEY_SEARXNG) if SECRET_KEY_SEARXNG else 'NOT SET'}")

logger.info("Environment configuration loaded successfully")