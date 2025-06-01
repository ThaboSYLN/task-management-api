from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import Optional

# Define the possible task statuses
class TaskStatus(str, Enum):
    PENDING = "Pending"
    COMPLETED = "Completed"

# This is what we receive when someone creates a task
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: Optional[str] = Field(None, max_length=1000, description="Task description")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Task status")

# This is what we receive when someone updates a task
class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[TaskStatus] = None

# Complete task object with all fields
class Task(BaseModel):
    id: int = Field(..., description="Unique task ID")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    status: TaskStatus = Field(..., description="Task status")
    created_at: datetime = Field(..., description="When task was created")
    updated_at: datetime = Field(..., description="When task was last updated")

    class Config:
        # The model can  work with datetime objects
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }