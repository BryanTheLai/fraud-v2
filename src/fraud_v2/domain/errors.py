class FraudV2Error(Exception):
    """Base error for expected fraud-v2 failures."""


class DuplicatePayloadConflict(FraudV2Error):
    """Raised when an idempotency key is reused with a different payload."""


class EventNotFound(FraudV2Error):
    """Raised when an event is missing."""


class DecisionNotFound(FraudV2Error):
    """Raised when a decision is missing."""
