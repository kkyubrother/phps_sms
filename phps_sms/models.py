from typing import NamedTuple, Optional


class ResultError(NamedTuple):
    status: int
    message: str

    @classmethod
    def create_result_error(cls, result: dict) -> "ResultError":
        return cls(
            status=int(result["status"]),
            message=result["message"]
        )


class ResultSuccess(NamedTuple):
    status: str
    current_count: int
    send_count: Optional[int]
    phone_count: Optional[int]
    tr_num: Optional[int]
    delete_count: Optional[int]

    @classmethod
    def create_result_success(cls, result: dict) -> "ResultSuccess":
        status = result["status"]
        current_count = int(result["curcount"])
        phone_count = int(result["phonecount"]) if "phonecount" in result else None
        send_count = int(result["sendcount"]) if "sendcount" in result else None
        tr_num = int(result['tr_num']) if "tr_num" in result else None
        delete_count = int(result["deletecount"]) if "deletecount" in result else None

        return cls(
            status=status,
            current_count=current_count,
            phone_count=phone_count,
            send_count=send_count,
            tr_num=tr_num,
            delete_count=delete_count,
        )


def parse_result(result):
    """Convert a service result to the legacy typed result."""
    from .errors import SMSError

    try:
        if result.get("status") == "success":
            return ResultSuccess.create_result_success(result)
        return ResultError.create_result_error(result)
    except (KeyError, ValueError, TypeError) as exc:
        raise SMSError("Invalid PHP School result fields.") from exc
