import uuid

from django.db import models
from django.utils import timezone


class Identity(models.Model):
    class TrackingMethod(models.TextChoices):
        COOKIE = "cookie", "Cookie Based"
        BROWSER_SIGNATURE = "browser_signature", "Browser Signature Based"
        TOKEN = "token", "Token Based"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity_value = models.CharField(max_length=255, db_index=True)
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

    first_ip_address = models.GenericIPAddressField(null=True, blank=True)
    first_user_agent = models.TextField(blank=True)

    user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attribution_identities",
    )

    class Meta:
        verbose_name_plural = "Identities"
        indexes = [
            models.Index(fields=["tracking_method", "identity_value"]),
            models.Index(fields=["created_at", "tracking_method"]),
        ]
        unique_together = ["tracking_method", "identity_value"]

    def __str__(self):
        return f"{self.tracking_method}:{self.identity_value[:20]}"

    def get_canonical_identity(self):
        if self.merged_into:
            return self.merged_into.get_canonical_identity()
        return self

    def is_merged(self):
        return self.merged_into is not None


class Touchpoint(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
