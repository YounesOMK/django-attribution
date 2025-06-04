# types.py
from typing import TYPE_CHECKING

from django.http import HttpRequest

if TYPE_CHECKING:
    from .middlewares import AttributionManager


class AttributionHttpRequest(HttpRequest):
    attribution: "AttributionManager"
