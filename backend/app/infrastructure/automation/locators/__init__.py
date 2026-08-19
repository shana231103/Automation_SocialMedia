# File: backend/app/infrastructure/automation/locators/__init__.py
"""Registry entry point for deterministic semantic locator specifications."""

from types import MappingProxyType
from typing import Mapping

from app.domain.models import Platform
from app.infrastructure.automation.locators.facebook import FACEBOOK_LOCATORS
from app.infrastructure.automation.locators.tiktok import TIKTOK_LOCATORS
from app.infrastructure.automation.locators.twitter import TWITTER_LOCATORS
from app.infrastructure.automation.locators.youtube import YOUTUBE_LOCATORS
from app.infrastructure.automation.semantic_types import LocatorSpec, SemanticIntent


_REGISTRIES: Mapping[Platform, Mapping[SemanticIntent, LocatorSpec]] = MappingProxyType({
    Platform.FACEBOOK: FACEBOOK_LOCATORS,
    Platform.TIKTOK: TIKTOK_LOCATORS,
    Platform.TWITTER: TWITTER_LOCATORS,
    Platform.YOUTUBE: YOUTUBE_LOCATORS,
})


def get_locator_spec(platform: Platform, intent: SemanticIntent) -> LocatorSpec | None:
    """Return the immutable locator specification for a platform intent."""
    registry = _REGISTRIES.get(platform)
    return registry.get(intent) if registry is not None else None


__all__ = ["get_locator_spec"]
