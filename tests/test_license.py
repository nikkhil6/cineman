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
        
        # Read LICENSE content once for all tests
        if self.license_path.exists():
            self.license_content = self.license_path.read_text()
        else:
            self.license_content = None

    def test_license_file_exists(self):
        """Verify that LICENSE file exists in the repository root."""
        self.assertTrue(
            self.license_path.exists(),
            f"LICENSE file not found at {self.license_path}"
        )

    def test_license_file_not_empty(self):
        """Verify that LICENSE file is not empty."""
        self.assertIsNotNone(
            self.license_content,
            f"LICENSE file not found at {self.license_path}"
        )
        self.assertGreater(
            len(self.license_content.strip()),
            0,
            "LICENSE file is empty"
        )

    def test_license_contains_mit_header(self):
        """Verify that LICENSE file contains MIT License header."""
        self.assertIsNotNone(
            self.license_content,
            f"LICENSE file not found at {self.license_path}"
        )
        self.assertIn(
            "MIT License",
            self.license_content,
            "LICENSE file should contain 'MIT License' header"
        )

    def test_license_contains_copyright_notice(self):
        """Verify that LICENSE file contains copyright notice."""
        self.assertIsNotNone(
            self.license_content,
            f"LICENSE file not found at {self.license_path}"
        )
        self.assertIn(
            "Copyright",
            self.license_content,
            "LICENSE file should contain copyright notice"
        )

    def test_license_contains_permission_grant(self):
        """Verify that LICENSE file contains permission grant."""
        self.assertIsNotNone(
            self.license_content,
            f"LICENSE file not found at {self.license_path}"
        )
        self.assertIn(
            "Permission is hereby granted",
            self.license_content,
            "LICENSE file should contain permission grant text"
        )

    def test_license_contains_warranty_disclaimer(self):
        """Verify that LICENSE file contains warranty disclaimer."""
        self.assertIsNotNone(
            self.license_content,
            f"LICENSE file not found at {self.license_path}"
        )
        self.assertIn(
            "WITHOUT WARRANTY OF ANY KIND",
            self.license_content,
            "LICENSE file should contain warranty disclaimer"
        )

    def test_license_is_readable(self):
        """Verify that LICENSE file is readable and well-formed."""
        self.assertIsNotNone(
            self.license_content,
            f"LICENSE file not found at {self.license_path}"
        )
        # Check that file has multiple lines
        lines = self.license_content.strip().split('\n')
        self.assertGreater(
            len(lines),
            10,
            "LICENSE file should have multiple lines of content"
        )


if __name__ == "__main__":
    unittest.main()
