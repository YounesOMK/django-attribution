# Django Attribution

Django package for tracking campaign conversions with UTM parameters.

## Installation

```bash
pip install django-attribution
```

## Quick Setup

Add to your Django settings:

```python
INSTALLED_APPS = [
    'django_attribution',
]

MIDDLEWARE = [
    'django_attribution.middlewares.UTMParameterMiddleware',
    'django_attribution.middlewares.AttributionMiddleware',
]
```

Run migrations:

```bash
python manage.py migrate
```

## Basic Usage

```python
pass
```
