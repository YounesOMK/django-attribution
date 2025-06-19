import pytest
from django.http import HttpResponse

from django_attribution.decorators import conversion_events


def test_decorator_sets_allowed_conversion_events(make_request):
    request = make_request("/test/")

    @conversion_events("signup", "purchase", "newsletter_subscribe")
    def test_view(request):
        assert hasattr(request, "_allowed_conversion_events")
        assert request._allowed_conversion_events == {
            "signup",
            "purchase",
            "newsletter_subscribe",
        }
        return HttpResponse("OK")

    response = test_view(request)

    assert response.status_code == 200


def test_decorator_cleans_up_request_attributes_after_execution(make_request):
    request = make_request("/test/")

    @conversion_events("signup", "purchase")
    def test_view(request):
        assert hasattr(request, "_allowed_conversion_events")
        return HttpResponse("OK")

    response = test_view(request)

    assert not hasattr(request, "_allowed_conversion_events")
    assert response.status_code == 200


def test_decorator_cleans_up_request_attributes_even_on_exception(make_request):
    request = make_request("/test/")

    @conversion_events("signup")
    def test_view(request):
        assert hasattr(request, "_allowed_conversion_events")
        raise ValueError("Test exception")

    with pytest.raises(ValueError, match="Test exception"):
        test_view(request)

    assert not hasattr(request, "_allowed_conversion_events")


@pytest.mark.django_db
def test_decorator_with_no_events_specified_allows_all(make_request):
    request = make_request("/test/")

    @conversion_events()
    def test_view(request):
        assert hasattr(request, "_allowed_conversion_events")
        assert request._allowed_conversion_events is None
        return HttpResponse("OK")

    response = test_view(request)

    assert not hasattr(request, "_allowed_conversion_events")
    assert response.status_code == 200


def test_decorator_with_single_event(make_request):
    request = make_request("/test/")

    @conversion_events("purchase")
    def test_view(request):
        assert request._allowed_conversion_events == {"purchase"}
        return HttpResponse("OK")

    response = test_view(request)

    assert not hasattr(request, "_allowed_conversion_events")
    assert response.status_code == 200


def test_decorator_passes_through_args_and_kwargs(make_request):
    request = make_request("/test/")

    @conversion_events("test_event")
    def test_view(request, pk, category=None):
        assert pk == 123
        assert category == "products"
        return HttpResponse("OK")

    response = test_view(request, 123, category="products")

    assert response.status_code == 200


def test_decorator_cleanup_handles_missing_attributes_gracefully(make_request):
    request = make_request("/test/")

    request._allowed_conversion_events = {"test"}

    @conversion_events("new_event")
    def test_view(request):
        return HttpResponse("OK")

    response = test_view(request)

    assert not hasattr(request, "_allowed_conversion_events")
    assert response.status_code == 200
