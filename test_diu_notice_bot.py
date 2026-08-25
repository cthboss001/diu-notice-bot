import os
import unittest
from unittest.mock import patch

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test-chat-id")

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


if __name__ == "__main__":
    unittest.main()
