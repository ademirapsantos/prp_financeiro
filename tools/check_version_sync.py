import json
import os
import re
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VERSION_FILE = os.path.join(ROOT_DIR, "app", "version.py")
MANIFESTS = {
    "dev": os.path.join(ROOT_DIR, "manifests", "dev.json"),
    "hml": os.path.join(ROOT_DIR, "manifests", "hml.json"),
    "prod": os.path.join(ROOT_DIR, "manifests", "prod.json"),
}
TAG_PREFIX = {
    "dev": "dev-v",
    "hml": "hml-v",
    "prod": "prod-v",
}


def fail(msg):
    print(f"[version-sync] ERROR: {msg}")
    sys.exit(1)


def read_version():
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r'__version__\s*=\s*["\'](\d+\.\d+\.\d+)["\']', content)
    if not match:
        fail(f"Could not parse __version__ in {VERSION_FILE}")
    return match.group(1)


def main():
    version = read_version()
    for env, path in MANIFESTS.items():
        if not os.path.exists(path):
            fail(f"Missing manifest: {path}")
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                fail(f"Invalid JSON in {path}: {e}")

        expected_tag = f"{TAG_PREFIX[env]}{version}"
        if data.get("version") != version:
            fail(f"{path} has version={data.get('version')} expected={version}")
        if data.get("latest_version") != version:
            fail(f"{path} has latest_version={data.get('latest_version')} expected={version}")
        if data.get("tag") != expected_tag:
            fail(f"{path} has tag={data.get('tag')} expected={expected_tag}")

    print("[version-sync] OK: app/version.py and manifests are synchronized.")


if __name__ == "__main__":
    main()
