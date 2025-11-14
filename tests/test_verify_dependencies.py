"""
Tests for dependency verification script.
"""

import pytest
from unittest.mock import patch, mock_open, MagicMock
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.verify_dependencies import (
    parse_requirements_file,
    get_import_name,
    check_package,
    verify_dependencies,
)


class TestParseRequirementsFile:
    """Test parsing requirements.txt file."""

    def test_parse_valid_requirements(self):
        """Test parsing valid requirements file."""
        mock_content = """
# Web Framework
flask>=3.0.0
gunicorn>=21.2.0

# Comments and empty lines should be ignored

requests>=2.31.0
pydantic>=2.0.0
"""
        with patch("builtins.open", mock_open(read_data=mock_content)), patch.object(
            type("Path", (), {"exists": lambda self: True})(),
            "exists",
            return_value=True,
        ):
            with patch("scripts.verify_dependencies.Path") as mock_path:
                mock_path.return_value.exists.return_value = True
                requirements = parse_requirements_file("requirements.txt")

        assert len(requirements) >= 4
        package_names = [pkg for pkg, _ in requirements]
        assert "flask" in package_names
        assert "gunicorn" in package_names
        assert "requests" in package_names
        assert "pydantic" in package_names

    def test_parse_with_inline_comments(self):
        """Test parsing requirements with inline comments."""
        mock_content = "flask>=3.0.0  # Web framework"
        with patch("builtins.open", mock_open(read_data=mock_content)):
            with patch("scripts.verify_dependencies.Path") as mock_path:
                mock_path.return_value.exists.return_value = True
                requirements = parse_requirements_file("requirements.txt")

        assert len(requirements) == 1
        assert requirements[0][0] == "flask"

    def test_parse_file_not_found(self):
        """Test parsing when file doesn't exist."""
        with patch("scripts.verify_dependencies.Path") as mock_path:
            mock_path.return_value.exists.return_value = False

            with pytest.raises(SystemExit):
                parse_requirements_file("nonexistent.txt")


class TestGetImportName:
    """Test package name to import name conversion."""

    def test_get_import_name_standard(self):
        """Test standard package names."""
        assert get_import_name("flask") == "flask"
        assert get_import_name("requests") == "requests"
        assert get_import_name("pydantic") == "pydantic"

    def test_get_import_name_special_mapping(self):
        """Test special package name mappings."""
        assert get_import_name("python-dotenv") == "dotenv"
        assert get_import_name("langchain-google-genai") == "langchain_google_genai"
        assert get_import_name("langchain-core") == "langchain_core"

    def test_get_import_name_hyphen_to_underscore(self):
        """Test hyphen to underscore conversion."""
        assert get_import_name("some-package") == "some_package"


class TestCheckPackage:
    """Test package checking functionality."""

    @patch("scripts.verify_dependencies.importlib.import_module")
    def test_check_package_success(self, mock_import):
        """Test successful package check."""
        from importlib import metadata

        mock_module = MagicMock()
        mock_import.return_value = mock_module

        with patch.object(metadata, "version", return_value="3.0.0"):
            success, version, error = check_package("flask", "flask")

            assert success is True
            assert version == "3.0.0"
            assert error == ""

    @patch("scripts.verify_dependencies.importlib.import_module")
    def test_check_package_not_found(self, mock_import):
        """Test package not found."""
        mock_import.side_effect = ImportError("No module named 'nonexistent'")

        success, version, error = check_package("nonexistent", "nonexistent")

        assert success is False
        assert version == ""
        assert "No module named" in error

    @patch("scripts.verify_dependencies.importlib.import_module")
    def test_check_package_version_from_attribute(self, mock_import):
        """Test version retrieval from module attribute."""
        mock_module = MagicMock()
        mock_module.__version__ = "1.2.3"
        mock_import.return_value = mock_module

        with patch("scripts.verify_dependencies.metadata") as mock_metadata:
            mock_metadata.version.side_effect = Exception("metadata not available")

            with patch("scripts.verify_dependencies.pkg_resources") as mock_pkg:
                mock_pkg.get_distribution.side_effect = Exception("pkg not available")

                success, version, error = check_package("test-pkg", "test_pkg")

                assert success is True
                assert version == "1.2.3"


class TestVerifyDependencies:
    """Test full dependency verification."""

    @patch("scripts.verify_dependencies.parse_requirements_file")
    @patch("scripts.verify_dependencies.check_package")
    def test_verify_dependencies_all_installed(self, mock_check, mock_parse):
        """Test verification when all dependencies are installed."""
        mock_parse.return_value = [("flask", ">=3.0.0"), ("requests", ">=2.31.0")]
        mock_check.return_value = (True, "3.0.0", "")

        results = verify_dependencies("requirements.txt")

        assert results["total"] == 2
        assert results["installed"] == 2
        assert results["missing"] == 0

    @patch("scripts.verify_dependencies.parse_requirements_file")
    @patch("scripts.verify_dependencies.check_package")
    def test_verify_dependencies_some_missing(self, mock_check, mock_parse):
        """Test verification when some dependencies are missing."""
        mock_parse.return_value = [("flask", ">=3.0.0"), ("nonexistent", ">=1.0.0")]

        def check_side_effect(pkg_name, import_name):
            if pkg_name == "flask":
                return (True, "3.0.0", "")
            else:
                return (False, "", "Module not found")

        mock_check.side_effect = check_side_effect

        results = verify_dependencies("requirements.txt")

        assert results["total"] == 2
        assert results["installed"] == 1
        assert results["missing"] == 1

    @patch("scripts.verify_dependencies.parse_requirements_file")
    def test_verify_dependencies_empty_file(self, mock_parse):
        """Test verification with empty requirements file."""
        mock_parse.return_value = []

        results = verify_dependencies("requirements.txt")

        assert results["total"] == 0
        assert results["installed"] == 0
        assert results["missing"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
