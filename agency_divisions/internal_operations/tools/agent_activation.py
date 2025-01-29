from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import json
import importlib
import sys

load_dotenv()

class AgentActivationTool(BaseTool):
    """
    Tool for activating agents and establishing their communication flows within the agency.
    Handles agent initialization, communication setup, and status tracking.
    """
    agent_name: str = Field(
        ..., description="Name of the agent to activate (must exist in agency_config.json)"
    )
    verify_dependencies: bool = Field(
        True, description="Whether to verify all required dependencies before activation"
    )

    def run(self):
        """
        Activates an agent and establishes its communication flows within the agency.
        """
        try:
            # Load agency configuration
            config = self._load_config()
            
            # Verify agent exists
            if self.agent_name not in config["agents"]:
                return f"Error: Agent {self.agent_name} not found in configuration"
            
            # Get agent details
            agent_info = config["agents"][self.agent_name]
            division = agent_info["division"]
            
            # Verify dependencies if requested
            if self.verify_dependencies:
                missing_deps = self._verify_dependencies(config)
                if missing_deps:
                    return f"Error: Missing required dependencies: {', '.join(missing_deps)}"
            
            # Import and initialize agent
            success = self._initialize_agent(division)
            if not success:
                return f"Error: Failed to initialize agent {self.agent_name}"
            
            # Update agent status
            config["agents"][self.agent_name]["status"] = "active"
            
            # Update division structure
            div_structure = config["division_structure"][division]
            if self.agent_name in div_structure["pending_agents"]:
                div_structure["pending_agents"].remove(self.agent_name)
            if self.agent_name not in div_structure["active_agents"]:
                div_structure["active_agents"].append(self.agent_name)
            
            # Save updated configuration
            self._save_config(config)
            
            return f"Successfully activated agent {self.agent_name} in {division} division"
            
        except Exception as e:
            return f"Error activating agent: {str(e)}"

    def _load_config(self):
        """Loads the agency configuration"""
        config_file = "agency_divisions/agency_config.json"
        with open(config_file, 'r') as f:
            return json.load(f)

    def _save_config(self, config):
        """Saves the updated agency configuration"""
        config_file = "agency_divisions/agency_config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def _verify_dependencies(self, config):
        """Verifies all required dependencies for the agent are active"""
        missing_deps = []
        
        # Check communication flows for dependencies
        for flow in config["communication_flows"]:
            if self.agent_name in flow:
                other_agent = flow[0] if flow[1] == self.agent_name else flow[1]
                if other_agent not in config["agents"] or config["agents"][other_agent]["status"] != "active":
                    missing_deps.append(other_agent)
        
        return missing_deps

    def _initialize_agent(self, division):
        """Imports and initializes the agent"""
        try:
            # Add agent's directory to Python path
            agent_path = f"agency_divisions/{division.lower()}/agents/{self.agent_name.lower()}"
            if agent_path not in sys.path:
                sys.path.append(agent_path)
            
            # Import agent module
            module = importlib.import_module(self.agent_name.lower())
            
            # Get agent class
            agent_class = getattr(module, self.agent_name)
            
            # Initialize agent (this will verify the agent can be instantiated)
            agent = agent_class()
            
            return True
        except Exception as e:
            print(f"Error initializing agent: {str(e)}")
            return False

    def _setup_communication_flows(self, config):
        """Sets up communication flows for the agent"""
        flows = []
        for flow in config["communication_flows"]:
            if self.agent_name in flow:
                flows.append(flow)
        return flows

if __name__ == "__main__":
    # Test the tool
    tool = AgentActivationTool(
        agent_name="TestAgent",
        verify_dependencies=True
    )
    print(tool.run()) 