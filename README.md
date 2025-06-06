# django-attribution

# Core Concepts

## Identity
A unique identifier for each visitor. Gets created when someone first clicks a UTM link to your site. The same real person might end up with multiple identities (different browsers, cleared cookies, mobile vs desktop). When someone logs in, the system can connect these separate identities together so you get the full picture of their journey across all their devices and sessions.

## Touchpoint
Records when someone visits a page WITH UTM parameters. Saves all the campaign info (utm_source=facebook, utm_medium=cpc, etc.) plus the URL they visited and when.
