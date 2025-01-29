from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import subprocess
import json

load_dotenv()

class AgentOnboardingTool(BaseTool):
    """
    Tool for automating the process of creating and configuring new agents.
    Handles agent template creation, configuration, and integration with the agency.
    """
    agent_name: str = Field(
        ..., description="Name of the agent to create (e.g., 'MarketAnalyst', 'RiskManager')"
    )
    agent_description: str = Field(
        ..., description="Brief description of the agent's role and responsibilities"
    )
    division: str = Field(
        ..., description="Division the agent belongs to (e.g., 'Analysis', 'Projects')"
    )

    def run(self):
        """
        Creates a new agent with the specified configuration and integrates it into the agency.
        """
        try:
            # Create agent directory structure
            agent_path = f"agency_divisions/{self.division.lower()}/agents/{self.agent_name.lower()}"
            os.makedirs(f"{agent_path}/tools", exist_ok=True)

            # Create agent class file
            self._create_agent_class()

            # Create agent instructions
            self._create_agent_instructions()

            # Create __init__.py
            self._create_init_file()

            # Update agency configuration
            self._update_agency_config()

            return f"Successfully created agent {self.agent_name} in {self.division} division"

        except Exception as e:
            return f"Error creating agent: {str(e)}"

    def _create_agent_class(self):
        """Creates the agent's main class file"""
        agent_code = f'''from agency_swarm import Agent

class {self.agent_name}(Agent):
    def __init__(self):
        super().__init__(
            name="{self.agent_name}",
            description="{self.agent_description}",
            instructions="./instructions.md",
            tools_folder="./tools",
            temperature=0.5,
            max_prompt_tokens=25000,
        )
'''
        agent_file = f"agency_divisions/{self.division.lower()}/agents/{self.agent_name.lower()}/{self.agent_name.lower()}.py"
        with open(agent_file, 'w') as f:
            f.write(agent_code)

    def _create_agent_instructions(self):
        """Creates the agent's instruction file"""
        instructions = f'''# Agent Role

{self.agent_description}

# Goals

1. [To be defined based on agent type]
2. [To be defined based on agent type]
3. [To be defined based on agent type]

# Process Workflow

1. Step 1
2. Step 2
3. Step 3
'''
        instructions_file = f"agency_divisions/{self.division.lower()}/agents/{self.agent_name.lower()}/instructions.md"
        with open(instructions_file, 'w') as f:
            f.write(instructions)

    def _create_init_file(self):
        """Creates the __init__.py file for the agent"""
        init_code = f'''from .{self.agent_name.lower()} import {self.agent_name}

__all__ = ['{self.agent_name}']
'''
        init_file = f"agency_divisions/{self.division.lower()}/agents/{self.agent_name.lower()}/__init__.py"
        with open(init_file, 'w') as f:
            f.write(init_code)

    def _update_agency_config(self):
        """Updates the agency configuration to include the new agent"""
        config_file = "agency_divisions/agency_config.json"
        
        # Create config if it doesn't exist
        if not os.path.exists(config_file):
            config = {
                "agents": {},
                "communication_flows": []
            }
        else:
            with open(config_file, 'r') as f:
                config = json.load(f)

        # Add agent to config
        config["agents"][self.agent_name] = {
            "division": self.division,
            "description": self.agent_description,
            "status": "initialized"
        }

        # Save updated config
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

if __name__ == "__main__":
    # Test the tool
    tool = AgentOnboardingTool(
        agent_name="TestAgent",
        agent_description="Test agent for validation",
        division="Testing"
    )
    print(tool.run()) 