from agency_swarm import Agent

class SelfImprovementAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Self Improvement Agent",
            description="Expert in analyzing system performance, identifying areas for improvement, and implementing optimizations across all components of the trading system.",
            instructions="./instructions.md",
            tools_folder="./tools",
            temperature=0.7,
            max_prompt_tokens=4000
        ) 