# Standard Operating Procedure: Tool Creation with Agency Swarm CLI

## Overview

This SOP outlines the process for creating and implementing tools using the Agency Swarm CLI, ensuring consistency and best practices across all tool development.

## Prerequisites

- Agency Swarm CLI installed
- Python 3.8+
- Basic understanding of pydantic models
- Access to project repository

## Procedure

### 1. Tool Creation Process

#### 1.1 Initialize Tool Template

```bash
agency-swarm create-tool-template --name "ToolName" --description "Tool Description" --path "/path/to/agent/tools"
```

#### 1.2 Tool Structure

```python
from agency_swarm.tools import BaseTool
from pydantic import Field
from typing import Optional, Dict, Any

class CustomTool(BaseTool):
    """
    Detailed description of the tool's purpose and functionality.
    Include specific use cases and examples.
    """

    # Required Parameters
    param1: str = Field(..., description="Description of parameter 1")
    param2: int = Field(..., description="Description of parameter 2")

    # Optional Parameters
    param3: Optional[str] = Field(None, description="Description of optional parameter")

    def run(self):
        """
        Implementation of the tool's main functionality.
        Returns: Result as specified in the tool's description.
        """
        # Implementation
        pass
```

### 2. Development Guidelines

#### 2.1 Parameter Definition

- Use clear, descriptive parameter names
- Provide detailed descriptions in Field definitions
- Mark optional parameters appropriately
- Use type hints consistently
- Group related parameters logically

#### 2.2 Documentation Requirements

- Comprehensive docstring explaining tool purpose
- Parameter descriptions with examples
- Return value documentation
- Usage examples
- Error handling documentation

#### 2.3 Error Handling

- Implement proper error checking
- Use appropriate exception types
- Provide informative error messages
- Handle edge cases gracefully
- Log errors appropriately

#### 2.4 Testing Requirements

- Create unit tests for each tool
- Test edge cases and error conditions
- Verify parameter validation
- Test integration with other components
- Document test cases

### 3. Best Practices

#### 3.1 Code Organization

- One tool per file
- Clear file naming convention
- Logical parameter grouping
- Consistent code style
- Proper import organization

#### 3.2 Performance Considerations

- Optimize resource usage
- Implement caching when appropriate
- Handle large data efficiently
- Consider async operations
- Monitor execution time

#### 3.3 Security Guidelines

- Validate all inputs
- Sanitize outputs
- Use environment variables for sensitive data
- Implement access controls
- Follow security best practices

### 4. Common Patterns

#### 4.1 API Integration

```python
class APITool(BaseTool):
    """Tool for API integration"""
    api_endpoint: str = Field(..., description="API endpoint URL")
    api_key: str = Field(None, description="API key (optional if using env vars)")

    def __init__(self, **data):
        super().__init__(**data)
        self.api_key = os.getenv("API_KEY") or self.api_key
```

#### 4.2 File Operations

```python
class FileTool(BaseTool):
    """Tool for file operations"""
    file_path: Path = Field(..., description="Path to the file")
    mode: str = Field("r", description="File operation mode")

    def run(self):
        with open(self.file_path, self.mode) as f:
            # File operations
            pass
```

### 5. Testing Template

```python
if __name__ == "__main__":
    # Test code
    tool = CustomTool(
        param1="test",
        param2=42
    )
    result = tool.run()
    print(f"Test result: {result}")
```

## Troubleshooting

### Common Issues

1. **Template Generation Fails**

   - Verify CLI installation
   - Check path permissions
   - Ensure valid tool name

2. **Parameter Validation Errors**

   - Verify parameter types
   - Check required vs optional
   - Validate default values

3. **Integration Issues**
   - Check import paths
   - Verify tool registration
   - Validate agent configuration

## References

- [Agency Swarm Documentation](https://github.com/VRSEN/agency-swarm)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

## Checklist

- [ ] Tool template generated
- [ ] Parameters properly defined
- [ ] Documentation complete
- [ ] Error handling implemented
- [ ] Tests created and passing
- [ ] Security measures implemented
- [ ] Code reviewed
- [ ] Integration tested
