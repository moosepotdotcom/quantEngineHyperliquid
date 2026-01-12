#!/usr/bin/env python3
"""
Pre-deployment validation script.
Run this BEFORE deploying to Cloud Run to catch missing dependencies.

Usage: python3 scripts/validate_deployment.py
"""

import ast
import os
import sys
from pathlib import Path

# Known standard library modules (not needed in requirements.txt)
STDLIB = {
    'os', 'sys', 'json', 'time', 'datetime', 'threading', 'random', 'math',
    'collections', 'itertools', 'functools', 'pathlib', 'logging', 'pickle',
    'hashlib', 're', 'copy', 'io', 'traceback', 'typing', 'abc', 'warnings',
    'dataclasses', 'enum', 'subprocess', 'shutil', 'tempfile', 'glob',
    'statistics', 'decimal', 'fractions', 'sqlite3', 'csv', 'configparser',
    'unittest', 'ast', 'textwrap', 'string', 'pprint', 'struct', 'socket',
    'http', 'urllib', 'base64', 'hmac', 'secrets', 'uuid', 'platform',
    'contextlib', 'concurrent', 'queue', 'multiprocessing', 'signal', 'gc',
    'argparse', 'asyncio', 'atexit', 'curses', 'fnmatch', 'importlib',
    'inspect', 'pdb', 'selectors', 'turtle', 'wave', 'webbrowser', 'xml',
    '__future__', 'builtins', 'types', 'operator', 'dis', 'code', 'codeop',
}

# Map import names to pip package names
IMPORT_TO_PACKAGE = {
    'sklearn': 'scikit-learn',
    'cv2': 'opencv-python',
    'PIL': 'pillow',
    'yaml': 'pyyaml',
    'bs4': 'beautifulsoup4',
    'talib': 'TA-Lib',
    'xgboost': 'xgboost',
    'lightgbm': 'lightgbm',
    'joblib': 'joblib',
    'flask_socketio': 'flask-socketio',
    'eth_account': 'eth-account',
    'eth_abi': 'eth-abi',
    'eth_utils': 'eth-utils',
    'eth_keys': 'eth-keys',
    'eth_rlp': 'eth-rlp',
    'eth_hash': 'eth-hash',
    'eth_keyfile': 'eth-keyfile',
    'eth_typing': 'eth-typing',
    'hyperliquid': 'hyperliquid-python-sdk',
}

# Core project directories to scan
CORE_DIRS = ['agents', 'strategies', 'data', 'utils', 'features', 'research', 
             'dashboard', 'optimization', 'scripts', 'tests']

# Local modules that aren't pip packages
LOCAL_MODULES = {
    'agents', 'strategies', 'data', 'utils', 'features', 'research',
    'dashboard', 'optimization', 'scripts', 'tests', 'trading_agent',
    'backtest_engine', 'feature_generator', 'dontshare', 'dontshare_config',
    'strategies_complete', 'strategy_deployer', 'config', 'settings',
    'models', 'helpers', 'core', 'app', 'main', 'run', 'start'
}


def get_imports_from_file(filepath: Path) -> set:
    """Extract all import names from a Python file."""
    imports = set()
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            tree = ast.parse(f.read(), filename=str(filepath))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
    except Exception:
        pass  # Silently skip unparseable files
    
    return imports


def get_requirements() -> set:
    """Get all packages from requirements.txt."""
    packages = set()
    req_file = Path('requirements.txt')
    
    if not req_file.exists():
        print("❌ requirements.txt not found!")
        return packages
    
    with open(req_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # Extract package name (remove version specifiers)
                pkg = line.split('>=')[0].split('==')[0].split('<')[0].split('>')[0]
                packages.add(pkg.lower().replace('-', '_'))  # normalize
                packages.add(pkg.lower().replace('_', '-'))  # both variants
                packages.add(pkg.lower())
    
    return packages


def validate():
    """Main validation function."""
    print("=" * 60)
    print("🔍 PRE-DEPLOYMENT VALIDATION")
    print("=" * 60)
    
    # Get ONLY core project Python files
    py_files = []
    
    # Root level py files
    for f in Path('.').glob('*.py'):
        py_files.append(f)
    
    # Core directories
    for dirname in CORE_DIRS:
        if Path(dirname).exists():
            py_files.extend(Path(dirname).rglob('*.py'))
    
    print(f"\n📁 Scanning {len(py_files)} core Python files...\n")
    
    # Collect all imports
    all_imports = set()
    for filepath in py_files:
        imports = get_imports_from_file(filepath)
        all_imports.update(imports)
    
    # Get requirements
    requirements = get_requirements()
    
    # Find missing packages
    missing = []
    for imp in sorted(all_imports):
        # Skip stdlib
        if imp in STDLIB:
            continue
        
        # Skip local modules
        if imp in CORE_DIRS or imp in LOCAL_MODULES:
            continue
        
        # Map import name to package name
        pkg_name = IMPORT_TO_PACKAGE.get(imp, imp).lower()
        pkg_normalized = pkg_name.replace('-', '_')
        
        # Check if in requirements
        if pkg_name not in requirements and pkg_normalized not in requirements:
            missing.append((imp, pkg_name))
    
    # Report results
    if missing:
        print("❌ MISSING DEPENDENCIES DETECTED:\n")
        for imp, pkg in missing:
            print(f"   - import '{imp}' → pip package: {pkg}")
        print(f"\n⚠️  Add these to requirements.txt before deploying!\n")
        
        print("📝 Suggested additions to requirements.txt:")
        print("-" * 40)
        for _, pkg in missing:
            print(f"{pkg}")
        print("-" * 40)
        
        return False
    else:
        print("✅ All imports are covered by requirements.txt!")
        print("✅ Safe to deploy to Cloud Run.\n")
        return True


if __name__ == '__main__':
    success = validate()
    sys.exit(0 if success else 1)
