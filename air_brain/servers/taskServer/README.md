# Task Management Server

A simple Flask-based RESTful API for task management that uses a JSON file as a database.

## Setup and Installation

1. Clone the repository
2. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python app.py
   ```
   The server will start on http://localhost:5000

## API Endpoints

### 1. Get All Tasks

**Endpoint:** `GET /api/tasks`

**Query Parameters:**
- `category` (optional): Filter by category
- `status` (optional): Filter by status
- `completed` (optional): Filter by completion status (true/false)
- `due_before` (optional): Filter tasks due before a specific date
- `due_after` (optional): Filter tasks due after a specific date
- `sort_by` (optional): Field to sort by (default: due_date)
- `sort_order` (optional): asc or desc (default: asc)

### 2. Get Task by ID

**Endpoint:** `GET /api/tasks/{task_id}`

### 3. Create Task

**Endpoint:** `POST /api/tasks`

**Request Body:**
```json
{
  "title": "New Task",
  "description": "Description of the new task",
  "due_date": "2023-07-20T10:00:00Z",
  "priority": "medium",
  "category": "personal",
  "status": "pending",
  "notes": "Additional notes",
  "location": "Office",
  "assigned_to": "Self"
}
```

### 4. Update Task

**Endpoint:** `PUT /api/tasks/{task_id}`

**Request Body:**
```json
{
  "title": "Updated Task Title",
  "description": "Updated description",
  "due_date": "2023-07-25T14:00:00Z",
  "priority": "high",
  "category": "health",
  "is_completed": true,
  "status": "completed",
  "notes": "Updated notes",
  "location": "Hospital",
  "assigned_to": "Self"
}
```

### 5. Delete Task

**Endpoint:** `DELETE /api/tasks/{task_id}`

### 6. Get Tasks by Date Range

**Endpoint:** `GET /api/tasks/date-range`

**Query Parameters:**
- `start_date`: Start date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD)

### 7. Get Today's Tasks

**Endpoint:** `GET /api/tasks/today`

### 8. Toggle Task Completion

**Endpoint:** `PATCH /api/tasks/{task_id}/toggle-completion`

## Data Structure

Each task has the following structure:

```json
{
  "id": "1",
  "title": "Task Title",
  "description": "Task Description",
  "due_date": "2023-07-15T08:00:00Z",
  "priority": "high",
  "category": "medication",
  "is_completed": false,
  "status": "pending",
  "created_at": "2023-07-10T14:30:00Z",
  "updated_at": "2023-07-10T14:30:00Z",
  "notes": "Additional notes",
  "location": "Location",
  "assigned_to": "Person"
}
```

## Example Usage

### Create a new task

```bash
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "New Task",
    "description": "Description of the new task",
    "due_date": "2023-07-20T10:00:00Z",
    "priority": "medium",
    "category": "personal",
    "notes": "Additional notes",
    "location": "Office",
    "assigned_to": "Self"
  }'
```

### Get all tasks

```bash
curl http://localhost:5000/api/tasks
```

### Get tasks by category

```bash
curl http://localhost:5000/api/tasks?category=personal
```

### Toggle task completion

```bash
curl -X PATCH http://localhost:5000/api/tasks/1/toggle-completion
``` 