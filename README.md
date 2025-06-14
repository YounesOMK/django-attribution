# Django Attribution

A Django package for tracking and attributing user conversions to their marketing touchpoints.

## Key Concepts

- **Touchpoints**: Records user interactions with UTM parameters (source, medium, campaign, etc.)
- **Conversions**: Tracks meaningful user actions like purchases, signups, or form submissions with optional monetary values
- **Attribution Models**: Supports first-touch and last-touch attribution methods
- **Identity**: Tracks users across sessions using cookies

## Quick Start

1. Install:
```bash
pip install django-attribution
```

2. Add to INSTALLED_APPS:
```python
INSTALLED_APPS = [
    ...
    'django_attribution',
]
```

3. Record conversions in your views:
```python
from django_attribution.shortcuts import record_conversion
from django_attribution.decorators import conversion_events

@conversion_events('order_completed')
def checkout_success(request, order_id):
    order = Order.objects.get(id=order_id)

    record_conversion(
        request,
        event_type='order_completed',
        value=order.total_amount,
        currency=order.currency,
        source_object=order,
        custom_data={
            'items_count': order.items.count(),
            'payment_method': order.payment_method
        }
    )

    return render(request, 'checkout/success.html', {'order': order})
```

4. Query conversions with attribution:
```python
from django_attribution.models import Conversion

# Get all completed orders with their marketing attribution
conversions = Conversion.objects.filter(
    conversion_type='order_completed'
).with_attribution(
    window_days=30  # Look back 30 days for attribution
)

# Example: Find which marketing channels drive the most revenue
channel_revenue = conversions.values(
    'attributed_source',
    'attributed_medium'
).annotate(
    total_revenue=Sum('conversion_value')
).order_by('-total_revenue')
```

## Features

- Automatic UTM parameter tracking
- Multiple attribution models (first-touch, last-touch)
- Conversion value tracking
- Bot filtering
- Django admin integration
- Configurable attribution windows

## Documentation

For detailed documentation, visit [docs/](docs/).
