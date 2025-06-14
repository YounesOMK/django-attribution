from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Dict, List, Union

from django.db import models
from django.db.models import JSONField, OuterRef, Subquery, Value

from django_attribution.conf import attribution_settings


class AttributionModel(ABC):
    @abstractmethod
    def apply(
        self, conversions_qs: models.QuerySet, window_days: int = 30
    ) -> models.QuerySet:
        pass

    def _get_attribution_fields(self) -> List[str]:
        return [
            "attributed_source",
            "attributed_medium",
            "attributed_campaign",
            "attributed_term",
            "attributed_content",
            "attributed_fbclid",
            "attributed_gclid",
            "attributed_msclkid",
            "attributed_ttclid",
            "attributed_li_fat_id",
            "attributed_twclid",
            "attributed_igshid",
        ]


class ORMBasedAttributionModel(AttributionModel):
    def apply(
        self, conversions_qs: models.QuerySet, window_days: int = 30
    ) -> models.QuerySet:
        from django_attribution.models import Touchpoint

        window = OuterRef("created_at") - timedelta(days=window_days)

        touchpoints = Touchpoint.objects.filter(
            identity=OuterRef("identity"),
            created_at__lt=OuterRef("created_at"),
            created_at__gte=window,
        )

        touchpoints = self.get_touchpoints(touchpoints)

        annotations: Dict[str, Union[Subquery, Value]] = {}
        for param in attribution_settings.UTM_PARAMETERS:
            field_name = param.replace("utm_", "attributed_")
            annotations[field_name] = Subquery(
                touchpoints.values(param)[:1], output_field=models.CharField()
            )

        annotations["attribution_metadata"] = Value(
            {
                "model": self.__class__.__name__,
                "window_days": window_days,
            },
            output_field=JSONField(),
        )

        return conversions_qs.annotate(**annotations)

    def get_touchpoints(self, touchpoints_qs):
        raise NotImplementedError


class LastTouchAttributionModel(ORMBasedAttributionModel):
    def get_touchpoints(self, touchpoints_qs):
        return touchpoints_qs.newest_first()


class FirstTouchAttributionModel(ORMBasedAttributionModel):
    def get_touchpoints(self, touchpoints_qs):
        return touchpoints_qs.oldest_first()


last_touch = LastTouchAttributionModel()
first_touch = FirstTouchAttributionModel()
