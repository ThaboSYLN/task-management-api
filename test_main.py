import pytest
from fastapi.testclient import TestClient
from main import app
from database import task_db
from auth import fake_users_db, create_user, get_password_hash
from models import TaskStatus, TaskCreate
from datetime import datetime, timedelta
import sqlite3
import os

# ========================================
# TEST SETUP & FIXTURES
# ========================================

@pytest.fixture(scope="function")
def test_db():
    """Create a fresh in-memory database for each test"""
    # Create new in-memory database
    test_db = sqlite3.connect(":memory:")
    cursor = test_db.cursor()
    
    # Create tasks table
    cursor.execute("""
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    test_db.commit()
    
    # Override main database with test version
    original_db = task_db.db_path
    task_db.db_path = ":memory:"
    task_db.conn = test_db
    
    yield test_db  # Provide to test
    
    # Cleanup
    task_db.db_path = original_db
    test_db.close()

@pytest.fixture(scope="function")
def test_client(test_db):
    """Test client with clean auth state"""
    # Reset fake users database
    fake_users_db.clear()
    
    # Create test user
    fake_users_db["testuser"] = {
        "username": "testuser",
        "hashed_password": get_password_hash("secret")
    }
    
    return TestClient(app)

@pytest.fixture
def auth_token(test_client):
    """Get auth token for test user"""
    response = test_client.post("/auth/login", json={
        "username": "testuser",
        "password": "secret"
    })
    return response.json()["access_token"]

# ========================================
# HELPER FUNCTIONS
# ========================================

def create_test_task(test_client, token, title="Test Task", status=TaskStatus.PENDING):
    """Helper to create a task"""
    return test_client.post("/tasks", 
        json={"title": title, "status": status.value},
        headers={"Authorization": f"Bearer {token}"}
    )

def iso_to_datetime(iso_str):
    """Convert ISO string to datetime object"""
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))

# ========================================
# AUTHENTICATION TESTS
# ========================================

def test_register_user(test_client):
    response = test_client.post("/auth/register", json={
        "username": "newuser",
        "password": "newpass123"
    })
    assert response.status_code == 201
    assert response.json()["username"] == "newuser"
    assert "newuser" in fake_users_db

def test_login_success(test_client, auth_token):
    assert isinstance(auth_token, str)
    assert len(auth_token) > 50  # Basic token validation

def test_login_invalid_credentials(test_client):
    response = test_client.post("/auth/login", json={
        "username": "invalid",
        "password": "wrong"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

def test_protected_endpoint_no_token(test_client):
    response = test_client.get("/tasks")
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers

# ========================================
# TASK CRUD TESTS
# ========================================

def test_create_task(test_client, auth_token):
    response = create_test_task(test_client, auth_token)
    assert response.status_code == 201
    task = response.json()
    assert task["id"] == 1
    assert task["title"] == "Test Task"
    assert task["status"] == "Pending"

def test_get_all_tasks(test_client, auth_token):
    # Create 2 tasks
    create_test_task(test_client, auth_token, "Task 1")
    create_test_task(test_client, auth_token, "Task 2", TaskStatus.COMPLETED)
    
    response = test_client.get("/tasks", headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 2
    assert tasks[0]["title"] == "Task 1"
    assert tasks[1]["status"] == "Completed"

def test_get_task_by_id(test_client, auth_token):
    create_response = create_test_task(test_client, auth_token)
    task_id = create_response.json()["id"]
    
    response = test_client.get(f"/tasks/{task_id}", headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    assert response.json()["id"] == task_id

def test_update_task(test_client, auth_token):
    create_response = create_test_task(test_client, auth_token)
    task_id = create_response.json()["id"]
    
    update_data = {
        "title": "Updated Title",
        "status": "Completed"
    }
    response = test_client.put(
        f"/tasks/{task_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "Updated Title"
    assert updated["status"] == "Completed"
    assert updated["updated_at"] != updated["created_at"]  # Timestamp should change

def test_delete_task(test_client, auth_token):
    create_response = create_test_task(test_client, auth_token)
    task_id = create_response.json()["id"]
    
    delete_response = test_client.delete(
        f"/tasks/{task_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert delete_response.status_code == 204
    
    # Verify task is gone
    get_response = test_client.get(f"/tasks/{task_id}", headers={"Authorization": f"Bearer {auth_token}"})
    assert get_response.status_code == 404

# ========================================
# FILTERING & STATS TESTS
# ========================================

def test_filter_tasks_by_status(test_client, auth_token):
    # Create tasks with different statuses
    create_test_task(test_client, auth_token, "Pending Task", TaskStatus.PENDING)
    create_test_task(test_client, auth_token, "Completed Task", TaskStatus.COMPLETED)
    
    # Test pending filter
    pending_response = test_client.get(
        "/tasks?status_filter=Pending",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    pending_tasks = pending_response.json()
    assert len(pending_tasks) == 1
    assert pending_tasks[0]["status"] == "Pending"
    
    # Test completed filter
    completed_response = test_client.get(
        "/tasks?status_filter=Completed",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    completed_tasks = completed_response.json()
    assert len(completed_tasks) == 1
    assert completed_tasks[0]["status"] == "Completed"

def test_weekly_stats_calculation(test_client, auth_token, monkeypatch):
    # Mock datetime for consistent week calculations
    fixed_date = datetime(2025, 5, 28)  # Week 22 of 2025
    class MockDatetime:
        @classmethod
        def now(cls):
            return fixed_date
    monkeypatch.setattr("main.datetime", MockDatetime)
    monkeypatch.setattr("database.datetime", MockDatetime)
    
    # Create tasks in different statuses
    create_test_task(test_client, auth_token, "Task 1", TaskStatus.PENDING)
    create_test_task(test_client, auth_token, "Task 2", TaskStatus.COMPLETED)
    create_test_task(test_client, auth_token, "Task 3", TaskStatus.COMPLETED)
    
    response = test_client.get(
        "/tasks/weekly-stats",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    stats = response.json()
    
    assert stats["total_weeks"] == 1
    week_data = stats["weekly_stats"][0]
    assert week_data["week"] == "2025-W22"
    assert week_data["total_tasks"] == 3
    assert week_data["completed_tasks"] == 2
    assert week_data["completion_percentage"] == 66.67

# ========================================
# ERROR HANDLING TESTS
# ========================================

def test_get_nonexistent_task(test_client, auth_token):
    response = test_client.get("/tasks/999", headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_update_nonexistent_task(test_client, auth_token):
    response = test_client.put(
        "/tasks/999",
        json={"title": "Update Attempt"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 404

def test_delete_nonexistent_task(test_client, auth_token):
    response = test_client.delete(
        "/tasks/999",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 404

def test_create_task_invalid_data(test_client, auth_token):
    # Missing required title
    response = test_client.post(
        "/tasks",
        json={"description": "Invalid task"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("title" in error["loc"] for error in errors)

# ========================================
# PUBLIC ENDPOINT TESTS
# ========================================

def test_health_check(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_database_test_endpoint(test_client):
    response = test_client.get("/test/database")
    assert response.status_code == 200
    assert "successful" in response.json()["message"]

def test_auth_info_endpoint(test_client):
    response = test_client.get("/test/auth-info")
    assert response.status_code == 200
    assert "testuser" in response.json()["default_test_user"]["username"]