from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
import asyncio
from dataclasses import dataclass
from enum import Enum
import threading
import queue
import signal
import logging
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('safety_monitor.log'),
        logging.StreamHandler()
    ]
)

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SafetyStatus(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    VIOLATION = "violation"
    EMERGENCY = "emergency"

@dataclass
class SafetyMetrics:
    risk_level: RiskLevel
    safety_score: float
    violations_detected: List[str]
    active_constraints: List[str]
    last_assessment: datetime

class SafetyMonitor(BaseTool):
    """
    Advanced real-time safety monitoring and intervention tool for ensuring
    alignment and preventing potential issues across all agent operations.
    """
    
    monitor_id: Optional[str] = Field(
        None, description="Unique identifier for the monitoring session"
    )
    target_agent: str = Field(
        ..., description="ID of the agent to monitor"
    )
    safety_threshold: float = Field(
        0.95, description="Safety threshold score (0-1)"
    )
    monitoring_interval: float = Field(
        1.0, description="Monitoring interval in seconds"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.db_path = Path('project_data/safety_monitoring.db')
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_database()
        
        # Initialize monitoring state
        self.is_monitoring = False
        self.monitoring_thread = None
        self.event_queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Initialize emergency shutdown handler
        signal.signal(signal.SIGINT, self.emergency_shutdown)
        signal.signal(signal.SIGTERM, self.emergency_shutdown)

    def initialize_database(self):
        """Initialize the SQLite database for safety monitoring."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS safety_events (
                id INTEGER PRIMARY KEY,
                monitor_id TEXT,
                agent_id TEXT,
                event_type TEXT,
                risk_level TEXT,
                description TEXT,
                timestamp TEXT,
                action_taken TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS safety_metrics (
                id INTEGER PRIMARY KEY,
                monitor_id TEXT,
                agent_id TEXT,
                metric_type TEXT,
                metric_value REAL,
                timestamp TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS safety_violations (
                id INTEGER PRIMARY KEY,
                monitor_id TEXT,
                agent_id TEXT,
                violation_type TEXT,
                severity TEXT,
                details TEXT,
                timestamp TEXT,
                resolution TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

    async def start_monitoring(self):
        """Start real-time safety monitoring."""
        if self.is_monitoring:
            return "Monitoring already active"
        
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
        
        logging.info(f"Started monitoring agent: {self.target_agent}")
        return "Monitoring started successfully"

    def _monitoring_loop(self):
        """Main monitoring loop running in a separate thread."""
        while self.is_monitoring:
            try:
                # Perform safety checks
                safety_status = self.check_safety_status()
                
                # Process any pending events
                while not self.event_queue.empty():
                    event = self.event_queue.get_nowait()
                    self.process_safety_event(event)
                
                # Take action if necessary
                if safety_status.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                    self.handle_safety_violation(safety_status)
                
                # Record metrics
                self.record_safety_metrics(safety_status)
                
                # Wait for next interval
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logging.error(f"Error in monitoring loop: {str(e)}")
                self.record_safety_event(
                    "error",
                    RiskLevel.HIGH,
                    f"Monitoring error: {str(e)}"
                )

    def check_safety_status(self) -> SafetyMetrics:
        """Check current safety status and risk levels."""
        try:
            # Analyze agent behavior
            behavior_metrics = self.analyze_agent_behavior()
            
            # Check safety constraints
            constraint_violations = self.check_safety_constraints()
            
            # Calculate safety score
            safety_score = self.calculate_safety_score(
                behavior_metrics,
                constraint_violations
            )
            
            # Determine risk level
            risk_level = self.determine_risk_level(
                safety_score,
                constraint_violations
            )
            
            return SafetyMetrics(
                risk_level=risk_level,
                safety_score=safety_score,
                violations_detected=constraint_violations,
                active_constraints=self.get_active_constraints(),
                last_assessment=datetime.now()
            )
            
        except Exception as e:
            logging.error(f"Error checking safety status: {str(e)}")
            return SafetyMetrics(
                risk_level=RiskLevel.HIGH,
                safety_score=0.0,
                violations_detected=["Error checking safety status"],
                active_constraints=[],
                last_assessment=datetime.now()
            )

    def analyze_agent_behavior(self) -> dict:
        """Analyze agent behavior patterns."""
        # Implementation would go here
        return {}

    def check_safety_constraints(self) -> List[str]:
        """Check for safety constraint violations."""
        # Implementation would go here
        return []

    def calculate_safety_score(self, behavior_metrics: dict, violations: List[str]) -> float:
        """Calculate overall safety score."""
        # Implementation would go here
        return 1.0

    def determine_risk_level(self, safety_score: float, violations: List[str]) -> RiskLevel:
        """Determine current risk level."""
        if safety_score < 0.5 or len(violations) > 3:
            return RiskLevel.CRITICAL
        elif safety_score < 0.7 or len(violations) > 1:
            return RiskLevel.HIGH
        elif safety_score < 0.9 or len(violations) > 0:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def get_active_constraints(self) -> List[str]:
        """Get list of active safety constraints."""
        # Implementation would go here
        return []

    def handle_safety_violation(self, safety_status: SafetyMetrics):
        """Handle detected safety violations."""
        try:
            # Log violation
            logging.warning(f"Safety violation detected: {safety_status}")
            
            # Record violation
            self.record_safety_violation(
                safety_status.risk_level,
                safety_status.violations_detected
            )
            
            # Take immediate action based on risk level
            if safety_status.risk_level == RiskLevel.CRITICAL:
                self.emergency_shutdown()
            elif safety_status.risk_level == RiskLevel.HIGH:
                self.pause_operations()
            
        except Exception as e:
            logging.error(f"Error handling safety violation: {str(e)}")

    def emergency_shutdown(self, signum=None, frame=None):
        """Perform emergency shutdown of operations."""
        try:
            logging.critical("EMERGENCY SHUTDOWN INITIATED")
            
            # Stop monitoring
            self.is_monitoring = False
            
            # Record emergency event
            self.record_safety_event(
                "emergency_shutdown",
                RiskLevel.CRITICAL,
                "Emergency shutdown initiated"
            )
            
            # Terminate operations
            # Implementation would go here - specific to your system
            
            # Clean up resources
            self.executor.shutdown(wait=False)
            
        except Exception as e:
            logging.error(f"Error during emergency shutdown: {str(e)}")
        
        finally:
            # Force exit if necessary
            if signum is not None:
                os._exit(1)

    def pause_operations(self):
        """Pause current operations."""
        try:
            logging.warning("PAUSING OPERATIONS")
            
            # Record pause event
            self.record_safety_event(
                "operations_paused",
                RiskLevel.HIGH,
                "Operations paused due to safety concerns"
            )
            
            # Pause operations
            # Implementation would go here - specific to your system
            
        except Exception as e:
            logging.error(f"Error pausing operations: {str(e)}")

    def record_safety_event(self, event_type: str, risk_level: RiskLevel, description: str):
        """Record a safety event in the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO safety_events
                (monitor_id, agent_id, event_type, risk_level, description, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                self.monitor_id,
                self.target_agent,
                event_type,
                risk_level.value,
                description,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error recording safety event: {str(e)}")

    def record_safety_metrics(self, metrics: SafetyMetrics):
        """Record safety metrics in the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO safety_metrics
                (monitor_id, agent_id, metric_type, metric_value, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                self.monitor_id,
                self.target_agent,
                'safety_score',
                metrics.safety_score,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error recording safety metrics: {str(e)}")

    def record_safety_violation(self, severity: RiskLevel, details: List[str]):
        """Record a safety violation in the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO safety_violations
                (monitor_id, agent_id, violation_type, severity, details, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                self.monitor_id,
                self.target_agent,
                'safety_violation',
                severity.value,
                json.dumps(details),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error recording safety violation: {str(e)}")

    async def run(self):
        """Execute the safety monitoring action."""
        try:
            # Start monitoring if not already active
            if not self.is_monitoring:
                return await self.start_monitoring()
            
            # Get current safety status
            safety_status = self.check_safety_status()
            
            return {
                'monitor_id': self.monitor_id,
                'target_agent': self.target_agent,
                'safety_status': safety_status,
                'is_monitoring': self.is_monitoring,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return f"Error in safety monitoring: {str(e)}"

if __name__ == "__main__":
    # Test the tool
    monitor = SafetyMonitor(
        target_agent="test_agent",
        safety_threshold=0.95,
        monitoring_interval=1.0
    )
    asyncio.run(monitor.run()) 