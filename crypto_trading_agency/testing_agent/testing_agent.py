from agency_swarm import Agent

class TestingAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Testing Agent",
            description="Expert in testing trading strategies, validating market analysis models, and ensuring system reliability through comprehensive testing protocols.",
            instructions="./instructions.md",
            tools_folder="./tools",
            temperature=0.7,
            max_prompt_tokens=4000
        ) 