"""
Pytest configuration for task management tests.
"""
import pytest
import asyncio

pytest_plugins = ["pytest_asyncio"]

@pytest.fixture(scope="session")
def event_loop_policy():
    """Configure the event loop policy."""
    return asyncio.WindowsSelectorEventLoopPolicy() if asyncio.get_event_loop_policy().__class__.__name__ == 'WindowsProactorEventLoopPolicy' else asyncio.DefaultEventLoopPolicy()