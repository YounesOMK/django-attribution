from django.conf import settings

from .settings import DEFAULTS


class AttributionSettings:
    def __init__(self):
        self.defaults = DEFAULTS
        self.user_settings = getattr(settings, "DJANGO_ATTRIBUTION", {})

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError(f"Invalid setting: '{attr}'")

        val = self.user_settings.get(attr, self.defaults[attr])

        # cache for next time
        setattr(self, attr, val)
        return val


attribution_settings = AttributionSettings()
