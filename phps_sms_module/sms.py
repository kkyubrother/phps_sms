"""Legacy direct API; implementation lives in phps_sms."""
from phps_sms.client import DirectSMS as SMS
from phps_sms._transport import SMS_SERVER_URL as SERVER_URL

__all__ = ["SMS"]
