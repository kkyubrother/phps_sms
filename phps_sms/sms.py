"""Queue-based SMS API, compatible with phps_sms and PhpsSMS."""
import datetime
import re
from collections import namedtuple
from typing import List

import requests

from . import _transport
from .errors import SMSError

IP_CHECK_URL = "https://api.ipify.org"
SERVER_URL = _transport.SMS_SERVER_URL
SERVER_ENCODING = _transport.SERVER_ENCODING
PATTERN_NUM = re.compile(r"^(?P<num0>0\d0)?[\s\-.]?(?P<num1>\d{3,4})[\s\-.]?(?P<num2>\d{4})$")


class SMSData(namedtuple("SMSData", ["tr_to", "tr_txtmsg"])):
    """Recipient and message text (bytes internally, str in SMS.get())."""
    __slots__ = ()


class SMS:
    """Queue messages with add(), then send them using the original API.

    Pass tr_ip to avoid automatic public-IP lookup. Without it the lookup is
    deferred until send(), so construction and imports never access the network.
    """

    def __init__(self, tr_id: str, tr_key: str, tr_from: str, tr_ip: str = None):
        self.__tr_id = tr_id
        self.__tr_key = tr_key
        self.__tr_from = tr_from
        self.__tr_ip = tr_ip
        self.__data = []

    def add(self, tr_to: str, tr_txtmsg: str, auto_slice: bool = False) -> None:
        tr_to = _valid_tr_to(tr_to)
        if not isinstance(tr_txtmsg, str):
            raise SMSError("tr_txtmsg must be a string.")
        text = tr_txtmsg.strip()
        encoded = _transport.encode_text(text)
        if not encoded:
            raise SMSError("tr_txtmsg is empty.")
        if len(encoded) > 90 and not auto_slice:
            raise SMSError("tr_txtmsg is too long.")
        chunks = _slice_tr_txtmsg(text) if len(encoded) > 90 else [encoded]
        self.__data.extend(SMSData(tr_to, chunk) for chunk in chunks)

    def get(self) -> List[SMSData]:
        return [SMSData(to, text.decode(SERVER_ENCODING)) for to, text in self.__data]

    def view(self) -> dict:
        return _transport.view(SERVER_URL, self.__tr_id, self.__tr_key)

    def cancel(self, tr_num: int) -> dict:
        return _transport.cancel(SERVER_URL, self.__tr_id, self.__tr_key, tr_num)

    def send(self, tr_date: datetime.datetime = None, tr_comment: str = None) -> List[dict]:
        if not self.__data:
            raise SMSError("no data")
        _transport.date_value(tr_date)
        if tr_date is not None:
            now = datetime.datetime.now(tr_date.tzinfo)
            if tr_date < now + datetime.timedelta(minutes=3):
                raise SMSError("Message reservation must be longer than 3 minutes.")
        if tr_comment:
            _transport.encode_text(tr_comment)
        if self.__tr_ip is None:
            try:
                response = requests.get(IP_CHECK_URL, timeout=_transport.DEFAULT_TIMEOUT)
                response.raise_for_status()
                self.__tr_ip = response.text.strip()
            except requests.RequestException as exc:
                raise SMSError("Public IP lookup failed; pass tr_ip explicitly.") from exc

        results = []
        while self.__data:
            to, text = self.__data[0]
            result = _transport.send_sms(
                SERVER_URL, self.__tr_id, self.__tr_key, self.__tr_from,
                to, text, tr_date, tr_comment, self.__tr_ip,
            )
            # Remove each acknowledged request immediately. A later failure
            # must not leave previously acknowledged messages queued again.
            self.__data.pop(0)
            results.append(result)
        return results


def _valid_tr_to(tr_to: str) -> str:
    if not isinstance(tr_to, str):
        raise SMSError("tr_to must be a string.")
    match = PATTERN_NUM.fullmatch(tr_to.strip())
    if match is None:
        raise SMSError("tr_to is not a valid phone number.")
    parts = match.groupdict()
    return (parts["num0"] or "010") + "-" + parts["num1"] + "-" + parts["num2"]


def _slice_tr_txtmsg(tr_txtmsg: str) -> List[bytes]:
    """Split at EUC-KR character boundaries into chunks of at most 90 bytes."""
    chunks = []
    current = bytearray()
    for character in tr_txtmsg:
        encoded = _transport.encode_text(character)
        if len(current) + len(encoded) > 90:
            chunks.append(bytes(current))
            current.clear()
        current.extend(encoded)
    if current:
        chunks.append(bytes(current))
    return chunks


_decode_response = _transport.decode_response
