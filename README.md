# Agency Swarm Framework Implementation

A comprehensive implementation of the Agency Swarm framework for managing and coordinating multiple AI agents.

## Features

- Multi-agent system with specialized roles
- Real-time monitoring dashboard
- Asynchronous task management
- Standardized message routing
- Performance metrics tracking
- Automated error handling and recovery

## Project Structure

```
agency_swarm/
├── agency_divisions/
│   ├── planning/
│   ├── internal_operations/
│   ├── analysis/
│   ├── projects/
│   ├── upgrades/
│   ├── research/
│   └── data_management/
├── data/
├── logs/
├── .env
├── requirements.txt
├── initialize_agency.py
└── run_agency.py
```

## Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Other API keys as required by specific agents

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/agency-swarm.git
   cd agency-swarm
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   BINANCE_API_KEY=your_binance_api_key_here
   BINANCE_SECRET_KEY=your_binance_secret_key_here
   ```

## Usage

1. Initialize the agency:
   ```bash
   python initialize_agency.py
   ```

2. Monitor the agency through the dashboard:
   - View agent status
   - Track performance metrics
   - Monitor message queues
   - Check system resources

3. Use keyboard shortcuts in the dashboard:
   - `Ctrl+C`: Gracefully shutdown the agency
   - `R`: Refresh dashboard manually
   - `H`: Show help menu

## Configuration

The agency can be configured through the following files:
- `.env`: Environment variables and API keys
- `agency_manifesto.md`: Shared instructions for all agents
- Individual agent instruction files in their respective directories

## Monitoring

The dashboard provides real-time monitoring of:
- Agent status and current tasks
- CPU and memory usage
- Message queue sizes
- System-wide metrics
- Error rates and alerts

## Development

To add new agents or modify existing ones:

1. Create a new agent directory in `agency_divisions/`
2. Implement the agent class and tools
3. Update the agent's instructions.md
4. Register the agent in run_agency.py

## Testing

Run the test suite:
```bash
pytest tests/
```

## Troubleshooting

Common issues and solutions:

1. OpenAI API Key Error:
   - Ensure the API key is correctly set in .env
   - Check for proper initialization in initialize_agency.py

2. Agent Communication Issues:
   - Verify message routing configuration
   - Check agent status in the dashboard
   - Review logs in the logs directory

3. Performance Issues:
   - Monitor system resources in the dashboard
   - Check individual agent metrics
   - Review and adjust concurrent task limits

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
1. Check the documentation
2. Review existing issues
3. Create a new issue with detailed information

## Acknowledgments

- OpenAI for the GPT models
- Agency Swarm framework developers
- Contributors and maintainers
