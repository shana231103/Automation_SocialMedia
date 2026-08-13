# File: backend/app/infrastructure/automation/login_status_policy.py
"""Pure URL/DOM guards for conservative AI login-status upgrades."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.application.ai_login import ProtectedObservation, TerminalAssessment
from app.domain.models import LoginStatus, Platform


_HOSTS = {
    Platform.FACEBOOK: {"facebook.com", "www.facebook.com", "m.facebook.com"},
    Platform.YOUTUBE: {"youtube.com", "www.youtube.com", "m.youtube.com"},
    Platform.TIKTOK: {"tiktok.com", "www.tiktok.com"},
    Platform.TWITTER: {"x.com", "www.x.com", "twitter.com", "www.twitter.com"},
}
_AUTH_MARKERS = {
    Platform.FACEBOOK: ('role="feed"', 'aria-label="account"'),
    Platform.YOUTUBE: ("guide-button", "avatar-btn", "ytd-app"),
    Platform.TIKTOK: ('data-e2e="profile-icon"', 'href="/@'),
    Platform.TWITTER: ('data-testid="app-tab-bar-home-link"', 'aria-label="home"'),
}
_BLOCKED_PATHS = ("login", "checkpoint", "challenge", "consent", "recovery", "signin", "oauth")
_BLOCKED_DOM = ('type="password"', "captcha", "checkpoint", "challenge", "two-factor", "verification")


def may_upgrade_to_logged_in(
    evidence: ProtectedObservation,
    assessment: TerminalAssessment,
    login_upgrade_threshold: float,
) -> bool:
    """Require trusted route and DOM signals before accepting a logged-in upgrade."""
    if evidence.preliminary_status != LoginStatus.LOGGED_OUT:
        return False
    if assessment.confidence < login_upgrade_threshold:
        return False
    parsed, dom = urlsplit(evidence.redacted_url), evidence.dom_snippet.lower()
    return (
        (parsed.hostname or "").lower() in _HOSTS[evidence.platform]
        and not any(token in parsed.path.lower() for token in _BLOCKED_PATHS)
        and not any(token in dom for token in _BLOCKED_DOM)
        and any(marker in dom for marker in _AUTH_MARKERS[evidence.platform])
        and bool(assessment.visual_evidence and assessment.dom_evidence)
    )


def sanitize_url(url: str) -> str:
    """Remove fragments and redact every query value while preserving diagnostic keys."""
    parsed = urlsplit(url)
    query = urlencode([(key, "[redacted]") for key, _ in parse_qsl(parsed.query, keep_blank_values=True)])
    hostname = parsed.hostname or ""
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    netloc = hostname
    if parsed.port is not None:
        netloc = f"{netloc}:{parsed.port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, query, ""))
