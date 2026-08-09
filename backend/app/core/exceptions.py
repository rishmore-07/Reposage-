"""
app/core/exceptions.py

Custom exception hierarchy for RepoSage.

Design principles:
- All application exceptions inherit from AppError (single catch point)
- Each exception carries an HTTP status code and a machine-readable error code
- HTTP error codes are string constants (not magic numbers scattered in handlers)
- The global exception handler in middleware.py converts these to JSON responses
"""

from __future__ import annotations

from http import HTTPStatus


class AppError(Exception):
    """
    Base class for all application exceptions.

    Attributes:
        status_code: HTTP status code to return to the client.
        error_code:  Machine-readable error identifier (snake_case string).
        message:     Human-readable error message for the client.
        detail:      Optional additional context (not shown to client in production).
    """

    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR.value
    error_code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        detail: str | None = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.detail = detail
        super().__init__(self.message)

    def to_dict(self) -> dict[str, str | int]:
        """Serialize to a JSON-safe dict for HTTP responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "status_code": self.status_code,
        }


# ── 400 Bad Request ───────────────────────────────────────────────────────────


class ValidationError(AppError):
    """Request payload fails validation beyond Pydantic's built-in checks."""

    status_code = HTTPStatus.BAD_REQUEST.value
    error_code = "validation_error"
    message = "The request data is invalid."


class BadRequestError(AppError):
    """Generic bad request when the client sends a malformed request."""

    status_code = HTTPStatus.BAD_REQUEST.value
    error_code = "bad_request"
    message = "Bad request."


# ── 401 Unauthorized ──────────────────────────────────────────────────────────


class AuthenticationError(AppError):
    """Missing or invalid authentication credentials."""

    status_code = HTTPStatus.UNAUTHORIZED.value
    error_code = "authentication_required"
    message = "Authentication is required to access this resource."


class InvalidTokenError(AppError):
    """JWT token is expired, malformed, or has an invalid signature."""

    status_code = HTTPStatus.UNAUTHORIZED.value
    error_code = "invalid_token"
    message = "The provided token is invalid or has expired."


class InvalidCredentialsError(AppError):
    """Email/password combination does not match any account."""

    status_code = HTTPStatus.UNAUTHORIZED.value
    error_code = "invalid_credentials"
    message = "Invalid email or password."


# ── 403 Forbidden ─────────────────────────────────────────────────────────────


class PermissionDeniedError(AppError):
    """Authenticated user does not have permission to perform this action."""

    status_code = HTTPStatus.FORBIDDEN.value
    error_code = "permission_denied"
    message = "You do not have permission to perform this action."


# ── 404 Not Found ─────────────────────────────────────────────────────────────


class NotFoundError(AppError):
    """Requested resource does not exist."""

    status_code = HTTPStatus.NOT_FOUND.value
    error_code = "not_found"
    message = "The requested resource was not found."


class UserNotFoundError(NotFoundError):
    error_code = "user_not_found"
    message = "User not found."


class OrganizationNotFoundError(NotFoundError):
    error_code = "organization_not_found"
    message = "Organization not found."


class RepositoryNotFoundError(NotFoundError):
    error_code = "repository_not_found"
    message = "Repository not found."


# ── 409 Conflict ──────────────────────────────────────────────────────────────


class ConflictError(AppError):
    """Resource already exists or state conflict."""

    status_code = HTTPStatus.CONFLICT.value
    error_code = "conflict"
    message = "A conflict occurred with the current state of the resource."


class EmailAlreadyExistsError(ConflictError):
    error_code = "email_already_exists"
    message = "An account with this email address already exists."


# ── 422 Unprocessable Entity ──────────────────────────────────────────────────


class UnprocessableEntityError(AppError):
    """Request is well-formed but semantically invalid."""

    status_code = HTTPStatus.UNPROCESSABLE_ENTITY.value
    error_code = "unprocessable_entity"
    message = "The request could not be processed."


# ── 429 Too Many Requests ─────────────────────────────────────────────────────


class RateLimitError(AppError):
    """Client has exceeded the rate limit."""

    status_code = HTTPStatus.TOO_MANY_REQUESTS.value
    error_code = "rate_limit_exceeded"
    message = "Too many requests. Please slow down."


# ── 503 Service Unavailable ───────────────────────────────────────────────────


class ServiceUnavailableError(AppError):
    """Downstream service (DB, Redis, GitHub API) is temporarily unavailable."""

    status_code = HTTPStatus.SERVICE_UNAVAILABLE.value
    error_code = "service_unavailable"
    message = "A required service is temporarily unavailable."


class DatabaseError(ServiceUnavailableError):
    error_code = "database_error"
    message = "A database error occurred."
