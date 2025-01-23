import os

def verify_structure():
    base_dir = "talent_pool"
    required_files = ["agency.py", "agency_manifesto.md", "requirements.txt"]
    agents = [
        "WorkflowDesigner", "WebResearchDirector", "WebResearcher", 
        "ReverseEngineer", "SwarmCommunicator", "SwarmCoordinator",
        "CodeAdapter", "CodeWriter", "CodeTester", "CodeDebugger",
        "ProjectManager", "ProgressChecker", "ReasoningAgent",
        "BiomimeticSpecialist", "AlignmentOversight"
    ]

    # Check if base directory exists
    if not os.path.exists(base_dir):
        print(f"❌ Base directory '{base_dir}' not found")
        return False

    # Check required files
    for file in required_files:
        file_path = os.path.join(base_dir, file)
        if not os.path.exists(file_path):
            print(f"❌ Required file '{file}' not found")
            return False
        else:
            print(f"✅ Found {file}")

    # Check agent directories and their structure
    for agent in agents:
        agent_dir = os.path.join(base_dir, agent)
        if not os.path.exists(agent_dir):
            print(f"❌ Agent directory '{agent}' not found")
            return False
        
        # Check agent files
        required_agent_files = [
            "__init__.py",
            f"{agent.lower()}.py",
            "instructions.md"
        ]
        for file in required_agent_files:
            file_path = os.path.join(agent_dir, file)
            if not os.path.exists(file_path):
                print(f"❌ Required file '{file}' not found in {agent}")
                return False
            else:
                print(f"✅ Found {agent}/{file}")
        
        # Check tools directory
        tools_dir = os.path.join(agent_dir, "tools")
        if not os.path.exists(tools_dir):
            print(f"❌ Tools directory not found in {agent}")
            return False
        else:
            print(f"✅ Found {agent}/tools directory")

    print("\n✅ All structure checks passed!")
    return True

if __name__ == "__main__":
    verify_structure() 