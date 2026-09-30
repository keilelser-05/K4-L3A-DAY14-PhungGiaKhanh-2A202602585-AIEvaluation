"""Check configured API access without printing credentials or response bodies."""

from pathlib import Path
import os

from dotenv import load_dotenv
from openai import OpenAI


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    client = OpenAI(timeout=20, max_retries=0)
    try:
        client.models.retrieve(os.environ["OPENAI_MODEL"])
    except Exception as exc:
        current = exc
        while current is not None:
            print("Error type:", type(current).__name__)
            current = current.__cause__
        status = getattr(exc, "status_code", None)
        if status is not None:
            print("HTTP status:", status)
        return 1
    print("API authentication and configured model access OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
