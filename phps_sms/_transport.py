"""Shared PHP School transport. Requests are never automatically retried."""
import datetime as dt
import logging

import phpserialize
import requests

from .errors import SMSError

SMS_SERVER_URL = "https://sms.phps.kr/lib/send.sms"
LMS_SERVER_URL = "https://sms.phps.kr/lib/sendmms.sms"
SERVER_ENCODING = "euc-kr"
DEFAULT_TIMEOUT = (5, 30)
logger = logging.getLogger(__name__)


def encode_text(value):
    try:
        return value.encode(SERVER_ENCODING)
    except (AttributeError, UnicodeEncodeError) as exc:
        raise SMSError("Text must be a string encodable as EUC-KR.") from exc


def date_value(value):
    if value is None:
        return 0
    if not isinstance(value, dt.datetime):
        raise SMSError("tr_date must be a datetime or None.")
    return value.strftime("%Y-%m-%d %H:%M:%S")


def decode_response(content):
    try:
        result = phpserialize.loads(content, decode_strings=True)
        if not isinstance(result, dict) or "status" not in result:
            raise ValueError("missing status")
        return result
    except (ValueError, TypeError, UnicodeError) as exc:
        raise SMSError("Invalid PHP School response.") from exc


def post(url, data, files=None):
    kwargs = {"data": data, "timeout": DEFAULT_TIMEOUT}
    if files:
        kwargs["files"] = files
    try:
        response = requests.post(url, **kwargs)
        response.raise_for_status()
    except requests.RequestException as exc:
        # A timeout does not prove that a message was not delivered.
        raise SMSError("PHP School request failed; check delivery before retrying.") from exc
    # Never log credentials, recipients, message bodies, or service responses.
    logger.debug("PHP School HTTP status: %s", response.status_code)
    return decode_response(response.content)


def send_sms(url, tr_id, tr_key, tr_from, tr_to, text_bytes,
             tr_date=None, tr_comment=None, tr_ip=None):
    data = {
        "adminuser": tr_id, "authkey": tr_key, "rphone": tr_from,
        "phone": tr_to, "sms": text_bytes,
        "date": date_value(tr_date),
        "msg": encode_text(tr_comment) if tr_comment else "",
    }
    if tr_ip is not None:
        data["ip"] = tr_ip
    return post(url, data)


def view(url, tr_id, tr_key):
    return post(url, {"adminuser": tr_id, "authkey": tr_key, "type": "view"})


def cancel(url, tr_id, tr_key, tr_num, lms=False):
    data = {"adminuser": tr_id, "authkey": tr_key, "tr_num": tr_num}
    if lms:
        data["type"] = "cancel"
    else:
        data["date"] = date_value(dt.datetime.now() + dt.timedelta(days=1))
    return post(url, data)
