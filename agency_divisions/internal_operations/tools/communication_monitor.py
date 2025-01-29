from agency_swarm.tools import BaseTool
from pydantic import Field
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
import os
import json
from dataclasses import dataclass, asdict
import aiosqlite
import aiofiles
from collections import defaultdict

@dataclass
class CommunicationMetrics:
    """Data class for communication metrics"""
    total_messages: int = 0
    successful_messages: int = 0
    failed_messages: int = 0
    average_response_time: float = 0.0
    messages_per_minute: float = 0.0
    active_agents: int = 0
    error_rate: float = 0.0

class CommunicationMonitor(BaseTool):
    """
    Tool for monitoring and logging inter-agent communication.
    Tracks message flow, performance metrics, and system health.
    """
    
    operation: str = Field(
        ..., description="Operation to perform ('log_message', 'get_metrics', 'analyze_patterns', 'get_alerts')"
    )
    
    data: Dict = Field(
        {}, description="Data for the operation (message details, time range, etc.)"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.setup_logging()
        self.db_path = "agency_divisions/internal_operations/data/communication/monitor.db"
        self.setup_database()
        self.alert_thresholds = {
            "error_rate": 0.1,  # 10% error rate
            "response_time": 5.0,  # 5 seconds
            "message_rate": 100,  # messages per minute
            "queue_size": 1000  # maximum queue size
        }

    def setup_logging(self):
        """Sets up logging for communication monitoring"""
        log_dir = "agency_divisions/internal_operations/logs/communication"
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            filename=f"{log_dir}/communication.log",
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('CommunicationMonitor')

    def setup_database(self):
        """Sets up SQLite database for message logging"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        async def init_db():
            async with aiosqlite.connect(self.db_path) as db:
                # Message logging table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        timestamp TEXT,
                        source TEXT,
                        destination TEXT,
                        message_type TEXT,
                        status TEXT,
                        response_time REAL,
                        error TEXT
                    )
                """)
                
                # Metrics table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS metrics (
                        timestamp TEXT,
                        metric_type TEXT,
                        value REAL,
                        metadata TEXT
                    )
                """)
                
                # Alerts table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS alerts (
                        timestamp TEXT,
                        alert_type TEXT,
                        severity TEXT,
                        message TEXT,
                        resolved INTEGER
                    )
                """)
                
                await db.commit()
        
        asyncio.run(init_db())

    async def run_async(self) -> Dict[str, Any]:
        """
        Asynchronously executes communication monitoring operations
        """
        try:
            if self.operation == "log_message":
                return await self._log_message()
            elif self.operation == "get_metrics":
                return await self._get_metrics()
            elif self.operation == "analyze_patterns":
                return await self._analyze_patterns()
            elif self.operation == "get_alerts":
                return await self._get_alerts()
            else:
                raise ValueError(f"Unknown operation: {self.operation}")
            
        except Exception as e:
            self.logger.error(f"Error in communication monitoring: {str(e)}")
            raise

    def run(self) -> Dict[str, Any]:
        """
        Synchronous wrapper for communication monitoring operations
        """
        return asyncio.run(self.run_async())

    async def _log_message(self) -> Dict[str, Any]:
        """Logs a message to the monitoring system"""
        try:
            message = self.data.get("message", {})
            
            async with aiosqlite.connect(self.db_path) as db:
                # Log message
                await db.execute(
                    """
                    INSERT INTO messages 
                    (id, timestamp, source, destination, message_type, status, response_time, error)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message.get("id", ""),
                        message.get("timestamp", datetime.now().isoformat()),
                        message.get("source", ""),
                        message.get("destination", ""),
                        message.get("type", ""),
                        message.get("status", ""),
                        message.get("response_time", 0.0),
                        message.get("error", "")
                    )
                )
                
                # Update metrics
                current_time = datetime.now().isoformat()
                await db.execute(
                    """
                    INSERT INTO metrics (timestamp, metric_type, value, metadata)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        current_time,
                        "message_count",
                        1,
                        json.dumps({"message_type": message.get("type", "")})
                    )
                )
                
                if message.get("error"):
                    await db.execute(
                        """
                        INSERT INTO metrics (timestamp, metric_type, value, metadata)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            current_time,
                            "error_count",
                            1,
                            json.dumps({"error_type": message.get("error", "")})
                        )
                    )
                
                await db.commit()
            
            # Check for alerts
            await self._check_alerts(message)
            
            return {
                "status": "success",
                "message_id": message.get("id", "")
            }
            
        except Exception as e:
            self.logger.error(f"Error logging message: {str(e)}")
            raise

    async def _get_metrics(self) -> Dict[str, Any]:
        """Retrieves communication metrics for a time range"""
        try:
            time_range = self.data.get("time_range", {})
            start_time = datetime.fromisoformat(time_range.get("start", ""))
            end_time = datetime.fromisoformat(time_range.get("end", datetime.now().isoformat()))
            
            metrics = CommunicationMetrics()
            
            async with aiosqlite.connect(self.db_path) as db:
                # Get message counts
                async with db.execute(
                    """
                    SELECT COUNT(*), 
                           SUM(CASE WHEN error != '' THEN 1 ELSE 0 END),
                           AVG(response_time)
                    FROM messages
                    WHERE timestamp BETWEEN ? AND ?
                    """,
                    (start_time.isoformat(), end_time.isoformat())
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        metrics.total_messages = row[0] or 0
                        metrics.failed_messages = row[1] or 0
                        metrics.successful_messages = metrics.total_messages - metrics.failed_messages
                        metrics.average_response_time = row[2] or 0.0
                
                # Calculate messages per minute
                time_diff = (end_time - start_time).total_seconds() / 60
                if time_diff > 0:
                    metrics.messages_per_minute = metrics.total_messages / time_diff
                
                # Get active agents
                async with db.execute(
                    """
                    SELECT COUNT(DISTINCT source)
                    FROM messages
                    WHERE timestamp BETWEEN ? AND ?
                    """,
                    (start_time.isoformat(), end_time.isoformat())
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        metrics.active_agents = row[0] or 0
                
                # Calculate error rate
                if metrics.total_messages > 0:
                    metrics.error_rate = metrics.failed_messages / metrics.total_messages
            
            return {
                "status": "success",
                "metrics": asdict(metrics)
            }
            
        except Exception as e:
            self.logger.error(f"Error retrieving metrics: {str(e)}")
            raise

    async def _analyze_patterns(self) -> Dict[str, Any]:
        """Analyzes communication patterns and trends"""
        try:
            time_range = self.data.get("time_range", {})
            start_time = datetime.fromisoformat(time_range.get("start", ""))
            end_time = datetime.fromisoformat(time_range.get("end", datetime.now().isoformat()))
            
            patterns = {
                "message_types": defaultdict(int),
                "agent_interactions": defaultdict(int),
                "hourly_distribution": defaultdict(int),
                "error_patterns": defaultdict(int)
            }
            
            async with aiosqlite.connect(self.db_path) as db:
                # Analyze message types
                async with db.execute(
                    """
                    SELECT message_type, COUNT(*)
                    FROM messages
                    WHERE timestamp BETWEEN ? AND ?
                    GROUP BY message_type
                    """,
                    (start_time.isoformat(), end_time.isoformat())
                ) as cursor:
                    async for row in cursor:
                        patterns["message_types"][row[0]] = row[1]
                
                # Analyze agent interactions
                async with db.execute(
                    """
                    SELECT source, destination, COUNT(*)
                    FROM messages
                    WHERE timestamp BETWEEN ? AND ?
                    GROUP BY source, destination
                    """,
                    (start_time.isoformat(), end_time.isoformat())
                ) as cursor:
                    async for row in cursor:
                        patterns["agent_interactions"][f"{row[0]}->{row[1]}"] = row[2]
                
                # Analyze hourly distribution
                async with db.execute(
                    """
                    SELECT strftime('%H', timestamp) as hour, COUNT(*)
                    FROM messages
                    WHERE timestamp BETWEEN ? AND ?
                    GROUP BY hour
                    """,
                    (start_time.isoformat(), end_time.isoformat())
                ) as cursor:
                    async for row in cursor:
                        patterns["hourly_distribution"][int(row[0])] = row[1]
                
                # Analyze error patterns
                async with db.execute(
                    """
                    SELECT error, COUNT(*)
                    FROM messages
                    WHERE timestamp BETWEEN ? AND ?
                    AND error != ''
                    GROUP BY error
                    """,
                    (start_time.isoformat(), end_time.isoformat())
                ) as cursor:
                    async for row in cursor:
                        patterns["error_patterns"][row[0]] = row[1]
            
            return {
                "status": "success",
                "patterns": {k: dict(v) for k, v in patterns.items()}
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing patterns: {str(e)}")
            raise

    async def _get_alerts(self) -> Dict[str, Any]:
        """Retrieves active alerts"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                alerts = []
                async with db.execute(
                    """
                    SELECT timestamp, alert_type, severity, message
                    FROM alerts
                    WHERE resolved = 0
                    ORDER BY timestamp DESC
                    """
                ) as cursor:
                    async for row in cursor:
                        alerts.append({
                            "timestamp": row[0],
                            "type": row[1],
                            "severity": row[2],
                            "message": row[3]
                        })
            
            return {
                "status": "success",
                "alerts": alerts
            }
            
        except Exception as e:
            self.logger.error(f"Error retrieving alerts: {str(e)}")
            raise

    async def _check_alerts(self, message: Dict[str, Any]):
        """Checks for alert conditions and generates alerts if needed"""
        try:
            current_time = datetime.now()
            start_time = current_time - timedelta(minutes=5)
            
            async with aiosqlite.connect(self.db_path) as db:
                # Check error rate
                metrics_result = await self._get_metrics()
                metrics = CommunicationMetrics(**metrics_result["metrics"])
                
                if metrics.error_rate > self.alert_thresholds["error_rate"]:
                    await db.execute(
                        """
                        INSERT INTO alerts (timestamp, alert_type, severity, message, resolved)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            current_time.isoformat(),
                            "high_error_rate",
                            "high",
                            f"Error rate ({metrics.error_rate:.2%}) exceeds threshold",
                            0
                        )
                    )
                
                # Check response time
                if metrics.average_response_time > self.alert_thresholds["response_time"]:
                    await db.execute(
                        """
                        INSERT INTO alerts (timestamp, alert_type, severity, message, resolved)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            current_time.isoformat(),
                            "high_response_time",
                            "medium",
                            f"Average response time ({metrics.average_response_time:.2f}s) exceeds threshold",
                            0
                        )
                    )
                
                # Check message rate
                if metrics.messages_per_minute > self.alert_thresholds["message_rate"]:
                    await db.execute(
                        """
                        INSERT INTO alerts (timestamp, alert_type, severity, message, resolved)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            current_time.isoformat(),
                            "high_message_rate",
                            "medium",
                            f"Message rate ({metrics.messages_per_minute:.2f}/min) exceeds threshold",
                            0
                        )
                    )
                
                await db.commit()
            
        except Exception as e:
            self.logger.error(f"Error checking alerts: {str(e)}")

if __name__ == "__main__":
    # Test the communication monitor
    async def test_communication_monitoring():
        monitor = CommunicationMonitor(
            operation="log_message",
            data={
                "message": {
                    "id": "test-message-1",
                    "timestamp": datetime.now().isoformat(),
                    "source": "market_analyst",
                    "destination": "risk_manager",
                    "type": "market_update",
                    "status": "delivered",
                    "response_time": 0.5,
                    "error": ""
                }
            }
        )
        
        try:
            # Log message
            result = await monitor.run_async()
            print("Logged message:", json.dumps(result, indent=2))
            
            # Get metrics
            monitor.operation = "get_metrics"
            monitor.data = {
                "time_range": {
                    "start": (datetime.now() - timedelta(hours=1)).isoformat(),
                    "end": datetime.now().isoformat()
                }
            }
            result = await monitor.run_async()
            print("Metrics:", json.dumps(result, indent=2))
            
            # Analyze patterns
            monitor.operation = "analyze_patterns"
            result = await monitor.run_async()
            print("Patterns:", json.dumps(result, indent=2))
            
            # Get alerts
            monitor.operation = "get_alerts"
            result = await monitor.run_async()
            print("Alerts:", json.dumps(result, indent=2))
            
        except Exception as e:
            print(f"Error in communication monitoring test: {str(e)}")
    
    asyncio.run(test_communication_monitoring()) 