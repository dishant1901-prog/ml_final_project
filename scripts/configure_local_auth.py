"""Create local-only admin/viewer credentials without printing secrets."""

import argparse
import secrets
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.operations import hash_password


def update_env(path: Path, values: dict[str, str]) -> None:
    existing = path.read_text().splitlines() if path.exists() else []
    kept = [line for line in existing if line.partition("=")[0].strip() not in values]
    content = (
        "\n".join(
            [
                *kept,
                "",
                "# Local internal-showcase authentication",
                *(f"{key}={shlex.quote(value)}" for key, value in values.items()),
            ]
        ).strip()
        + "\n"
    )
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(content)
    temporary.chmod(0o600)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure local HimaRoad accounts")
    parser.add_argument("--env", type=Path, default=Path(".env"))
    parser.add_argument(
        "--credentials-file",
        type=Path,
        default=Path("data/private/internal-credentials.txt"),
    )
    parser.add_argument("--admin-username", default="himaroad-admin")
    parser.add_argument("--viewer-username", default="himaroad-viewer")
    args = parser.parse_args()
    if args.admin_username == args.viewer_username or any(
        not name or ":" in name or len(name) > 64
        for name in (args.admin_username, args.viewer_username)
    ):
        parser.error(
            "Usernames must be distinct, non-empty, at most 64 characters and contain no colon"
        )
    destination = args.credentials_file.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        parser.error(
            "Credentials file already exists; move it aside before rotating accounts"
        )
    admin_password = secrets.token_urlsafe(24)
    viewer_password = secrets.token_urlsafe(24)
    values = {
        "LOCAL_AUTH_ADMIN_USERNAME": args.admin_username,
        "LOCAL_AUTH_ADMIN_PASSWORD_HASH": hash_password(admin_password),
        "LOCAL_AUTH_VIEWER_USERNAME": args.viewer_username,
        "LOCAL_AUTH_VIEWER_PASSWORD_HASH": hash_password(viewer_password),
        "LOCAL_AUTH_COOKIE_SECRET": secrets.token_urlsafe(48),
        "LOCAL_SERVICE_TOKEN": secrets.token_urlsafe(48),
    }
    update_env(args.env.resolve(), values)
    destination.write_text(
        "HimaRoad internal showcase credentials\n"
        "Store offline; do not commit or paste into chat.\n\n"
        f"Administrator username: {args.admin_username}\n"
        f"Administrator password: {admin_password}\n\n"
        f"Viewer username: {args.viewer_username}\n"
        f"Viewer password: {viewer_password}\n"
    )
    destination.chmod(0o600)
    print(f"Updated {args.env.resolve()}")
    print(f"Wrote mode-0600 credentials to {destination}")


if __name__ == "__main__":
    main()
