"""Direct SMS adapter for existing phps_sms_module callers."""
import logging

from . import _transport
from .models import parse_result


class DirectSMS:
    _name = "SMS"
    _server_url = _transport.SMS_SERVER_URL
    _print_debug_message = False
    logger = logging.getLogger(__name__)

    def __init__(self, tr_id: str, tr_key: str, tr_from: str = None):
        self.tr_id = tr_id
        self.tr_key = tr_key
        self.tr_from = tr_from

    def set_tr_from(self, tr_from: str):
        self.tr_from = tr_from

    def send_msg(self, tr_to, tr_txt_msg, tr_date=None, tr_comment=None):
        return self.send(self.tr_id, self.tr_key, self.tr_from,
                         tr_to, tr_txt_msg, tr_date, tr_comment)

    def get_count(self):
        return self.view(self.tr_id, self.tr_key)

    def cancel_msg(self, tr_num):
        return self.cancel(self.tr_id, self.tr_key, tr_num)

    @classmethod
    def set_print_debug_message(cls, is_print):
        # Keep the switch, but never emit raw payloads or service responses.
        cls._print_debug_message = bool(is_print)

    @classmethod
    def _log_operation(cls, operation):
        log = cls.logger.info if cls._print_debug_message else cls.logger.debug
        log("%s operation: %s", cls._name, operation)

    @classmethod
    def send(cls, tr_id, tr_key, tr_from, tr_to, tr_txt_msg,
             tr_date=None, tr_comment=None):
        result = _transport.send_sms(
            cls._server_url, tr_id, tr_key, tr_from, tr_to,
            _transport.encode_text(tr_txt_msg), tr_date, tr_comment,
        )
        cls._log_operation("send")
        return parse_result(result)

    @classmethod
    def view(cls, tr_id, tr_key):
        result = _transport.view(cls._server_url, tr_id, tr_key)
        cls._log_operation("view")
        return parse_result(result)

    @classmethod
    def cancel(cls, tr_id, tr_key, tr_num):
        result = _transport.cancel(cls._server_url, tr_id, tr_key, tr_num)
        cls._log_operation("cancel")
        return parse_result(result)
