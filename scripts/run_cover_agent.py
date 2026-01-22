#!/usr/bin/env python3
"""
Run Cover-Agent with project-specific configuration.

Usage:
    python scripts/run_cover_agent.py runtime/bedrock_client.py
    python scripts/run_cover_agent.py --all
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Project configuration
COVERAGE_THRESHOLD = 90
MAX_ITERATIONS = 5

# Source to test file mapping
SOURCE_TEST_MAP = {
    "runtime/agent_runner.py": "tests/test_agent_runner.py",
    "runtime/bedrock_client.py": "tests/test_bedrock_client.py",
    "runtime/tool_registry.py": "tests/test_tool_registry.py",
    "agents/planner/graph.py": "tests/test_planner_agent.py",
    "agents/executor/graph.py": "tests/test_executor_agent.py",
}

# Files with low coverage that need attention
LOW_COVERAGE_FILES = [
    "runtime/bedrock_client.py",  # 74%
]


def run_cover_agent(source_file: str, test_file: str, threshold: int = COVERAGE_THRESHOLD):
    """Run cover-agent on a source file."""
    print(f"\n🤖 Running Cover-Agent on {source_file}")
    print(f"   Test file: {test_file}")
    print(f"   Target coverage: {threshold}%")
    print("-" * 50)

    cmd = [
        "cover-agent",
        "--source-file", source_file,
        "--test-file", test_file,
        "--coverage-type", "cobertura",
        "--desired-coverage", str(threshold),
        "--max-iterations", str(MAX_ITERATIONS),
    ]

    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Cover-Agent failed: {e}")
        return False
    except FileNotFoundError:
        print("❌ cover-agent not found. Install with: pip install cover-agent")
        return False


def get_test_file(source_file: str) -> str:
    """Get the test file for a source file."""
    if source_file in SOURCE_TEST_MAP:
        return SOURCE_TEST_MAP[source_file]

    # Auto-generate test file path
    source_path = Path(source_file)
    return f"tests/test_{source_path.stem}.py"


def main():
    parser = argparse.ArgumentParser(description="Run Cover-Agent with project config")
    parser.add_argument("source_file", nargs="?", help="Source file to generate tests for")
    parser.add_argument("--all", action="store_true", help="Run on all low-coverage files")
    parser.add_argument("--threshold", type=int, default=COVERAGE_THRESHOLD,
                        help=f"Coverage threshold (default: {COVERAGE_THRESHOLD})")

    args = parser.parse_args()

    if args.all:
        print("🤖 Running Cover-Agent on all low-coverage files...")
        success = True
        for source_file in LOW_COVERAGE_FILES:
            test_file = get_test_file(source_file)
            if not run_cover_agent(source_file, test_file, args.threshold):
                success = False
        sys.exit(0 if success else 1)

    if not args.source_file:
        parser.print_help()
        print("\n📁 Available source files:")
        for src, test in SOURCE_TEST_MAP.items():
            print(f"   {src} -> {test}")
        sys.exit(1)

    test_file = get_test_file(args.source_file)
    success = run_cover_agent(args.source_file, test_file, args.threshold)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
