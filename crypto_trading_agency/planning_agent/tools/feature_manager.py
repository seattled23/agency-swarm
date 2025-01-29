from agency_swarm.tools import BaseTool
from pydantic import Field
import os
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

class FeatureManager(BaseTool):
    """
    Tool for managing feature lifecycle including planning, implementation, testing, and deployment.
    Handles feature requests, dependencies, and integration with existing capabilities.
    """
    
    feature_spec: Dict = Field(
        ...,
        description="Feature specification including requirements, dependencies, and implementation details"
    )
    
    target_agent: str = Field(
        ...,
        description="Name of the agent to implement the feature for"
    )
    
    priority: str = Field(
        default="medium",
        description="Priority level for feature implementation: 'high', 'medium', or 'low'"
    )
    
    implementation_strategy: str = Field(
        default="incremental",
        description="Strategy for feature implementation: 'incremental', 'parallel', or 'staged'"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.results_dir = Path("feature_management")
        self.results_dir.mkdir(exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(self.results_dir / 'feature_management.log'),
                logging.StreamHandler()
            ]
        )

    def analyze_feature_requirements(self) -> Dict:
        """Analyze feature requirements and dependencies."""
        logging.info(f"Analyzing feature requirements for {self.target_agent}")
        
        requirements = {
            "functional": {
                "core_requirements": self.feature_spec.get("requirements", []),
                "dependencies": self.feature_spec.get("dependencies", []),
                "integrations": self.feature_spec.get("integrations", [])
            },
            "technical": {
                "api_requirements": self.feature_spec.get("api_requirements", []),
                "data_requirements": self.feature_spec.get("data_requirements", []),
                "performance_requirements": self.feature_spec.get("performance_requirements", {})
            },
            "constraints": {
                "compatibility": self.feature_spec.get("compatibility", []),
                "resource_limits": self.feature_spec.get("resource_limits", {}),
                "security_requirements": self.feature_spec.get("security_requirements", [])
            }
        }
        
        return requirements

    def validate_feature_spec(self) -> Dict[str, List[str]]:
        """Validate the feature specification."""
        issues = {"errors": [], "warnings": []}
        
        required_fields = ["name", "description", "requirements", "dependencies"]
        for field in required_fields:
            if field not in self.feature_spec:
                issues["errors"].append(f"Missing required field: {field}")
        
        if "requirements" in self.feature_spec:
            if not isinstance(self.feature_spec["requirements"], list):
                issues["errors"].append("Requirements must be a list")
            elif not self.feature_spec["requirements"]:
                issues["warnings"].append("No requirements specified")
        
        if "dependencies" in self.feature_spec:
            deps = self.feature_spec["dependencies"]
            for dep in deps:
                if "name" not in dep or "version" not in dep:
                    issues["warnings"].append(f"Incomplete dependency specification: {dep}")
        
        return issues

    def create_implementation_plan(self, requirements: Dict) -> Dict:
        """Create implementation plan for the feature."""
        plan = {
            "timestamp": datetime.now().isoformat(),
            "feature": self.feature_spec["name"],
            "agent": self.target_agent,
            "strategy": self.implementation_strategy,
            "phases": []
        }
        
        # Phase 1: Preparation
        plan["phases"].append({
            "phase": "preparation",
            "steps": [
                {
                    "action": "environment_setup",
                    "description": "Set up development environment"
                },
                {
                    "action": "dependency_installation",
                    "description": "Install required dependencies",
                    "dependencies": requirements["functional"]["dependencies"]
                }
            ]
        })
        
        # Phase 2: Implementation
        implementation_steps = []
        for req in requirements["functional"]["core_requirements"]:
            implementation_steps.append({
                "action": "implement_requirement",
                "requirement": req,
                "description": f"Implement {req}",
                "status": "pending"
            })
        
        if implementation_steps:
            plan["phases"].append({
                "phase": "implementation",
                "steps": implementation_steps
            })
        
        # Phase 3: Integration
        integration_steps = []
        for integration in requirements["functional"]["integrations"]:
            integration_steps.append({
                "action": "integrate_feature",
                "target": integration,
                "description": f"Integrate with {integration}",
                "status": "pending"
            })
        
        if integration_steps:
            plan["phases"].append({
                "phase": "integration",
                "steps": integration_steps
            })
        
        # Phase 4: Testing
        plan["phases"].append({
            "phase": "testing",
            "steps": [
                {
                    "action": "unit_testing",
                    "description": "Run unit tests"
                },
                {
                    "action": "integration_testing",
                    "description": "Run integration tests"
                },
                {
                    "action": "performance_testing",
                    "description": "Run performance tests",
                    "requirements": requirements["technical"]["performance_requirements"]
                }
            ]
        })
        
        # Phase 5: Deployment
        plan["phases"].append({
            "phase": "deployment",
            "steps": [
                {
                    "action": "feature_deployment",
                    "description": "Deploy feature to production"
                },
                {
                    "action": "monitoring_setup",
                    "description": "Set up monitoring and alerts"
                },
                {
                    "action": "documentation_update",
                    "description": "Update documentation"
                }
            ]
        })
        
        return plan

    def estimate_resource_requirements(self, implementation_plan: Dict) -> Dict:
        """Estimate resource requirements for feature implementation."""
        estimates = {
            "development": {
                "time_estimate": len(implementation_plan["phases"]) * 2,  # days per phase
                "complexity": self._calculate_complexity(implementation_plan),
                "resource_allocation": {
                    "developers": max(1, len(implementation_plan["phases"]) // 2),
                    "testers": max(1, len(implementation_plan["phases"]) // 3)
                }
            },
            "infrastructure": {
                "compute_resources": self._estimate_compute_resources(),
                "storage_requirements": self._estimate_storage_requirements(),
                "network_requirements": self._estimate_network_requirements()
            },
            "maintenance": {
                "monitoring_requirements": self._estimate_monitoring_requirements(),
                "backup_requirements": self._estimate_backup_requirements()
            }
        }
        
        return estimates

    def _calculate_complexity(self, plan: Dict) -> str:
        """Calculate implementation complexity based on plan details."""
        total_steps = sum(len(phase["steps"]) for phase in plan["phases"])
        if total_steps <= 5:
            return "low"
        elif total_steps <= 10:
            return "medium"
        return "high"

    def _estimate_compute_resources(self) -> Dict:
        """Estimate required compute resources."""
        return {
            "cpu": "2 cores",
            "memory": "4GB",
            "gpu": "not required"
        }

    def _estimate_storage_requirements(self) -> Dict:
        """Estimate storage requirements."""
        return {
            "persistent": "10GB",
            "temporary": "5GB",
            "backup": "15GB"
        }

    def _estimate_network_requirements(self) -> Dict:
        """Estimate network requirements."""
        return {
            "bandwidth": "100Mbps",
            "latency": "low",
            "availability": "99.9%"
        }

    def _estimate_monitoring_requirements(self) -> Dict:
        """Estimate monitoring requirements."""
        return {
            "metrics": ["cpu", "memory", "latency", "errors"],
            "alerts": ["error_rate", "latency_threshold", "resource_usage"],
            "logging_level": "info"
        }

    def _estimate_backup_requirements(self) -> Dict:
        """Estimate backup requirements."""
        return {
            "frequency": "daily",
            "retention": "30 days",
            "type": "incremental"
        }

    def run(self) -> str:
        """
        Execute feature management process and generate report.
        """
        try:
            # Create feature management session directory
            session_dir = self.results_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
            session_dir.mkdir(exist_ok=True)
            
            # Analyze feature requirements
            requirements = self.analyze_feature_requirements()
            
            # Validate feature specification
            validation_results = self.validate_feature_spec()
            if validation_results["errors"]:
                raise ValueError(f"Feature specification validation failed: {validation_results['errors']}")
            
            # Create implementation plan
            implementation_plan = self.create_implementation_plan(requirements)
            
            # Estimate resource requirements
            resource_estimates = self.estimate_resource_requirements(implementation_plan)
            
            # Compile results
            feature_results = {
                "timestamp": datetime.now().isoformat(),
                "feature": self.feature_spec["name"],
                "agent": self.target_agent,
                "requirements": requirements,
                "validation": validation_results,
                "implementation_plan": implementation_plan,
                "resource_estimates": resource_estimates
            }
            
            # Export results
            report_path = session_dir / "feature_management_report.json"
            with open(report_path, 'w') as f:
                json.dump(feature_results, f, indent=4)
            
            logging.info(f"Feature management plan completed. Report saved to {report_path}")
            
            # Return summary
            return self._generate_summary(feature_results)
            
        except Exception as e:
            logging.error(f"Error during feature management: {str(e)}")
            raise

    def _generate_summary(self, results: Dict) -> str:
        """Generate a human-readable summary of the feature management results."""
        summary = []
        summary.append(f"Feature Management Summary for {results['feature']}")
        summary.append("=" * 50)
        
        # Feature Overview
        summary.append("\nFeature Overview:")
        summary.append(f"Target Agent: {results['agent']}")
        summary.append(f"Description: {self.feature_spec['description']}")
        
        # Requirements Summary
        summary.append("\nRequirements:")
        for req_type, reqs in results["requirements"]["functional"].items():
            if isinstance(reqs, list) and reqs:
                summary.append(f"\n{req_type.title()}:")
                for req in reqs:
                    summary.append(f"- {req}")
        
        # Validation Results
        if results["validation"]["warnings"]:
            summary.append("\nValidation Warnings:")
            for warning in results["validation"]["warnings"]:
                summary.append(f"- {warning}")
        
        # Implementation Plan
        summary.append("\nImplementation Plan:")
        for phase in results["implementation_plan"]["phases"]:
            summary.append(f"\n{phase['phase'].title()}:")
            for step in phase["steps"]:
                summary.append(f"- {step['action']}: {step.get('description', '')}")
        
        # Resource Estimates
        summary.append("\nResource Estimates:")
        dev_estimates = results["resource_estimates"]["development"]
        summary.append(f"\nDevelopment:")
        summary.append(f"- Time Estimate: {dev_estimates['time_estimate']} days")
        summary.append(f"- Complexity: {dev_estimates['complexity']}")
        summary.append(f"- Team Size: {dev_estimates['resource_allocation']['developers']} developers, "
                      f"{dev_estimates['resource_allocation']['testers']} testers")
        
        return "\n".join(summary)

if __name__ == "__main__":
    # Test the FeatureManager tool
    feature_spec = {
        "name": "Advanced Analytics",
        "description": "Implement advanced analytics capabilities with ML integration",
        "requirements": [
            "Data preprocessing pipeline",
            "ML model integration",
            "Real-time analytics dashboard"
        ],
        "dependencies": [
            {"name": "tensorflow", "version": "2.8.0"},
            {"name": "pandas", "version": "1.4.0"}
        ],
        "integrations": [
            "data_pipeline",
            "visualization_system"
        ],
        "performance_requirements": {
            "latency": "< 100ms",
            "throughput": "> 1000 requests/sec"
        }
    }
    
    manager = FeatureManager(
        feature_spec=feature_spec,
        target_agent="planning_agent",
        priority="high",
        implementation_strategy="incremental"
    )
    print(manager.run()) 