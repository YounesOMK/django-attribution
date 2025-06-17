from datetime import timedelta

import pytest
from django.utils import timezone

from django_attribution.attribution_models import (
    FirstTouchAttributionModel,
    LastTouchAttributionModel,
    first_touch,
    last_touch,
)
from django_attribution.models import Conversion, Touchpoint


@pytest.fixture
def now():
    return timezone.now()


@pytest.mark.django_db
def test_last_touch_attribution_with_touchpoints_in_window(identity, now):
    Touchpoint.objects.create(
        identity=identity,
        url="https://site.com/page1",
        utm_source="google",
        utm_medium="cpc",
        utm_campaign="campaign1",
        created_at=now - timedelta(days=20),
    )

    Touchpoint.objects.create(
        identity=identity,
        url="https://site.com/page2",
        utm_source="facebook",
        utm_medium="social",
        utm_campaign="campaign2",
        created_at=now - timedelta(days=10),
    )

    Touchpoint.objects.create(
        identity=identity,
        url="https://site.com/page3",
        utm_source="email",
        utm_medium="newsletter",
        utm_campaign="campaign3",
        created_at=now - timedelta(days=5),
    )

    conversion = Conversion.objects.create(
        identity=identity, event="purchase", created_at=now
    )

    model = LastTouchAttributionModel()
    attributed_conversions = model.apply(Conversion.objects.filter(id=conversion.id))

    attributed_conversion = attributed_conversions.first()
    assert attributed_conversion is not None

    assert attributed_conversion.attributed_source == "email"
    assert attributed_conversion.attributed_medium == "newsletter"
    assert attributed_conversion.attributed_campaign == "campaign3"


@pytest.mark.django_db
def test_last_touch_attribution_with_multiple_conversions(identity, now):
    Touchpoint.objects.create(
        identity=identity,
        utm_source="google",
        utm_campaign="search",
        created_at=now - timedelta(days=15),
    )

    Touchpoint.objects.create(
        identity=identity,
        utm_source="facebook",
        utm_campaign="social",
        created_at=now - timedelta(days=5),
    )

    Conversion.objects.create(
        identity=identity, event="signup", created_at=now - timedelta(days=10)
    )

    Conversion.objects.create(identity=identity, event="purchase", created_at=now)

    model = LastTouchAttributionModel()
    attributed_conversions = model.apply(Conversion.objects.all()).order_by(
        "created_at"
    )

    conv1, conv2 = list(attributed_conversions)

    assert conv1.attributed_source == "google"
    assert conv1.attributed_campaign == "search"

    assert conv2.attributed_source == "facebook"
    assert conv2.attributed_campaign == "social"


@pytest.mark.django_db
def test_first_touch_attribution_with_touchpoints_in_window(identity, now):
    Touchpoint.objects.create(
        identity=identity,
        utm_source="google",
        utm_medium="cpc",
        utm_campaign="campaign1",
        created_at=now - timedelta(days=25),
    )

    Touchpoint.objects.create(
        identity=identity,
        utm_source="facebook",
        utm_medium="social",
        utm_campaign="campaign2",
        created_at=now - timedelta(days=15),
    )

    Touchpoint.objects.create(
        identity=identity,
        utm_source="email",
        utm_medium="newsletter",
        utm_campaign="campaign3",
        created_at=now - timedelta(days=5),
    )

    conversion = Conversion.objects.create(
        identity=identity, event="purchase", created_at=now
    )

    model = FirstTouchAttributionModel()
    attributed_conversions = model.apply(Conversion.objects.filter(id=conversion.id))

    attributed_conversion = attributed_conversions.first()
    assert attributed_conversion is not None

    assert attributed_conversion.attributed_source == "google"
    assert attributed_conversion.attributed_medium == "cpc"
    assert attributed_conversion.attributed_campaign == "campaign1"


