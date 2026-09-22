"""Request records retained for phps_sms_module callers."""
from typing import NamedTuple, Optional


class RequestSMSData(NamedTuple):
    tel: str
    name1: Optional[str]
    name2: Optional[str]
    text: str


class RequestMMSData(NamedTuple):
    # NamedTuple inheritance cannot add tuple fields; define the full record.
    tel: str
    name1: Optional[str]
    name2: Optional[str]
    text: str
    subject: Optional[str]
