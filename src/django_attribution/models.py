import logging
import uuid
from typing import List

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
    from django_attribution.conf import django_attribution_settings

    return django_attribution_settings.CURRENCY


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

    objects = models.Manager.from_queryset(IdentityQuerySet)()

    class Meta:
        verbose_name_plural = "Identities"
        indexes = [
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.uuid}"

    def get_canonical_identity(self):
        visited = set()
        current = self
        path: List["Identity"] = []
        max_depth = 100

        while current and current.id not in visited and len(path) < max_depth:
            visited.add(current.id)
            path.append(current)

            if not current.merged_into:
                return current

            current = current.merged_into

        if len(path) >= max_depth:
            logger.error(
                f"Identity chain too deep (>{max_depth}) starting from {self.uuid}"
            )
            return self

        if current and current.id in visited:
            logger.warning(
                f"Circular merge detected"
                f" in identity chain starting from {self.uuid}"
            )

            cycle_start_index = next(
                i for i, identity in enumerate(path) if identity.id == current.id
            )
            cycle_identities = path[cycle_start_index:]

            canonical = self._heal_circular_merge(cycle_identities)
            return canonical

        logger.error(f"Unexpected state in get_canonical_identity for {self.uuid}")
        return self

    def _heal_circular_merge(self, cycle_identities: List["Identity"]) -> "Identity":
        if not cycle_identities:
            return self

        canonical = min(cycle_identities, key=lambda x: x.created_at)

        logger.info(
            f"Healing circular merge:"
            f" chose {canonical.uuid} as canonical"
            f" from {len(cycle_identities)} identities"
        )

        for identity in cycle_identities:
            if identity != canonical:
                identity.touchpoints.update(identity=canonical)
                identity.conversions.update(identity=canonical)

                identity.merged_into = canonical
                identity.save(update_fields=["merged_into"])

                logger.info(
                    f"Merged identity {identity.uuid}"
                    f" into canonical {canonical.uuid}"
                )

        if canonical.merged_into:
            canonical.merged_into = None
            canonical.save(update_fields=["merged_into"])

        logger.info(f"Circular merge healed: {canonical.uuid} is now canonical")
        return canonical

    def is_merged(self) -> bool:
        return self.merged_into is not None

    def is_canonical(self) -> bool:
        return self.get_canonical_identity() == self


class Touchpoint(BaseModel):
    identity = models.ForeignKey(
        Identity, on_delete=models.CASCADE, related_name="touchpoints"
    )

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

    objects = models.Manager.from_queryset(ConversionQuerySet)()

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
