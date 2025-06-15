## What It Does

Tracks which marketing campaigns drive conversions on your site. When someone visits from a campaign (with UTM parameters or click IDs), the package remembers where they came from. When they convert later - even weeks later - you'll know which campaign deserves credit.

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
    # After AuthenticationMiddleware:
    'django_attribution.middleware.UTMParameterMiddleware',  # Extracts UTM from URLs
    'django_attribution.middleware.AttributionMiddleware',    # Core attribution tracking
]
```

```bash
python manage.py migrate
```

## Quick Start

```python
from django_attribution.decorators import conversion_events
from django_attribution.shortcuts import record_conversion

# Single conversion event
@conversion_events('signup')
def register(request):
    user = create_user(...)
    record_conversion(request, 'signup')
    return redirect('dashboard')

# Multiple conversion events
@conversion_events('signup', 'trial_start')
def register(request):
    user = create_user(...)
    record_conversion(request, 'signup')
    
    if request.POST.get('start_trial'):
        record_conversion(request, 'trial_start')
        return redirect('trial')
    
    return redirect('dashboard')

# Unconfirmed conversions (for payment flows)
@conversion_events('purchase')
def checkout(request):
    order = create_order(...)
    
    record_conversion(
        request,
        'purchase',
        value=order.total,
        source_object=order,
        is_confirmed=False  # Confirm after payment
    )
    return redirect('payment')

# In payment webhook
def payment_webhook(request):
    from django_attribution.models import Conversion
    Conversion.objects.filter(
        source_object_id=order_id
    ).update(is_confirmed=True)
```

```python
# Get attributed conversions
from django_attribution.models import Conversion

conversions = Conversion.objects.active().confirmed().filter(
    event='purchase'
).with_attribution(window_days=30)

for c in conversions:
    print(f"{c.attributed_source} / {c.attributed_campaign} → ${c.conversion_value}")
```

<details>
<summary><strong>How It Works</strong></summary>

1. User visits: `site.com?utm_source=google&utm_campaign=summer`
2. Middleware captures UTM parameters as a touchpoint
3. Identity cookie (`_dj_attr_id`) is set to track user across sessions
4. User converts days/weeks later
5. Conversion is attributed to the original campaign

The package automatically handles identity reconciliation when anonymous users authenticate.
</details>

<details>
<summary><strong>Configuration</strong></summary>

```python
DJANGO_ATTRIBUTION = {
    # Cookie settings
    'COOKIE_NAME': '_dj_attr_id',
    'COOKIE_MAX_AGE': 60 * 60 * 24 * 90,  # 90 days
    'COOKIE_DOMAIN': '.example.com',       # For subdomains
    'COOKIE_PATH': '/',
    'COOKIE_SECURE': None,                 # Auto-detects
    'COOKIE_HTTPONLY': True,
    'COOKIE_SAMESITE': 'Lax',
    
    # Bot filtering
    'FILTER_BOTS': True,
    
    # URL exclusions
    'UTM_EXCLUDED_URLS': ['/admin/', '/api/'],
    
    # Other settings
    'CURRENCY': 'USD',
    'MAX_UTM_LENGTH': 200,
    'ATTRIBUTION_TRIGGER_HEADER': 'HTTP_X_ATTRIBUTION_TRIGGER',
    'ATTRIBUTION_TRIGGER_VALUE': 'true',
}
```
</details>

<details>
<summary><strong>JSON API Setup</strong></summary>

For decoupled architectures (separate frontend and backend API):

1. Skip `UTMParameterMiddleware` - it only extracts from URL query parameters
2. Keep `AttributionMiddleware` for identity management
3. Create an endpoint that receives tracking parameters and creates touchpoints
4. Frontend extracts UTM parameters from the URL and sends them to your endpoint
5. Include the `X-Attribution-Trigger: true` header in the request

**Important**: This only works when frontend and backend share the same domain (or subdomains). Cross-domain tracking isn't supported due to cookie restrictions.
</details>

<details>
<summary><strong>Attribution Models</strong></summary>

```python
from django_attribution.attribution_models import first_touch, last_touch

# Last-touch attribution (default)
# Credit goes to the last campaign before conversion
conversions = Conversion.objects.active().confirmed().with_attribution(
    model=last_touch,
    window_days=30
)

# First-touch attribution
# Credit goes to the first campaign that brought the user
conversions = Conversion.objects.active().confirmed().with_attribution(
    model=first_touch,
    window_days=90
)

# Attributed fields:
# - attributed_source
# - attributed_medium
# - attributed_campaign
# - attributed_term
# - attributed_content
# - attribution_metadata
```
</details>

<details>
<summary><strong>Tracked Parameters</strong></summary>

UTM parameters:
- utm_source
- utm_medium
- utm_campaign
- utm_term
- utm_content

Click IDs:
- gclid (Google Ads)
- fbclid (Facebook)
- msclkid (Microsoft Ads)
- ttclid (TikTok)
- li_fat_id (LinkedIn)
- twclid (Twitter)
- igshid (Instagram)
</details>

<details>
<summary><strong>Best Practices</strong></summary>

**Always declare conversion events**  
Use the `@conversion_events` decorator to explicitly declare which events a view can track. This prevents accidental tracking.

**Handle payment flows properly**  
Use `is_confirmed=False` for pending payments. Update to `is_confirmed=True` only after payment confirmation.

**Filter analytics queries**  
Always use `.confirmed()` when analyzing conversion data to exclude unconfirmed conversions.

**Configure for subdomains**  
Set `COOKIE_DOMAIN = '.yourdomain.com'` if you use multiple subdomains.

**Test tracking**  
Add `?utm_source=test&utm_campaign=test` to URLs during development. Check for the `_dj_attr_id` cookie in browser DevTools.
</details>

<details>
<summary><strong>Limitations</strong></summary>

- **Cookie-dependent**: Doesn't work if users block cookies
- **Same-origin only**: No cross-domain tracking support
- **Basic attribution models**: Only first-touch and last-touch currently available
- **No impression tracking**: Only tracks clicks with UTM parameters or click IDs
</details>
