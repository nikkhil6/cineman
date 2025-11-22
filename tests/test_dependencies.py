"""
Test suite for dependency pinning and reproducibility.
This ensures dependencies are installed at exact pinned versions.
"""
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
        """Verify that requirements.txt is not empty and contains package declarations."""
        self.assertIsNotNone(
            self.requirements_content,
            f"requirements.txt not found at {self.requirements_path}"
        )
        self.assertGreater(
            len(self.requirements_content.strip()),
            0,
            "requirements.txt is empty"
        )
        
        # Verify it contains at least one package declaration
        has_package = False
        for line in self.requirements_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and '==' in line:
                has_package = True
                break
        
        self.assertTrue(
            has_package,
            "requirements.txt should contain at least one package declaration with =="
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

    @staticmethod
    def _parse_package_line(line):
        """Parse a package==version line.
        
        Returns tuple of (normalized_name, version) or None if invalid.
        Handles valid Python package version specifiers according to PEP 440.
        """
        if '==' not in line:
            return None
        
        # PEP 440 compliant version pattern
        # Matches: N.N.N, N.N.NaN, N.N.NbN, N.N.NrcN, N.N.N.postN, N.N.N+local, etc.
        version_pattern = r'[0-9]+(?:\.[0-9]+)*(?:[a-zA-Z0-9]+(?:\.[0-9]+)?)?(?:\+[a-zA-Z0-9.]+)?'
        match = re.match(r'^([a-zA-Z0-9_.-]+)==(' + version_pattern + r')$', line)
        if match:
            package_name, version = match.groups()
            # Normalize package name (pip uses lowercase with hyphens)
            normalized_name = package_name.lower().replace('_', '-')
            return (normalized_name, version.strip())
        return None

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
            
            parsed = self._parse_package_line(line)
            if parsed:
                normalized_name, version = parsed
                pinned_packages[normalized_name] = version
        
        # Get installed packages using pip freeze with timeout
        try:
            result = subprocess.run(
                ['pip', 'freeze'],
                capture_output=True,
                text=True,
                check=True,
                timeout=30  # Prevent hanging processes
            )
            installed_packages = {}
            for line in result.stdout.split('\n'):
                line = line.strip()
                parsed = self._parse_package_line(line)
                if parsed:
                    normalized_name, version = parsed
                    installed_packages[normalized_name] = version
        except subprocess.TimeoutExpired:
            self.fail("pip freeze command timed out after 30 seconds")
        except subprocess.CalledProcessError as e:
            self.fail(f"Failed to run pip freeze: {e}")
        except FileNotFoundError:
            self.fail("pip command not found in PATH")
        
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
        
        # Count the number of hash entries
        # Each package should have at least one hash, typically multiple for different platforms
        hash_count = lock_content.count('--hash=sha256:')
        
        # Calculate minimum expected hashes: at least one hash per direct dependency
        # Count direct dependencies from requirements.txt
        direct_deps_count = 0
        for line in self.requirements_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and '==' in line:
                direct_deps_count += 1
        
        # We expect many more hashes than direct dependencies (multiple per package for different wheels)
        self.assertGreater(
            hash_count,
            direct_deps_count,
            f"requirements.lock should contain hashes for all packages (expected >{direct_deps_count}, found {hash_count})"
        )


if __name__ == "__main__":
    unittest.main()
