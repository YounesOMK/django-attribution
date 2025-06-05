import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


def get_default_currency():
    from django_attribution.conf import django_attribution_settings

    return django_attribution_settings.CURRENCY


class Identity(models.Model):
    class TrackingMethod(models.TextChoices):
        COOKIE = "cookie", "Cookie Based"

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    tracking_method = models.CharField(
        max_length=20,
        choices=TrackingMethod.choices,
        default=TrackingMethod.COOKIE,
        db_index=True,
    )

    merged_into = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="merged_identities",
    )

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_visit_at = models.DateTimeField(default=timezone.now, db_index=True)

    linked_user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attribution_identities",
    )

    class Meta:
        verbose_name_plural = "Identities"
        indexes = [
            models.Index(fields=["tracking_method"]),
            models.Index(fields=["created_at", "tracking_method"]),
        ]

    def __str__(self):
        return f"{self.tracking_method}:{self.uuid}"

    def get_canonical_identity(self):
        if self.merged_into:
            return self.merged_into.get_canonical_identity()
        return self

    def is_merged(self):
        return self.merged_into is not None


class Touchpoint(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    identity = models.ForeignKey(
        Identity, on_delete=models.CASCADE, related_name="touchpoints"
    )

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    url = models.URLField(max_length=2048)
    referrer = models.URLField(max_length=2048, blank=True)
    page_title = models.CharField(max_length=255, blank=True)
    utm_source = models.CharField(max_length=255, blank=True, db_index=True)
    utm_medium = models.CharField(max_length=255, blank=True, db_index=True)
    utm_campaign = models.CharField(max_length=255, blank=True, db_index=True)
    utm_term = models.CharField(max_length=255, blank=True)
    utm_content = models.CharField(max_length=255, blank=True)
    custom_parameters = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["identity", "created_at"]),
            models.Index(fields=["utm_source", "utm_medium"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.utm_source or 'direct'} ({self.created_at})"


class Conversion(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    identity = models.ForeignKey(
        Identity, on_delete=models.CASCADE, related_name="conversions"
    )

    conversion_type = models.CharField(max_length=255, db_index=True)
    conversion_value = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default=get_default_currency, blank=True)

    custom_data = models.JSONField(default=dict, blank=True)

    source_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="conversions_as_source_object",
    )
    source_object_id = models.PositiveIntegerField()
    source_object = GenericForeignKey("source_content_type", "source_object_id")

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["identity", "created_at"]),
            models.Index(fields=["conversion_type", "created_at"]),
            models.Index(fields=["source_content_type", "source_object_id"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        if self.conversion_value:
            value_str = f" ({self.currency} {self.conversion_value})"
        else:
            value_str = ""
        return f"{self.conversion_type}{value_str} - {self.created_at}"

    def is_monetary(self):
        return self.conversion_value is not None and self.conversion_value > 0
