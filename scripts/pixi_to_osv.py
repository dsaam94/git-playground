#!/usr/bin/env python3
"""
Parse pixi.lock file and convert to OSV-Scanner compatible formats.

This script extracts package information from pixi.lock and creates:
1. requirements.txt (Python packages in pip format)
2. conda-requirements.txt (All conda packages)
3. osv-lockfile.json (OSV-Scanner compatible manifest)
"""

import json
import re
import yaml
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse

def parse_pixi_lock(lock_file_path: str) -> Dict:
    """Parse pixi.lock YAML file."""
    try:
        with open(lock_file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data
    except Exception as e:
        print(f"❌ Error parsing pixi.lock: {e}")
        return {}

def extract_package_info(conda_url: str) -> Tuple[str, str]:
    """Extract package name and version from conda URL."""
    # Example URL: https://conda.anaconda.org/conda-forge/linux-64/brotli-python-1.1.0-py39hf88036b_3.conda
    filename = Path(urlparse(conda_url).path).name
    
    # Remove file extensions
    filename = re.sub(r'\.(conda|tar\.bz2)$', '', filename)
    
    # Pattern to match: package-name-version-build_hash
    # Look for version pattern: numbers with dots, followed by build info
    match = re.match(r'^(.+?)-(\d+(?:\.\d+)*(?:\w+)?)-.*$', filename)
    
    if match:
        name = match.group(1)
        version = match.group(2)
        return name, version
    
    # Fallback: try to find version by looking for number patterns
    parts = filename.split('-')
    if len(parts) >= 2:
        for i in range(len(parts)-1, 0, -1):
            if re.match(r'^\d+', parts[i]):
                name = '-'.join(parts[:i])
                version = parts[i]
                return name, version
    
    # If we can't parse it, return the filename as name
    return filename, "unknown"

def extract_packages_from_pixi_lock(data: Dict) -> List[Dict]:
    """Extract all packages from pixi.lock data structure."""
    packages = []
    
    if 'environments' not in data:
        print("❌ No environments found in pixi.lock")
        return packages
    
    for env_name, env_data in data['environments'].items():
        if 'packages' not in env_data:
            continue
            
        for platform, platform_packages in env_data['packages'].items():
            for package_entry in platform_packages:
                if 'conda' in package_entry:
                    conda_url = package_entry['conda']
                    name, version = extract_package_info(conda_url)
                    
                    packages.append({
                        'name': name,
                        'version': version,
                        'environment': env_name,
                        'platform': platform,
                        'url': conda_url,
                        'ecosystem': 'conda'
                    })
    
    return packages

def create_requirements_txt(packages: List[Dict], output_path: str) -> int:
    """Create requirements.txt file for Python packages."""
    python_packages = set()
    
    # Identify Python packages based on common indicators
    python_indicators = {
        'python', 'py-', 'pip', 'setuptools', 'wheel', 'certifi', 
        'charset-normalizer', 'idna', 'urllib3', 'requests', 'numpy',
        'pandas', 'scipy', 'matplotlib', 'seaborn', 'scikit-learn',
        'tensorflow', 'torch', 'pytorch', 'flask', 'django', 'fastapi',
        'pydantic', 'sqlalchemy', 'psycopg2', 'pymongo', 'redis-py',
        'brotli-python', 'pycparser', 'pysocks', 'pyyaml', 'markupsafe',
        'jinja2', 'networkx', 'gitpython', 'typing_extensions'
    }
    
    for pkg in packages:
        name = pkg['name'].lower()
        version = pkg['version']
        
        # Check if it's a Python package
        if (any(indicator in name for indicator in python_indicators) or 
            name.startswith('py') or 
            '-py' in name or 
            name.endswith('-python') or
            'python' in name):
            
            if version != "unknown":
                # Use standard pip format: package==version
                python_packages.add(f"{pkg['name']}=={version}")
            else:
                python_packages.add(pkg['name'])
    
    # Write to requirements.txt
    with open(output_path, 'w', encoding='utf-8') as f:
        for pkg in sorted(python_packages):
            f.write(f"{pkg}\n")
    
    return len(python_packages)

def create_conda_requirements(packages: List[Dict], output_path: str) -> int:
    """Create conda-requirements.txt for all conda packages."""
    conda_packages = set()
    
    for pkg in packages:
        if pkg['version'] != "unknown":
            conda_packages.add(f"{pkg['name']}=={pkg['version']}")
        else:
            conda_packages.add(pkg['name'])
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for pkg in sorted(conda_packages):
            f.write(f"{pkg}\n")
    
    return len(conda_packages)

def create_osv_lockfile(packages: List[Dict], output_path: str) -> int:
    """Create OSV-Scanner compatible lockfile JSON."""
    # Create a lockfile format that OSV-Scanner can understand
    lockfile = {
        "lockfileVersion": 1,
        "source": "pixi.lock",
        "generated": True,
        "metadata": {
            "generator": "pixi_to_osv.py",
            "total_packages": len(packages),
            "environments": list(set(pkg['environment'] for pkg in packages)),
            "platforms": list(set(pkg['platform'] for pkg in packages))
        },
        "packages": {}
    }
    
    # Group packages by name and version
    for pkg in packages:
        pkg_key = f"{pkg['name']}@{pkg['version']}"
        lockfile["packages"][pkg_key] = {
            "name": pkg['name'],
            "version": pkg['version'],
            "resolved": pkg['url'],
            "ecosystem": "conda",
            "environment": pkg['environment'],
            "platform": pkg['platform']
        }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(lockfile, f, indent=2)
    
    return len(lockfile["packages"])

def create_package_json_style(packages: List[Dict], output_path: str) -> int:
    """Create a package.json style lockfile for better OSV compatibility."""
    # Some OSV scanners work better with npm-style package files
    package_lock = {
        "name": "pixi-converted-packages",
        "lockfileVersion": 2,
        "requires": True,
        "packages": {
            "": {
                "name": "pixi-converted-packages",
                "dependencies": {}
            }
        },
        "dependencies": {}
    }
    
    for pkg in packages:
        if pkg['version'] != "unknown":
            package_lock["packages"][""]["dependencies"][pkg['name']] = pkg['version']
            package_lock["dependencies"][pkg['name']] = {
                "version": pkg['version'],
                "resolved": pkg['url'],
                "ecosystem": "conda"
            }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(package_lock, f, indent=2)
    
    return len(package_lock["dependencies"])

def main():
    """Main function to convert pixi.lock to OSV-compatible formats."""
    pixi_lock_path = "pixi.lock"
    
    print("🔍 Converting pixi.lock to OSV-Scanner compatible formats...")
    
    if not Path(pixi_lock_path).exists():
        print(f"❌ Error: {pixi_lock_path} not found")
        sys.exit(1)
    
    # Parse pixi.lock
    data = parse_pixi_lock(pixi_lock_path)
    if not data:
        print("❌ Failed to parse pixi.lock")
        sys.exit(1)
    
    # Extract packages
    packages = extract_packages_from_pixi_lock(data)
    if not packages:
        print("❌ No packages found in pixi.lock")
        sys.exit(1)
    
    print(f"📦 Found {len(packages)} packages from pixi.lock")
    
    # Create output directory
    output_dir = Path("osv-lockfiles")
    output_dir.mkdir(exist_ok=True)
    
    # Generate different OSV-compatible formats
    print("\n🛠️  Creating OSV-compatible lockfiles...")
    
    # 1. requirements.txt for Python packages
    python_count = create_requirements_txt(packages, output_dir / "requirements.txt")
    print(f"   ✅ requirements.txt: {python_count} Python packages")
    
    # 2. conda-requirements.txt for all conda packages  
    conda_count = create_conda_requirements(packages, output_dir / "conda-requirements.txt")
    print(f"   ✅ conda-requirements.txt: {conda_count} conda packages")
    
    # 3. OSV lockfile JSON
    osv_count = create_osv_lockfile(packages, output_dir / "osv-lockfile.json")
    print(f"   ✅ osv-lockfile.json: {osv_count} packages in OSV format")
    
    # 4. Package.json style for better compatibility
    npm_count = create_package_json_style(packages, output_dir / "package-lock.json")
    print(f"   ✅ package-lock.json: {npm_count} packages in npm-style format")
    
    # Create summary report
    summary = {
        "conversion_summary": {
            "source_file": pixi_lock_path,
            "total_packages_found": len(packages),
            "python_packages": python_count,
            "conda_packages": conda_count,
            "environments": list(set(pkg['environment'] for pkg in packages)),
            "platforms": list(set(pkg['platform'] for pkg in packages))
        },
        "osv_files_created": [
            "requirements.txt",
            "conda-requirements.txt", 
            "osv-lockfile.json",
            "package-lock.json"
        ],
        "packages": packages[:10]  # First 10 packages as sample
    }
    
    with open(output_dir / "conversion-summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    print("\n🎯 Conversion completed!")
    print(f"   📁 Output directory: {output_dir}")
    print(f"   📊 Total packages: {len(packages)}")
    print(f"   🐍 Python packages: {python_count}")
    print(f"   📦 All packages: {conda_count}")
    
    print("\n📋 Files created for OSV-Scanner:")
    print("   • requirements.txt - Python packages (pip ecosystem)")
    print("   • conda-requirements.txt - All conda packages")
    print("   • osv-lockfile.json - Custom OSV manifest")
    print("   • package-lock.json - npm-style format")
    print("   • conversion-summary.json - Detailed conversion report")
    
    print("\n🔍 To scan with OSV-Scanner:")
    print(f"   osv-scanner {output_dir}/requirements.txt")
    print(f"   osv-scanner {output_dir}/")

if __name__ == "__main__":
    main()
