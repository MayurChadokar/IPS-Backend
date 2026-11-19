import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.models.models import AmbitionMicSubmission
from main import app


class AmbitionMicEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        cls.TestSession = sessionmaker(bind=cls.engine)
        Base.metadata.create_all(cls.engine)
        cls.original_upload_dir = settings.UPLOAD_DIR
        cls.temp_dir = tempfile.TemporaryDirectory()
        settings.UPLOAD_DIR = cls.temp_dir.name

        def override_db():
            db = cls.TestSession()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.pop(get_db, None)
        settings.UPLOAD_DIR = cls.original_upload_dir
        Base.metadata.drop_all(cls.engine)
        cls.temp_dir.cleanup()

    def setUp(self):
        self.client = TestClient(app)
        db = self.TestSession()
        db.query(AmbitionMicSubmission).delete()
        db.commit()
        db.close()
        self.form = {
            "fullName": "Aarav Sharma",
            "email": "aarav@example.com",
            "phoneNumber": "9876543210",
            "city": "Indore",
            "educationLevel": "Undergraduate",
            "institutionName": "IPS Academy",
        }

    @patch("app.api.public.send_ambition_mic_entry", new_callable=AsyncMock)
    def test_valid_entry_is_stored_and_emailed_as_link(self, send_email):
        response = self.client.post(
            "/api/ambition-mic/entries",
            data=self.form,
            files={"video": ("entry.mp4", io.BytesIO(b"video-data"), "video/mp4")},
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"message": "Entry submitted successfully"})
        send_email.assert_awaited_once()
        entry = send_email.await_args.args[0]
        self.assertEqual(entry.full_name, "Aarav Sharma")
        self.assertEqual(entry.institution_name, "IPS Academy")
        video_url = send_email.await_args.args[1]
        self.assertTrue(
            video_url.startswith(
                f"{settings.BASE_URL.rstrip('/')}/api/ambition-mic/videos/"
            )
        )

        db = self.TestSession()
        submission = db.query(AmbitionMicSubmission).one()
        self.assertEqual(submission.email_status, "sent")
        self.assertTrue((Path(settings.UPLOAD_DIR) / submission.video_path).is_file())
        db.close()

        video_response = self.client.get(
            f"/api/ambition-mic/videos/{Path(submission.video_path).name}"
        )
        self.assertEqual(video_response.status_code, 200)
        self.assertEqual(video_response.content, b"video-data")

    @patch("app.api.public.send_ambition_mic_entry", new_callable=AsyncMock)
    def test_email_failure_does_not_lose_submission(self, send_email):
        from app.services.ambition_mic import AmbitionMicEmailError

        send_email.side_effect = AmbitionMicEmailError("Mailgun rejected the notification")
        response = self.client.post(
            "/api/ambition-mic/entries", data=self.form,
            files={"video": ("entry.mp4", io.BytesIO(b"video-data"), "video/mp4")},
        )
        self.assertEqual(response.status_code, 202)
        db = self.TestSession()
        submission = db.query(AmbitionMicSubmission).one()
        self.assertEqual(submission.email_status, "failed")
        self.assertTrue((Path(settings.UPLOAD_DIR) / submission.video_path).is_file())
        db.close()

    @patch("app.api.public.send_ambition_mic_entry", new_callable=AsyncMock)
    def test_non_video_file_is_rejected(self, send_email):
        response = self.client.post(
            "/api/ambition-mic/entries",
            data=self.form,
            files={"video": ("notes.pdf", io.BytesIO(b"not-video"), "application/pdf")},
        )

        self.assertEqual(response.status_code, 415)
        send_email.assert_not_awaited()

    @patch("app.api.public.send_ambition_mic_entry", new_callable=AsyncMock)
    @patch("app.api.public.settings.AMBITION_MIC_MAX_VIDEO_SIZE", 4)
    def test_oversized_video_is_rejected(self, send_email):
        response = self.client.post(
            "/api/ambition-mic/entries",
            data=self.form,
            files={"video": ("entry.mp4", io.BytesIO(b"12345"), "video/mp4")},
        )

        self.assertEqual(response.status_code, 413)
        send_email.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
