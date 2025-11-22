"""
Test suite for dependency pinning and reproducibility.
This ensures dependencies are installed at exact pinned versions.
"""
import os
import unittest
import subprocess
import re
from pathlib import Path


class TestDependencies(unittest.TestCase):
    """Test cases for dependency pinning verification."""

    def setUp(self):
        """Set up test fixtures."""
        # Get the root directory of the project (parent of tests directory)
        self.project_root = Path(__file__).parent.parent
        self.requirements_path = self.project_root / "requirements.txt"
        self.requirements_lock_path = self.project_root / "requirements.lock"
        
        # Read requirements.txt content
        if self.requirements_path.exists():
            self.requirements_content = self.requirements_path.read_text()
        else:
            self.requirements_content = None

    def test_requirements_file_exists(self):
        """Verify that requirements.txt file exists."""
        self.assertTrue(
            self.requirements_path.exists(),
            f"requirements.txt not found at {self.requirements_path}"
        )

    def test_requirements_lock_file_exists(self):
        """Verify that requirements.lock file exists."""
        self.assertTrue(
            self.requirements_lock_path.exists(),
            f"requirements.lock not found at {self.requirements_lock_path}"
        )

    def test_requirements_not_empty(self):
        """Verify that requirements.txt is not empty."""
        self.assertIsNotNone(
            self.requirements_content,
            f"requirements.txt not found at {self.requirements_path}"
        )
        self.assertGreater(
            len(self.requirements_content.strip()),
            0,
            "requirements.txt is empty"
        )

    def test_all_dependencies_are_pinned(self):
        """Verify that all direct dependencies use exact version pinning (==)."""
        self.assertIsNotNone(
            self.requirements_content,
            f"requirements.txt not found at {self.requirements_path}"
        )
        
        # Find all package lines (non-comment, non-empty)
        lines = self.requirements_content.split('\n')
        unpinned_packages = []
        
        for line in lines:
            # Strip whitespace
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Check if line contains a package specification
            # Valid pinned format: package==version
            if '>=' in line or '>' in line or '~=' in line or '<=' in line or '<' in line:
                unpinned_packages.append(line)
            elif '==' not in line and not line.startswith('-'):
                # Line doesn't have any version specifier
                unpinned_packages.append(line)
        
        self.assertEqual(
            len(unpinned_packages),
            0,
            f"Found unpinned dependencies (should use ==): {unpinned_packages}"
        )

    def test_installed_packages_match_requirements(self):
        """Verify that installed packages match the pinned versions in requirements.txt."""
        self.assertIsNotNone(
            self.requirements_content,
            f"requirements.txt not found at {self.requirements_path}"
        )
        
        # Parse requirements.txt for pinned versions
        pinned_packages = {}
        lines = self.requirements_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse package==version format
            if '==' in line:
                match = re.match(r'^([a-zA-Z0-9_-]+)==([0-9.]+[a-zA-Z0-9.]*)', line)
                if match:
                    package_name, version = match.groups()
                    # Normalize package name (pip uses lowercase with hyphens)
                    normalized_name = package_name.lower().replace('_', '-')
                    pinned_packages[normalized_name] = version
        
        # Get installed packages using pip freeze
        try:
            result = subprocess.run(
                ['pip', 'freeze'],
                capture_output=True,
                text=True,
                check=True
            )
            installed_packages = {}
            for line in result.stdout.split('\n'):
                line = line.strip()
                if '==' in line:
                    match = re.match(r'^([a-zA-Z0-9_-]+)==([0-9.]+[a-zA-Z0-9.]*)', line)
                    if match:
                        package_name, version = match.groups()
                        normalized_name = package_name.lower().replace('_', '-')
                        installed_packages[normalized_name] = version
        except subprocess.CalledProcessError as e:
            self.fail(f"Failed to run pip freeze: {e}")
        
        # Verify each pinned package is installed at the correct version
        mismatches = []
        for package_name, expected_version in pinned_packages.items():
            if package_name in installed_packages:
                installed_version = installed_packages[package_name]
                if installed_version != expected_version:
                    mismatches.append(
                        f"{package_name}: expected {expected_version}, got {installed_version}"
                    )
            else:
                mismatches.append(f"{package_name}: not installed")
        
        self.assertEqual(
            len(mismatches),
            0,
            f"Package version mismatches found:\n" + "\n".join(mismatches)
        )

    def test_requirements_lock_has_hashes(self):
        """Verify that requirements.lock contains package hashes for security."""
        self.assertTrue(
            self.requirements_lock_path.exists(),
            f"requirements.lock not found at {self.requirements_lock_path}"
        )
        
        lock_content = self.requirements_lock_path.read_text()
        
        # Check that the file contains hash entries
        self.assertIn(
            '--hash=sha256:',
            lock_content,
            "requirements.lock should contain SHA256 hashes for packages"
        )
        
        # Count the number of hash entries (should be many)
        hash_count = lock_content.count('--hash=sha256:')
        self.assertGreater(
            hash_count,
            50,  # Should have many hashes for all dependencies
            f"requirements.lock should contain many hashes (found {hash_count})"
        )


if __name__ == "__main__":
    unittest.main()
