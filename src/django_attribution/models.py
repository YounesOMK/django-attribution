import logging
import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from .querysets import (
    ConversionQuerySet,
    IdentityQuerySet,
    TouchpointQuerySet,
)

logger = logging.getLogger(__name__)


def get_default_currency():
    from django_attribution.conf import attribution_settings

    return attribution_settings.CURRENCY


class BaseModel(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class Identity(BaseModel):
    merged_into = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="merged_identities",
    )

    linked_user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attribution_identities",
    )

    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    objects = models.Manager.from_queryset(IdentityQuerySet)()

    class Meta:
        verbose_name_plural = "Identities"
        indexes = [
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["linked_user"],
                condition=models.Q(merged_into__isnull=True),
                name="unique_canonical_identity_per_user",
            ),
            models.CheckConstraint(
                check=~models.Q(merged_into=models.F("id")),
                name="prevent_self_merge",
            ),
        ]

    def __str__(self):
        if self.linked_user:
            return f"Identity {self.uuid} (User: {self.linked_user.username})"
        return f"Identity {self.uuid} (Anonymous)"

    def get_canonical_identity(self):
        return self.merged_into if self.merged_into else self

    def is_merged(self) -> bool:
        return self.merged_into is not None

    def is_canonical(self) -> bool:
        return self.merged_into is None


class Touchpoint(BaseModel):
    identity = models.ForeignKey(
        Identity,
        on_delete=models.SET_NULL,
        related_name="touchpoints",
        null=True,
        blank=True,
    )

    url = models.URLField(max_length=2048)
    referrer = models.URLField(max_length=2048, blank=True)
    # utm_params
    utm_source = models.CharField(max_length=255, blank=True, db_index=True)
    utm_medium = models.CharField(max_length=255, blank=True, db_index=True)
    utm_campaign = models.CharField(max_length=255, blank=True, db_index=True)
    utm_term = models.CharField(max_length=255, blank=True)
    utm_content = models.CharField(max_length=255, blank=True)

    # click tracking params
    fbclid = models.CharField(max_length=255, blank=True)
    gclid = models.CharField(max_length=255, blank=True)
    msclkid = models.CharField(max_length=255, blank=True)
    ttclid = models.CharField(max_length=255, blank=True)
    li_fat_id = models.CharField(max_length=255, blank=True)
    twclid = models.CharField(max_length=255, blank=True)
    igshid = models.CharField(max_length=255, blank=True)

    objects = models.Manager.from_queryset(TouchpointQuerySet)()

    class Meta:
        indexes = [
            models.Index(fields=["identity", "created_at"]),
            models.Index(fields=["utm_source", "utm_medium"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.utm_source or 'direct'} ({self.created_at})"


class Conversion(BaseModel):
    identity = models.ForeignKey(
        Identity,
        on_delete=models.SET_NULL,
        related_name="conversions",
        null=True,
        blank=True,
    )

    event = models.CharField(max_length=255, db_index=True)
    conversion_value = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default=get_default_currency, blank=True)

    custom_data = models.JSONField(default=dict, blank=True)

    source_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        related_name="conversions_as_source_object",
        null=True,
        blank=True,
    )
    source_object_id = models.PositiveIntegerField(null=True, blank=True)
    source_object = GenericForeignKey("source_content_type", "source_object_id")

    is_confirmed = models.BooleanField(default=True)
    objects = models.Manager.from_queryset(ConversionQuerySet)()

    class Meta:
        indexes = [
            models.Index(fields=["identity", "created_at"]),
            models.Index(fields=["event", "created_at"]),
            models.Index(fields=["source_content_type", "source_object_id"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        if self.conversion_value:
            value_str = f" ({self.currency} {self.conversion_value})"
        else:
            value_str = ""
        return f"{self.event}{value_str} - {self.created_at}"

    def is_monetary(self):
        return self.conversion_value is not None and self.conversion_value > 0
