from fastapi import FastAPI, HTTPException, status, Depends
from models import TaskCreate, TaskStatus, Task, TaskUpdate
from database import task_db
from auth import (
    authenticate_user, create_access_token, get_current_user, 
    UserLogin, UserCreate, Token, create_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from typing import List, Dict
from datetime import datetime, timedelta
from collections import defaultdict
app = FastAPI(
    title="Task Management API with Authentication->Technical Assessment [:)]",
    description="A RESTful API for managing tasks with JWT authentication(bonus yami) ",
    version="1.1.0"
)
@app.get("/")
async def read_root():
    """
    Welcome endpoint - publicly accessible  
    """
    return {
        "message": "Welcome to Task Management API with Authentication",
        "version": "1.1.0",
        "docs": "/docs",
        "auth_endpoints": {
            "register": "POST /auth/register",
            "login": "POST /auth/login"
        }
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint - publicly accessible
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected"
    }
    # Here we could add more checks like database connection, etc.
@app.post("/auth/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate):
    """
    Register a new user account.
    
     **Authentication required**: Use registered username and password(just a demo).
    
    **Request Body:**
    - **username**: Username 
    - **password**: Password 
    
    **Response:**
    - Success message with username
    """
    try:
        result = create_user(user_data.username, user_data.password)
        return result
    except HTTPException:
        # Re-raise HTTP exceptions from create_user function
        raise
    except Exception as e:
        # Handle any unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )

@app.post("/auth/login", response_model=Token)
async def login_user(user_credentials: UserLogin):
    """
    Login and receive an access token.
    **Authentication required**: Use registered username and password(just a demo).
    **Request Body:**
    - **username**: Your registered username
    - **password**: Your password
    
    **Response:**
    - **access_token**: JWT token for API authentication
    - **token_type**: Always "bearer"
    
    **How to use the token:**
    Include in Authorization header: `Authorization: Bearer your-token-here`
    
    **Token expires in 30 minutes** - you'll need to login again after that.
    
    """
    # Try to authenticate the user(Just  a demo)
    user = authenticate_user(user_credentials.username, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer"
    }

@app.get("/auth/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """
    Get current user information.
    
    **Authentication required**: Include Bearer token in Authorization header.
    
    **Response:**
    - Current user's username
    - Useful for testing if your token works
    
    **Example:**
    ```bash
    curl -H "Authorization: Bearer your-token" http://localhost:8000/auth/me
    ```
    """
    return {
        "username": current_user["username"],
        "message": "Token is valid!",
        "token_expires_in_minutes": ACCESS_TOKEN_EXPIRE_MINUTES
    }


# All endpoints below require authentication via Bearer token

@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate, 
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new task with title, description, and status.
    
    ** Authentication required**: Include Bearer token in Authorization header.
    
    **Request Body:**
    - **title**: Task title (required, 1-200 characters)
    - **description**: Task description (optional, max 1000 characters)  
    - **status**: Task status (Pending or Completed, defaults to Pending)
    
    **Response:**
    - Complete task object with ID, timestamps, etc.
    
    **Example Request:**
    ```json
    {
        "title": "Complete project documentation",
        "description": "Write comprehensive docs for the API",
        "status": "Pending"
    }
    ```
    
    **How to authenticate:**
    ```bash
    curl -X POST "http://localhost:8000/tasks" \
         -H "Authorization: Bearer your-token-here" \
         -H "Content-Type: application/json" \
         -d '{"title": "My Task", "description": "Task details"}'
    ```
    """
    try:
        # The current_user parameter ensures user is authenticated
        created_task = task_db.create_task(task_data)
        return created_task
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
        )

@app.get("/tasks", response_model=List[Task])
async def get_all_tasks(
    status_filter: TaskStatus = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve all tasks, with optional filtering by status.
    
    **Authentication required**: Include Bearer token in Authorization header.
    
    **Query Parameters:**
    - **status_filter**: Optional. Filter tasks by status (Pending or Completed)
    
    **Returns:**
    - List of all tasks if no filter is provided
    - List of filtered tasks if status is specified
    
    """
    try:
        # Get tasks with optional status filter
        tasks = task_db.get_all_tasks(status_filter=status_filter)
        return tasks
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve tasks: {str(e)}"
        )

@app.get("/tasks/{task_id}", response_model=Task)
async def get_task_by_id(
    task_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific task by its ID.
    
    **Authentication required**: Include Bearer token in Authorization header.
    
    **Path Parameters:**
    - **task_id**: The ID of the task to retrieve
    
    **Response:**
    - Complete task object if found
    - 404 error if task doesn't exist
    """
    try:
        task = task_db.get_task_by_id(task_id)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        return task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve task: {str(e)}"
        )

@app.put("/tasks/{task_id}", response_model=Task)
async def update_task(
    task_id: int, 
    task_update: TaskUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing task by ID.
    
    **Authentication required**: Include Bearer token in Authorization header.
    
    **Path Parameters:**
    - **task_id**: The ID of the task to update
    
    **Request Body:**
    - **title**: New task title (optional)
    - **description**: New task description (optional)
    - **status**: New task status (optional)
    
    **Note:** Only provided fields will be updated. Others remain unchanged.
    
    **Example:**
    """
    try:
        updated_task = task_db.update_task(task_id, task_update)
        
        if updated_task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        
        return updated_task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task: {str(e)}"
        )

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a task by ID.
    
    **Authentication required**: Include Bearer token in Authorization header.
    
    **Path Parameters:**
    - **task_id**: The ID of the task to delete
    
    **Response:**
    - 204 No Content on successful deletion
    - 404 Not Found if task doesn't exist
    
    """
    try:
        was_deleted = task_db.delete_task(task_id)
        
        if not was_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        
        # Success! FastAPI automatically returns 204 No Content
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete task: {str(e)}"
        )

@app.get("/tasks/weekly-stats", response_model=dict)
async def get_weekly_stats(current_user: dict = Depends(get_current_user)):
    """
    Get the percentage of completed tasks per week.
    
    **Authentication required**: Include Bearer token in Authorization header.
    
    **Response:**
    Statistics showing:
    - Week identifier (YYYY-W##)
    - Week date range (start and end dates)
    - Total tasks created that week
    - Completed tasks that week  
    - Completion percentage
    
    **Note:** Weeks are based on when tasks were created (created_at field).
    
    **Example Response:**
    ```json
    {
        "message": "Weekly statistics for 2 weeks",
        "total_weeks": 2,
        "weekly_stats": [
            {
                "week": "2025-W22",
                "week_start": "2025-05-26",
                "week_end": "2025-06-01",
                "total_tasks": 5,
                "completed_tasks": 3,
                "completion_percentage": 60.0
            }
        ]
    }
    ```
    """
    try:
        # Get all tasks from database
        all_tasks = task_db.get_all_tasks()
        
        if not all_tasks:
            return {
                "message": "No tasks found",
                "total_weeks": 0,
                "weekly_stats": []
            }
        
        # Group tasks by week using defaultdict
        weekly_data = defaultdict(lambda: {"total": 0, "completed": 0})
        
        for task in all_tasks:
            # Get the ISO week string (e.g., "2025-W22")
            year, week_num, _ = task.created_at.isocalendar()
            week_key = f"{year}-W{week_num:02d}"
            
            # Count total tasks for this week
            weekly_data[week_key]["total"] += 1
            
            # Count completed tasks for this week
            if task.status == TaskStatus.COMPLETED:
                weekly_data[week_key]["completed"] += 1
        
        # Calculate percentages and build response
        weekly_stats = []
        for week, data in sorted(weekly_data.items()):
            total = data["total"]
            completed = data["completed"]
            
            # Calculate completion percentage
            percentage = round((completed / total) * 100, 2) if total > 0 else 0
            
            # Get week date range for better readability
            year, week_num = week.split("-W")
            week_start = datetime.strptime(f"{year}-W{week_num}-1", "%Y-W%W-%w")
            week_end = week_start + timedelta(days=6)
            
            weekly_stats.append({
                "week": week,
                "week_start": week_start.strftime("%Y-%m-%d"),
                "week_end": week_end.strftime("%Y-%m-%d"),
                "total_tasks": total,
                "completed_tasks": completed,
                "completion_percentage": percentage
            })
        
        return {
            "message": f"Weekly statistics for {len(weekly_stats)} weeks",
            "total_weeks": len(weekly_stats),
            "weekly_stats": weekly_stats,
            "user": current_user["username"]  # Show which user requested this
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate weekly stats: {str(e)}"
        )

# These are for testing and don't require authentication

@app.get("/test/database")
async def test_database():
    """
    Test database functionality - publicly accessible for testing.
    
    **This endpoint is public** - useful for initial testing.
    
    Creates a sample task and shows database info.
    """
    try:
        # Create a sample task
        sample_task = TaskCreate(
            title="Database Test Task",
            description="This task was created by the test endpoint!",
            status=TaskStatus.PENDING
        )
        
        # Add it to database
        created_task = task_db.create_task(sample_task)
        
        # Get database info
        db_info = task_db.get_database_info()
        
        # Get all tasks count
        all_tasks = task_db.get_all_tasks()
        
        return {
            "message": "✅ SQLite database test successful!",
            "database_info": db_info,
            "sample_task_created": {
                "id": created_task.id,
                "title": created_task.title,
                "status": created_task.status
            },
            "total_tasks_in_db": len(all_tasks),
            "note": "This is a public endpoint for testing. Use /tasks endpoints with authentication for real usage."
        }
        
    except Exception as e:
        return {
            "message": "❌ Database test failed!",
            "error": str(e),
            "suggestion": "Check if database file permissions are correct"
        }

@app.get("/test/auth-info")
async def test_auth_info():
    """
    Get information about authentication system - publicly accessible.
    
    **This endpoint is public** - shows how to use authentication.
    """
    return {
        "message": "Authentication system information",
        "default_test_user": {
            "username": "testuser",
            "password": "secret",
            "note": "Use this to test login without registering"
        },
        "how_to_use": {
            "step_1": "Register: POST /auth/register with username/password",
            "step_2": "Login: POST /auth/login to get access token", 
            "step_3": "Use token: Add 'Authorization: Bearer <token>' header to requests",
            "step_4": "Access protected endpoints like GET /tasks"
        },
        "token_info": {
            "expires_in_minutes": ACCESS_TOKEN_EXPIRE_MINUTES,
            "type": "JWT Bearer token"
        },
        "protected_endpoints": [
            "GET /tasks",
            "POST /tasks", 
            "PUT /tasks/{id}",
            "DELETE /tasks/{id}",
            "GET /tasks/weekly-stats",
            "GET /auth/me"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Task Management API with Authentication...")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔐 Test user: username='testuser', password='secret'")
    print("ℹ️  Authentication info: http://localhost:8000/test/auth-info")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=True  # Auto-reload when code changes (for development)
    )