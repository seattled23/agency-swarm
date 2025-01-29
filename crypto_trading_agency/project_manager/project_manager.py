from agency_swarm import Agent

class ProjectManager(Agent):
    def __init__(self):
        super().__init__(
            name="Project Manager",
            description="Responsible for overseeing the entire development process, coordinating between agents, and ensuring project success.",
            instructions="./instructions.md",
            tools_folder="./tools",
            temperature=0.7,
            max_prompt_tokens=4000
        ) 