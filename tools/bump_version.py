import re
import os
import sys
from datetime import datetime

VERSION_FILE = os.path.join(os.path.dirname(__file__), '..', 'app', 'version.py')

def bump_version():
    if not os.path.exists(VERSION_FILE):
        print(f"File {VERSION_FILE} not found. Creating a new one.")
        content = '__version__ = "1.0.0"\n__build__ = "initial"\n'
        with open(VERSION_FILE, 'w') as f:
            f.write(content)

    with open(VERSION_FILE, 'r') as f:
        content = f.read()

    # Find __version__ = "X.Y.Z"
    version_match = re.search(r'__version__\s*=\s*["\'](\d+)\.(\d+)\.(\d+)["\']', content)
    if not version_match:
        print("Could not find __version__ in file.")
        return False

    major, minor, patch = map(int, version_match.groups())
    new_patch = patch + 1
    new_version = f"{major}.{minor}.{new_patch}"
    new_build = datetime.now().strftime("%Y%m%d%H%M")

    # Replace version and build
    content = re.sub(r'__version__\s*=\s*["\']\d+\.\d+\.\d+["\']', f'__version__ = "{new_version}"', content)
    content = re.sub(r'__build__\s*=\s*["\'].*?["\']', f'__build__ = "{new_build}"', content)

    with open(VERSION_FILE, 'w') as f:
        f.write(content)

    print(f"Bumped version to {new_version} (Build: {new_build})")
    return True

if __name__ == "__main__":
    if bump_version():
        sys.exit(0)
    else:
        sys.exit(1)
