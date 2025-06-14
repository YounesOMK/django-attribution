## What It Does

Tracks which marketing campaigns (UTM parameters) bring users to your views and attributes conversions back to their source. Automatically handles anonymous → authenticated user transitions.

## Installation

```bash
pip install django-attribution
```

```python
INSTALLED_APPS = [
    'django_attribution',
]

MIDDLEWARE = [
    # ...
    # must be added after AuthenticationMiddleware
    'django_attribution.middleware.UTMParameterMiddleware',  # this is not needed for json based apis
    'django_attribution.middleware.AttributionMiddleware',
]
```

```bash
python manage.py migrate
```

## Quick Start

```python
from django_attribution.decorators import conversion_events
from django_attribution.shortcuts import record_conversion

# Multiple conversion events in one view
@conversion_events('signup', 'trial_start')
def register(request):
    user = create_user(...)
    record_conversion(request, 'signup')

    if request.POST.get('start_trial'):
        record_conversion(request, 'trial_start')
        return redirect('trial')

# Unconfirmed conversions (for async flows)
@conversion_events('purchase')
def checkout(request):
    order = create_order(...)

    record_conversion(
        request,
        'purchase',
        value=order.total,
        source_object=order,
        confirmed=False  # Confirm after payment
    )

# In payment webhook
def payment_webhook(request):
    from django_attribution.models import Conversion
    Conversion.objects.filter(
        source_object_id=order_id
    ).update(is_confirmed=True)
```

```python
# See what's working (confirmed conversions only)
from django_attribution.models import Conversion

conversions = Conversion.objects.filter(
    event='purchase',
    is_confirmed=True  # Only completed payments
).with_attribution(window_days=30)

for c in conversions:
    print(f"{c.attributed_campaign} → ${c.conversion_value}")
```

<details>
<summary><strong>How It Works</strong></summary>

1. User clicks ad: `site.com?utm_source=google&utm_campaign=summer`
2. Middleware captures UTM parameters as touchpoint
3. User converts later (can be days/weeks later)
4. Conversion is attributed to original campaign

The package uses cookies to maintain identity across sessions and automatically handles when anonymous users create accounts.
</details>

<details>
<summary><strong>Configuration</strong></summary>

```python
DJANGO_ATTRIBUTION = {
    # Cookie settings
    'COOKIE_MAX_AGE': 60 * 60 * 24 * 90,  # 90 days
    'COOKIE_DOMAIN': '.example.com',       # For subdomains

    # Bot filtering
    'FILTER_BOTS': True,

    # Exclude paths
    'UTM_EXCLUDED_URLS': ['/admin/', '/api/'],
}
```
</details>

<details>
<summary><strong>JSON API based Setup</strong></summary>

**Same domain API** (e.g., app.example.com + api.example.com):
- Skip `UTMParameterMiddleware` (it's for URL parameters)
- Create endpoint to receive UTM data
- Send `X-Attribution-Trigger: true` header to the endpoint responsible for receive UTM data
- Cookies handle identity across subdomains

**Different domains**: Not supported (cookies don't cross domains).
</details>

<details>
<summary><strong>Attribution Models</strong></summary>

```python
from django_attribution.attribution_models import first_touch, last_touch

# Last-touch (default): Credit goes to final campaign before conversion
conversions = Conversion.objects.with_attribution(model=last_touch)

# First-touch: Credit goes to first campaign that brought user
conversions = Conversion.objects.with_attribution(model=first_touch)

# with_attribution() annotates these fields:
for c in conversions:
    print(c.attributed_source)      # e.g., 'google'
    print(c.attributed_medium)      # e.g., 'cpc'
    print(c.attributed_campaign)    # e.g., 'summer_sale'
    print(c.attributed_term)        # e.g., 'running shoes'
    print(c.attributed_content)     # e.g., 'blue_banner'
    print(c.attribution_metadata)   # {'model': 'LastTouchAttributionModel', 'window_days': 30}
```

**Tip**: For pending conversions (unpaid orders, trials), use `confirmed=False` and update later via webhooks. Always filter by `is_confirmed=True` in your analytics to ensure accuracy.
</details>

<details>
<summary><strong>Limitations</strong></summary>

- **Cookie-based**: Won't work across different domains
- **UTM only**: No support for gclid, fbclid, etc for now
- **Attribution models**: Only first/last touch for now
</details>
