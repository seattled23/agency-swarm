from agency_swarm.tools import BaseTool
from pydantic import Field
import os
import json
import logging
import psutil
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

class ResourceOptimizer(BaseTool):
    """
    Tool for optimizing resource allocation and utilization across the system.
    Implements dynamic resource management, predictive scaling, and adaptive optimization.
    """
    
    resource_config: Dict = Field(
        ...,
        description="Resource configuration and constraints"
    )
    
    target_components: List[str] = Field(
        ...,
        description="Components to optimize resources for"
    )
    
    optimization_strategy: str = Field(
        default="adaptive",
        description="Resource optimization strategy: 'adaptive', 'predictive', or 'static'"
    )
    
    monitoring_interval: int = Field(
        default=60,
        description="Interval in seconds for resource monitoring"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.results_dir = Path("resource_optimization")
        self.results_dir.mkdir(exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(self.results_dir / 'resource_optimization.log'),
                logging.StreamHandler()
            ]
        )

    def analyze_current_usage(self) -> Dict:
        """Analyze current resource usage patterns."""
        logging.info("Analyzing current resource usage")
        
        return {
            "cpu": {
                "usage_percent": psutil.cpu_percent(interval=1),
                "core_count": psutil.cpu_count(),
                "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "used": psutil.virtual_memory().used,
                "percent": psutil.virtual_memory().percent
            },
            "disk": {
                mount: psutil.disk_usage(mount)._asdict()
                for mount in self.resource_config.get("monitored_mounts", ["/"])
            },
            "network": {
                "connections": len(psutil.net_connections()),
                "io_counters": psutil.net_io_counters()._asdict()
            }
        }

    def calculate_resource_requirements(self, usage_data: Dict) -> Dict:
        """Calculate optimal resource requirements based on usage patterns."""
        requirements = {}
        
        # CPU Requirements
        cpu_data = usage_data["cpu"]
        requirements["cpu"] = {
            "cores": max(
                2,  # minimum cores
                int(cpu_data["core_count"] * (cpu_data["usage_percent"] / 75.0))  # scale based on target 75% utilization
            ),
            "frequency": {
                "min": cpu_data["frequency"]["min"] if cpu_data["frequency"] else None,
                "target": cpu_data["frequency"]["current"] if cpu_data["frequency"] else None
            }
        }
        
        # Memory Requirements
        mem_data = usage_data["memory"]
        requirements["memory"] = {
            "base": int(mem_data["used"] * 1.2),  # 20% headroom
            "cache": int(mem_data["total"] * 0.2),  # 20% for caching
            "buffer": int(mem_data["total"] * 0.1)  # 10% buffer
        }
        
        # Storage Requirements
        requirements["storage"] = {
            mount: {
                "capacity": int(data["total"] * 1.5),  # 50% growth allowance
                "iops": "auto",  # determined by monitoring
                "type": "ssd" if mount == "/" else "hdd"
            }
            for mount, data in usage_data["disk"].items()
        }
        
        # Network Requirements
        net_data = usage_data["network"]
        requirements["network"] = {
            "bandwidth": {
                "ingress": int(net_data["io_counters"]["bytes_recv"] / self.monitoring_interval * 1.5),
                "egress": int(net_data["io_counters"]["bytes_sent"] / self.monitoring_interval * 1.5)
            },
            "connections": {
                "max": max(1000, net_data["connections"] * 2),
                "buffer": int(net_data["connections"] * 0.3)
            }
        }
        
        return requirements

    def generate_optimization_plan(self, current_usage: Dict, requirements: Dict) -> Dict:
        """Generate resource optimization plan."""
        plan = {
            "timestamp": datetime.now().isoformat(),
            "strategy": self.optimization_strategy,
            "optimizations": {}
        }
        
        # CPU Optimization
        if current_usage["cpu"]["usage_percent"] > 80:
            plan["optimizations"]["cpu"] = {
                "action": "scale_up",
                "target_cores": requirements["cpu"]["cores"],
                "priority": "high"
            }
        elif current_usage["cpu"]["usage_percent"] < 20:
            plan["optimizations"]["cpu"] = {
                "action": "scale_down",
                "target_cores": max(2, requirements["cpu"]["cores"]),
                "priority": "medium"
            }
        
        # Memory Optimization
        mem_usage = current_usage["memory"]["percent"]
        if mem_usage > 85:
            plan["optimizations"]["memory"] = {
                "action": "expand",
                "target_size": requirements["memory"]["base"] + requirements["memory"]["buffer"],
                "priority": "high"
            }
        elif mem_usage < 30:
            plan["optimizations"]["memory"] = {
                "action": "optimize",
                "recommendations": [
                    "Implement memory pooling",
                    "Adjust cache size",
                    "Review memory leaks"
                ],
                "priority": "medium"
            }
        
        # Storage Optimization
        for mount, usage in current_usage["disk"].items():
            if usage["percent"] > 80:
                plan["optimizations"][f"storage_{mount}"] = {
                    "action": "expand",
                    "target_size": requirements["storage"][mount]["capacity"],
                    "priority": "high"
                }
        
        # Network Optimization
        if current_usage["network"]["connections"] > requirements["network"]["connections"]["max"] * 0.8:
            plan["optimizations"]["network"] = {
                "action": "optimize",
                "recommendations": [
                    "Implement connection pooling",
                    "Review connection timeouts",
                    "Consider load balancing"
                ],
                "priority": "high"
            }
        
        return plan

    def calculate_optimization_metrics(self, current_usage: Dict, requirements: Dict) -> Dict:
        """Calculate optimization metrics and potential improvements."""
        metrics = {
            "current_efficiency": {},
            "potential_improvements": {},
            "resource_savings": {}
        }
        
        # CPU Metrics
        cpu_efficiency = min(100, (current_usage["cpu"]["usage_percent"] / 75) * 100)  # Target 75% utilization
        metrics["current_efficiency"]["cpu"] = cpu_efficiency
        metrics["potential_improvements"]["cpu"] = max(0, 75 - cpu_efficiency)
        
        # Memory Metrics
        mem_efficiency = (current_usage["memory"]["used"] / current_usage["memory"]["total"]) * 100
        metrics["current_efficiency"]["memory"] = mem_efficiency
        metrics["potential_improvements"]["memory"] = max(0, 80 - mem_efficiency)
        
        # Storage Metrics
        metrics["current_efficiency"]["storage"] = {}
        metrics["potential_improvements"]["storage"] = {}
        for mount, usage in current_usage["disk"].items():
            efficiency = usage["percent"]
            metrics["current_efficiency"]["storage"][mount] = efficiency
            metrics["potential_improvements"]["storage"][mount] = max(0, 80 - efficiency)
        
        # Calculate Resource Savings
        metrics["resource_savings"] = {
            "cpu_cores": max(0, current_usage["cpu"]["core_count"] - requirements["cpu"]["cores"]),
            "memory": max(0, current_usage["memory"]["total"] - requirements["memory"]["base"]),
            "storage": {
                mount: max(0, usage["total"] - requirements["storage"][mount]["capacity"])
                for mount, usage in current_usage["disk"].items()
            }
        }
        
        return metrics

    def run(self) -> str:
        """
        Execute resource optimization process and generate report.
        """
        try:
            # Create optimization session directory
            session_dir = self.results_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
            session_dir.mkdir(exist_ok=True)
            
            # Analyze current resource usage
            current_usage = self.analyze_current_usage()
            
            # Calculate resource requirements
            requirements = self.calculate_resource_requirements(current_usage)
            
            # Generate optimization plan
            optimization_plan = self.generate_optimization_plan(current_usage, requirements)
            
            # Calculate optimization metrics
            metrics = self.calculate_optimization_metrics(current_usage, requirements)
            
            # Compile results
            optimization_results = {
                "timestamp": datetime.now().isoformat(),
                "current_usage": current_usage,
                "requirements": requirements,
                "optimization_plan": optimization_plan,
                "metrics": metrics
            }
            
            # Export results
            report_path = session_dir / "optimization_report.json"
            with open(report_path, 'w') as f:
                json.dump(optimization_results, f, indent=4)
            
            logging.info(f"Resource optimization completed. Report saved to {report_path}")
            
            # Return summary
            return self._generate_summary(optimization_results)
            
        except Exception as e:
            logging.error(f"Error during resource optimization: {str(e)}")
            raise

    def _generate_summary(self, results: Dict) -> str:
        """Generate a human-readable summary of the optimization results."""
        summary = []
        summary.append("Resource Optimization Summary")
        summary.append("=" * 50)
        
        # Current Usage Summary
        summary.append("\nCurrent Resource Usage:")
        summary.append(f"- CPU: {results['current_usage']['cpu']['usage_percent']}%")
        summary.append(f"- Memory: {results['current_usage']['memory']['percent']}%")
        for mount, usage in results['current_usage']['disk'].items():
            summary.append(f"- Storage ({mount}): {usage['percent']}%")
        
        # Optimization Plan
        summary.append("\nOptimization Plan:")
        for resource, plan in results['optimization_plan']['optimizations'].items():
            summary.append(f"\n{resource.upper()}:")
            summary.append(f"- Action: {plan['action']}")
            summary.append(f"- Priority: {plan['priority']}")
            if "recommendations" in plan:
                summary.append("- Recommendations:")
                for rec in plan["recommendations"]:
                    summary.append(f"  * {rec}")
        
        # Efficiency Metrics
        summary.append("\nEfficiency Metrics:")
        for resource, efficiency in results['metrics']['current_efficiency'].items():
            if isinstance(efficiency, dict):
                for sub_resource, value in efficiency.items():
                    summary.append(f"- {resource.title()} ({sub_resource}): {value:.1f}%")
            else:
                summary.append(f"- {resource.title()}: {efficiency:.1f}%")
        
        # Potential Improvements
        summary.append("\nPotential Improvements:")
        for resource, improvement in results['metrics']['potential_improvements'].items():
            if isinstance(improvement, dict):
                for sub_resource, value in improvement.items():
                    summary.append(f"- {resource.title()} ({sub_resource}): {value:.1f}%")
            else:
                summary.append(f"- {resource.title()}: {improvement:.1f}%")
        
        return "\n".join(summary)

if __name__ == "__main__":
    # Test the ResourceOptimizer tool
    resource_config = {
        "monitored_mounts": ["/"],
        "thresholds": {
            "cpu": {"high": 80, "low": 20},
            "memory": {"high": 85, "low": 30},
            "storage": {"high": 80, "low": 40}
        }
    }
    
    optimizer = ResourceOptimizer(
        resource_config=resource_config,
        target_components=["planning_agent", "testing_agent"],
        optimization_strategy="adaptive"
    )
    print(optimizer.run()) 