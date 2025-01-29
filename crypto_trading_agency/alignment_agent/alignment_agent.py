from agency_swarm import Agent
from agency_swarm.tools import CodeInterpreter, FileSearch

class AlignmentAgent(Agent):
    """
    Alignment Agent responsible for real-time monitoring and safety enforcement
    across all agent operations.
    """
    
    def __init__(self):
        super().__init__(
            name="Alignment Agent",
            description="Expert in ensuring alignment between trading strategies, risk management policies, and overall project objectives.",
            instructions="./instructions.md",
            tools_folder="./tools",
            temperature=0.7,
            max_prompt_tokens=4000
        ) 