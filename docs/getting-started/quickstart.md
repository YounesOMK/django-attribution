# Quick Start Guide

This guide will get you up and running with Django Attribution in under 10 minutes.

## Installation

Install django-attribution using pip:

```bash
pip install django-attribution
```

## Django Configuration

### 1. Add to INSTALLED_APPS

Add `django_attribution` to your Django settings:

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Your apps
    'myapp',

    # Django Attribution
    'django_attribution',
]
```

### 2. Configure Middleware

Add the attribution middlewares to your middleware stack:

```python
# settings.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # Django Attribution Middleware
    'django_attribution.middlewares.UTMParameterMiddleware',
    'django_attribution.middlewares.AttributionMiddleware',
]
```

!!! warning "Middleware Order"
    The `UTMParameterMiddleware` must come before `AttributionMiddleware`. The attribution middleware should be placed after authentication middleware to properly handle user login scenarios.

### 3. Run Migrations

Create and apply the database migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

## Basic Usage

### Recording Conversions

The simplest way to record conversions is using the `record_conversion` shortcut:

```python
# views.py
from django.shortcuts import render
from django_attribution.shortcuts import record_conversion

def signup_view(request):
    if request.method == 'POST':
        # Your signup logic here
        user = create_user(request.POST)

        # Record the conversion
        record_conversion(request, 'signup')

        return redirect('success')
    return render(request, 'signup.html')

def purchase_view(request):
    if request.method == 'POST':
        # Your purchase logic here
        order = process_order(request.POST)

        # Record conversion with value
        record_conversion(
            request,
            'purchase',
            value=order.total,
            currency='USD',
            source_object=order  # Optional: link to your model
        )

        return redirect('order_success')
    return render(request, 'checkout.html')
```

### Using Decorators

For cleaner code, use the conversion events decorator:

```python
# views.py
from django_attribution.decorators import conversion_events
from django_attribution.models import Conversion

@conversion_events('signup', 'newsletter_subscribe')
def marketing_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'signup':
            # Your signup logic
            user = create_user(request.POST)

            # Record conversion
            Conversion.objects.record(request, 'signup')

        elif action == 'newsletter_subscribe':
            # Your newsletter logic
            subscribe_to_newsletter(request.POST['email'])

            # Record conversion
            Conversion.objects.record(request, 'newsletter_subscribe')

    return render(request, 'landing.html')
```

### Class-Based Views

Use the mixin for class-based views:

```python
# views.py
from django.views.generic import CreateView
from django_attribution.mixins import ConversionEventsMixin
from django_attribution.shortcuts import record_conversion

class SignupView(ConversionEventsMixin, CreateView):
    conversion_events = {'signup'}
    template_name = 'signup.html'

    def form_valid(self, form):
        response = super().form_valid(form)

        # Record the conversion
        record_conversion(self.request, 'signup')

        return response
```

## Testing Your Setup

### 1. Test UTM Parameter Tracking

Visit your site with UTM parameters:

```
http://localhost:8000/?utm_source=google&utm_medium=cpc&utm_campaign=test
```

### 2. Check the Database

After visiting with UTM parameters, check if data is being recorded:

```python
# Django shell
python manage.py shell

from django_attribution.models import Identity, Touchpoint

# Check if identity was created
print(f"Identities: {Identity.objects.count()}")

# Check if touchpoint was recorded
touchpoints = Touchpoint.objects.all()
for tp in touchpoints:
    print(f"Source: {tp.utm_source}, Campaign: {tp.utm_campaign}")
```

### 3. Record a Test Conversion

```python
# In your view or Django shell
from django.test import RequestFactory
from django_attribution.shortcuts import record_conversion

# Create a test request (in real usage, this comes from your views)
factory = RequestFactory()
request = factory.get('/')
request.identity = Identity.objects.first()  # Get existing identity

# Record conversion
conversion = record_conversion(request, 'test_event', value=10.00)
print(f"Conversion recorded: {conversion}")
```

## Viewing Data in Django Admin

Django Attribution provides a comprehensive admin interface:

1. Create a superuser:
```bash
python manage.py createsuperuser
```

2. Run your development server:
```bash
python manage.py runserver
```

3. Visit the admin at `http://localhost:8000/admin/`

4. Navigate to the "Django Attribution" section to explore:
   - **Identities**: User tracking records
   - **Touchpoints**: UTM parameter captures
   - **Conversions**: Recorded conversion events

## Attribution Analysis

### Basic Attribution Query

```python
from django_attribution.models import Conversion
from django_attribution.attribution_models import last_touch

# Get conversions with attribution data
conversions = Conversion.objects.with_attribution(
    model=last_touch,
    window_days=30
)

# Analyze results
for conversion in conversions:
    print(f"Event: {conversion.event}")
    print(f"Value: {conversion.conversion_value}")
    print(f"Attributed Source: {conversion.attributed_source}")
    print(f"Attributed Campaign: {conversion.attributed_campaign}")
    print("---")
```

### Campaign Performance Analysis

```python
from django.db.models import Sum, Count
from django_attribution.models import Conversion

# Analyze by attributed source
performance = (
    Conversion.objects
    .with_attribution()
    .values('attributed_source')
    .annotate(
        total_conversions=Count('id'),
        total_value=Sum('conversion_value')
    )
    .order_by('-total_value')
)

for source in performance:
    print(f"Source: {source['attributed_source']}")
    print(f"Conversions: {source['total_conversions']}")
    print(f"Value: ${source['total_value']}")
    print("---")
```

## Next Steps

Now that you have Django Attribution up and running:

1. **[Configure Settings](configuration.md)**: Customize the package for your needs
2. **[Learn About Models](../guide/models.md)**: Understand the data structure
3. **[Explore Attribution Models](../guide/attribution-models.md)**: Implement different attribution strategies
4. **[Set Up Analytics](../examples/basic.md)**: Build reports and dashboards

## Common Issues

### No Data Being Recorded

- Check that middleware is properly configured and in the correct order
- Verify that you're visiting pages with UTM parameters
- Ensure migrations have been run
- Check that bot filtering isn't blocking your requests

### Identity Not Persisting

- Verify that cookies are enabled in your browser
- Check your `DJANGO_ATTRIBUTION` settings for cookie configuration
- Ensure your domain settings are correct for cookie handling

### Conversions Not Recording

- Make sure you have an identity (visit with UTM parameters first)
- Check that conversion events are properly declared if using decorators
- Verify that the conversion recording code is actually being executed

Need help? Check our [troubleshooting guide](../guide/troubleshooting.md) or [open an issue](https://github.com/younesoumakhou/django-attribution/issues).
