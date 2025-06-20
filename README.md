# django-attribution

Track UTM parameters and marketing campaigns to identify which sources drive conversions and revenue.


# Core Concepts

<details>
<summary><strong>Identity</strong></summary>

An identity represents a visitor who came to your site from a trackable marketing source.

An identity can be:
- Browsing without logging in (tracked by cookie)
- Linked to a logged-in user account
- Merged when an anonymous visitor logs in (their history gets consolidated with their user account)
</details>

<details>
<summary><strong>Touchpoint</strong></summary>

A touchpoint captures where someone came from when they visit your site with tracking data.

Includes:
- UTM parameters (`utm_source=google`, `utm_campaign=summer_sale`)  
- Click IDs (`gclid`, `fbclid`, etc.)
- URL they landed on and referrer
</details>

<details>
<summary><strong>Conversion</strong></summary>

A conversion is when someone does something valuable - signs up, makes a purchase, starts a trial.

- Links to the identity who converted
- Can have a monetary value and currency
- Can be marked as confirmed/unconfirmed (useful for pending payments)
- Gets attributed back to touchpoints to see which campaigns drove results
</details>

## Installation

```bash
pip install django-attribution
```

## Middleware Configuration

Add these middlewares to your Django `MIDDLEWARE` setting:

```python
MIDDLEWARE = [
    # ... other middlewares ...
    "django_attribution.middlewares.TrackingParameterMiddleware",
    "django_attribution.middlewares.AttributionMiddleware",
    # ... other middlewares ...
]
```

**Note:** You can skip `TrackingParameterMiddleware` if your Django app is a JSON-based API with a separate frontend



## Usage

### Recording Conversions

```python
from django_attribution.shortcuts import record_conversion

# Simple conversion
def signup_view(request):
    # ... signup logic ...
    record_conversion(request, 'signup')

# Async flow with confirmation
def order_view(request):
    # ... order processing ...
    order = Order.objects.create(total=99.99)
    
    record_conversion(
        request, 
        'order_placed', 
        value=order.total,
        source_object=order,  # Link to order for later reference
        is_confirmed=False
    )

# Later, in payment confirmation view:
def payment_webhook(request):
    # ... payment processing ...
    order = Order.objects.get(id=order_id)
    
    # Find and confirm the conversion
    conversion = Conversion.objects.get(
        source_content_type=ContentType.objects.get_for_model(Order),
        source_object_id=order.id,
        event='order_placed'
    )
    conversion.is_confirmed = True
    conversion.save()
```

### Event Restrictions

Use decorators or mixins to enforce allowed events. This prevents typos and ensures consistency:

```python
from django_attribution.decorators import conversion_events
from django_attribution.mixins import ConversionEventsMixin

# Function-based view
@conversion_events('signup', 'purchase')
def my_view(request):
    record_conversion(request, 'signup')  # Allowed
    record_conversion(request, 'purchase')  # Allowed
    record_conversion(request, 'newsletter')  # Raises ValueError

# Class-based view
class CheckoutView(ConversionEventsMixin, View):
    conversion_events = ['purchase']
    
    def post(self, request):
        record_conversion(request, 'purchase')  # Allowed
        record_conversion(request, 'signup')  # Raises ValueError
```

### Available Parameters

The `record_conversion` function accepts:

- `request`: Django request object (required)
- `event_type`: Conversion event name (required) 
- `value`: Monetary value (optional)
- `currency`: Currency code (optional, defaults to settings)
- `custom_data`: Additional metadata (optional)
- `source_object`: Related model instance (optional)
- `is_confirmed`: Whether confirmed (optional, defaults to True)

## Attribution Analysis

See which campaigns drove your conversions:

```python
from django_attribution.models import Conversion
from django_attribution.attribution_models import first_touch, last_touch

# Last-touch attribution (most recent campaign gets credit)
conversions = Conversion.objects.valid().with_attribution(last_touch) # .valid() = is_active + is_confrimed

for conversion in conversions:
    print(f"Conversion: {conversion.event}")
    print(f"Source: {conversion.attribution_data.get('utm_source')}")
    print(f"Campaign: {conversion.attribution_data.get('utm_campaign')}")

# First-touch attribution (first campaign gets credit)
conversions = Conversion.objects.valid().with_attribution(first_touch)

# Custom attribution window (default is 30 days)
conversions = Conversion.objects.valid().with_attribution(last_touch, window_days=7)

# Different windows per source
source_windows = {
    'google': 14,
    'email': 7,
}

conversions = Conversion.objects.with_attribution(
    last_touch, 
    window_days=30,  # default window
    source_windows=source_windows
)
```

## Configuration

Optional settings to customize behavior in your Django `settings.py`:

```python
DJANGO_ATTRIBUTION = {
    "CURRENCY": "USD",
    
    # Cookie settings
    "COOKIE_MAX_AGE": 60 * 60 * 24 * 90,  # 90 days
    "COOKIE_NAME": "_dj_attr_id",
    
    "FILTER_BOTS": True,
    
    # Skip tracking utm params on these URLs
    "UTM_EXCLUDED_URLS": [
        "/admin/",
        "/api/",
    ],
    
    # Max length for UTM parameters
    "MAX_UTM_LENGTH": 200,
}