@pytest.mark.django_db
def test_first_touch_vs_last_touch_attribution_difference(identity, now):
    Touchpoint.objects.create(
        identity=identity,
        utm_source="google",
        utm_campaign="first",
        created_at=now - timedelta(days=20),
    )

    Touchpoint.objects.create(
        identity=identity,
        utm_source="facebook",
        utm_campaign="last",
        created_at=now - timedelta(days=5),
    )

    conversion = Conversion.objects.create(
        identity=identity, event="purchase", created_at=now
    )

    first_touch = FirstTouchAttributionModel()
    last_touch = LastTouchAttributionModel()

    first_touch_result = first_touch.apply(
        Conversion.objects.filter(id=conversion.id)
    ).first()
    assert first_touch_result is not None
    last_touch_result = last_touch.apply(
        Conversion.objects.filter(id=conversion.id)
    ).first()
    assert last_touch_result is not None

    assert first_touch_result.attributed_source == "google"
    assert first_touch_result.attributed_campaign == "first"

    assert last_touch_result.attributed_source == "facebook"
    assert last_touch_result.attributed_campaign == "last"


@pytest.mark.django_db
def test_attribution_with_no_touchpoints_in_window_returns_empty(identity, now):
    Touchpoint.objects.create(
        identity=identity,
        utm_source="google",
        utm_campaign="old_campaign",
        created_at=now - timedelta(days=40),
    )

    conversion = Conversion.objects.create(
        identity=identity, event="purchase", created_at=now
    )

    model = LastTouchAttributionModel()
    attributed_conversions = model.apply(Conversion.objects.filter(id=conversion.id))

    attributed_conversion = attributed_conversions.first()
    assert attributed_conversion is not None

    assert attributed_conversion.attributed_source is None
    assert attributed_conversion.attributed_medium is None
    assert attributed_conversion.attributed_campaign is None


@pytest.mark.django_db
def test_attribution_with_no_touchpoints_at_all_returns_empty(identity, now):
    conversion = Conversion.objects.create(
        identity=identity, event="purchase", created_at=now
    )

    model = LastTouchAttributionModel()
    attributed_conversions = model.apply(Conversion.objects.filter(id=conversion.id))

    attributed_conversion = attributed_conversions.first()
    assert attributed_conversion is not None

    assert attributed_conversion.attributed_source is None
    assert attributed_conversion.attributed_medium is None
    assert attributed_conversion.attributed_campaign is None


@pytest.mark.django_db
def test_attribution_with_custom_window_days_parameter(identity, now):
    Touchpoint.objects.create(
        identity=identity,
        utm_source="google",
        utm_campaign="within_7_days",
        created_at=now - timedelta(days=5),
    )

    Touchpoint.objects.create(
        identity=identity,
        utm_source="facebook",
        utm_campaign="outside_7_days",
        created_at=now - timedelta(days=10),
    )

    conversion = Conversion.objects.create(
        identity=identity, event="purchase", created_at=now
    )

    model = LastTouchAttributionModel()
    attributed_conversions = model.apply(
        Conversion.objects.filter(id=conversion.id), window_days=7
    )

    attributed_conversion = attributed_conversions.first()
    assert attributed_conversion is not None

    assert attributed_conversion.attributed_source == "google"
    assert attributed_conversion.attributed_campaign == "within_7_days"


@pytest.mark.django_db
def test_attribution_with_different_window_sizes(identity, now):
    Touchpoint.objects.create(
        identity=identity, utm_source="recent", created_at=now - timedelta(days=3)
    )

    Touchpoint.objects.create(
        identity=identity, utm_source="medium", created_at=now - timedelta(days=15)
    )

    Touchpoint.objects.create(
        identity=identity, utm_source="old", created_at=now - timedelta(days=45)
    )

    conversion = Conversion.objects.create(
        identity=identity, event="purchase", created_at=now
    )

    model = LastTouchAttributionModel()

    result_1day = model.apply(
        Conversion.objects.filter(id=conversion.id), window_days=1
    ).first()
    assert result_1day is not None
    assert result_1day.attributed_source is None

    result_7day = model.apply(
        Conversion.objects.filter(id=conversion.id), window_days=7
    ).first()
    assert result_7day is not None
    assert result_7day.attributed_source == "recent"

    result_30day = model.apply(
        Conversion.objects.filter(id=conversion.id), window_days=30
    ).first()
    assert result_30day is not None
    assert result_30day.attributed_source == "recent"

    result_60day = model.apply(
        Conversion.objects.filter(id=conversion.id), window_days=60
    ).first()
    assert result_60day is not None
    assert result_60day.attributed_source == "recent"


