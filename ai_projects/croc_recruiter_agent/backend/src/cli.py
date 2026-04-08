from __future__ import annotations

import argparse
import sys

from src.core.router_factory import build_router
from src.utils.logger import get_logger

logger = get_logger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Conversational AI Assistant CLI"
    )

    parser.add_argument(
        "--user",
        type=str,
        required=True,
        help="User identifier for access control (e.g. analyst_1)",
    )

    return parser.parse_args()


def run_cli():
    args = parse_args()
    user = args.user

    logger.info("cli.start", extra={"user": user})

    router = build_router()

    print("\nAI Assistant Ready (type 'exit' to quit)\n")

    while True:
        try:
            question = input(">>> ").strip()

            if question.lower() in {"exit", "quit"}:
                print("Goodbye!")
                break

            if not question:
                continue

            result = router.handle(question=question, user_id=user)

            print()
            print(result["answer"])
            print()
            print(f"  cache_hit   : {result.get('cache_hit', False)}")
            print(f"  engine_used : {result.get('engine_used', 'unknown')}")
            print()

        except KeyboardInterrupt:
            print("\nInterrupted. Goodbye!")
            sys.exit(0)

        except Exception as e:
            logger.exception("cli.error", extra={"error": str(e)})
            print("An error occurred. Please try again.")


if __name__ == "__main__":
    run_cli()
