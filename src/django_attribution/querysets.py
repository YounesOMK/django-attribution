from django.db import models


class BaseQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)

    def newest_first(self):
        return self.order_by("-created_at")

    def oldest_first(self):
        return self.order_by("created_at")


class IdentityQuerySet(BaseQuerySet):
    pass


class TouchpointQuerySet(BaseQuerySet):
    pass


class ConversionQuerySet(BaseQuerySet):
    pass