@pytest.mark.django_db
def test_attribution_metadata_annotation_last_touch(identity, now):
    conversion = Conversion.objects.create(
        identity=identity, event="purchase", created_at=now
    )

    model = LastTouchAttributionModel()
    attributed_conversions = model.apply(
        Conversion.objects.filter(id=conversion.id), window_days=14
    )

    attributed_conversion = attributed_conversions.first()
    assert attributed_conversion is not None

    assert attributed_conversion.attribution_metadata == {
        "model": "LastTouchAttributionModel",
        "window_days": 14,
    }


@pytest.mark.django_db
def test_attribution_metadata_annotation_first_touch(identity, now):
    conversion = Conversion.objects.create(
        identity=identity, event="purchase", created_at=now
    )

    model = FirstTouchAttributionModel()
    attributed_conversions = model.apply(
        Conversion.objects.filter(id=conversion.id), window_days=45
    )

    attributed_conversion = attributed_conversions.first()
    assert attributed_conversion is not None

    assert attributed_conversion.attribution_metadata == {
        "model": "FirstTouchAttributionModel",
        "window_days": 45,
    }


@pytest.mark.django_db
def test_attribution_metadata_with_default_window(identity, now):
    conversion = Conversion.objects.create(
        identity=identity, event="purchase", created_at=now
    )

    model = LastTouchAttributionModel()
    attributed_conversions = model.apply(Conversion.objects.filter(id=conversion.id))

    attributed_conversion = attributed_conversions.first()
    assert attributed_conversion is not None

    assert attributed_conversion.attribution_metadata == {
        "model": "LastTouchAttributionModel",
        "window_days": 30,
    }


@pytest.mark.django_db
def test_touchpoints_exactly_at_window_boundary(identity, now):
    Touchpoint.objects.create(
        identity=identity,
        utm_source="boundary",
        utm_campaign="exactly_30_days",
        created_at=now - timedelta(days=30),
    )

    Touchpoint.objects.create(
        identity=identity,
        utm_source="outside",
        utm_campaign="just_outside",
        created_at=now - timedelta(days=30, seconds=1),
    )

    Touchpoint.objects.create(
        identity=identity,
        utm_source="inside",
        utm_campaign="just_inside",
        created_at=now - timedelta(days=29, hours=23, minutes=59),
    )

    conversion = Conversion.objects.create(
        identity=identity, event="purchase", created_at=now
    )

    model = LastTouchAttributionModel()
    attributed_conversions = model.apply(
        Conversion.objects.filter(id=conversion.id), window_days=30
    )

    attributed_conversion = attributed_conversions.first()
    assert attributed_conversion is not None

    assert attributed_conversion.attributed_source == "inside"
    assert attributed_conversion.attributed_campaign == "just_inside"


@pytest.mark.django_db
def test_window_boundary_with_first_touch_attribution(identity, now):
    Touchpoint.objects.create(
        identity=identity,
        utm_source="outside",
        created_at=now - timedelta(days=31),
    )

    Touchpoint.objects.create(
        identity=identity,
        utm_source="boundary",
        created_at=now - timedelta(days=30),
    )

    Touchpoint.objects.create(
        identity=identity,
        utm_source="inside",
        created_at=now - timedelta(days=29),
    )

    conversion = Conversion.objects.create(
        identity=identity, event="purchase", created_at=now
    )

    model = FirstTouchAttributionModel()
    attributed_conversions = model.apply(
        Conversion.objects.filter(id=conversion.id), window_days=30
    )

    attributed_conversion = attributed_conversions.first()
    assert attributed_conversion is not None

    assert attributed_conversion.attributed_source == "boundary"


@pytest.mark.django_db
def test_convenience_instances_last_touch_and_first_touch(identity, now):
    Touchpoint.objects.create(
        identity=identity, utm_source="first", created_at=now - timedelta(days=20)
    )

    Touchpoint.objects.create(
        identity=identity, utm_source="last", created_at=now - timedelta(days=5)
    )

    conversion = Conversion.objects.create(
        identity=identity, event="purchase", created_at=now
    )

    conversions_qs = Conversion.objects.filter(id=conversion.id)

    first_touch_result = first_touch.apply(conversions_qs).first()
    assert first_touch_result is not None
    last_touch_result = last_touch.apply(conversions_qs).first()
    assert last_touch_result is not None

    assert first_touch_result.attributed_source == "first"
    assert last_touch_result.attributed_source == "last"

    assert isinstance(first_touch, FirstTouchAttributionModel)
    assert isinstance(last_touch, LastTouchAttributionModel)
