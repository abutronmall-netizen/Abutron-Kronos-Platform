"""Synthetic-only contract tests. No live customer DB or mail is accessed."""
import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app import privacy_optout

KEY = "5c" * 32


class FakeDB:
    def __init__(self, result):
        self.result = result
        self.calls = 0
        self.statement = ""
        self.params = {}

    async def scalar(self, stmt, params):
        self.calls += 1
        self.statement = str(stmt)
        self.params = params
        return self.result


class FailingDB:
    async def scalar(self, *args, **kwargs):
        raise RuntimeError("simulated database unavailability")


class PrivacyOptOutTests(unittest.IsolatedAsyncioTestCase):
    async def test_opted_out_registration_rejected(self):
        with patch.dict(os.environ, {"ABUTRON_V7_PRIVACY_OPTOUT_KEY": KEY}):
            db = FakeDB(True)
            with self.assertRaises(HTTPException) as ctx:
                await privacy_optout.reject_opted_out_registration(db, "test@example.invalid")
            self.assertEqual(ctx.exception.status_code, 409)
            self.assertEqual(db.calls, 1)
            self.assertNotIn("test@example.invalid", str(db.statement) + str(db.params))

    async def test_unlisted_registration_allowed(self):
        with patch.dict(os.environ, {"ABUTRON_V7_PRIVACY_OPTOUT_KEY": KEY}):
            self.assertIsNone(await privacy_optout.reject_opted_out_registration(
                FakeDB(False), "new@example.invalid"))

    async def test_no_key_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as ctx:
                await privacy_optout.reject_opted_out_registration(FakeDB(False), "test@example.invalid")
            self.assertEqual(ctx.exception.status_code, 503)

    async def test_bad_key_fails_closed(self):
        with patch.dict(os.environ, {"ABUTRON_V7_PRIVACY_OPTOUT_KEY": "invalid"}):
            with self.assertRaises(HTTPException) as ctx:
                await privacy_optout.reject_opted_out_registration(FakeDB(False), "test@example.invalid")
            self.assertEqual(ctx.exception.status_code, 503)

    async def test_zero_key_fails_closed(self):
        with patch.dict(os.environ, {"ABUTRON_V7_PRIVACY_OPTOUT_KEY": "00" * 32}):
            with self.assertRaises(HTTPException) as ctx:
                await privacy_optout.reject_opted_out_registration(FakeDB(False), "test@example.invalid")
            self.assertEqual(ctx.exception.status_code, 503)

    async def test_database_error_fails_closed(self):
        with patch.dict(os.environ, {"ABUTRON_V7_PRIVACY_OPTOUT_KEY": KEY}):
            with self.assertRaises(HTTPException) as ctx:
                await privacy_optout.reject_opted_out_registration(FailingDB(), "test@example.invalid")
            self.assertEqual(ctx.exception.status_code, 503)

    async def test_normalization_is_case_insensitive(self):
        self.assertEqual(privacy_optout.email_fingerprint(" USER@EXAMPLE.INVALID ", KEY),
                         privacy_optout.email_fingerprint("user@example.invalid", KEY))

    async def test_different_emails_have_different_digests(self):
        self.assertNotEqual(privacy_optout.email_fingerprint("a@example.invalid", KEY),
                            privacy_optout.email_fingerprint("b@example.invalid", KEY))

    async def test_different_keys_have_different_digests(self):
        self.assertNotEqual(privacy_optout.email_fingerprint("a@example.invalid", KEY),
                            privacy_optout.email_fingerprint("a@example.invalid", "6d" * 32))

    async def test_ambiguous_result_fails_closed(self):
        with patch.dict(os.environ, {"ABUTRON_V7_PRIVACY_OPTOUT_KEY": KEY}):
            with self.assertRaises(HTTPException) as ctx:
                await privacy_optout.reject_opted_out_registration(FakeDB(None), "test@example.invalid")
            self.assertEqual(ctx.exception.status_code, 503)

    async def test_db_gets_only_digest_not_email(self):
        with patch.dict(os.environ, {"ABUTRON_V7_PRIVACY_OPTOUT_KEY": KEY}):
            db = FakeDB(True)
            self.assertTrue(await privacy_optout.is_opted_out(db, "unknown@example.invalid"))
            self.assertEqual(len(db.params["fingerprint"]), 64)
            self.assertNotIn("@", str(db.params))


if __name__ == "__main__":
    unittest.main()
