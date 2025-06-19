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


__all__ = [
    "Identity",
    "Touchpoint",
    "Conversion",
]


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
    """
    Represents a trackable visitor identity for attribution purposes.

    An Identity is created when a visitor arrives with tracking parameters
    (UTM codes, click IDs) or attribution triggers. It can be anonymous
    (browser/device-based) or authenticated (linked to a User account).
    Identities can be merged when an anonymous visitor logs in, consolidating
    their touchpoint and conversion history under a single canonical identity.

    Attributes:
        merged_into: Reference to canonical identity if this one was merged
        linked_user: Django User this identity belongs to (if authenticated)
        first_visit_user_agent: Browser user agent string from first visit
    """

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

    first_visit_user_agent = models.TextField(blank=True)

    objects = models.Manager.from_queryset(IdentityQuerySet)()

    class Meta:
        verbose_name_plural = "Identities"
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["linked_user", "merged_into", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["linked_user"],
                condition=models.Q(merged_into__isnull=True),
                name="unique_canonical_identity_per_user",
            ),
            models.CheckConstraint(
                condition=~models.Q(merged_into=models.F("id")),
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
    """
    Records a single marketing touch when a visitor arrives with tracking data.

    A Touchpoint captures the marketing context (UTM parameters, click IDs)
    and visit details (URL, referrer) for each visit that contains
    tracking parameters. These touchpoints form the attribution trail that gets
    analyzed when determining which marketing efforts led to conversions.

    Attributes:
        identity: The Identity this touchpoint belongs to
        url: Full URL the visitor landed on
        referrer: HTTP referrer header value
        utm_source: Marketing source (e.g., 'google', 'facebook')
        utm_medium: Marketing medium (e.g., 'cpc', 'email', 'social')
        utm_campaign: Campaign identifier
        utm_term: Keywords/search terms (typically for paid search)
        utm_content: Ad content identifier for A/B testing
        fbclid, gclid, etc.: Platform-specific click tracking IDs
    """

    identity = models.ForeignKey(
        Identity,
        on_delete=models.SET_NULL,
        related_name="touchpoints",
        null=True,
        blank=True,
    )

    url = models.URLField(max_length=2048)
    referrer = models.URLField(max_length=2048, blank=True)

    utm_source = models.CharField(max_length=255, blank=True, db_index=True)
    utm_medium = models.CharField(max_length=255, blank=True, db_index=True)
    utm_campaign = models.CharField(max_length=255, blank=True, db_index=True)
    utm_term = models.CharField(max_length=255, blank=True)
    utm_content = models.CharField(max_length=255, blank=True)

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
            models.Index(fields=["utm_campaign", "utm_source", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.utm_source or 'direct'} ({self.created_at})"


class Conversion(BaseModel):
    """
    Records a conversion event that can be attributed to marketing touchpoints.

    A Conversion represents a valuable action taken by a visitor, such as a
    purchase, signup, or subscription. Conversions are linked to identities
    and can later be attributed to specific marketing touchpoints using
    attribution models to understand which campaigns drove the most value.

    Attributes:
        identity: The Identity that performed this conversion
        event: Type of conversion (e.g., 'purchase', 'signup', 'trial')
        conversion_value: Monetary value of this conversion
        currency: Currency code for the conversion value
        custom_data: Additional conversion metadata as JSON
        source_content_type: Django content type of related object
        source_object_id: ID of related object (e.g., Order, Subscription)
        source_object: Generic foreign key to related object
        is_confirmed: Whether this conversion is confirmed/valid
    """

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
        if self.conversion_value is not None:
            value_str = f" ({self.currency} {self.conversion_value:.2f})"
        else:
            value_str = ""
        return f"{self.event}{value_str} - {self.created_at}"
