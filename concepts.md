# Core Concepts

## Attribution Tracking

Attribution tracks which marketing campaigns drive conversions. When someone visits your site from a campaign link, you capture where they came from. Later, when they convert, you can see which campaign deserves credit.

## Identity

An identity represents a visitor. It can be anonymous (tracked by browser cookie) or linked to a user account. When an anonymous visitor logs in, their touchpoint history gets merged under their user identity.

## Touchpoints

Touchpoints record each marketing interaction. They capture UTM parameters, click IDs, and visit details. These form the trail that gets analyzed when attributing conversions.

## Conversions

Conversions are valuable actions - purchases, signups, trials. They're linked to identities and can be attributed back to touchpoints using attribution models.

## Attribution Models

Models determine which touchpoint gets credit for a conversion:

- **Last-touch**: Credits the final interaction before conversion
- **First-touch**: Credits the initial interaction that started the journey

## Attribution Windows

Time limits for considering touchpoints. A 30-day window means only touchpoints from the last 30 days are considered when attributing a conversion.

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

## Confirmed vs Unconfirmed

Conversions can be marked as unconfirmed (like pending payments) and updated to confirmed after verification. Only confirmed conversions should be used in analytics.
