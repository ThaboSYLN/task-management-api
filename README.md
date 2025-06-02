# 📝 FastAPI Task Manager

A simple task management API built using FastAPI, supporting user registration, login, JWT-based authentication, task CRUD operations, and weekly task statistics.

---

## 🚀 Features

- **User Registration & Login**  
- **JWT Authentication**  
- **Create, Read, Update, Delete Tasks**  
- **Weekly Completion Stats**  
- **Secure Password Hashing**  
- **Test Coverage with Pytest**

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/ThaboSYLN/task-management-api
cd task-management-api
```

### 2. (Optional) Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install fastapi uvicorn passlib[bcrypt] python-jose pytest
```

### 4. Run the Server

```bash
uvicorn main:app --reload
```

Access API docs at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🔐 Authentication

- JWT-based authentication
- Use the `/token` endpoint to log in and receive a token
- Include the token in the `Authorization` header as:

```
Authorization: Bearer <your_token>
```

---

## 📡 API Endpoints

### 🧑 User Routes

| Method | Endpoint     | Description         |
|--------|--------------|---------------------|
| POST   | `/users/`    | Register a user     |
| POST   | `/token`     | Get JWT token       |

---

### ✅ Task Routes

| Method | Endpoint       | Description                    |
|--------|----------------|--------------------------------|
| GET    | `/tasks/`      | List all user tasks            |
| POST   | `/tasks/`      | Create a new task              |
| PUT    | `/tasks/{id}`  | Update an existing task        |
| DELETE | `/tasks/{id}`  | Delete a task                  |
| GET    | `/tasks/stats` | Weekly completed tasks summary |

---

## 🧪 Running Tests

```bash
pytest
```

This runs the test suite using an in-memory SQLite database (`sqlite:///:memory:`). Tests check user creation, login, task creation, and retrieval.

---

## 🧠 Assumptions

| # | Assumption |
|---|------------|
| 1 | SQLite is used for simplicity; no external DB setup required |
| 2 | Token expires after 30 minutes |
| 3 | Only authenticated users can manage their tasks |
| 4 | Passwords are stored using bcrypt hashing |
| 5 | Weekly stats are generated based on `completed_at` timestamp |
| 6 | Each user can only access their own tasks |
| 7 | There’s no frontend – this is a backend API only |
| 8 | API will run in local environment (Python 3.8+) |

---

## 🛠️ Technologies Used

- **FastAPI** – Web Framework    
- **SQLite** – Local Development Database  
- **JWT (python-jose)** – Authentication  
- **Passlib (bcrypt)** – Password Hashing  
- **Pytest** – Unit Testing

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---
