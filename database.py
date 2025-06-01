import sqlite3
from datetime import datetime
from typing import List, Optional
from models import Task, TaskCreate, TaskUpdate, TaskStatus
import json

class TaskDatabase:
    def __init__(self, db_path: str = "tasks.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the SQLite database and create tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()
            print(f"✅ Database initialized: {self.db_path}")

    def create_task(self, task_data: TaskCreate) -> Task:
        """Create a new task and return it"""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (title, description, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (task_data.title, task_data.description, task_data.status.value, now, now))
            
            task_id = cursor.lastrowid
            conn.commit()
        
        # Return the created task
        return Task(
            id=task_id,
            title=task_data.title,
            description=task_data.description,
            status=task_data.status,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now)
        )

    def get_all_tasks(self, status_filter: Optional[TaskStatus] = None) -> List[Task]:
        """Get all tasks, optionally filtered by status"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if status_filter:
                cursor.execute("SELECT * FROM tasks WHERE status = ?", (status_filter.value,))
            else:
                cursor.execute("SELECT * FROM tasks")
            
            rows = cursor.fetchall()
            
            tasks = []
            for row in rows:
                tasks.append(Task(
                    id=row[0],
                    title=row[1],
                    description=row[2],
                    status=TaskStatus(row[3]),
                    created_at=datetime.fromisoformat(row[4]),
                    updated_at=datetime.fromisoformat(row[5])
                ))
            
            return tasks

    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """Get a specific task by its ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            
            if row:
                return Task(
                    id=row[0],
                    title=row[1],
                    description=row[2],
                    status=TaskStatus(row[3]),
                    created_at=datetime.fromisoformat(row[4]),
                    updated_at=datetime.fromisoformat(row[5])
                )
            return None

    def update_task(self, task_id: int, task_update: TaskUpdate) -> Optional[Task]:
        """Update an existing task"""
        # First check if task exists
        existing_task = self.get_task_by_id(task_id)
        if not existing_task:
            return None
        
        # Prepare update data
        now = datetime.now().isoformat()
        
        # Use existing values if update fields are None
        new_title = task_update.title if task_update.title is not None else existing_task.title
        new_description = task_update.description if task_update.description is not None else existing_task.description
        new_status = task_update.status if task_update.status is not None else existing_task.status
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks 
                SET title = ?, description = ?, status = ?, updated_at = ?
                WHERE id = ?
            """, (new_title, new_description, new_status.value, now, task_id))
            conn.commit()
        
        # Return the updated task
        return Task(
            id=task_id,
            title=new_title,
            description=new_description,
            status=new_status,
            created_at=existing_task.created_at,
            updated_at=datetime.fromisoformat(now)
        )

    def delete_task(self, task_id: int) -> bool:
        """Delete a task by ID. Returns True if deleted, False if not found"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            deleted_rows = cursor.rowcount
            conn.commit()
            
            return deleted_rows > 0

    def get_task_count(self) -> int:
        """Get total number of tasks"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tasks")
            return cursor.fetchone()[0]

    def get_completed_tasks_count(self) -> int:
        """Get number of completed tasks"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = ?", (TaskStatus.COMPLETED.value,))
            return cursor.fetchone()[0]

    def get_database_info(self) -> dict:
        """Get info about the database - useful for testing"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            return {
                "database_path": self.db_path,
                "tables": [table[0] for table in tables],
                "total_tasks": self.get_task_count()
            }

# Create a global instance that will be used by our API
task_db = TaskDatabase()