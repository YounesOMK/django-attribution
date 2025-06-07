from unittest.mock import Mock

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponse
from django.test import RequestFactory

from django_attribution.middlewares import AttributionMiddleware, UTMParameterMiddleware


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def make_request(request_factory):
    def _make_request(path="/", utm_params=None, other_params=None):
        params = {}
        if utm_params:
            params.update(utm_params)
        if other_params:
            params.update(other_params)
        return request_factory.get(path, params)

    return _make_request


@pytest.fixture
def utm_parameter_middleware():
    get_response = Mock(return_value=HttpResponse("OK"))
    return UTMParameterMiddleware(get_response)


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
