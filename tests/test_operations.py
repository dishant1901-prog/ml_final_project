"""Local production controls: credentials, durable sessions, queue and backups."""

import asyncio
import base64
import tempfile
import unittest
from pathlib import Path

from backend.app.api import create_app
from backend.app.operations import RuntimeStore, hash_password, verify_password
from backend.app.settings import Settings
from tests.helpers import asgi_request


class LocalAuthentication(unittest.TestCase):
    def test_scrypt_password_hash_is_salted_and_verifiable(self):
        first = hash_password("correct horse battery staple")
        second = hash_password("correct horse battery staple")
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password("correct horse battery staple", first))
        self.assertFalse(verify_password("wrong password here", first))

    def test_admin_and_viewer_roles_are_enforced(self):
        with tempfile.TemporaryDirectory(dir="data/test-runs") as temporary:
            root = Path(temporary).resolve()
            settings = Settings(
                _env_file=None,
                data_root=root / "copilot",
                himaroad_data_dir=root,
                local_auth_admin_username="admin",
                local_auth_admin_password_hash=hash_password("administrator password"),
                local_auth_viewer_username="viewer",
                local_auth_viewer_password_hash=hash_password("viewer password value"),
                local_auth_cookie_secret="cookie-secret-with-more-than-thirty-two-characters",
                local_service_token="service-token-with-more-than-thirty-two-characters",
            )
            app = create_app(settings)

            def request(username=None, password=None, **kwargs):
                extra = []
                if username is not None:
                    value = base64.b64encode(f"{username}:{password}".encode())
                    extra.append((b"authorization", b"Basic " + value))
                return asyncio.run(
                    asgi_request(
                        app, "GET", "/api/admin/runtime", extra_headers=extra, **kwargs
                    )
                )

            self.assertEqual(request()[0], 401)
            self.assertEqual(request("viewer", "viewer password value")[0], 403)
            self.assertEqual(request("admin", "administrator password")[0], 200)
            self.assertEqual(
                asyncio.run(
                    asgi_request(
                        app,
                        "GET",
                        "/api/admin/runtime",
                        extra_headers=[
                            (
                                b"x-himaroad-service-token",
                                b"service-token-with-more-than-thirty-two-characters",
                            )
                        ],
                    )
                )[0],
                200,
            )


class DurableRuntime(unittest.TestCase):
    def test_sessions_and_jobs_survive_store_reopen(self):
        with tempfile.TemporaryDirectory(dir="data/test-runs") as temporary:
            database = Path(temporary) / "runtime.sqlite3"
            store = RuntimeStore(database, max_jobs=2)
            store.create_session("a" * 64, "b" * 64, 3600, 2)
            identifier = store.enqueue("analysis", {"provider": "local"})

            reopened = RuntimeStore(database, max_jobs=2)
            self.assertEqual(reopened.session("a" * 64), "b" * 64)
            claimed = reopened.claim()
            self.assertEqual(claimed[0], identifier)
            reopened.finish(identifier, result="/safe/result")
            self.assertEqual(reopened.job(identifier)["state"], "complete")
            reopened.delete_session("a" * 64)
            self.assertIsNone(reopened.session("a" * 64))

    def test_queue_is_bounded(self):
        with tempfile.TemporaryDirectory(dir="data/test-runs") as temporary:
            store = RuntimeStore(Path(temporary) / "runtime.sqlite3", max_jobs=1)
            store.enqueue("analysis", {"provider": "local"})
            with self.assertRaisesRegex(RuntimeError, "job_queue_full"):
                store.enqueue("analysis", {"provider": "local"})


if __name__ == "__main__":
    unittest.main()
