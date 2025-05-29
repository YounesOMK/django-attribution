from django.conf import settings

import django_attribution


def test_import():
    assert django_attribution.__version__


def test_django_setup():
    assert "django_attribution" in settings.INSTALLED_APPS
