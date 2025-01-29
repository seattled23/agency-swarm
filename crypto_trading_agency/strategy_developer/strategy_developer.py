from agency_swarm import Agent

class StrategyDeveloper(Agent):
    def __init__(self):
        super().__init__(
            name="Strategy Developer",
            description="Expert in developing and optimizing trading strategies based on market analysis and machine learning models.",
            instructions="./instructions.md",
            tools_folder="./tools",
            temperature=0.7,
            max_prompt_tokens=4000
        ) 