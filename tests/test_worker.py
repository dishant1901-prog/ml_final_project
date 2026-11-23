"""The durable worker executes a bounded synthetic analysis and rejects path escape."""

import tempfile
import unittest
from pathlib import Path

from backend.app.settings import Settings
from scripts.local_worker import execute
from tests.helpers import synthetic_manifest


class AnalysisWorker(unittest.TestCase):
    def test_executes_local_job_inside_configured_roots(self):
        with tempfile.TemporaryDirectory(dir="data/test-runs") as temporary:
            root = Path(temporary).resolve()
            manifest = synthetic_manifest(root / "inputs", optical=True)
            settings = Settings(
                _env_file=None,
                data_root=root / "copilot",
                himaroad_data_dir=root,
            )
            result = execute(
                {
                    "provider": "local",
                    "manifest": str(manifest),
                    "bbox": None,
                    "polygon": None,
                    "event_date": "2026-08-26",
                    "cutoff": None,
                    "detector": "baseline",
                    "output": str(root / "outputs" / "worker-test"),
                    "project": None,
                    "model_config": None,
                },
                settings,
            )
            self.assertTrue((Path(result) / "report.json").is_file())

    def test_rejects_output_outside_analysis_root(self):
        with tempfile.TemporaryDirectory(dir="data/test-runs") as temporary:
            root = Path(temporary).resolve()
            settings = Settings(
                _env_file=None,
                data_root=root / "copilot",
                himaroad_data_dir=root,
            )
            with self.assertRaisesRegex(ValueError, "outside"):
                execute(
                    {
                        "provider": "local",
                        "detector": "baseline",
                        "event_date": "2026-08-26",
                        "output": str(root.parent / "escape"),
                    },
                    settings,
                )


if __name__ == "__main__":
    unittest.main()
