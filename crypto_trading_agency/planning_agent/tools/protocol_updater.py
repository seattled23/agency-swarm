from agency_swarm.tools import BaseTool
from pydantic import Field
import os
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

class ProtocolUpdater(BaseTool):
    """
    Tool for implementing and managing optimized communication protocols between agents.
    Handles protocol transitions, message format updates, and routing optimizations.
    """
    
    protocol_config: Dict = Field(
        ...,
        description="Communication protocol configuration to implement"
    )
    
    affected_agents: List[str] = Field(
        ...,
        description="List of agents affected by the protocol update"
    )
    
    update_strategy: str = Field(
        default="rolling",
        description="Strategy for updating protocols: 'rolling', 'immediate', or 'scheduled'"
    )
    
    fallback_enabled: bool = Field(
        default=True,
        description="Whether to enable fallback mechanisms during updates"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.results_dir = Path("protocol_updates")
        self.results_dir.mkdir(exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(self.results_dir / 'protocol_update.log'),
                logging.StreamHandler()
            ]
        )

    def validate_protocol_config(self) -> Dict[str, List[str]]:
        """Validate the protocol configuration for completeness and compatibility."""
        issues = {"errors": [], "warnings": []}
        
        required_fields = ["protocol", "sync_methods", "message_formats", "routing"]
        for field in required_fields:
            if field not in self.protocol_config:
                issues["errors"].append(f"Missing required field: {field}")
        
        if "sync_methods" in self.protocol_config:
            sync_methods = self.protocol_config["sync_methods"]
            if not isinstance(sync_methods, dict):
                issues["errors"].append("sync_methods must be a dictionary")
            elif not sync_methods.get("real_time") and not sync_methods.get("batch"):
                issues["warnings"].append("No sync methods specified")
        
        if "message_formats" in self.protocol_config:
            formats = self.protocol_config["message_formats"]
            if not formats.get("default"):
                issues["errors"].append("No default message format specified")
            if not formats.get("fallback") and self.fallback_enabled:
                issues["warnings"].append("No fallback message format specified")
        
        return issues

    def prepare_protocol_transition(self) -> Dict:
        """Prepare the protocol transition plan."""
        transition_plan = {
            "timestamp": datetime.now().isoformat(),
            "strategy": self.update_strategy,
            "phases": []
        }
        
        if self.update_strategy == "rolling":
            # Create phased transition plan
            for i, agent in enumerate(self.affected_agents):
                phase = {
                    "phase": i + 1,
                    "agent": agent,
                    "actions": [
                        {
                            "step": "backup",
                            "description": f"Backup current protocol configuration for {agent}"
                        },
                        {
                            "step": "update",
                            "description": f"Update protocol configuration for {agent}"
                        },
                        {
                            "step": "verify",
                            "description": f"Verify protocol functionality for {agent}"
                        }
                    ],
                    "rollback_plan": {
                        "trigger_conditions": ["connectivity_loss", "performance_degradation"],
                        "steps": ["revert_to_backup", "verify_rollback"]
                    }
                }
                transition_plan["phases"].append(phase)
        
        elif self.update_strategy == "immediate":
            # Create single-phase transition plan
            transition_plan["phases"].append({
                "phase": 1,
                "agents": self.affected_agents,
                "actions": [
                    {
                        "step": "backup",
                        "description": "Backup current protocol configuration for all agents"
                    },
                    {
                        "step": "update",
                        "description": "Update protocol configuration for all agents"
                    },
                    {
                        "step": "verify",
                        "description": "Verify protocol functionality across all agents"
                    }
                ],
                "rollback_plan": {
                    "trigger_conditions": ["connectivity_loss", "performance_degradation"],
                    "steps": ["revert_to_backup", "verify_rollback"]
                }
            })
        
        return transition_plan

    def configure_message_routing(self) -> Dict:
        """Configure message routing based on the protocol configuration."""
        routing_config = {
            "timestamp": datetime.now().isoformat(),
            "routes": {}
        }
        
        routing = self.protocol_config.get("routing", {})
        method = routing.get("method", "static")
        
        for agent in self.affected_agents:
            agent_routes = {
                "primary_route": {
                    "protocol": self.protocol_config["protocol"],
                    "sync_method": self.protocol_config["sync_methods"]["real_time"][0],
                    "message_format": self.protocol_config["message_formats"]["default"]
                }
            }
            
            if self.fallback_enabled:
                agent_routes["fallback_route"] = {
                    "protocol": "basic",
                    "sync_method": self.protocol_config["sync_methods"]["batch"][0],
                    "message_format": self.protocol_config["message_formats"]["fallback"]
                }
            
            if method == "adaptive":
                agent_routes["routing_policy"] = {
                    "load_balancing": routing.get("load_balancing", True),
                    "fallback_strategy": routing.get("fallback_strategy", "round_robin")
                }
            
            routing_config["routes"][agent] = agent_routes
        
        return routing_config

    def verify_protocol_compatibility(self) -> Dict[str, bool]:
        """Verify protocol compatibility between agents."""
        compatibility_status = {}
        
        for agent in self.affected_agents:
            # Verify protocol support
            protocol_supported = True  # Simulated check
            sync_methods_supported = True  # Simulated check
            message_formats_supported = True  # Simulated check
            
            compatibility_status[agent] = {
                "protocol_supported": protocol_supported,
                "sync_methods_supported": sync_methods_supported,
                "message_formats_supported": message_formats_supported,
                "overall_compatible": all([
                    protocol_supported,
                    sync_methods_supported,
                    message_formats_supported
                ])
            }
        
        return compatibility_status

    def run(self) -> str:
        """
        Execute protocol update process and generate report.
        """
        try:
            # Create update session directory
            session_dir = self.results_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
            session_dir.mkdir(exist_ok=True)
            
            # Validate protocol configuration
            validation_results = self.validate_protocol_config()
            if validation_results["errors"]:
                raise ValueError(f"Protocol configuration validation failed: {validation_results['errors']}")
            
            # Verify compatibility
            compatibility_status = self.verify_protocol_compatibility()
            incompatible_agents = [
                agent for agent, status in compatibility_status.items()
                if not status["overall_compatible"]
            ]
            if incompatible_agents:
                raise ValueError(f"Protocol incompatible for agents: {incompatible_agents}")
            
            # Prepare transition plan
            transition_plan = self.prepare_protocol_transition()
            
            # Configure routing
            routing_config = self.configure_message_routing()
            
            # Compile results
            update_results = {
                "timestamp": datetime.now().isoformat(),
                "validation": validation_results,
                "compatibility": compatibility_status,
                "transition_plan": transition_plan,
                "routing_config": routing_config
            }
            
            # Export results
            report_path = session_dir / "protocol_update_report.json"
            with open(report_path, 'w') as f:
                json.dump(update_results, f, indent=4)
            
            logging.info(f"Protocol update plan completed. Report saved to {report_path}")
            
            # Return summary
            return self._generate_summary(update_results)
            
        except Exception as e:
            logging.error(f"Error during protocol update: {str(e)}")
            raise

    def _generate_summary(self, results: Dict) -> str:
        """Generate a human-readable summary of the protocol update results."""
        summary = []
        summary.append("Protocol Update Summary")
        summary.append("=" * 50)
        
        # Validation Results
        summary.append("\nValidation Results:")
        if results["validation"]["warnings"]:
            summary.append("Warnings:")
            for warning in results["validation"]["warnings"]:
                summary.append(f"- {warning}")
        
        # Compatibility Status
        summary.append("\nCompatibility Status:")
        for agent, status in results["compatibility"].items():
            summary.append(f"\n{agent}:")
            for check, result in status.items():
                summary.append(f"- {check.replace('_', ' ').title()}: {'Yes' if result else 'No'}")
        
        # Transition Plan
        summary.append("\nTransition Plan:")
        summary.append(f"Strategy: {results['transition_plan']['strategy']}")
        summary.append(f"Total Phases: {len(results['transition_plan']['phases'])}")
        
        # Routing Configuration
        summary.append("\nRouting Configuration:")
        for agent, routes in results["routing_config"]["routes"].items():
            summary.append(f"\n{agent}:")
            summary.append(f"- Primary: {routes['primary_route']['protocol']} / {routes['primary_route']['sync_method']}")
            if "fallback_route" in routes:
                summary.append(f"- Fallback: {routes['fallback_route']['protocol']} / {routes['fallback_route']['sync_method']}")
        
        return "\n".join(summary)

if __name__ == "__main__":
    # Test the ProtocolUpdater tool
    protocol_config = {
        "protocol": "hybrid",
        "sync_methods": {
            "real_time": ["WebSocket", "gRPC"],
            "batch": ["REST", "Message Queue"]
        },
        "message_formats": {
            "default": "Protocol Buffers",
            "fallback": "JSON"
        },
        "routing": {
            "method": "adaptive",
            "load_balancing": True,
            "fallback_strategy": "round_robin"
        }
    }
    
    updater = ProtocolUpdater(
        protocol_config=protocol_config,
        affected_agents=["planning_agent", "testing_agent"],
        update_strategy="rolling"
    )
    print(updater.run()) 