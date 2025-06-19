TRACKING_PARAMETERS = [
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "msclkid",
    "ttclid",
    "li_fat_id",
    "twclid",
    "igshid",
]

DEFAULTS = {
    "MAX_UTM_LENGTH": 200,
    # Bot Filtering Configuration
    "FILTER_BOTS": True,
    "BOT_PATTERNS": [
        "bot",
        "crawler",
        "spider",
        "scraper",
        "robot",
        "facebookexternalhit",
        "facebookcatalog",
        "facebookbot",
        "twitterbot",
        "linkedinbot",
        "slackbot",
        "whatsapp",
        "telegrambot",
        "skypeuripreview",
        "googlebot",
        "bingbot",
        "yandexbot",
        "duckduckbot",
        "baiduspider",
        "sogou",
        "ahrefsbot",
        "semrushbot",
        "mj12bot",
        "dotbot",
        "screamingfrogseospider",
        "siteauditbot",
        "applebot",
        "pinterestbot",
        "redditbot",
        "ia_archiver",
    ],
    # Currency
    "CURRENCY": "EUR",
    # URL Exclusion Configuration
    "UTM_EXCLUDED_URLS": [
        "/admin/",
        "/api/",
    ],
    # Attribution Cookie Configuration
    "COOKIE_NAME": "_dj_attr_id",
    "COOKIE_MAX_AGE": 60 * 60 * 24 * 90,  # 90 days
    "COOKIE_DOMAIN": None,
    "COOKIE_PATH": "/",
    "COOKIE_SECURE": None,  # Auto-detect
    "COOKIE_HTTPONLY": True,
    "COOKIE_SAMESITE": "Lax",
    # Attribution Trigger Configuration
    "ATTRIBUTION_TRIGGER_HEADER": "HTTP_X_ATTRIBUTION_TRIGGER",
}
