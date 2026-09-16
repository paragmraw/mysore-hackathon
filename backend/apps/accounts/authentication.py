"""Authentication classes.

CSRF enforcement is disabled across the API by design: the session cookie is
the credential. Without this override, DRF's SessionAuthentication rejects
every unsafe request that carries a logged-in session cookie but no CSRF
token (Django's CsrfViewMiddleware is also removed in settings).
"""

from rest_framework.authentication import SessionAuthentication


class SessionAuthWithoutCSRF(SessionAuthentication):
    """Session authentication with CSRF enforcement disabled."""

    def enforce_csrf(self, request):
        return None
