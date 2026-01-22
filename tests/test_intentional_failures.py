"""
Intentionally Failing Tests

These tests are designed to FAIL to demonstrate test reporting capabilities.
They show how the CI pipeline handles and reports test failures.

DO NOT FIX THESE TESTS - they are meant to fail!
"""

import pytest


class TestIntentionalFailures:
    """
    Tests that intentionally fail for demonstration purposes.

    These tests demonstrate:
    1. How test failures appear in reports
    2. That the CI pipeline properly captures failures
    3. Different types of assertion failures
    """

    @pytest.mark.xfail(reason="Intentional failure for report demonstration", strict=True)
    def test_intentional_assertion_failure(self):
        """
        This test intentionally fails with an assertion error.

        Purpose: Demonstrate assertion failure in test reports.
        """
        expected = "success"
        actual = "failure"

        # This assertion will fail
        assert actual == expected, (
            "This is an intentional failure to demonstrate test reporting. "
            "Expected 'success' but got 'failure'."
        )

    @pytest.mark.xfail(reason="Intentional failure for report demonstration", strict=True)
    def test_intentional_value_mismatch(self):
        """
        This test intentionally fails with a value mismatch.

        Purpose: Demonstrate numeric comparison failure in reports.
        """
        calculated_value = 42
        expected_value = 100

        # This will fail
        assert calculated_value == expected_value, (
            f"Intentional mismatch: calculated {calculated_value}, expected {expected_value}"
        )

    @pytest.mark.xfail(reason="Intentional failure for report demonstration", strict=True)
    def test_intentional_missing_key(self):
        """
        This test intentionally fails due to missing dictionary key.

        Purpose: Demonstrate KeyError handling in test reports.
        """
        data = {
            "name": "test",
            "status": "active"
        }

        # This key doesn't exist - intentional failure
        assert "missing_key" in data, (
            "Intentional failure: 'missing_key' not found in data dictionary"
        )


class TestDemonstrationFailures:
    """
    Additional failing tests to ensure reports show multiple failure types.
    """

    @pytest.mark.xfail(reason="Intentional failure for report demonstration", strict=True)
    def test_list_comparison_failure(self):
        """Test that fails due to list mismatch."""
        actual_list = [1, 2, 3]
        expected_list = [1, 2, 3, 4, 5]

        assert actual_list == expected_list, "Lists do not match (intentional)"

    @pytest.mark.xfail(reason="Intentional failure for report demonstration", strict=True)
    def test_boolean_failure(self):
        """Test that fails due to boolean condition."""
        condition = False

        assert condition is True, "Boolean check failed (intentional)"
