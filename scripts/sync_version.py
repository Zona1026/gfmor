import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "frontend" / "package.json"
LOCK_PATH = ROOT / "frontend" / "package-lock.json"
MAIN_PATH = ROOT / "main.py"
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
API_VERSION_PATTERN = re.compile(r'(\s+version=")[^"]+("[,])')


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synchronize the FastAPI version with frontend/package.json."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only verify that package, lockfile, and API versions match.",
    )
    args = parser.parse_args()

    package_version = read_json(PACKAGE_PATH).get("version")
    if not isinstance(package_version, str) or not SEMVER_PATTERN.fullmatch(
        package_version
    ):
        raise SystemExit(f"Invalid package version: {package_version!r}")

    lock_data = read_json(LOCK_PATH)
    lock_version = lock_data.get("version")
    root_lock_version = lock_data.get("packages", {}).get("", {}).get("version")
    if lock_version != package_version or root_lock_version != package_version:
        raise SystemExit(
            "package-lock.json is not synchronized with frontend/package.json"
        )

    main_source = MAIN_PATH.read_text(encoding="utf-8")
    matches = list(API_VERSION_PATTERN.finditer(main_source))
    if len(matches) != 1:
        raise SystemExit("Expected exactly one FastAPI version in main.py")

    api_version = matches[0].group(0).split('"')[1]
    if args.check:
        if api_version != package_version:
            raise SystemExit(
                f"Version mismatch: frontend={package_version}, API={api_version}"
            )
        print(f"Version {package_version} is synchronized.")
        return 0

    updated_source = API_VERSION_PATTERN.sub(
        rf"\g<1>{package_version}\g<2>", main_source, count=1
    )
    MAIN_PATH.write_text(updated_source, encoding="utf-8")
    print(f"Synchronized API version to {package_version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
