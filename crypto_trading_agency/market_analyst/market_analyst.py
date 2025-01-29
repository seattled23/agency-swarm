from agency_swarm import Agent

class MarketAnalyst(Agent):
    def __init__(self):
        super().__init__(
            name="Market Analyst",
            description="Expert in cryptocurrency market analysis, technical analysis, and market prediction using advanced tools and ML models.",
            instructions="./instructions.md",
            tools_folder="./tools",
            temperature=0.7,
            max_prompt_tokens=4000
        ) 