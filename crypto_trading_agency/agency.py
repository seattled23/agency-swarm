from agency_swarm import Agency

# Import all agents
from project_manager.project_manager import ProjectManager
from market_analyst.market_analyst import MarketAnalyst
from strategy_developer.strategy_developer import StrategyDeveloper
from risk_manager.risk_manager import RiskManager
from execution_manager.execution_manager import ExecutionManager
from testing_agent.testing_agent import TestingAgent
from planning_agent.planning_agent import PlanningAgent
from alignment_agent.alignment_agent import AlignmentAgent
from self_improvement_agent.self_improvement_agent import SelfImprovementAgent

# Initialize all agents
project_manager = ProjectManager()
market_analyst = MarketAnalyst()
strategy_developer = StrategyDeveloper()
risk_manager = RiskManager()
execution_manager = ExecutionManager()
testing_agent = TestingAgent()
planning_agent = PlanningAgent()
alignment_agent = AlignmentAgent()
self_improvement = SelfImprovementAgent()

# Create agency with communication flows
agency = Agency(
    [
        project_manager,  # Project Manager is the entry point
        # Project Manager's direct communications
        [project_manager, market_analyst],
        [project_manager, strategy_developer],
        [project_manager, risk_manager],
        [project_manager, execution_manager],
        [project_manager, testing_agent],
        [project_manager, planning_agent],
        
        # Market Analysis and Strategy Development flow
        [market_analyst, strategy_developer],
        [market_analyst, risk_manager],
        
        # Strategy Development and Risk Management flow
        [strategy_developer, risk_manager],
        [strategy_developer, execution_manager],
        
        # Risk Management and Execution flow
        [risk_manager, execution_manager],
        
        # Testing and Quality Assurance flow
        [testing_agent, market_analyst],
        [testing_agent, strategy_developer],
        [testing_agent, execution_manager],
        
        # Planning and Optimization flow
        [planning_agent, market_analyst],
        [planning_agent, strategy_developer],
        [planning_agent, execution_manager],
        
        # System Improvement and Alignment flow
        [self_improvement, alignment_agent],
        [alignment_agent, testing_agent],
    ],
    shared_instructions='agency_manifesto.md',
    temperature=0.7,
    max_prompt_tokens=4000
)

if __name__ == "__main__":
    agency.run_demo() 