from __future__ import annotations

import argparse
from pathlib import Path

import boto3


# This helper is intentionally small and reusable so the local CLI and the EC2
# pipeline runner share one upload implementation.
def upload_file(*, file_path: Path, bucket: str, key: str, region: str | None = None) -> tuple[str, str]:
    session = boto3.session.Session(region_name=region)
    client = session.client("s3")
    client.upload_file(str(file_path), bucket, key)

    resolved_region = region or session.region_name or "us-east-1"
    return f"s3://{bucket}/{key}", f"https://{bucket}.s3.{resolved_region}.amazonaws.com/{key}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload a file to S3.")
    parser.add_argument("--file", required=True, help="Local file to upload.")
    parser.add_argument("--bucket", required=True, help="Target S3 bucket.")
    parser.add_argument("--key", required=True, help="S3 object key.")
    parser.add_argument("--region", default=None, help="AWS region override.")
    return parser


def main() -> int:
    # Keeping the CLI wrapper separate from `upload_file` makes it simpler to
    # reuse the upload logic from tests or orchestration scripts.
    args = build_parser().parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        raise FileNotFoundError(f"File does not exist: {file_path}")

    s3_uri, https_url = upload_file(
        file_path=file_path,
        bucket=args.bucket,
        key=args.key,
        region=args.region,
    )
    print(s3_uri)
    print(https_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
