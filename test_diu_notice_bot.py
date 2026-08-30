import os
import unittest
from unittest.mock import patch

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "@testchannel")

import diu_notice_bot


class GetNoticeDetailTests(unittest.TestCase):
    def test_falls_back_to_title_when_notice_marker_missing(self):
        notice = {"id": "1", "title": "Important Notice", "url": "https://example.com/notice/1"}
        html_doc = """
        <html><body>
        <div>Header</div>
        <h1>Important Notice</h1>
        <p>Line one</p>
        <p>Line two</p>
        <div>Get in Touch</div>
        </body></html>
        """

        with patch("diu_notice_bot.fetch_html", return_value=html_doc):
            detail = diu_notice_bot.get_notice_detail(notice)

        self.assertEqual(detail["content"], "Line one\nLine two")

    def test_keeps_existing_notice_marker_path(self):
        notice = {"id": "2", "title": "Updated Notice", "url": "https://example.com/notice/2"}
        html_doc = """
        <html><body>
        <div>Notice</div>
        <div>Date: 2026-08-25</div>
        <h1>Updated Notice</h1>
        <p>Body line</p>
        <div>Useful Links</div>
        </body></html>
        """

        with patch("diu_notice_bot.fetch_html", return_value=html_doc):
            detail = diu_notice_bot.get_notice_detail(notice)

        self.assertIn("Date: 2026-08-25", detail["content"])
        self.assertIn("Body line", detail["content"])


class NormalizeChatIdTests(unittest.TestCase):
    def test_accepts_numeric_chat_id(self):
        self.assertEqual(diu_notice_bot.normalize_chat_id("-1001234567890"), "-1001234567890")

    def test_accepts_public_username(self):
        self.assertEqual(diu_notice_bot.normalize_chat_id("my_channel123"), "@my_channel123")

    def test_accepts_t_me_link(self):
        self.assertEqual(diu_notice_bot.normalize_chat_id("https://t.me/mychannel"), "@mychannel")

    def test_rejects_invalid_value(self):
        with self.assertRaises(ValueError):
            diu_notice_bot.normalize_chat_id("invalid-value")


if __name__ == "__main__":
    unittest.main()
