from agency_swarm import Agent
from agency_swarm.tools import CodeInterpreter, FileSearch

class PlanningAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Planning Agent",
            description="Expert in project planning, task delegation, and resource allocation, ensuring efficient development and implementation of trading systems.",
            instructions="./instructions.md",
            tools_folder="./tools",
            tools=[CodeInterpreter, FileSearch],
            temperature=0.7,
            max_prompt_tokens=4000
        ) 