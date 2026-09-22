import datetime as dt
import importlib
import io
import os
import unittest
from unittest.mock import Mock, patch

import phpserialize
import requests

from phps_sms import SMS, DirectSMS, LMS, MMS, SMSError, ResultSuccess, ResultError
from phps_sms import _transport
from phps_sms.model import RequestMMSData
from phps_sms.sms import _slice_tr_txtmsg, _valid_tr_to


def response(result=None, content=None):
    if result is None:
        result = {"status": "success", "curcount": "99", "sendcount": "1",
                  "phonecount": 1, "tr_num": "123"}
    return Mock(status_code=200,
                content=phpserialize.dumps(result) if content is None else content)


class APITest(unittest.TestCase):
    def setUp(self):
        # Fail closed if a test accidentally reaches the real HTTP transport.
        patch("requests.sessions.Session.send",
              side_effect=AssertionError("Live HTTP forbidden")).start()
        self.post = patch("phps_sms._transport.requests.post").start()
        self.get = patch("phps_sms.sms.requests.get").start()
        self.addCleanup(patch.stopall)
        self.post.return_value = response()

    def client(self, tr_ip="192.0.2.1"):
        return SMS("test-id", "test-key", "010-0000-0000", tr_ip=tr_ip)

    def payload(self):
        return self.post.call_args[1]["data"]

    def test_imports_and_constructors_make_no_requests(self):
        for name in ("phps_sms", "phps_sms.sms", "phps_sms.lms",
                     "phps_sms_module", "phps_sms_module.sms",
                     "phps_sms_module.lms", "phps_sms_module.model",
                     "phps_sms_module.models", "phps_sms_module.constants", "kkyubr_sms"):
            importlib.reload(importlib.import_module(name))
        SMS("id", "key", "sender")
        DirectSMS("id", "key")
        self.get.assert_not_called()
        self.post.assert_not_called()

    def test_queue_api_payload_and_return_type(self):
        client = self.client()
        client.add("01012345678", "안녕하세요")
        self.assertEqual(client.get()[0].tr_to, "010-1234-5678")
        self.assertEqual(client.get()[0].tr_txtmsg, "안녕하세요")
        result = client.send(tr_comment="메모")
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], dict)
        self.assertEqual(self.payload(), {
            "adminuser": "test-id", "authkey": "test-key", "rphone": "010-0000-0000",
            "phone": "010-1234-5678", "sms": "안녕하세요".encode("euc-kr"),
            "date": 0, "msg": "메모".encode("euc-kr"), "ip": "192.0.2.1",
        })
        self.assertEqual(self.post.call_args[0][0], _transport.SMS_SERVER_URL)
        self.assertEqual(self.post.call_args[1]["timeout"], (5, 30))
        self.assertEqual(client.get(), [])
        self.get.assert_not_called()

    def test_phone_normalization(self):
        for value in ("01012345678", "010-1234-5678", "010.1234.5678", "12345678"):
            self.assertEqual(_valid_tr_to(value), "010-1234-5678")
        for value in ("01012345678junk", "invalid", None):
            with self.assertRaises(SMSError):
                _valid_tr_to(value)

    def test_byte_splitting_preserves_text(self):
        for text in ("가" * 46, "a" * 91, "a" * 89 + "한", "가a" * 100, "short"):
            chunks = _slice_tr_txtmsg(text)
            self.assertEqual(b"".join(chunks).decode("euc-kr"), text)
            self.assertTrue(all(0 < len(c) <= 90 for c in chunks))
            for chunk in chunks:
                chunk.decode("euc-kr")

    def test_auto_slice_sends_every_part(self):
        client = self.client()
        client.add("01012345678", "가" * 46, auto_slice=True)
        self.assertEqual(len(client.get()), 2)
        self.assertEqual(len(client.send()), 2)
        self.assertEqual(self.post.call_count, 2)

    def test_invalid_text_never_sends(self):
        for value in ("", "  ", "가" * 46, "emoji 😀", None):
            with self.assertRaises(SMSError):
                self.client().add("01012345678", value)
        self.post.assert_not_called()

    def test_error_compatibility_attributes(self):
        error = SMSError("bad input")
        self.assertEqual(str(error), "bad input")
        self.assertEqual(error.message, "bad input")
        self.assertEqual(error.text, "bad input")

    def test_empty_queue_does_not_lookup_ip(self):
        with self.assertRaises(SMSError):
            self.client(tr_ip=None).send()
        self.get.assert_not_called()
        self.post.assert_not_called()

    def test_reservation_payload(self):
        client = self.client()
        client.add("01012345678", "예약")
        when = dt.datetime.now() + dt.timedelta(days=1)
        client.send(when)
        self.assertEqual(self.payload()["date"], when.strftime("%Y-%m-%d %H:%M:%S"))

    def test_invalid_reservation_never_sends(self):
        for value in (dt.datetime.now(), "tomorrow"):
            client = self.client(tr_ip=None)
            client.add("01012345678", "예약")
            with self.assertRaises(SMSError):
                client.send(value)
        self.get.assert_not_called()
        self.post.assert_not_called()

    def test_timezone_aware_reservation(self):
        client = self.client()
        client.add("01012345678", "예약")
        when = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)
        client.send(when)
        self.assertEqual(self.payload()["date"], when.strftime("%Y-%m-%d %H:%M:%S"))

    def test_ip_is_lazy_and_cached(self):
        self.get.return_value = Mock(text="192.0.2.2\n")
        client = self.client(tr_ip=None)
        self.get.assert_not_called()
        for _ in range(2):
            client.add("01012345678", "hello")
            client.send()
        self.get.assert_called_once_with("https://api.ipify.org", timeout=(5, 30))
        self.assertEqual(self.payload()["ip"], "192.0.2.2")

    def test_ip_failure_preserves_queue(self):
        client = self.client(tr_ip=None)
        client.add("01012345678", "hello")
        self.get.side_effect = requests.Timeout()
        with self.assertRaisesRegex(SMSError, "IP lookup failed"):
            client.send()
        self.assertEqual(len(client.get()), 1)
        self.post.assert_not_called()

    def test_legacy_module_and_remote_addr(self):
        import kkyubr_sms
        with patch.dict(os.environ, {"REMOTE_ADDR": "192.0.2.3"}):
            client = kkyubr_sms.SMS("id", "key", "sender")
        client.add("01012345678", "hello")
        self.assertIsInstance(client.get()[0], kkyubr_sms.Data)
        client.send()
        self.assertEqual(self.payload()["ip"], "192.0.2.3")
        self.get.assert_not_called()

    def test_queue_view_and_cancel(self):
        client = self.client(tr_ip=None)
        self.assertIsInstance(client.view(), dict)
        self.assertEqual(self.payload()["type"], "view")
        client.cancel(456)
        self.assertEqual(self.payload()["tr_num"], 456)
        self.assertIn("date", self.payload())
        self.assertNotIn("type", self.payload())
        self.get.assert_not_called()

    def test_partial_failure_keeps_only_unacknowledged(self):
        client = self.client()
        client.add("01012345678", "first")
        client.add("01012345678", "second")
        self.post.side_effect = [response(), requests.Timeout()]
        with self.assertRaises(SMSError):
            client.send()
        self.assertEqual([item.tr_txtmsg for item in client.get()], ["second"])
        self.assertEqual(self.post.call_count, 2)

    def test_service_error_remains_a_result(self):
        self.post.return_value = response({"status": "9001", "message": "denied"})
        client = self.client()
        client.add("01012345678", "hello")
        self.assertEqual(client.send()[0], {"status": "9001", "message": "denied"})
        self.assertEqual(client.get(), [])

    def test_http_error_is_not_parsed_or_retried(self):
        self.post.return_value.raise_for_status.side_effect = requests.HTTPError()
        with self.assertRaisesRegex(SMSError, "check delivery"):
            DirectSMS.view("id", "key")
        self.assertEqual(self.post.call_count, 1)

    def test_invalid_response_is_reported(self):
        for content in (b"<html>error</html>", phpserialize.dumps("unexpected"),
                        phpserialize.dumps({"unexpected": "field"}), b""):
            self.post.return_value = response(content=content)
            with self.assertRaisesRegex(SMSError, "Invalid PHP School"):
                DirectSMS.view("id", "key")

    def test_direct_sms_compatibility(self):
        from phps_sms_module.sms import SMS as LegacySMS
        client = LegacySMS("id", "key", "sender")
        client.set_tr_from("new-sender")
        result = client.send_msg("receiver", "메시지")
        self.assertIsInstance(result, ResultSuccess)
        self.assertEqual(result.current_count, 99)
        self.assertEqual(result.tr_num, 123)
        self.assertEqual(self.payload()["rphone"], "new-sender")
        self.assertNotIn("ip", self.payload())
        self.assertEqual(client.get_count().status, "success")
        client.cancel_msg(321)
        self.assertEqual(self.payload()["tr_num"], 321)

    def test_direct_class_method_and_date(self):
        DirectSMS.send("id", "key", "from", "to", "본문",
                       dt.datetime(2030, 1, 2, 3, 4, 5), "메모")
        self.assertEqual(self.payload()["date"], "2030-01-02 03:04:05")
        self.assertEqual(self.payload()["msg"], "메모".encode("euc-kr"))

    def test_typed_error_and_optional_success_fields(self):
        self.post.return_value = response({"status": "9001", "message": "denied"})
        self.assertEqual(DirectSMS.view("id", "key"), ResultError(9001, "denied"))
        self.post.return_value = response({"status": "success", "curcount": "3"})
        result = DirectSMS.view("id", "key")
        self.assertEqual(result.current_count, 3)
        self.assertIsNone(result.send_count)
        self.post.return_value = response({"status": "success", "curcount": "3", "deletecount": "2"})
        self.assertEqual(DirectSMS.cancel("id", "key", 1).delete_count, 2)

    def test_bad_typed_result_has_clear_error(self):
        for data in ({"status": "success"}, {"status": "invalid", "message": "bad"}):
            self.post.return_value = response(data)
            with self.assertRaisesRegex(SMSError, "result fields"):
                DirectSMS.view("id", "key")

    def test_lms_subject_encoding_and_compatibility(self):
        from phps_sms_module.lms import LMS as LegacyLMS
        self.assertIs(LegacyLMS, importlib.import_module("phps_sms.lms").LMS)
        result = LMS.send("id", "key", "from", "to", "긴 본문", "제목")
        self.assertIsInstance(result, ResultSuccess)
        self.assertEqual(self.post.call_args[0][0], _transport.LMS_SERVER_URL)
        self.assertEqual(self.payload()["subject"], "제목".encode("euc-kr"))
        self.assertNotIn("files", self.post.call_args[1])

    def test_mms_preserves_attachments_and_caller_owns_stream(self):
        files = [io.BytesIO(b"one"), ("two.jpg", b"two", "image/jpeg")]
        MMS.send("id", "key", "from", "to", "본문", files=files)
        self.assertEqual(self.post.call_args[1]["files"],
                         {"files[0]": files[0], "files[1]": files[1]})
        self.assertFalse(files[0].closed)
        self.assertEqual(files[0].tell(), 0)

    def test_seventh_attachment_is_rejected_before_request(self):
        with self.assertRaisesRegex(SMSError, "six"):
            LMS.send("id", "key", "from", "to", "body", files=[b"x"] * 7)
        self.post.assert_not_called()

    def test_lms_view_and_cancel_contract(self):
        LMS.view("id", "key")
        self.assertEqual(self.post.call_args[0][0], _transport.LMS_SERVER_URL)
        self.assertEqual(self.payload()["type"], "view")
        LMS.cancel("id", "key", 456)
        self.assertEqual(self.payload(), {
            "adminuser": "id", "authkey": "key", "tr_num": 456, "type": "cancel",
        })

    def test_lms_instance_arguments_do_not_shift(self):
        client = LMS("id", "key", "from")
        client.send_msg("to", "본문", "제목", dt.datetime(2030, 1, 2), "메모")
        self.assertEqual(self.payload()["date"], "2030-01-02 00:00:00")
        self.assertEqual(self.payload()["subject"], "제목".encode("euc-kr"))

    def test_logging_excludes_payload(self):
        DirectSMS.set_print_debug_message(True)
        self.addCleanup(DirectSMS.set_print_debug_message, False)
        with self.assertLogs("phps_sms", level="DEBUG") as logs:
            DirectSMS.send("secret-user", "secret-key", "private-sender",
                           "private-recipient", "private-body")
        output = "\n".join(logs.output)
        self.assertIn("200", output)
        for value in ("secret-user", "secret-key", "private-sender",
                      "private-recipient", "private-body", "curcount"):
            self.assertNotIn(value, output)

    def test_request_mms_record_has_subject_field(self):
        record = RequestMMSData("to", None, None, "body", "subject")
        self.assertEqual(record.subject, "subject")
        self.assertEqual(len(record), 5)

    def test_real_requests_encoding_without_sending(self):
        prepared = requests.Request(
            "POST", _transport.SMS_SERVER_URL, data={"sms": "가".encode("euc-kr")},
        ).prepare()
        self.assertIn("sms=%B0%A1", prepared.body)
        prepared = requests.Request(
            "POST", _transport.LMS_SERVER_URL,
            data={"sms": "가".encode("euc-kr")},
            files={"files[0]": ("test.jpg", b"image-data", "image/jpeg")},
        ).prepare()
        self.assertIn("multipart/form-data", prepared.headers["Content-Type"])
        self.assertIn(b"files[0]", prepared.body)
        self.assertIn(b"image-data", prepared.body)


if __name__ == "__main__":
    unittest.main()
