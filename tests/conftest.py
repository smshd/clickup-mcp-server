"""Shared test configuration and fixtures."""
import os
import sys
import pytest

# Add server root to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set required env vars BEFORE importing config
os.environ.setdefault("CLICKUP_API_TOKEN", "pk_test_token_12345")
os.environ.setdefault("CLICKUP_TEAM_ID", "12345")
os.environ.setdefault("CACHE_TTL_SECONDS", "300")


@pytest.fixture
def sample_spaces():
    return {
        "spaces": [
            {
                "id": "space1",
                "name": "Client Space",
                "private": False,
                "statuses": [],
            },
            {
                "id": "space2",
                "name": "Internal",
                "private": True,
                "statuses": [],
            },
        ]
    }


@pytest.fixture
def sample_folders():
    return {
        "folders": [
            {
                "id": "folder1",
                "name": "Acme Corp",
                "lists": [
                    {"id": "list1", "name": "Website Build"},
                    {"id": "list2", "name": "SEO Tasks"},
                ],
            },
            {
                "id": "folder2",
                "name": "Beta Client",
                "lists": [
                    {"id": "list3", "name": "Maintenance"},
                ],
            },
        ]
    }


@pytest.fixture
def sample_lists():
    return {
        "lists": [
            {"id": "list4", "name": "General Tasks"},
        ]
    }


@pytest.fixture
def sample_members():
    return {
        "members": [
            {
                "user": {
                    "id": 100,
                    "username": "John",
                    "email": "john@example.com",
                    "role": 1,
                }
            },
            {
                "user": {
                    "id": 200,
                    "username": "Alice",
                    "email": "alice@example.com",
                    "role": 2,
                }
            },
            {
                "user": {
                    "id": 300,
                    "username": "Sarah",
                    "email": "sarah@example.com",
                    "role": 2,
                }
            },
        ]
    }


@pytest.fixture
def sample_tasks():
    return {
        "tasks": [
            {
                "id": "task1",
                "name": "Build homepage",
                "status": {"status": "in progress", "type": "open"},
                "priority": {"id": "2", "priority": "high"},
                "assignees": [{"id": 200, "username": "Alice", "email": "alice@example.com"}],
                "due_date": "1740000000000",
                "start_date": "1739000000000",
                "tags": [{"name": "website"}],
                "list": {"id": "list1", "name": "Website Build"},
                "folder": {"id": "folder1", "name": "Acme Corp"},
                "space": {"id": "space1"},
                "url": "https://app.clickup.com/t/task1",
                "description": "Build the homepage for Acme Corp",
                "custom_fields": [],
            },
            {
                "id": "task2",
                "name": "Fix navigation bug",
                "status": {"status": "open", "type": "open"},
                "priority": {"id": "3", "priority": "normal"},
                "assignees": [],
                "due_date": None,
                "start_date": None,
                "tags": [],
                "list": {"id": "list3", "name": "Maintenance"},
                "folder": {"id": "folder2", "name": "Beta Client"},
                "space": {"id": "space1"},
                "url": "https://app.clickup.com/t/task2",
                "description": "Navigation menu not working on mobile",
                "custom_fields": [],
            },
        ]
    }
