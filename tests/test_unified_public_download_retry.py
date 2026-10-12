"""Only two transient transport codes may retry the original callable."""

import unittest
from unittest.mock import Mock
from urllib.error import HTTPError, URLError
from scripts.retry_public_download import retry_public_download


class PublicDownloadRetryTests(unittest.TestCase):
    def error(self, code):
        return HTTPError(
            "https://example.invalid/original-pin", code, "transport", {}, None
        )

    def test_success_preserves_exact_return_and_does_not_sleep(self):
        original = (b"original material", b"original rights metadata")
        download = Mock(return_value=original)
        sleep = Mock()
        self.assertIs(retry_public_download(download, sleep=sleep), original)
        download.assert_called_once_with()
        sleep.assert_not_called()

    def test_only_503_504_retry_same_callable_with_bounded_backoff(self):
        original = (b"original", b"metadata")
        download = Mock(side_effect=[self.error(503), self.error(504), original])
        sleep = Mock()
        self.assertIs(retry_public_download(download, sleep=sleep), original)
        self.assertEqual(download.call_count, 3)
        self.assertEqual([call.args for call in sleep.call_args_list], [(2,), (4,)])
        self.assertTrue(
            all(not c.args and not c.kwargs for c in download.call_args_list)
        )

    def test_fourth_transient_error_propagates_and_cannot_silently_pass(self):
        errors = [self.error(504) for _ in range(4)]
        download = Mock(side_effect=errors)
        sleep = Mock()
        with self.assertRaises(HTTPError) as caught:
            retry_public_download(download, sleep=sleep)
        self.assertIs(caught.exception, errors[-1])
        self.assertEqual(download.call_count, 4)
        self.assertEqual([c.args for c in sleep.call_args_list], [(2,), (4,), (8,)])
        self.assertEqual(sum(c.args[0] for c in sleep.call_args_list), 14)

    def test_authorization_tls_hash_and_other_errors_never_retry(self):
        for error in (
            self.error(401),
            self.error(403),
            self.error(404),
            self.error(500),
            URLError("TLS verification failed"),
            ValueError("source hash mismatch"),
            AssertionError("downstream assertion"),
        ):
            with self.subTest(type=type(error), code=getattr(error, "code", None)):
                download = Mock(side_effect=error)
                sleep = Mock()
                with self.assertRaises(type(error)) as caught:
                    retry_public_download(download, sleep=sleep)
                self.assertIs(caught.exception, error)
                download.assert_called_once_with()
                sleep.assert_not_called()

    def test_workflow_transport_steps_have_total_wall_time_guards(self):
        from pathlib import Path

        for name, step in [
            ("hcl-i02-clifford-provider-free.yml", "Download pinned public edition"),
            (
                "hcl-i02-gregory-multiparty-provider-free.yml",
                "Fetch pinned public edition without printing or publishing source",
            ),
        ]:
            text = (
                Path(__file__).resolve().parents[1] / ".github/workflows" / name
            ).read_text()
            self.assertIn(
                "- name: " + step + "\n        timeout-minutes: 3\n        run:", text
            )
            self.assertIn("raw,rdf=retry_public_download(download_material)", text)

    def test_returned_wrong_bytes_still_fail_original_downstream_validation(self):
        import hashlib

        download = Mock(return_value=(b"wrong edition", b"wrong rights"))
        sleep = Mock()
        raw, rdf = retry_public_download(download, sleep=sleep)
        with self.assertRaises(AssertionError):
            self.assertEqual(
                hashlib.sha256(raw).hexdigest(),
                hashlib.sha256(b"original pinned edition").hexdigest(),
            )
        with self.assertRaises(AssertionError):
            self.assertEqual(
                hashlib.sha256(rdf).hexdigest(),
                hashlib.sha256(b"original pinned rights").hexdigest(),
            )
        download.assert_called_once_with()
        sleep.assert_not_called()
