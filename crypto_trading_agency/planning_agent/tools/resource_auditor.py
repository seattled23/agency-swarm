from agency_swarm.tools import BaseTool
from pydantic import Field
import os
import json
import psutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

class ResourceAuditor(BaseTool):
    """
    Tool for detailed resource utilization analysis and optimization recommendations.
    """
    
    audit_targets: List[str] = Field(
        default=["cpu", "memory", "disk", "network"],
        description="Resource types to audit"
    )
    
    sampling_interval: int = Field(
        default=60,
        description="Interval in seconds between resource measurements"
    )
    
    sample_count: int = Field(
        default=10,
        description="Number of samples to collect for each resource"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.results_dir = Path("audit_results")
        self.results_dir.mkdir(exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(self.results_dir / 'resource_audit.log'),
                logging.StreamHandler()
            ]
        )

    def collect_cpu_metrics(self) -> Dict:
        """Collect CPU utilization metrics."""
        return {
            "usage_percent": psutil.cpu_percent(interval=1),
            "core_count": psutil.cpu_count(),
            "load_average": psutil.getloadavg(),
            "frequency": {
                "current": psutil.cpu_freq().current if psutil.cpu_freq() else None,
                "min": psutil.cpu_freq().min if psutil.cpu_freq() else None,
                "max": psutil.cpu_freq().max if psutil.cpu_freq() else None
            }
        }

    def collect_memory_metrics(self) -> Dict:
        """Collect memory utilization metrics."""
        mem = psutil.virtual_memory()
        return {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "percent": mem.percent,
            "swap_usage": psutil.swap_memory()._asdict()
        }

    def collect_disk_metrics(self) -> Dict:
        """Collect disk utilization metrics."""
        disk_usage = {}
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_usage[partition.mountpoint] = {
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent
                }
            except Exception as e:
                logging.warning(f"Could not collect disk metrics for {partition.mountpoint}: {str(e)}")
        return disk_usage

    def collect_network_metrics(self) -> Dict:
        """Collect network utilization metrics."""
        net_io = psutil.net_io_counters()
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "connections": len(psutil.net_connections())
        }

    def analyze_resource_usage(self, metrics: Dict) -> Dict:
        """Analyze resource usage patterns and generate recommendations."""
        recommendations = []
        warnings = []
        
        # CPU Analysis
        if "cpu" in metrics:
            cpu_usage = metrics["cpu"]["usage_percent"]
            if cpu_usage > 80:
                warnings.append("High CPU utilization detected")
                recommendations.append("Consider scaling CPU resources or optimizing CPU-intensive operations")
            elif cpu_usage < 20:
                recommendations.append("CPU resources may be over-provisioned")

        # Memory Analysis
        if "memory" in metrics:
            mem_usage = metrics["memory"]["percent"]
            if mem_usage > 85:
                warnings.append("High memory usage detected")
                recommendations.append("Implement memory optimization or increase available memory")
            elif mem_usage < 30:
                recommendations.append("Memory resources may be over-provisioned")

        # Disk Analysis
        if "disk" in metrics:
            for mount, usage in metrics["disk"].items():
                if usage["percent"] > 85:
                    warnings.append(f"High disk usage on {mount}")
                    recommendations.append(f"Clean up or expand disk space on {mount}")

        # Network Analysis
        if "network" in metrics:
            if metrics["network"]["connections"] > 1000:
                warnings.append("High number of network connections")
                recommendations.append("Review network connection handling and implement connection pooling")

        return {
            "warnings": warnings,
            "recommendations": recommendations
        }

    def run(self) -> str:
        """
        Execute resource audit and generate report.
        """
        try:
            # Create audit session directory
            session_dir = self.results_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
            session_dir.mkdir(exist_ok=True)
            
            # Collect metrics
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "metrics": {}
            }
            
            if "cpu" in self.audit_targets:
                metrics["metrics"]["cpu"] = self.collect_cpu_metrics()
            
            if "memory" in self.audit_targets:
                metrics["metrics"]["memory"] = self.collect_memory_metrics()
            
            if "disk" in self.audit_targets:
                metrics["metrics"]["disk"] = self.collect_disk_metrics()
            
            if "network" in self.audit_targets:
                metrics["metrics"]["network"] = self.collect_network_metrics()
            
            # Analyze metrics
            analysis = self.analyze_resource_usage(metrics["metrics"])
            metrics["analysis"] = analysis
            
            # Export results
            report_path = session_dir / "audit_report.json"
            with open(report_path, 'w') as f:
                json.dump(metrics, f, indent=4)
            
            logging.info(f"Audit completed. Report saved to {report_path}")
            
            # Generate and return summary
            return self._generate_summary(metrics)
            
        except Exception as e:
            logging.error(f"Error during resource audit: {str(e)}")
            raise

    def _generate_summary(self, results: Dict) -> str:
        """Generate a human-readable summary of the audit results."""
        summary = []
        summary.append("Resource Audit Summary:")
        summary.append("-" * 50)
        
        metrics = results["metrics"]
        
        if "cpu" in metrics:
            summary.append("\nCPU Utilization:")
            summary.append(f"- Usage: {metrics['cpu']['usage_percent']}%")
            summary.append(f"- Cores: {metrics['cpu']['core_count']}")
            summary.append(f"- Load Average: {metrics['cpu']['load_average']}")
        
        if "memory" in metrics:
            summary.append("\nMemory Utilization:")
            summary.append(f"- Used: {metrics['memory']['percent']}%")
            summary.append(f"- Available: {metrics['memory']['available'] / (1024**3):.2f} GB")
            summary.append(f"- Total: {metrics['memory']['total'] / (1024**3):.2f} GB")
        
        if "disk" in metrics:
            summary.append("\nDisk Utilization:")
            for mount, usage in metrics["disk"].items():
                summary.append(f"\nMount Point: {mount}")
                summary.append(f"- Used: {usage['percent']}%")
                summary.append(f"- Free: {usage['free'] / (1024**3):.2f} GB")
                summary.append(f"- Total: {usage['total'] / (1024**3):.2f} GB")
        
        if "network" in metrics:
            summary.append("\nNetwork Utilization:")
            summary.append(f"- Bytes Sent: {metrics['network']['bytes_sent'] / (1024**2):.2f} MB")
            summary.append(f"- Bytes Received: {metrics['network']['bytes_recv'] / (1024**2):.2f} MB")
            summary.append(f"- Active Connections: {metrics['network']['connections']}")
        
        if "analysis" in results:
            if results["analysis"]["warnings"]:
                summary.append("\nWarnings:")
                for warning in results["analysis"]["warnings"]:
                    summary.append(f"- {warning}")
            
            if results["analysis"]["recommendations"]:
                summary.append("\nRecommendations:")
                for rec in results["analysis"]["recommendations"]:
                    summary.append(f"- {rec}")
        
        return "\n".join(summary)

if __name__ == "__main__":
    # Test the ResourceAuditor tool
    auditor = ResourceAuditor()
    print(auditor.run()) 