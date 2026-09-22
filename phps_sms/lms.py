"""LMS and MMS using the existing sendmms.sms contract."""
from . import _transport
from .client import DirectSMS
from .errors import SMSError
from .models import parse_result


SERVER_URL = _transport.LMS_SERVER_URL


class LMS(DirectSMS):
    _name = "LMS"
    _server_url = SERVER_URL

    @classmethod
    def send(cls, tr_id, tr_key, tr_from, tr_to, tr_txt_msg,
             tr_subject=None, tr_date=None, tr_comment=None, files=()):
        # Reject excess attachments instead of silently dropping the seventh.
        files = tuple(files)
        if len(files) > 6:
            raise SMSError("At most six attachments are supported.")
        data = {
            "adminuser": tr_id, "authkey": tr_key, "rphone": tr_from,
            "phone": tr_to,
            "subject": _transport.encode_text(tr_subject) if tr_subject else "",
            "sms": _transport.encode_text(tr_txt_msg),
            "msg": _transport.encode_text(tr_comment) if tr_comment else "",
            "date": _transport.date_value(tr_date),
        }
        result = _transport.post(
            cls._server_url, data,
            files={"files[{}]".format(i): file for i, file in enumerate(files)},
        )
        cls._log_operation("send")
        return parse_result(result)

    def send_msg(self, tr_to, tr_txt_msg, tr_subject=None,
                 tr_date=None, tr_comment=None, files=()):
        return self.send(self.tr_id, self.tr_key, self.tr_from, tr_to,
                         tr_txt_msg, tr_subject, tr_date, tr_comment, files)

    @classmethod
    def cancel(cls, tr_id, tr_key, tr_num):
        result = _transport.cancel(cls._server_url, tr_id, tr_key, tr_num, lms=True)
        cls._log_operation("cancel")
        return parse_result(result)


MMS = LMS
