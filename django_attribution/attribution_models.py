from datetime import timedelta
from typing import Dict, Optional

from django.db import models
from django.db.models import (
    JSONField,
    OuterRef,
    Q,
    Subquery,
    Value,
)
from django.db.models.functions import (
    Coalesce,
    JSONObject,
)

from django_attribution.conf import attribution_settings

__all__ = [
    "SingleTouchAttributionModel",
    "LastTouchAttributionModel",
    "FirstTouchAttributionModel",
    "last_touch",
    "first_touch",
]


class SingleTouchAttributionModel:
    """
    Base class for single-touch attribution models.

    Single-touch attribution assigns 100% of the conversion credit to one
    touchpoint in the customer journey. Subclasses implement different
    strategies for choosing which touchpoint gets the credit (first-touch,
    last-touch.) by overriding the prepare_touchpoints method.

    The model applies attribution windows to limit which touchpoints are
    considered, with support for different window lengths per traffic source.
    """

    def prepare_touchpoints(self, touchpoints_qs):
        raise NotImplementedError

    def apply(
        self,
        conversions_qs: models.QuerySet,
        window_days: int = 30,
        source_windows: Optional[Dict[str, int]] = None,
    ) -> models.QuerySet:
        from django_attribution.models import Touchpoint

        window_config = self._build_window_config(window_days, source_windows)

        touchpoints = Touchpoint.objects.filter(
            identity=OuterRef("identity"),
            created_at__lt=OuterRef("created_at"),
        ).filter(self._build_window_conditions(window_config))

        touchpoints = self.prepare_touchpoints(touchpoints)

        attribution_data = Coalesce(
            Subquery(
                touchpoints.annotate(
                    attribution_json=JSONObject(**self._get_attribution_fields())
                ).values("attribution_json")[:1],
                output_field=JSONField(),
            ),
            Value({}, output_field=JSONField()),
        )

        return conversions_qs.annotate(
            attribution_data=attribution_data,
            attribution_metadata=Value(
                {
                    "model": self.__class__.__name__,
                    "window_days": window_days,
                    "source_windows": source_windows,
                },
                output_field=JSONField(),
            ),
        )

    def _build_window_conditions(self, window_config: Dict[str, int]) -> Q:
        conditions = Q()

        for source, days in window_config.items():
            if source == "default":
                continue

            window_start = OuterRef("created_at") - timedelta(days=days)
            conditions |= Q(
                utm_source=source,
                created_at__gte=window_start,
            )

        default_days = window_config["default"]
        default_window_start = OuterRef("created_at") - timedelta(days=default_days)
        explicit_sources = [s for s in window_config if s != "default"]

        if explicit_sources:
            conditions |= Q(
                created_at__gte=default_window_start,
            ) & ~Q(utm_source__in=explicit_sources)
        else:
            conditions |= Q(created_at__gte=default_window_start)

        return conditions

    def _build_window_config(
        self, default_days: int, source_windows: Optional[Dict[str, int]]
    ) -> Dict[str, int]:
        config = {"default": default_days}

        if source_windows:
            config.update(source_windows)

        return config

    def _get_attribution_fields(self) -> Dict[str, str]:
        fields = {param: param for param in attribution_settings.TRACKING_PARAMETERS}
        fields["referrer"] = "referrer"
        return fields


class LastTouchAttributionModel(SingleTouchAttributionModel):
    """
    Attribution model that credits the most recent touchpoint before conversion.

    Assigns 100% of conversion credit to the last marketing touchpoint that
    occurred within the attribution window. This model emphasizes the final
    interaction that directly preceded the conversion action.
    """

    def prepare_touchpoints(self, touchpoints_qs):
        return touchpoints_qs.newest_first()


class FirstTouchAttributionModel(SingleTouchAttributionModel):
    """
    Attribution model that credits the earliest touchpoint before conversion.

    Assigns 100% of conversion credit to the first marketing touchpoint that
    occurred within the attribution window. This model emphasizes the initial
    interaction that started the customer journey leading to conversion.
    """

    def prepare_touchpoints(self, touchpoints_qs):
        return touchpoints_qs.oldest_first()


last_touch = LastTouchAttributionModel()
first_touch = FirstTouchAttributionModel()
