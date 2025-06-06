from datetime import timedelta

from django.db import models
from django.utils import timezone
from typing_extensions import Self


class BaseQuerySet(models.QuerySet):
    def active(self) -> "Self":
        return self.filter(is_active=True)

    def inactive(self) -> "Self":
        return self.filter(is_active=False)

    def newest_first(self) -> "Self":
        return self.order_by("-created_at")

    def oldest_first(self) -> "Self":
        return self.order_by("created_at")

    def created_since(self, days_ago: int) -> "Self":
        cutoff = timezone.now() - timedelta(days=days_ago)
        return self.filter(created_at__gte=cutoff)


class IdentityQuerySet(BaseQuerySet):
    pass


class TouchpointQuerySet(BaseQuerySet):
    pass


class ConversionQuerySet(BaseQuerySet):
    pass
