#!/usr/bin/env python3
"""Regression tests for the conservative candidate checker (no network needed)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("check_candidate.py")


class CandidateCheckerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        (root / "research").mkdir()
        (root / "research" / "Australia.json").write_text(
            json.dumps({
                "revision": "test-au",
                "labels": [{"name": "Ruff Kutz", "status": "contextual"}],
                "artist_provenance": [{"name": "Pugilist", "status": "qualified"}],
                "listening": [
                    {"label": "Self-released", "release": "Eight Foot At Fisho's – Search: Atmospheric Jungle (SELEKTAH)", "status": "prior_listening_verdict_unrecovered"},
                    {"label": "Ruff Kutz", "release": "Pugilist & Tamen – Source EP", "status": "qualified"}
                ],
                "open_tasks": []
            }, ensure_ascii=False), encoding="utf-8"
        )
        (root / "Australia.md").write_text(
            "- Hidden Artist – Old Track was previously checked; missing in the JSON.\n",
            encoding="utf-8"
        )
        self.root = root

    def check(self, expected, expected_text, *args):
        p = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(self.root), *args],
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(p.returncode, expected, p.stdout + p.stderr)
        self.assertIn(expected_text, p.stdout + p.stderr)

    def test_existing_release_from_json_blocks_reassignment(self):
        self.check(2, "PRIOR MATERIAL REFERENCED", "--track", "SELEKTAH")

    def test_existing_ep_blocks_reassignment(self):
        self.check(2, "PRIOR MATERIAL REFERENCED", "--release", "Source EP")

    def test_markdown_only_artist_requires_check(self):
        self.check(1, "EXISTING CONTEXT", "--artist", "Hidden Artist")

    def test_markdown_only_track_requires_check(self):
        self.check(1, "EXISTING CONTEXT", "--track", "Old Track")

    def test_known_artist_does_not_block_all_new_tracks(self):
        self.check(1, "EXISTING CONTEXT", "--artist", "Pugilist")

    def test_no_repository_match_is_not_proof_of_newness(self):
        self.check(0, "NOT proof of newness", "--artist", "Unknown Performer")

    def test_requires_search_term(self):
        p = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.root)],
                           text=True, capture_output=True, check=False)
        self.assertEqual(p.returncode, 2)
        self.assertIn("Provide at least one", p.stderr)


if __name__ == "__main__":
    unittest.main()
