"""
Test report generator for documentation validation.
Generates detailed HTML and Markdown reports with metrics and visualizations.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class TestStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIP = "skip"

@dataclass
class TestResult:
    name: str
    status: TestStatus
    duration: float
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

@dataclass
class TestSuiteResult:
    name: str
    results: List[TestResult]
    start_time: datetime
    end_time: datetime
    total_duration: float

class ReportGenerator:
    def __init__(self, output_dir: str = "docs/tests/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_run = datetime.now().strftime("%Y%m%d_%H%M%S")

    def generate_report(self, suite_results: List[TestSuiteResult]):
        """Generate comprehensive test reports"""
        self._generate_markdown_report(suite_results)
        self._generate_html_report(suite_results)
        self._generate_json_report(suite_results)
        self._generate_metrics_summary(suite_results)

    def _generate_markdown_report(self, suite_results: List[TestSuiteResult]):
        """Generate markdown report"""
        report_path = self.output_dir / f"report_{self.current_run}.md"

        with report_path.open('w') as f:
            f.write("# Documentation Validation Report\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Overall Summary
            f.write("## Overall Summary\n\n")
            total_tests = sum(len(suite.results) for suite in suite_results)
            total_passed = sum(
                sum(1 for r in suite.results if r.status == TestStatus.PASS)
                for suite in suite_results
            )
            f.write(f"- Total Tests: {total_tests}\n")
            f.write(f"- Passed: {total_passed}\n")
            f.write(f"- Failed: {total_tests - total_passed}\n")
            f.write(f"- Success Rate: {(total_passed/total_tests)*100:.2f}%\n\n")

            # Test Suite Details
            for suite in suite_results:
                f.write(f"## {suite.name}\n\n")
                f.write(f"Duration: {suite.total_duration:.2f}s\n\n")

                # Results Table
                f.write("| Test | Status | Duration | Details |\n")
                f.write("|------|--------|-----------|----------|\n")

                for result in suite.results:
                    status_icon = "✅" if result.status == TestStatus.PASS else "❌"
                    details = result.error_message if result.status != TestStatus.PASS else ""
                    f.write(f"| {result.name} | {status_icon} | {result.duration:.2f}s | {details} |\n")

                f.write("\n")

    def _generate_html_report(self, suite_results: List[TestSuiteResult]):
        """Generate HTML report with visualizations"""
        report_path = self.output_dir / f"report_{self.current_run}.html"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Documentation Validation Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
                .suite {{ margin: 20px 0; }}
                .test-result {{ margin: 10px 0; padding: 10px; border-radius: 3px; }}
                .pass {{ background: #e6ffe6; }}
                .fail {{ background: #ffe6e6; }}
                .metrics {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .metric-card {{ background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            </style>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        </head>
        <body>
            <h1>Documentation Validation Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

            <div class="summary">
                <h2>Overall Summary</h2>
                <div class="metrics">
                    {self._generate_metrics_html(suite_results)}
                </div>
                <div id="results-chart"></div>
            </div>

            {self._generate_suite_results_html(suite_results)}

            <script>
                {self._generate_visualization_js(suite_results)}
            </script>
        </body>
        </html>
        """

        with report_path.open('w') as f:
            f.write(html_content)

    def _generate_json_report(self, suite_results: List[TestSuiteResult]):
        """Generate JSON report for programmatic access"""
        report_path = self.output_dir / f"report_{self.current_run}.json"

        report_data = {
            "generated_at": datetime.now().isoformat(),
            "suites": [
                {
                    "name": suite.name,
                    "duration": suite.total_duration,
                    "start_time": suite.start_time.isoformat(),
                    "end_time": suite.end_time.isoformat(),
                    "results": [
                        {
                            "name": result.name,
                            "status": result.status.value,
                            "duration": result.duration,
                            "error_message": result.error_message,
                            "details": result.details
                        }
                        for result in suite.results
                    ]
                }
                for suite in suite_results
            ]
        }

        with report_path.open('w') as f:
            json.dump(report_data, f, indent=2)

    def _generate_metrics_summary(self, suite_results: List[TestSuiteResult]):
        """Generate metrics summary"""
        metrics_path = self.output_dir / f"metrics_{self.current_run}.json"

        metrics = {
            "total_tests": sum(len(suite.results) for suite in suite_results),
            "total_passed": sum(
                sum(1 for r in suite.results if r.status == TestStatus.PASS)
                for suite in suite_results
            ),
            "total_duration": sum(suite.total_duration for suite in suite_results),
            "suite_metrics": {
                suite.name: {
                    "total": len(suite.results),
                    "passed": sum(1 for r in suite.results if r.status == TestStatus.PASS),
                    "duration": suite.total_duration
                }
                for suite in suite_results
            }
        }

        with metrics_path.open('w') as f:
            json.dump(metrics, f, indent=2)

    def _generate_metrics_html(self, suite_results: List[TestSuiteResult]) -> str:
        """Generate HTML for metrics cards"""
        total_tests = sum(len(suite.results) for suite in suite_results)
        total_passed = sum(
            sum(1 for r in suite.results if r.status == TestStatus.PASS)
            for suite in suite_results
        )
        total_duration = sum(suite.total_duration for suite in suite_results)

        return f"""
            <div class="metric-card">
                <h3>Total Tests</h3>
                <p>{total_tests}</p>
            </div>
            <div class="metric-card">
                <h3>Pass Rate</h3>
                <p>{(total_passed/total_tests)*100:.2f}%</p>
            </div>
            <div class="metric-card">
                <h3>Total Duration</h3>
                <p>{total_duration:.2f}s</p>
            </div>
        """

    def _generate_suite_results_html(self, suite_results: List[TestSuiteResult]) -> str:
        """Generate HTML for suite results"""
        html = ""
        for suite in suite_results:
            html += f"""
                <div class="suite">
                    <h2>{suite.name}</h2>
                    <p>Duration: {suite.total_duration:.2f}s</p>
                    <div class="test-results">
            """

            for result in suite.results:
                status_class = "pass" if result.status == TestStatus.PASS else "fail"
                details = result.error_message if result.status != TestStatus.PASS else ""
                html += f"""
                    <div class="test-result {status_class}">
                        <h4>{result.name}</h4>
                        <p>Duration: {result.duration:.2f}s</p>
                        <p>{details}</p>
                    </div>
                """

            html += "</div></div>"

        return html

    def _generate_visualization_js(self, suite_results: List[TestSuiteResult]) -> str:
        """Generate JavaScript for interactive visualizations"""
        return """
            // Results Pie Chart
            var data = [{
                values: [%s, %s],
                labels: ['Passed', 'Failed'],
                type: 'pie',
                marker: {
                    colors: ['#4CAF50', '#f44336']
                }
            }];

            var layout = {
                title: 'Test Results Distribution'
            };

            Plotly.newPlot('results-chart', data, layout);
        """ % (
            sum(sum(1 for r in suite.results if r.status == TestStatus.PASS)
                for suite in suite_results),
            sum(sum(1 for r in suite.results if r.status != TestStatus.PASS)
                for suite in suite_results)
        )

def create_test_result(
    name: str,
    status: TestStatus,
    duration: float,
    error_message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> TestResult:
    """Helper function to create test results"""
    return TestResult(
        name=name,
        status=status,
        duration=duration,
        error_message=error_message,
        details=details
    )

def create_suite_result(
    name: str,
    results: List[TestResult],
    start_time: datetime,
    end_time: datetime
) -> TestSuiteResult:
    """Helper function to create suite results"""
    return TestSuiteResult(
        name=name,
        results=results,
        start_time=start_time,
        end_time=end_time,
        total_duration=(end_time - start_time).total_seconds()
    )