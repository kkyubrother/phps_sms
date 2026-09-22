"""Compatibility namespace. Install only the phps_sms distribution."""
from .sms import SMS
from .lms import LMS, MMS

__all__ = ["SMS", "LMS", "MMS"]
