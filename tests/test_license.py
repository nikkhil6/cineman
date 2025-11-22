"""
Test suite for LICENSE file presence and content verification.
This ensures the project maintains proper open source licensing.
"""
import os
import unittest
from pathlib import Path


class TestLicense(unittest.TestCase):
    """Test cases for LICENSE file verification."""

    def setUp(self):
        """Set up test fixtures."""
        # Get the root directory of the project (parent of tests directory)
        self.project_root = Path(__file__).parent.parent
        self.license_path = self.project_root / "LICENSE"

    def test_license_file_exists(self):
        """Verify that LICENSE file exists in the repository root."""
        self.assertTrue(
            self.license_path.exists(),
            f"LICENSE file not found at {self.license_path}"
        )

    def test_license_file_not_empty(self):
        """Verify that LICENSE file is not empty."""
        self.assertTrue(
            self.license_path.exists(),
            f"LICENSE file not found at {self.license_path}"
        )
        content = self.license_path.read_text()
        self.assertGreater(
            len(content.strip()),
            0,
            "LICENSE file is empty"
        )

    def test_license_contains_mit_header(self):
        """Verify that LICENSE file contains MIT License header."""
        content = self.license_path.read_text()
        self.assertIn(
            "MIT License",
            content,
            "LICENSE file should contain 'MIT License' header"
        )

    def test_license_contains_copyright_notice(self):
        """Verify that LICENSE file contains copyright notice."""
        content = self.license_path.read_text()
        self.assertIn(
            "Copyright",
            content,
            "LICENSE file should contain copyright notice"
        )

    def test_license_contains_permission_grant(self):
        """Verify that LICENSE file contains permission grant."""
        content = self.license_path.read_text()
        self.assertIn(
            "Permission is hereby granted",
            content,
            "LICENSE file should contain permission grant text"
        )

    def test_license_contains_warranty_disclaimer(self):
        """Verify that LICENSE file contains warranty disclaimer."""
        content = self.license_path.read_text()
        self.assertIn(
            "WITHOUT WARRANTY OF ANY KIND",
            content,
            "LICENSE file should contain warranty disclaimer"
        )

    def test_license_is_readable(self):
        """Verify that LICENSE file is readable and well-formed."""
        try:
            content = self.license_path.read_text()
            # Check that file has multiple lines
            lines = content.strip().split('\n')
            self.assertGreater(
                len(lines),
                10,
                "LICENSE file should have multiple lines of content"
            )
        except Exception as e:
            self.fail(f"Failed to read LICENSE file: {e}")


if __name__ == "__main__":
    unittest.main()
