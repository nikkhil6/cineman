#!/usr/bin/env python3
"""
Dependency Verification Script
Verifies that all required packages from requirements.txt are installed and importable.
"""

import sys
import re
import importlib
from pathlib import Path
from typing import List, Tuple, Dict

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def parse_requirements_file(requirements_path: str) -> List[Tuple[str, str]]:
    """
    Parse requirements.txt and extract package names and version specifiers.
    Returns a list of tuples: (package_name, version_specifier)
    """
    requirements = []
    requirements_file = Path(requirements_path)
    
    if not requirements_file.exists():
        print(f"{Colors.RED}❌ Error: {requirements_path} not found!{Colors.END}")
        sys.exit(1)
    
    with open(requirements_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Remove inline comments
            if '#' in line:
                line = line[:line.index('#')].strip()
            
            # Parse package name and version specifier
            # Handles formats like: package>=1.0.0, package==1.0.0, package~=1.0.0, etc.
            match = re.match(r'^([a-zA-Z0-9_-]+(?:\[[^\]]+\])?)(.*)$', line)
            if match:
                package_name = match.group(1)
                version_spec = match.group(2).strip() if match.group(2) else ""
                
                # Remove extras (e.g., package[extra] -> package)
                package_name = re.sub(r'\[.*\]', '', package_name)
                
                requirements.append((package_name, version_spec))
    
    return requirements

def get_import_name(package_name: str) -> str:
    """
    Convert package name to import name (e.g., 'python-dotenv' -> 'dotenv')
    """
    # Common mappings for packages with different install vs import names
    mappings = {
        'python-dotenv': 'dotenv',
        'langchain-google-genai': 'langchain_google_genai',
        'langchain-core': 'langchain_core',
        'google-cloud-secret-manager': 'google.cloud.secretmanager',
        'google-auth': 'google.auth',
        'psycopg2-binary': 'psycopg2',
    }
    
    return mappings.get(package_name, package_name.replace('-', '_'))

def check_package(package_name: str, import_name: str) -> Tuple[bool, str, str]:
    """
    Check if a package can be imported and get its version.
    Returns: (success, version, error_message)
    """
    try:
        module = importlib.import_module(import_name)
        
        # Try to get version using importlib.metadata first (preferred method)
        version = "unknown"
        try:
            from importlib import metadata
            version = metadata.version(package_name)
        except (ImportError, Exception):
            # Fallback to pkg_resources
            try:
                import pkg_resources
                version = pkg_resources.get_distribution(package_name).version
            except (ImportError, Exception):
                # Last resort: try module attributes
                version_attrs = ['__version__', 'version', 'VERSION', '__VERSION__']
                for attr in version_attrs:
                    if hasattr(module, attr):
                        version = str(getattr(module, attr))
                        break
        
        return (True, version, "")
    
    except ImportError as e:
        return (False, "", str(e))
    except Exception as e:
        return (False, "", f"Unexpected error: {str(e)}")

def verify_dependencies(requirements_path: str = "requirements.txt") -> Dict:
    """
    Verify all dependencies from requirements.txt.
    Returns a dictionary with results.
    """
    print(f"{Colors.BOLD}{Colors.BLUE}🔍 Verifying dependencies from {requirements_path}...{Colors.END}\n")
    
    requirements = parse_requirements_file(requirements_path)
    
    if not requirements:
        print(f"{Colors.YELLOW}⚠️  No requirements found in {requirements_path}{Colors.END}")
        return {"total": 0, "installed": 0, "missing": 0, "details": []}
    
    results = {
        "total": len(requirements),
        "installed": 0,
        "missing": 0,
        "details": []
    }
    
    for package_name, version_spec in requirements:
        import_name = get_import_name(package_name)
        success, version, error = check_package(package_name, import_name)
        
        result_entry = {
            "package": package_name,
            "import_name": import_name,
            "version_spec": version_spec,
            "installed": success,
            "version": version,
            "error": error
        }
        
        results["details"].append(result_entry)
        
        if success:
            results["installed"] += 1
            version_display = f" (v{version})" if version != "unknown" else ""
            print(f"{Colors.GREEN}✅ {package_name}{version_display}{Colors.END}")
        else:
            results["missing"] += 1
            print(f"{Colors.RED}❌ {package_name} - {error}{Colors.END}")
    
    return results

def print_summary(results: Dict):
    """Print a summary of the verification results."""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}Summary:{Colors.END}")
    print(f"  Total packages: {results['total']}")
    print(f"  {Colors.GREEN}✅ Installed: {results['installed']}{Colors.END}")
    print(f"  {Colors.RED}❌ Missing: {results['missing']}{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
    
    if results['missing'] > 0:
        print(f"{Colors.YELLOW}💡 To install missing packages, run:{Colors.END}")
        print(f"   pip install -r requirements.txt")
        print(f"   or")
        print(f"   pip install {' '.join([d['package'] for d in results['details'] if not d['installed']])}\n")
        return False
    else:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 All dependencies are installed!{Colors.END}\n")
        return True

def main():
    """Main entry point for the verification script."""
    # Check if requirements.txt path is provided as argument
    requirements_path = sys.argv[1] if len(sys.argv) > 1 else "requirements.txt"
    
    try:
        results = verify_dependencies(requirements_path)
        success = print_summary(results)
        sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  Verification interrupted by user{Colors.END}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Fatal error: {e}{Colors.END}")
        sys.exit(1)

if __name__ == "__main__":
    main()

