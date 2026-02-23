import json
import os
import re
import sys
from datetime import datetime, timezone

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


def _read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write_text(path, content):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def _parse_version(version_text):
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version_text.strip())
    if not match:
        raise ValueError("Version must match X.Y.Z")
    return tuple(map(int, match.groups()))


def _read_current_version():
    content = _read_text(VERSION_FILE)
    match = re.search(r'__version__\s*=\s*["\'](\d+\.\d+\.\d+)["\']', content)
    if not match:
        raise RuntimeError(f"Could not find __version__ in {VERSION_FILE}")
    return match.group(1)


def _set_version_file(new_version):
    content = _read_text(VERSION_FILE)
    today_build = datetime.now(timezone.utc).strftime("%Y%m%d")

    content = re.sub(
        r'__version__\s*=\s*["\']\d+\.\d+\.\d+["\']',
        f'__version__ = "{new_version}"',
        content,
    )
    content = re.sub(
        r'__build__\s*=\s*["\'].*?["\']',
        f'__build__ = "{today_build}"',
        content,
    )
    _write_text(VERSION_FILE, content)


def _sync_manifest(env, version):
    manifest_path = MANIFESTS[env]
    payload = {
        "version": version,
        "latest_version": version,
        "tag": f"{TAG_PREFIX[env]}{version}",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": "auto-version-sync",
        "environment": env,
    }
    _write_text(manifest_path, json.dumps(payload, indent=4, ensure_ascii=True) + "\n")


def _next_patch_version(current_version):
    major, minor, patch = _parse_version(current_version)
    return f"{major}.{minor}.{patch + 1}"


def main():
    explicit_version = sys.argv[1].strip() if len(sys.argv) > 1 else None

    current_version = _read_current_version()
    if explicit_version:
        _parse_version(explicit_version)
        target_version = explicit_version
    else:
        target_version = _next_patch_version(current_version)

    _set_version_file(target_version)
    for env in ("dev", "hml", "prod"):
        _sync_manifest(env, target_version)

    print(f"Version synced successfully: {current_version} -> {target_version}")
    print("Updated files:")
    print(f"- {os.path.relpath(VERSION_FILE, ROOT_DIR)}")
    for env in ("dev", "hml", "prod"):
        print(f"- {os.path.relpath(MANIFESTS[env], ROOT_DIR)}")


if __name__ == "__main__":
    main()
