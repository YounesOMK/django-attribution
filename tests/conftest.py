from unittest.mock import Mock

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponse
from django.test import RequestFactory

from django_attribution.middlewares import AttributionMiddleware, UTMParameterMiddleware
from django_attribution.models import Conversion, Identity, Touchpoint


@pytest.fixture(autouse=True)
def clean_database(db):
    # Clean up attribution-specific models
    Touchpoint.objects.all().delete()
    Identity.objects.all().delete()
    Conversion.objects.all().delete()

    yield  # Run the test

    # Optional: cleanup after test as well
    Touchpoint.objects.all().delete()
    Identity.objects.all().delete()
    Conversion.objects.all().delete()


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def make_request(request_factory):
    def _make_request(path="/", tracking_params=None, other_params=None):
        params = {}
        if tracking_params:
            params.update(tracking_params)
        if other_params:
            params.update(other_params)
        return request_factory.get(path, params)

    return _make_request


@pytest.fixture
def tracking_parameter_middleware():
    get_response = Mock(return_value=HttpResponse("OK"))
    return UTMParameterMiddleware(get_response)


@pytest.fixture
def attribution_middleware_with_utm():
    utm_get_response = Mock(return_value=HttpResponse("OK"))
    utm_middleware = UTMParameterMiddleware(utm_get_response)

    attribution_get_response = Mock(return_value=HttpResponse("OK"))
    attribution_middleware = AttributionMiddleware(attribution_get_response)

    def process_request(request):
        utm_middleware(request)
        return attribution_middleware(request)

    return process_request


@pytest.fixture
def attribution_middleware():
    get_response = Mock(return_value=HttpResponse("OK"))
    return AttributionMiddleware(get_response)


@pytest.fixture
def authenticated_user():
    return User.objects.create_user(username="testuser", password="testpassword")


@pytest.fixture
def anonymous_user():
    return AnonymousUser()
