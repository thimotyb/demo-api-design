#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


DEFAULT_VERSION = "26.6.1"


def download_zip(url: str, target: Path) -> None:
    with urllib.request.urlopen(url) as response, target.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def ensure_distribution(version: str, install_dir: Path) -> Path:
    if install_dir.exists():
        return install_dir

    install_dir.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://github.com/keycloak/keycloak/releases/download/{version}/keycloak-{version}.zip"
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / f"keycloak-{version}.zip"
        print(f"Downloading Keycloak {version} from {url}")
        download_zip(url, zip_path)
        print(f"Extracting to {install_dir.parent}")
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(install_dir.parent)

    if not install_dir.exists():
        raise FileNotFoundError(f"Keycloak distribution not found after extraction: {install_dir}")
    return install_dir


def copy_realm(import_dir: Path, realm_file: Path) -> None:
    import_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(realm_file, import_dir / realm_file.name)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download and start a local Keycloak instance for M3")
    parser.add_argument("--version", default=DEFAULT_VERSION, help="Keycloak distribution version")
    parser.add_argument(
        "--install-dir",
        default=None,
        help="Where to extract the Keycloak distribution (default: examples/.../.keycloak/keycloak-<version>)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    script_dir = Path(__file__).resolve().parent
    example_dir = script_dir.parent
    realm_file = example_dir / "keycloak" / "realm" / "m3-jwt-realm.json"
    if not realm_file.exists():
        raise FileNotFoundError(f"Realm file not found: {realm_file}")

    install_dir = Path(args.install_dir) if args.install_dir else example_dir / ".keycloak" / f"keycloak-{args.version}"
    install_dir = ensure_distribution(args.version, install_dir)
    copy_realm(install_dir / "data" / "import", realm_file)

    env = os.environ.copy()
    env.update(
        {
            "KC_BOOTSTRAP_ADMIN_USERNAME": "admin",
            "KC_BOOTSTRAP_ADMIN_PASSWORD": "admin",
            "KC_HTTP_ENABLED": "true",
            "KC_HOSTNAME_STRICT": "false",
            "KC_PROXY_HEADERS": "xforwarded",
        }
    )

    keycloak_bin = install_dir / "bin" / ("kc.bat" if sys.platform.startswith("win") else "kc.sh")
    if not keycloak_bin.exists():
        raise FileNotFoundError(f"Keycloak launcher not found: {keycloak_bin}")
    if not sys.platform.startswith("win"):
        keycloak_bin.chmod(keycloak_bin.stat().st_mode | 0o111)

    print("Starting Keycloak in development mode with realm import...")
    os.execvpe(str(keycloak_bin), [str(keycloak_bin), "start-dev", "--import-realm"], env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
