from django.conf import settings

from .settings import DEFAULTS, TRACKING_PARAMETERS

__all__ = [
    "attribution_settings",
]


class AttributionSettings:
    def __init__(self):
        self.defaults = DEFAULTS
        self.TRACKING_PARAMETERS = TRACKING_PARAMETERS
        self.user_settings = getattr(settings, "DJANGO_ATTRIBUTION", {})

    def __getattr__(self, attr):
        if attr == "TRACKING_PARAMETERS":
            return self.TRACKING_PARAMETERS

        if attr not in self.defaults:
            raise AttributeError(f"Invalid setting: '{attr}'")

        val = self.user_settings.get(attr, self.defaults[attr])

        # cache for next time
        setattr(self, attr, val)
        return val


attribution_settings = AttributionSettings()
