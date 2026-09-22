# phps_sms

PHP School 문자 전송 모듈을 한 저장소·한 배포 패키지로 통합합니다.
기존 SMS 대기열 API, 직접 전송 API, LMS·첨부파일 전송을 제공합니다.

## 설치

Python 3.6 이상을 대상으로 작성했습니다. 로컬 검증 환경은 Python 3.12입니다.

```bash
python -m pip install .
```

`requests`, `phpserialize`가 함께 설치됩니다.
이번 패키지 버전은 `0.4.0`이며 이 PR 자체가 PyPI 배포를 의미하지는 않습니다.
구 패키지가 설치되어 있다면 [MIGRATION.md](MIGRATION.md)를 확인하세요.

## 기존 SMS API

```python
import os
from phps_sms import SMS

sms = SMS(
    tr_id=os.environ["PHPS_SMS_ID"],
    tr_key=os.environ["PHPS_SMS_KEY"],
    tr_from=os.environ["PHPS_SMS_FROM"],
    tr_ip=os.environ["PHPS_SMS_IP"],
)
sms.add("010-1234-5678", "안녕하세요")
print(sms.get())  # 전송 대기 목록
# 실제 발송: results = sms.send()
# 잔여 건수 조회: result = sms.view()
# 예약 취소: result = sms.cancel(tr_num)
```

- `from phps_sms.sms import SMS`도 그대로 사용할 수 있습니다.
- `add(..., auto_slice=True)`는 EUC-KR 기준 90바이트 이하로 분할합니다.
- `send(tr_date=datetime, tr_comment="메모")`는 예약을 지원합니다.
  기존 규칙대로 예약 시각은 현재보다 3분 이상 뒤여야 합니다.
- `send()`는 `list[dict]`, `view()`·`cancel()`은 `dict`를 반환합니다.
- `tr_ip`를 생략하면 최초 `send()`에서 공인 IP를 조회하여 재사용합니다.
  생성자와 import는 네트워크 요청을 하지 않습니다.
- 날짜는 입력한 시각을 `YYYY-MM-DD HH:MM:SS`로 전달하며 시간대를 변환하지 않습니다.
  서비스가 사용하는 현지 시각에 맞춰 입력하세요.

## 직접 전송 API

```python
from phps_sms import DirectSMS

client = DirectSMS(tr_id="...", tr_key="...", tr_from="...")
# 실제 발송: result = client.send_msg("010-1234-5678", "안녕하세요")
# 클래스 호출: result = DirectSMS.send("id", "key", "from", "to", "본문")
```

`ResultSuccess` 또는 `ResultError`를 반환합니다.
성공 결과 필드: `status`, `current_count`, `send_count`, `phone_count`,
`tr_num`, `delete_count`. 응답에 없는 선택 필드는 `None`입니다.
이 직접 전송 API에는 SMS 대기열의 자동 분할이 적용되지 않습니다.

## LMS·첨부파일

```python
from phps_sms import LMS, MMS

# 실제 LMS 발송:
# result = LMS.send("id", "key", "from", "to", "긴 본문", tr_subject="제목")

# MMS는 LMS의 별칭이며 같은 전송 경로에 첨부파일을 전달합니다.
# with open("photo.jpg", "rb") as photo:
#     result = MMS.send(
#         "id", "key", "from", "to", "본문", tr_subject="제목",
#         files=[("photo.jpg", photo, "image/jpeg")],
#     )
```

`LMS.view(id, key)`, `LMS.cancel(id, key, tr_num)`을 지원합니다.
첨부파일은 최대 6개이며 열린 파일은 호출자가 닫습니다.
서비스의 파일 형식·크기 허용 여부는 서버 응답으로 확인해야 합니다.

## 오류 처리

서비스 실패 응답은 기존 반환 형식으로 전달합니다.
입력 오류, HTTP 실패, 응답 파싱 실패는 `SMSError`를 발생시킵니다.
HTTP 연결·읽기 제한시간은 각각 5초·30초입니다. 자동 재시도는 하지 않습니다.

여러 SMS 중 뒤쪽 요청이 실패하면 이미 응답받은 항목은 대기열에서 제거되고
실패한 항목과 이후 항목은 남습니다. 실패한 요청은 발송 여부가 불명확할 수 있으므로
서비스 내역을 확인한 후 재시도하세요.
본문·수신자·인증키·원본 응답은 로그에 남기지 않습니다.

## 검증

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m pip wheel --no-deps --no-build-isolation . -w dist
```

테스트는 HTTP를 모킹하며 실제 전송 경로에 도달하면 실패하도록 차단합니다.
실제 문자 발송, 서비스 계정 인증, PyPI 배포 검증은 포함하지 않습니다.
