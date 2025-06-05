DEFAULT_UTM_PARAMETERS = [
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
]

DEFAULT_MAX_UTM_LENGTH = 200

DEFAULT_FILTER_BOTS = True

DEFAULT_BOT_PATTERNS = [
    # Generic patterns
    "bot",
    "crawler",
    "spider",
    "scraper",
    "robot",
    # Social media crawlers
    "facebookexternalhit",
    "facebookcatalog",
    "facebookbot",
    "twitterbot",
    "linkedinbot",
    "slackbot",
    "whatsapp",
    "telegrambot",
    "skypeuripreview",
    # Search engines
    "googlebot",
    "bingbot",
    "yandexbot",
    "duckduckbot",
    "baiduspider",
    "sogou",
    # SEO/Analytics tools
    "ahrefsbot",
    "semrushbot",
    "mj12bot",
    "dotbot",
    "screamingfrogseospider",
    "siteauditbot",
    # Other common crawlers
    "applebot",
    "pinterestbot",
    "redditbot",
    "ia_archiver",
]

DEFAULT_LOG_VALIDATION_ERRORS = True

DEFAULT_DJANGO_ATTRIBUTION_CURRENCY = "EUR"


DEFAULT_EXCLUDED_URLS = [
    "/admin/",
    "/api/",
    "/health/",
]

DEFAULT_WINDOW_DAYS = 30


DEFAULT_ATTRIBUTION_COOKIE_NAME = "_dj_attr_id"
DEFAULT_ATTRIBUTION_COOKIE_MAX_AGE = 60 * 60 * 24 * 90  # 90 days
DEFAULT_ATTRIBUTION_COOKIE_DOMAIN = None
DEFAULT_ATTRIBUTION_COOKIE_PATH = "/"
DEFAULT_ATTRIBUTION_COOKIE_SECURE = None  # Auto-detect
DEFAULT_ATTRIBUTION_COOKIE_HTTPONLY = True
DEFAULT_ATTRIBUTION_COOKIE_SAMESITE = "Lax"
