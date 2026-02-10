# Knowledge Base API

A robust Knowledge Base backend system built with **FastAPI** and **PostgreSQL** using raw SQL queries for maximum performance and control. This project manages knowledge entries, clients, stakeholders, and deliverables.

## 🚀 Features

- **FastAPI** for high-performance Async I/O.
- **PostgreSQL** database interactivity using `psycopg2` (Raw SQL).
- **Pydantic** for data validation and settings management.
- **JWT Authentication** for secure access.
- **Role-Based Access Control (RBAC)** for granular permission management.
- **Comprehensive Logging** setup.

## 🏗️ Architecture & Flow

This project follows a clear separation of concerns pattern:

```mermaid
graph LR
    A[Client Request] --> B[Router (app/routers)]
    B --> C[Service Layer (app/service)]
    C --> D[Database (PostgreSQL)]
    D --> C
    C --> B
    B --> A[JSON Response]
```

### Request Flow Explained
1.  **Router (`app/routers/`)**: 
    - Receives the HTTP request (GET, POST, etc.).
    - Validates input using **DTOs** (Data Transfer Objects) defined in `app/dto/`.
    - Extract user context (e.g., `current_user`) using dependencies.
    - Calls the appropriate method in the **Service Layer**.

2.  **Service Layer (`app/service/`)**:
    - Contains the core business logic.
    - Handles complex operations like permission checks (RBAC).
    - Interacts with the database using `psycopg2` connections.
    - Returns domain objects or data to the router.

3.  **Database (`app/db/`)**:
    - Raw SQL queries are executed here/via service.
    - Schema is defined in `app/db/schema.sql`.

## 📂 Project Structure

```
Knowledge_Base-main/
├── app/
│   ├── config/          # Configuration settings (Env vars)
│   ├── db/              # Database schema & connection utilities
│   │   └── schema.sql   # The SQL schema for creating tables
│   ├── dependencies/    # Dependency injection (e.g., get_current_user)
│   ├── dto/             # Pydantic models for Request/Response validation
│   ├── exceptions/      # Custom exception handlers
│   ├── routers/         # API Endpoints (Controllers)
│   ├── service/         # Business Logic & Database Interactions
│   └── utils/           # Helper functions (RBAC, etc.)
├── main.py              # Application Entry Point
├── .env                 # Environment variables
└── pyproject.toml       # Dependencies (uv/poetry)
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.14+
- PostgreSQL

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Knowledge_Base-main
```

### 2. Set Up Virtual Environment
```bash
# Using uv (recommended)
uv sync

# OR using venv
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt # if available, or install dependencies manually
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory:
```env
# Database Configuration
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=knowledge_base
DATABASE_USER=postgres
DATABASE_PASSWORD=yourpassword

# App Configuration
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 4. Initialize Database
Apply the schema to your PostgreSQL database:
```bash
psql -h localhost -U postgres -d knowledge_base -f app/db/schema.sql
```
*Note: Make sure the database `knowledge_base` exists first.*

### 5. Run the Application
```bash
uvicorn main:app --reload
```
The API will be available at: `http://localhost:8000`

## 📚 API Documentation

Once the server is running, you can access the interactive API docs:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Key Modules
- **Auth**: Login and Token generation.
- **Knowledge**: Create, Search, and Retrieve knowledge entries.
- **Clients**: Manage client organizations.
- **Stakeholders**: Manage key stakeholders associated with clients.
- **Deliverables**: Track distinct deliverables.

## 💻 Development Guide

### Adding a New Feature
1.  **Define DTO**: Create request/response models in `app/dto/`.
2.  **Create Service**: Implement business logic and SQL queries in `app/service/`.
3.  **Create Router**: Define the endpoint in `app/routers/` and use the service.
4.  **Register Router**: Add the router to `main.py`.

---
*Built with ❤️ by the Engineering Team*
