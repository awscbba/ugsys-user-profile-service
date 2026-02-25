"""NotificationPreferences value object — immutable notification channel settings."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationPreferences:
    """Immutable value object for user notification channel preferences.

    Default: email notifications enabled, SMS and WhatsApp disabled.
    """

    email: bool = True
    sms: bool = False
    whatsapp: bool = False
