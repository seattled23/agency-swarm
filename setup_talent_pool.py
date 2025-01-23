import os
import shutil

# Base directory for the talent pool agency
base_dir = "talent_pool"

# List of agents
agents = [
    "WorkflowDesigner",
    "WebResearchDirector",
    "WebResearcher",
    "ReverseEngineer",
    "SwarmCommunicator",
    "SwarmCoordinator",
    "CodeAdapter",
    "CodeWriter",
    "CodeTester",
    "CodeDebugger",
    "ProjectManager",
    "ProgressChecker",
    "ReasoningAgent",
    "BiomimeticSpecialist",
    "AlignmentOversight"
]

# Create base directory
if os.path.exists(base_dir):
    shutil.rmtree(base_dir)
os.makedirs(base_dir)

# Create agent directories and files
for agent in agents:
    # Create agent directory
    agent_dir = os.path.join(base_dir, agent)
    os.makedirs(agent_dir)
    
    # Create tools directory
    tools_dir = os.path.join(agent_dir, "tools")
    os.makedirs(tools_dir)
    
    # Create __init__.py
    with open(os.path.join(agent_dir, "__init__.py"), "w") as f:
        f.write(f"from .{agent.lower()} import {agent}\n")
    
    # Create agent.py
    with open(os.path.join(agent_dir, f"{agent.lower()}.py"), "w") as f:
        f.write(f"""from agency_swarm import Agent

class {agent}(Agent):
    def __init__(self):
        super().__init__(
            name="{agent}",
            description="{agent} specialized agent in the talent pool",
            instructions="./instructions.md",
            tools_folder="./tools",
            temperature=0.5,
            max_prompt_tokens=4000,
        )
""")
    
    # Create instructions.md
    with open(os.path.join(agent_dir, "instructions.md"), "w") as f:
        f.write(f"""# Agent Role

The {agent} is a specialized agent in the talent pool responsible for specific tasks and capabilities.

# Goals

1. Primary goal specific to {agent}
2. Secondary goals and objectives
3. Support goals for the talent pool agency

# Process Workflow

1. Initialize and prepare for tasks
2. Execute primary responsibilities
3. Collaborate with other agents as needed
4. Report progress and results
""")

# Create agency.py
with open(os.path.join(base_dir, "agency.py"), "w") as f:
    f.write("""from agency_swarm import Agency
""")
    
    # Import all agents
    for agent in agents:
        f.write(f"from {agent}.{agent.lower()} import {agent}\n")
    
    f.write("\n# Initialize agents\n")
    for agent in agents:
        f.write(f"{agent.lower()} = {agent}()\n")
    
    f.write("\n# Create agency with communication flows\n")
    f.write("agency = Agency([\n")
    f.write("    alignment_oversight,  # AlignmentOversight agent is the entry point\n")
    
    # Create communication flows
    for agent in agents:
        if agent != "AlignmentOversight":
            f.write(f"    [alignment_oversight, {agent.lower()}],  # AlignmentOversight can communicate with {agent}\n")
    
    # Add additional communication flows
    f.write("    # Additional communication flows between agents\n")
    f.write("    [projectmanager, workflowdesigner],\n")
    f.write("    [webresearchdirector, webresearcher],\n")
    f.write("    [swarmcoordinator, swarmcommunicator],\n")
    f.write("    [codewriter, codetester],\n")
    f.write("    [codetester, codedebugger],\n")
    f.write("],\n")
    f.write('    shared_instructions="agency_manifesto.md",\n')
    f.write("    temperature=0.5,\n")
    f.write("    max_prompt_tokens=4000\n")
    f.write(")\n\n")
    f.write('if __name__ == "__main__":\n')
    f.write("    agency.run_demo()")

# Create agency_manifesto.md
with open(os.path.join(base_dir, "agency_manifesto.md"), "w") as f:
    f.write("""# Talent Pool Agency

## Agency Description
The Talent Pool Agency is a specialized collection of AI agents designed to provide various capabilities and services to other swarms. It functions as a centralized resource pool where different swarms can access specialized agents for specific tasks and functions.

## Mission Statement
To provide a reliable, safe, and efficient pool of specialized AI agents that can be utilized by other swarms to enhance their capabilities while maintaining strict alignment and safety standards.

## Operating Environment
The agency operates in a distributed environment where multiple swarms can request and utilize its agents. The AlignmentOversight agent ensures all operations remain safe and aligned with beneficial objectives.

## Core Principles
1. Safety First - All operations are monitored by the AlignmentOversight agent
2. Efficiency - Agents are optimized for their specific roles
3. Collaboration - Seamless integration with other swarms
4. Adaptability - Flexible response to various requirements
5. Continuous Improvement - Regular updates and improvements to agent capabilities

## Communication Protocol
1. All requests must pass through the AlignmentOversight agent
2. Clear communication channels between agents
3. Standardized reporting and monitoring
4. Regular status updates and progress checks
""")

# Create requirements.txt
with open(os.path.join(base_dir, "requirements.txt"), "w") as f:
    f.write("""agency-swarm>=0.1.0
python-dotenv>=0.19.0
openai>=1.3.0
""")

print("Talent Pool agency structure created successfully!")