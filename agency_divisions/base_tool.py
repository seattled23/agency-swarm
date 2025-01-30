from abc import ABC, abstractmethod
from pydantic import BaseModel

class BaseTool(BaseModel, ABC):
    """Base class for all tools in the agency."""
    
    @abstractmethod
    def run(self):
        """Execute the tool's main functionality."""
        pass 