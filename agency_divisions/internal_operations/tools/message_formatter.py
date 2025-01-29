from agency_swarm.tools import BaseTool
from pydantic import Field, BaseModel
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import json
import logging
import os
from enum import Enum

class MessageType(str, Enum):
    """Enumeration of standard message types"""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    ERROR_NOTIFICATION = "error_notification"
    DATA_REQUEST = "data_request"
    DATA_RESPONSE = "data_response"
    COMMAND = "command"
    EVENT = "event"
    QUERY = "query"
    RESULT = "result"

class MessagePriority(str, Enum):
    """Enumeration of message priorities"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class MessageStatus(str, Enum):
    """Enumeration of message statuses"""
    PENDING = "pending"
    DELIVERED = "delivered"
    PROCESSED = "processed"
    FAILED = "failed"

class StandardMessage(BaseModel):
    """Standard message format for inter-agent communication"""
    id: str
    type: MessageType
    source: str
    destination: str
    timestamp: str
    priority: MessagePriority = MessagePriority.MEDIUM
    status: MessageStatus = MessageStatus.PENDING
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    expires_at: Optional[str] = None
    version: str = "1.0"

class MessageFormatter(BaseTool):
    """
    Tool for standardizing message formats in inter-agent communication.
    Handles message validation, formatting, and schema enforcement.
    """
    
    operation: str = Field(
        ..., description="Operation to perform ('format_message', 'validate_message', 'transform_message')"
    )
    
    data: Dict = Field(
        {}, description="Data for the operation (message content, format rules, etc.)"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.setup_logging()
        self._load_schemas()

    def setup_logging(self):
        """Sets up logging for message formatting"""
        log_dir = "agency_divisions/internal_operations/logs/message_formatting"
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            filename=f"{log_dir}/message_formatting.log",
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('MessageFormatting')

    async def run_async(self) -> Dict[str, Any]:
        """
        Asynchronously executes message formatting operations
        """
        try:
            if self.operation == "format_message":
                return await self._format_message()
            elif self.operation == "validate_message":
                return await self._validate_message()
            elif self.operation == "transform_message":
                return await self._transform_message()
            else:
                raise ValueError(f"Unknown operation: {self.operation}")
            
        except Exception as e:
            self.logger.error(f"Error in message formatting: {str(e)}")
            raise

    def run(self) -> Dict[str, Any]:
        """
        Synchronous wrapper for message formatting operations
        """
        return asyncio.run(self.run_async())

    async def _format_message(self) -> Dict[str, Any]:
        """Formats a message according to the standard schema"""
        try:
            message_data = self.data.get("message", {})
            
            # Generate message ID if not provided
            if "id" not in message_data:
                import uuid
                message_data["id"] = str(uuid.uuid4())
            
            # Set timestamp if not provided
            if "timestamp" not in message_data:
                message_data["timestamp"] = datetime.now().isoformat()
            
            # Create StandardMessage instance
            message = StandardMessage(**message_data)
            
            self.logger.info(f"Formatted message: {message.id}")
            
            return {
                "status": "success",
                "message": message.dict()
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting message: {str(e)}")
            raise

    async def _validate_message(self) -> Dict[str, Any]:
        """Validates a message against the standard schema"""
        try:
            message_data = self.data.get("message", {})
            validation_rules = self.data.get("rules", {})
            
            # Basic schema validation
            message = StandardMessage(**message_data)
            
            # Additional custom validation
            validation_errors = []
            
            # Check required fields
            if validation_rules.get("required_fields"):
                for field in validation_rules["required_fields"]:
                    if not message_data.get(field):
                        validation_errors.append(f"Missing required field: {field}")
            
            # Check field types
            if validation_rules.get("field_types"):
                for field, expected_type in validation_rules["field_types"].items():
                    if field in message_data:
                        value = message_data[field]
                        if not isinstance(value, expected_type):
                            validation_errors.append(
                                f"Invalid type for field {field}: "
                                f"expected {expected_type.__name__}, got {type(value).__name__}"
                            )
            
            # Check content schema
            if validation_rules.get("content_schema"):
                from pydantic import create_model
                content_model = create_model(
                    "ContentModel",
                    **validation_rules["content_schema"]
                )
                try:
                    content_model(**message.content)
                except Exception as e:
                    validation_errors.append(f"Content validation error: {str(e)}")
            
            return {
                "status": "success" if not validation_errors else "error",
                "valid": not bool(validation_errors),
                "errors": validation_errors,
                "message": message.dict()
            }
            
        except Exception as e:
            self.logger.error(f"Error validating message: {str(e)}")
            raise

    async def _transform_message(self) -> Dict[str, Any]:
        """Transforms a message from one format to another"""
        try:
            message_data = self.data.get("message", {})
            source_format = self.data.get("source_format")
            target_format = self.data.get("target_format", "standard")
            
            if source_format == "standard":
                # Already in standard format
                transformed = message_data
            else:
                # Load transformation schema
                schema = self._get_transformation_schema(source_format)
                if not schema:
                    raise ValueError(f"Unknown source format: {source_format}")
                
                # Apply transformation
                transformed = self._apply_transformation(message_data, schema)
            
            # Validate transformed message
            message = StandardMessage(**transformed)
            
            return {
                "status": "success",
                "message": message.dict()
            }
            
        except Exception as e:
            self.logger.error(f"Error transforming message: {str(e)}")
            raise

    def _load_schemas(self):
        """Loads message schemas from configuration"""
        try:
            schema_dir = "agency_divisions/internal_operations/config/message_schemas"
            os.makedirs(schema_dir, exist_ok=True)
            
            self.schemas = {}
            schema_file = f"{schema_dir}/schemas.json"
            
            if os.path.exists(schema_file):
                with open(schema_file, 'r') as f:
                    self.schemas = json.load(f)
            
        except Exception as e:
            self.logger.error(f"Error loading schemas: {str(e)}")
            self.schemas = {}

    def _get_transformation_schema(self, format_name: str) -> Dict[str, Any]:
        """Retrieves transformation schema for a given format"""
        return self.schemas.get(format_name, {})

    def _apply_transformation(self, message: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Applies transformation schema to a message"""
        transformed = {}
        
        # Apply field mappings
        for target_field, source_field in schema.get("field_mappings", {}).items():
            if isinstance(source_field, str):
                # Direct mapping
                if source_field in message:
                    transformed[target_field] = message[source_field]
            elif isinstance(source_field, dict):
                # Complex mapping with transformation
                if "field" in source_field and source_field["field"] in message:
                    value = message[source_field["field"]]
                    if "transform" in source_field:
                        transform_type = source_field["transform"]
                        if transform_type == "datetime":
                            # Convert to ISO format
                            if isinstance(value, (int, float)):
                                from datetime import datetime
                                value = datetime.fromtimestamp(value).isoformat()
                        elif transform_type == "string":
                            value = str(value)
                        elif transform_type == "int":
                            value = int(value)
                        elif transform_type == "float":
                            value = float(value)
                    transformed[target_field] = value
        
        # Apply default values
        for field, default in schema.get("defaults", {}).items():
            if field not in transformed:
                transformed[field] = default
        
        return transformed

