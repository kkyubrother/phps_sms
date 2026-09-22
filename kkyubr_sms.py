"""Compatibility entry point for PhpsSMS's original module name."""
import os

from phps_sms.sms import SMS as _SMS, SMSData as Data, SMSError


class SMS(_SMS):
    def __init__(self, tr_id, tr_key, tr_from, tr_ip=None):
        if tr_ip is None:
            tr_ip = os.environ.get("REMOTE_ADDR")
        super().__init__(tr_id, tr_key, tr_from, tr_ip=tr_ip)


__all__ = ["SMS", "Data", "SMSError"]
