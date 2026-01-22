#!/usr/bin/env python3
"""
Generate GitHub Actions Summary from JUnit XML test results.

Categorizes tests by group and produces a markdown summary with metrics.
"""

import xml.etree.ElementTree as ET
import sys
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class TestResult:
    name: str
    classname: str
    time: float
    status: str  # passed, failed, skipped, xfailed
    message: str = ""


# Test category definitions
CATEGORIES = {
    "Agent Runner": {
        "pattern": "test_agent_runner",
        "description": "Core agent execution engine tests",
        "icon": "🔧"
    },
    "Bedrock Client": {
        "pattern": "test_bedrock_client",
        "description": "AWS Bedrock integration tests",
        "icon": "☁️"
    },
    "Tool Registry": {
        "pattern": "test_tool_registry",
        "description": "Tool definitions and stubbing tests",
        "icon": "🛠️"
    },
    "Planner Agent": {
        "pattern": "test_planner_agent",
        "description": "Planner agent behavior tests",
        "icon": "📋"
    },
    "Executor Agent": {
        "pattern": "test_executor_agent",
        "description": "Executor agent behavior tests",
        "icon": "⚡"
    },
    "E2E Workflow": {
        "pattern": "test_e2e_workflow",
        "description": "End-to-end planner→executor tests",
        "icon": "🔄"
    },
    "Prompt Regression": {
        "pattern": "test_prompt_regression",
        "description": "Golden input/output validation tests",
        "icon": "📊"
    },
    "Intentional Failures": {
        "pattern": "test_intentional_failures",
        "description": "Expected failures for demo purposes",
        "icon": "⚠️"
    }
}


def parse_junit_xml(xml_path: str) -> list[TestResult]:
    """Parse JUnit XML file and return list of test results."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    results = []

    for testcase in root.iter("testcase"):
        name = testcase.get("name", "")
        classname = testcase.get("classname", "")
        time = float(testcase.get("time", 0))

        # Determine status
        status = "passed"
        message = ""

        failure = testcase.find("failure")
        error = testcase.find("error")
        skipped = testcase.find("skipped")

        if failure is not None:
            status = "failed"
            message = failure.get("message", "")
        elif error is not None:
            status = "error"
            message = error.get("message", "")
        elif skipped is not None:
            skip_type = skipped.get("type", "")
            skip_msg = skipped.get("message", "")
            if "xfail" in skip_type.lower() or "xfail" in skip_msg.lower():
                status = "xfailed"
            else:
                status = "skipped"
            message = skip_msg

        results.append(TestResult(
            name=name,
            classname=classname,
            time=time,
            status=status,
            message=message
        ))

    return results


def categorize_tests(results: list[TestResult]) -> dict[str, list[TestResult]]:
    """Categorize tests by their group."""
    categorized = defaultdict(list)

    for result in results:
        # Find matching category
        matched = False
        for category, config in CATEGORIES.items():
            if config["pattern"] in result.classname.lower():
                categorized[category].append(result)
                matched = True
                break

        if not matched:
            categorized["Other"].append(result)

    return dict(categorized)


def generate_summary(categorized: dict[str, list[TestResult]], total_time: float) -> str:
    """Generate markdown summary for GitHub Actions."""
    lines = []

    # Header
    lines.append("# 🧪 Test Results Summary\n")

    # Overall metrics
    total_tests = sum(len(tests) for tests in categorized.values())
    total_passed = sum(1 for tests in categorized.values() for t in tests if t.status == "passed")
    total_failed = sum(1 for tests in categorized.values() for t in tests if t.status == "failed")
    total_xfailed = sum(1 for tests in categorized.values() for t in tests if t.status == "xfailed")
    total_skipped = sum(1 for tests in categorized.values() for t in tests if t.status == "skipped")

    # Status badge
    if total_failed > 0:
        status_icon = "❌"
        status_text = "FAILED"
    elif total_passed == total_tests - total_xfailed:
        status_icon = "✅"
        status_text = "PASSED"
    else:
        status_icon = "⚠️"
        status_text = "PARTIAL"

    lines.append(f"## {status_icon} Overall Status: {status_text}\n")

    # Metrics table
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Tests | {total_tests} |")
    lines.append(f"| ✅ Passed | {total_passed} |")
    lines.append(f"| ❌ Failed | {total_failed} |")
    lines.append(f"| ⚠️ Expected Failures | {total_xfailed} |")
    lines.append(f"| ⏭️ Skipped | {total_skipped} |")
    lines.append(f"| ⏱️ Duration | {total_time:.2f}s |")
    lines.append("")

    # Category breakdown
    lines.append("## 📁 Results by Category\n")

    for category in CATEGORIES.keys():
        if category not in categorized:
            continue

        tests = categorized[category]
        config = CATEGORIES[category]

        passed = sum(1 for t in tests if t.status == "passed")
        failed = sum(1 for t in tests if t.status == "failed")
        xfailed = sum(1 for t in tests if t.status == "xfailed")
        total = len(tests)
        duration = sum(t.time for t in tests)

        # Category status
        if failed > 0:
            cat_status = "❌"
        elif passed == total - xfailed:
            cat_status = "✅"
        else:
            cat_status = "⚠️"

        lines.append(f"### {config['icon']} {category} {cat_status}")
        lines.append(f"> {config['description']}")
        lines.append("")
        lines.append(f"| Status | Tests | Duration |")
        lines.append(f"|--------|-------|----------|")
        lines.append(f"| ✅ Passed | {passed} | {duration:.2f}s |")
        if failed > 0:
            lines.append(f"| ❌ Failed | {failed} | - |")
        if xfailed > 0:
            lines.append(f"| ⚠️ XFailed | {xfailed} | - |")
        lines.append("")

        # List individual tests
        lines.append("<details>")
        lines.append(f"<summary>View {total} tests</summary>")
        lines.append("")
        lines.append("| Test | Status | Time |")
        lines.append("|------|--------|------|")
        for test in tests:
            status_icon = {
                "passed": "✅",
                "failed": "❌",
                "xfailed": "⚠️",
                "skipped": "⏭️",
                "error": "💥"
            }.get(test.status, "❓")
            lines.append(f"| `{test.name}` | {status_icon} | {test.time:.3f}s |")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    # Handle "Other" category if exists
    if "Other" in categorized and categorized["Other"]:
        lines.append("### 📦 Other Tests")
        lines.append("")
        for test in categorized["Other"]:
            status_icon = "✅" if test.status == "passed" else "❌"
            lines.append(f"- {status_icon} `{test.name}`")
        lines.append("")

    # Failed tests details
    failed_tests = [t for tests in categorized.values() for t in tests if t.status == "failed"]
    if failed_tests:
        lines.append("## ❌ Failed Tests Details\n")
        for test in failed_tests:
            lines.append(f"### `{test.name}`")
            lines.append(f"```")
            lines.append(test.message[:500] if test.message else "No error message")
            lines.append(f"```")
            lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: generate_test_summary.py <junit.xml> [output_file]")
        sys.exit(1)

    xml_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not Path(xml_path).exists():
        print(f"Error: {xml_path} not found")
        sys.exit(1)

    # Parse results
    results = parse_junit_xml(xml_path)

    # Get total time from XML
    tree = ET.parse(xml_path)
    root = tree.getroot()
    total_time = float(root.get("time", 0))

    # Categorize
    categorized = categorize_tests(results)

    # Generate summary
    summary = generate_summary(categorized, total_time)

    # Output
    if output_path:
        with open(output_path, "w") as f:
            f.write(summary)
        print(f"Summary written to {output_path}")
    else:
        print(summary)


if __name__ == "__main__":
    main()
