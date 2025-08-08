from src.utils.infisical import getenv_or_action

QDRANT_URL = getenv_or_action("QDRANT_URL")
COLL = getenv_or_action("COLL")
CRAWL_URL = getenv_or_action("CRAWL_URL")
SEARX_URL = getenv_or_action("SEARX_URL")

GEMINI_API_KEY = getenv_or_action("GEMINI_API_KEY")

SECRET_KEY_SEARXNG = getenv_or_action("SECRET_KEY_SEARXNG")