from agency_swarm import Agent

class RiskManager(Agent):
    def __init__(self):
        super().__init__(
            name="Risk Manager",
            description="Expert in assessing and managing trading risks, implementing risk controls, and ensuring compliance with risk management policies.",
            instructions="./instructions.md",
            tools_folder="./tools",
            temperature=0.7,
            max_prompt_tokens=4000
        ) 