if __name__ == "__main__":
    # Test the message formatter
    import asyncio
    
    async def test_message_formatting():
        formatter = MessageFormatter(
            operation="format_message",
            data={
                "message": {
                    "type": MessageType.TASK_REQUEST,
                    "source": "market_analyst",
                    "destination": "risk_manager",
                    "content": {
                        "action": "analyze_market",
                        "parameters": {
                            "symbol": "BTC/USD",
                            "timeframe": "1h"
                        }
                    },
                    "priority": MessagePriority.HIGH
                }
            }
        )
        
        try:
            # Format message
            result = await formatter.run_async()
            formatted_message = result["message"]
            print("Formatted message:", json.dumps(formatted_message, indent=2))
            
            # Validate message
            formatter.operation = "validate_message"
            formatter.data = {
                "message": formatted_message,
                "rules": {
                    "required_fields": ["type", "source", "destination", "content"],
                    "field_types": {
                        "priority": str,
                        "content": dict
                    },
                    "content_schema": {
                        "action": (str, ...),
                        "parameters": (dict, ...)
                    }
                }
            }
            result = await formatter.run_async()
            print("Validation result:", json.dumps(result, indent=2))
            
        except Exception as e:
            print(f"Error in message formatting test: {str(e)}")
    
    asyncio.run(test_message_formatting()) 