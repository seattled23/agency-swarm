from agency_swarm.tools import BaseTool
from pydantic import Field
import asyncio
from typing import Dict, List, Any, Optional
import uuid
from datetime import datetime
import logging
import os
import json
from dataclasses import dataclass, asdict

@dataclass
class MessageRoute:
    """Data class for message routing information"""
    id: str
    source: str
    destination: str
    message_type: str
    priority: str
    created_at: str
    rules: Dict[str, Any]
    active: bool = True

class MessageRouter(BaseTool):
    """
    Tool for managing message routing between agents.
    Handles message routing, filtering, and delivery based on configurable rules.
    """
    
    operation: str = Field(
        ..., description="Operation to perform ('add_route', 'update_route', 'remove_route', 'get_routes', 'route_message')"
    )
    
    data: Dict = Field(
        {}, description="Data for the operation (route details, message content, etc.)"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.routes: Dict[str, MessageRoute] = {}
        self.message_history: List[Dict] = []
        self.setup_logging()
        self._load_state()

    def setup_logging(self):
        """Sets up logging for message routing"""
        log_dir = "agency_divisions/internal_operations/logs/message_routing"
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            filename=f"{log_dir}/message_routing.log",
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('MessageRouting')

    async def run_async(self) -> Dict[str, Any]:
        """
        Asynchronously executes message routing operations
        """
        try:
            if self.operation == "add_route":
                return await self._add_route()
            elif self.operation == "update_route":
                return await self._update_route()
            elif self.operation == "remove_route":
                return await self._remove_route()
            elif self.operation == "get_routes":
                return await self._get_routes()
            elif self.operation == "route_message":
                return await self._route_message()
            else:
                raise ValueError(f"Unknown operation: {self.operation}")
            
        except Exception as e:
            self.logger.error(f"Error in message routing: {str(e)}")
            raise
        
        finally:
            await self._save_state()

    def run(self) -> Dict[str, Any]:
        """
        Synchronous wrapper for message routing operations
        """
        return asyncio.run(self.run_async())

    async def _add_route(self) -> Dict[str, Any]:
        """Adds a new message route"""
        try:
            route_data = self.data.get("route", {})
            route_id = str(uuid.uuid4())
            current_time = datetime.now().isoformat()
            
            route = MessageRoute(
                id=route_id,
                source=route_data.get("source", ""),
                destination=route_data.get("destination", ""),
                message_type=route_data.get("message_type", ""),
                priority=route_data.get("priority", "medium"),
                created_at=current_time,
                rules=route_data.get("rules", {}),
                active=True
            )
            
            self.routes[route_id] = route
            
            self.logger.info(f"Added route: {route_id}")
            
            return {
                "status": "success",
                "route_id": route_id,
                "route": asdict(route)
            }
            
        except Exception as e:
            self.logger.error(f"Error adding route: {str(e)}")
            raise

    async def _update_route(self) -> Dict[str, Any]:
        """Updates an existing message route"""
        try:
            route_id = self.data.get("route_id")
            updates = self.data.get("updates", {})
            
            if route_id not in self.routes:
                raise ValueError(f"Route not found: {route_id}")
            
            route = self.routes[route_id]
            
            # Update route fields
            for field, value in updates.items():
                if hasattr(route, field):
                    setattr(route, field, value)
            
            self.logger.info(f"Updated route: {route_id}")
            
            return {
                "status": "success",
                "route_id": route_id,
                "route": asdict(route)
            }
            
        except Exception as e:
            self.logger.error(f"Error updating route: {str(e)}")
            raise

    async def _remove_route(self) -> Dict[str, Any]:
        """Removes a message route"""
        try:
            route_id = self.data.get("route_id")
            
            if route_id not in self.routes:
                raise ValueError(f"Route not found: {route_id}")
            
            del self.routes[route_id]
            
            self.logger.info(f"Removed route: {route_id}")
            
            return {
                "status": "success",
                "route_id": route_id
            }
            
        except Exception as e:
            self.logger.error(f"Error removing route: {str(e)}")
            raise

    async def _get_routes(self) -> Dict[str, Any]:
        """Retrieves message routes based on filters"""
        try:
            filters = self.data.get("filters", {})
            source = filters.get("source")
            destination = filters.get("destination")
            message_type = filters.get("message_type")
            active_only = filters.get("active_only", True)
            
            routes = self.routes.values()
            
            # Apply filters
            if source:
                routes = [r for r in routes if r.source == source]
            if destination:
                routes = [r for r in routes if r.destination == destination]
            if message_type:
                routes = [r for r in routes if r.message_type == message_type]
            if active_only:
                routes = [r for r in routes if r.active]
            
            return {
                "status": "success",
                "routes": [asdict(r) for r in routes]
            }
            
        except Exception as e:
            self.logger.error(f"Error retrieving routes: {str(e)}")
            raise

    async def _route_message(self) -> Dict[str, Any]:
        """Routes a message based on configured routes"""
        try:
            message = self.data.get("message", {})
            source = message.get("source")
            message_type = message.get("type")
            content = message.get("content")
            
            # Find matching routes
            matching_routes = [
                r for r in self.routes.values()
                if r.active and r.source == source and r.message_type == message_type
            ]
            
            if not matching_routes:
                return {
                    "status": "error",
                    "message": "No matching routes found"
                }
            
            # Sort routes by priority
            priority_map = {"high": 1, "medium": 2, "low": 3}
            matching_routes.sort(key=lambda r: priority_map.get(r.priority, 999))
            
            # Apply routing rules and collect destinations
            destinations = []
            for route in matching_routes:
                if await self._apply_routing_rules(route, content):
                    destinations.append(route.destination)
            
            # Record in message history
            self.message_history.append({
                "timestamp": datetime.now().isoformat(),
                "source": source,
                "destinations": destinations,
                "message_type": message_type,
                "content": content
            })
            
            return {
                "status": "success",
                "destinations": destinations
            }
            
        except Exception as e:
            self.logger.error(f"Error routing message: {str(e)}")
            raise

    async def _apply_routing_rules(self, route: MessageRoute, content: Any) -> bool:
        """Applies routing rules to message content"""
        try:
            rules = route.rules
            
            # Check content type rules
            if "content_type" in rules:
                if not isinstance(content, rules["content_type"]):
                    return False
            
            # Check content value rules
            if "content_value" in rules:
                if content != rules["content_value"]:
                    return False
            
            # Check content pattern rules
            if "content_pattern" in rules and isinstance(content, str):
                import re
                if not re.match(rules["content_pattern"], content):
                    return False
            
            # Check custom rules
            if "custom_check" in rules and callable(rules["custom_check"]):
                if not await rules["custom_check"](content):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying routing rules: {str(e)}")
            return False

    async def _save_state(self):
        """Saves current state to disk"""
        try:
            state_dir = "agency_divisions/internal_operations/data/message_routing"
            os.makedirs(state_dir, exist_ok=True)
            
            state = {
                "routes": {k: asdict(v) for k, v in self.routes.items()},
                "message_history": self.message_history[-1000:],  # Keep last 1000 messages
                "last_updated": datetime.now().isoformat()
            }
            
            state_file = f"{state_dir}/state.json"
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving state: {str(e)}")
            raise

    def _load_state(self):
        """Loads state from disk"""
        try:
            state_file = "agency_divisions/internal_operations/data/message_routing/state.json"
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    
                    # Reconstruct MessageRoute objects
                    self.routes = {
                        k: MessageRoute(**v)
                        for k, v in state.get("routes", {}).items()
                    }
                    self.message_history = state.get("message_history", [])
                    
        except Exception as e:
            self.logger.error(f"Error loading state: {str(e)}")
            self.routes = {}
            self.message_history = []

if __name__ == "__main__":
    # Test the message router
    async def test_message_routing():
        router = MessageRouter(
            operation="add_route",
            data={
                "route": {
                    "source": "market_analyst",
                    "destination": "risk_manager",
                    "message_type": "market_update",
                    "priority": "high",
                    "rules": {
                        "content_type": dict,
                        "content_pattern": r".*market.*"
                    }
                }
            }
        )
        
        try:
            # Add route
            result = await router.run_async()
            route_id = result["route_id"]
            print("Added route:", json.dumps(result, indent=2))
            
            # Route message
            router.operation = "route_message"
            router.data = {
                "message": {
                    "source": "market_analyst",
                    "type": "market_update",
                    "content": {
                        "market": "BTC/USD",
                        "action": "buy"
                    }
                }
            }
            result = await router.run_async()
            print("Routed message:", json.dumps(result, indent=2))
            
            # Get routes
            router.operation = "get_routes"
            router.data = {
                "filters": {
                    "source": "market_analyst",
                    "active_only": True
                }
            }
            result = await router.run_async()
            print("Retrieved routes:", json.dumps(result, indent=2))
            
        except Exception as e:
            print(f"Error in message routing test: {str(e)}")
    
    asyncio.run(test_message_routing()) 