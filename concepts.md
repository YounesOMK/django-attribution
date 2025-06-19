django-attribution tracks which marketing campaigns drive events. When someone visits your site from a campaign link, you capture where they came from. Later, when they perform an event, you can see which campaign deserves credit.

## Core Concepts

### Touchpoints
Marketing interactions that get tracked - visits from campaign links, ads, emails, etc. Each touchpoint captures UTM parameters, click IDs, and visit details that get analyzed when attributing events.

## Events

Events are valuable actions - purchases, signups, trials. They're linked to identities and can be attributed back to touchpoints using attribution models.

### Attribution Models
Models determine which touchpoint gets credit for an event:

- **Last-touch**: Credits the final interaction before event
- **First-touch**: Credits the initial interaction that started the journey

### Attribution Windows
Time limits for considering touchpoints. A 30-day window means only touchpoints from the last 30 days are considered when attributing an event.

### Identities
Visitor identities that link touchpoints and events together. Can be anonymous (browser-based) or authenticated (linked to Django User accounts).

### Identity Merging
When an anonymous visitor logs in, their touchpoint and event history gets merged under their authenticated identity, creating a complete customer journey.

### Event Confirmation
Events can be marked as unconfirmed (like pending payments) and updated to confirmed after verification. Only confirmed events should be used in analytics.

## UTM Parameters

Standard tracking parameters:
- utm_source (where traffic came from)
- utm_medium (marketing channel)
- utm_campaign (campaign name)
- utm_term (keywords)
- utm_content (ad content)

## Click IDs

Platform-specific tracking IDs:
- gclid (Google Ads)
- fbclid (Facebook)
- msclkid (Microsoft)
- ttclid (TikTok)
- li_fat_id (LinkedIn)
