from agency_swarm import Agent

class ExecutionManager(Agent):
    def __init__(self):
        super().__init__(
            name="Execution Manager",
            description="Expert in executing trading strategies, managing orders, and optimizing trade execution across multiple exchanges.",
            instructions="./instructions.md",
            tools_folder="./tools",
            temperature=0.7,
            max_prompt_tokens=4000
        ) 