"""
Test runner for documentation validation.
Executes all test suites and generates comprehensive reports.
"""

import time
from datetime import datetime
from typing import List, Dict, Any
import traceback

from .test_navigation import TestNavigation
from .test_content import TestContent
from .test_implementation import TestImplementation
from .report_generator import (
    ReportGenerator,
    TestStatus,
    create_test_result,
    create_suite_result,
    TestResult,
    TestSuiteResult
)

class TestRunner:
    def __init__(self):
        self.report_generator = ReportGenerator()
        self.suites = [
            ("Navigation Tests", TestNavigation),
            ("Content Tests", TestContent),
            ("Implementation Tests", TestImplementation)
        ]

    def run_all_tests(self) -> List[TestSuiteResult]:
        """Run all test suites and return results"""
        suite_results = []

        for suite_name, suite_class in self.suites:
            print(f"\nRunning {suite_name}...")
            suite_result = self._run_suite(suite_name, suite_class)
            suite_results.append(suite_result)
            print(f"Completed {suite_name}")

        return suite_results

    def _run_suite(self, suite_name: str, suite_class) -> TestSuiteResult:
        """Run a test suite and return results"""
        start_time = datetime.now()
        test_instance = suite_class()
        test_instance.setup_method()
        results = []

        # Get all test methods
        test_methods = [
            method for method in dir(suite_class)
            if method.startswith('test_') and callable(getattr(suite_class, method))
        ]

        for method_name in test_methods:
            test_method = getattr(test_instance, method_name)
            result = self._run_test(method_name, test_method)
            results.append(result)

        end_time = datetime.now()

        return create_suite_result(
            name=suite_name,
            results=results,
            start_time=start_time,
            end_time=end_time
        )

    def _run_test(self, test_name: str, test_method) -> TestResult:
        """Run a single test and return result"""
        start_time = time.time()
        error_message = None
        status = TestStatus.PASS
        details = {}

        try:
            test_method()
        except AssertionError as e:
            status = TestStatus.FAIL
            error_message = str(e)
            details["traceback"] = traceback.format_exc()
        except Exception as e:
            status = TestStatus.ERROR
            error_message = f"{type(e).__name__}: {str(e)}"
            details["traceback"] = traceback.format_exc()

        duration = time.time() - start_time

        return create_test_result(
            name=test_name,
            status=status,
            duration=duration,
            error_message=error_message,
            details=details
        )

    def run_and_report(self):
        """Run all tests and generate reports"""
        print("Starting documentation validation tests...")

        try:
            # Run all test suites
            suite_results = self.run_all_tests()

            # Generate reports
            print("\nGenerating test reports...")
            self.report_generator.generate_report(suite_results)

            # Print summary
            self._print_summary(suite_results)

        except Exception as e:
            print(f"\n❌ Error running tests: {type(e).__name__}: {str(e)}")
            print(traceback.format_exc())
            return 1

        # Return exit code based on test results
        return 0 if self._all_tests_passed(suite_results) else 1

    def _print_summary(self, suite_results: List[TestSuiteResult]):
        """Print test execution summary"""
        print("\n=== Test Execution Summary ===")

        total_tests = sum(len(suite.results) for suite in suite_results)
        total_passed = sum(
            sum(1 for r in suite.results if r.status == TestStatus.PASS)
            for suite in suite_results
        )
        total_duration = sum(suite.total_duration for suite in suite_results)

        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {total_passed}")
        print(f"Failed: {total_tests - total_passed}")
        print(f"Success Rate: {(total_passed/total_tests)*100:.2f}%")
        print(f"Total Duration: {total_duration:.2f}s")

        print("\nSuite Results:")
        for suite in suite_results:
            passed = sum(1 for r in suite.results if r.status == TestStatus.PASS)
            total = len(suite.results)
            print(f"- {suite.name}: {passed}/{total} passed ({suite.total_duration:.2f}s)")

    def _all_tests_passed(self, suite_results: List[TestSuiteResult]) -> bool:
        """Check if all tests passed"""
        return all(
            all(result.status == TestStatus.PASS for result in suite.results)
            for suite in suite_results
        )

def main():
    """Main entry point"""
    runner = TestRunner()
    exit_code = runner.run_and_report()
    exit(exit_code)

if __name__ == "__main__":
    main()