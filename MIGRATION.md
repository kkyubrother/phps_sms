# 통합 및 이전 안내

통합 저장소는 **kkyubrother/phps_sms**, 설치할 배포 패키지는 **phps_sms**입니다.
기본 브랜치 반영 후 사용처를 이 저장소로 옮길 수 있습니다.

## 유지하는 호출 방식

| 기존 코드 | 통합 후 |
|---|---|
| `from phps_sms.sms import SMS` | 그대로 사용. 대기열 방식과 dict/list 반환 유지 |
| `from kkyubr_sms import SMS` | 호환 모듈 제공. `REMOTE_ADDR`도 반영 |
| `from phps_sms_module import SMS` | 직접 전송 API로 연결 |
| `from phps_sms_module.sms import SMS` | 직접 전송 API로 연결 |
| `from phps_sms_module.lms import LMS` | 통합 LMS 구현으로 연결 |
| `from phps_sms_module.models import ResultSuccess, ResultError` | 필드 구조 유지 |
| `from phps_sms_module.model import RequestSMSData, RequestMMSData` | 요청 레코드 제공 |
| `from phps_sms_module.constants import SMS_SERVER_URL, LMS_SERVER_URL` | 동일한 주소 제공 |

새 코드는 `from phps_sms import SMS, DirectSMS, LMS, MMS`를 권장합니다.
대기열 SMS와 직접 전송 SMS는 인자·반환 형식이 다릅니다.
`phps_sms_module.SMS`를 `phps_sms.SMS`로 기계적으로 치환하지 마세요.

## 설치 충돌 방지

구 `php_school_sms_module`도 `phps_sms_module` 경로를 제공합니다.
동시에 설치하면 파일 소유권이 겹치므로 새 가상환경을 권장합니다.
기존 환경을 옮긴다면 의존성을 기록하고 구 패키지를 제거한 뒤 통합 패키지를 설치합니다.
다음 명령은 통합 저장소 루트에서 실행합니다.

```bash
python -m pip freeze > requirements-before-phps-migration.txt
python -m pip uninstall php_school_sms_module phps_sms
python -m pip install .
```

프로젝트에 직접 복사한 `kkyubr_sms.py` 또는 `phps_sms_module/`가
설치된 모듈보다 우선 로드되는지도 확인하세요.

## 수정된 동작

- 잘못된 절대 import 및 import 시 인자 없는 `SMS_V2()` 호출 제거.
- 미완성 `SMS_V2`/`send_many`는 호환 API에 포함하지 않음.
  SMS 여러 건은 `SMS.add()` 반복 후 `send()` 사용.
- HTTP 처리·응답 파싱 통합 및 제한시간 적용. 자동 재시도 없음.
- 로깅 타입 오류 수정 및 본문·인증정보·원본 응답 로깅 제거.
- 공인 IP 조회는 생성자에서 최초 전송 시점으로 지연.
- 앞뒤 공백을 제거한 본문을 기준으로 EUC-KR 문자 경계를 지키며 SMS 분할.
- 요청 실패 이전에 응답받은 메시지는 대기열에서 즉시 제거.
- `RequestMMSData.subject`가 실제 튜플 필드가 되도록 수정.
  SMS 레코드 하위 타입 관계에 의존하는 코드는 필드 기반 처리로 변경 필요.
- 7개 이상의 첨부파일은 누락시키지 않고 오류로 처리.
- 런타임 의존성을 `setup_requires`에서 `install_requires`로 수정.
- HTTP/응답 파싱 오류는 `SMSError`로 통일.
  requests 예외를 직접 잡던 코드는 이 예외도 처리하도록 변경 필요.

## 통합 근거와 보존 범위

| 원본 | 확인한 커밋 | 반영 |
|---|---|---|
| [phps_sms](https://github.com/kkyubrother/phps_sms) | `21683d9bb43bea6d635dc34144d5194ba6d61ccf` | 기준 코드, 대기열 API |
| [phps-sms-module](https://github.com/kkyubrother/phps-sms-module) | `2626ba9f3f2af7f1d9bfb25187cfd492a33c5acc` | 직접 전송, LMS/첨부파일, 결과 모델 |
| PhpsSMS | `54e106354381fa03958e0b361295b3359c65a57c` | 기존 모듈 API용 호환 진입점 |

빈 `phps_sms_hosting_module`에는 이전할 코드가 없었습니다.
PHP 참고 예제·IDE 설정은 실행 패키지에 복사하지 않고 원본 저장소에 보존했습니다.
비공개 저장소의 구현 파일을 공개 저장소로 복사하지 않았습니다.

이 변경은 코드 통합입니다. 구 저장소 삭제·보관, 패키지 게시,
다른 프로젝트의 의존성 수정은 별도 작업입니다.
사용처 검색 결과가 없었지만 미사용을 입증하는 근거는 아닙니다.

## 반영 순서

1. 통합 PR 검토 및 기본 브랜치 반영.
2. 새 가상환경에서 설치하고 사용처별 import·호출 확인.
3. 필요한 환경에서 별도로 실제 서비스 인증·예약·첨부파일 확인.
4. 사용처 전환 완료 후 구 저장소 보관 및 필요시 패키지 배포.
