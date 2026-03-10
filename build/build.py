"""
Build script for WhisperWriter standalone binaries.

Usage:
    python build/build.py --variant api     # API-only build (~150-200 MB)
    python build/build.py --variant full    # Full build with local models (~2-3 GB)
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
DIST_DIR = os.path.join(PROJECT_ROOT, 'dist')


def get_version():
    """Read version from pyproject.toml."""
    pyproject_path = os.path.join(PROJECT_ROOT, 'pyproject.toml')
    with open(pyproject_path, 'r') as f:
        for line in f:
            if line.strip().startswith('version'):
                # Parse: version = "0.2.0"
                return line.split('=')[1].strip().strip('"').strip("'")
    return 'unknown'


def run_pyinstaller(variant):
    """Run PyInstaller with the appropriate spec file."""
    spec_file = os.path.join(SCRIPT_DIR, f'whisperwriter_{variant}.spec')
    if not os.path.exists(spec_file):
        print(f'Error: spec file not found: {spec_file}')
        sys.exit(1)

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--distpath', DIST_DIR,
        '--workpath', os.path.join(PROJECT_ROOT, 'build', 'pyinstaller_work'),
        spec_file,
    ]

    print(f'Running: {" ".join(cmd)}')
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print('PyInstaller build failed!')
        sys.exit(1)

    print('PyInstaller build completed successfully.')


def create_zip(variant, version):
    """Create a zip archive of the built application."""
    app_dir = os.path.join(DIST_DIR, 'WhisperWriter')
    if not os.path.isdir(app_dir):
        print(f'Error: build output not found: {app_dir}')
        sys.exit(1)

    zip_name = f'WhisperWriter-v{version}-windows-{variant}.zip'
    zip_path = os.path.join(DIST_DIR, zip_name)

    print(f'Creating archive: {zip_name}')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(app_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.join(
                    'WhisperWriter',
                    os.path.relpath(file_path, app_dir),
                )
                zf.write(file_path, arcname)

    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f'Archive created: {zip_path} ({size_mb:.1f} MB)')
    return zip_path


def main():
    parser = argparse.ArgumentParser(description='Build WhisperWriter standalone binary')
    parser.add_argument(
        '--variant',
        choices=['api', 'full'],
        required=True,
        help='Build variant: "api" (API-only, ~150-200 MB) or "full" (with local models, ~2-3 GB)',
    )
    parser.add_argument(
        '--no-zip',
        action='store_true',
        help='Skip creating zip archive',
    )
    args = parser.parse_args()

    version = get_version()
    print(f'Building WhisperWriter v{version} ({args.variant} variant)')

    run_pyinstaller(args.variant)

    if not args.no_zip:
        create_zip(args.variant, version)

    print('Done!')


if __name__ == '__main__':
    main()
