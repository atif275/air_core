import os
import json
import uuid
from datetime import datetime, timedelta, timezone
from langchain_core.tools import tool

# Default todo file path
TODO_FILE = "todos.json"


def _ensure_todo_file_exists():
    """Ensure the todo file exists with proper structure."""
    if not os.path.exists(TODO_FILE):
        with open(TODO_FILE, 'w', encoding='utf-8') as f:
            json.dump({"todos": []}, f, indent=2)
        print(f"DEBUG: Created new todo file at {TODO_FILE}")
    else:
        # Verify file has valid JSON structure
        try:
            with open(TODO_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict) or "todos" not in data:
                    # Reset file if structure is invalid
                    with open(TODO_FILE, 'w', encoding='utf-8') as f:
                        json.dump({"todos": []}, f, indent=2)
        except json.JSONDecodeError:
            # Reset file if JSON is invalid
            with open(TODO_FILE, 'w', encoding='utf-8') as f:
                json.dump({"todos": []}, f, indent=2)

def _load_todos():
    """Load todos from the JSON file."""
    _ensure_todo_file_exists()
    with open(TODO_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(f"DEBUG: Loaded {len(data.get('todos', []))} todos from {TODO_FILE}")
        return data

def _save_todos(data):
    """Save todos to the JSON file."""
    with open(TODO_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
        print(f"DEBUG: Saved {len(data.get('todos', []))} todos to {TODO_FILE}")

def _get_iso_datetime():
    """Get current datetime in ISO format with Z timezone."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _get_next_id(data):
    """Get the next available ID by finding the highest current ID and incrementing it."""
    todos = data.get("todos", [])
    if not todos:
        return 1  # Start with ID 1 if no todos exist
    
    # Try to get the highest numeric ID
    try:
        highest_id = max(int(todo["id"]) for todo in todos if todo["id"].isdigit())
        return highest_id + 1
    except (ValueError, KeyError):
        # If any conversion fails or there are no numeric IDs, start with 1
        return 1

@tool
def add_todo(
    title: str, 
    description: str = "", 
    due_date: str = "",
    priority: str = "medium",
    category: str = "personal",
    status: str = "pending",
    notes: str = "",
    location: str = "",
    assigned_to: str = "Self"
) -> str:
    """Add a new todo item."""
    try:
        data = _load_todos()
        current_time = _get_iso_datetime()
        
        # Generate incremental ID instead of UUID
        new_id = str(_get_next_id(data))
        
        new_todo = {
            "id": new_id,  # Now using incremental ID
            "title": title,
            "description": description,
            "due_date": due_date,
            "priority": priority.lower(),
            "category": category,
            "is_completed": status.lower() == "completed",
            "status": status.lower(),
            "created_at": current_time,
            "updated_at": current_time,
            "notes": notes,
            "location": location,
            "assigned_to": assigned_to
        }
        
        data["todos"].append(new_todo)
        _save_todos(data)
        
        return f"Todo '{title}' added successfully with ID: {new_id}"
    except Exception as e:
        return f"Error adding todo: {str(e)}"

@tool
def get_current_datetime() -> str:
    """Get the current date, time, and day of the week."""
    print("DEBUG: get_current_datetime() function called")
    try:
        current = datetime.now()
        utc_now = datetime.now(timezone.utc)  # Get current UTC time
        
        formatted_datetime = {
            "date": current.strftime("%Y-%m-%d"),
            "time": current.strftime("%H:%M:%S"),
            "day": current.strftime("%A"),
            "timezone": datetime.now(timezone.utc).astimezone().tzname(),
            "utc_date": utc_now.strftime("%Y-%m-%d"),
            "utc_time": utc_now.strftime("%H:%M:%S"),
            "utc_day": utc_now.strftime("%A"),
            "utc_timezone": "UTC"  # Static since we're using UTC
        }
        
        result = (f"Current Date: {formatted_datetime['date']}\n"
                f"Current Time: {formatted_datetime['time']}\n"
                f"Day: {formatted_datetime['day']}\n"
                f"Timezone: {formatted_datetime['timezone']}\n"
                f"UTC Date: {formatted_datetime['utc_date']}\n"
                f"UTC Time: {formatted_datetime['utc_time']}\n"
                f"UTC Day: {formatted_datetime['utc_day']}\n"
                f"UTC Timezone: {formatted_datetime['utc_timezone']}")
                
        print(f"DEBUG: get_current_datetime() completed successfully with result:\n{result}")
        return result
    except Exception as e:
        error_msg = f"Error getting current datetime: {str(e)}"
        print(f"DEBUG: get_current_datetime() failed with error: {error_msg}")
        return error_msg
    
@tool
def delete_todo(todo_id: str) -> str:
    """Delete a todo item by ID."""
    try:
        print(f"DEBUG: delete_todo() called with todo_id: {todo_id}")
        data = _load_todos()
        todos = data.get("todos", [])
        todo_to_delete = next((todo for todo in todos if todo["id"] == todo_id), None)
        if todo_to_delete:
            todos.remove(todo_to_delete)
            _save_todos(data)
            return f"Todo '{todo_to_delete['title']}' deleted successfully"
        else:
            return f"Todo with ID '{todo_id}' not found"
    except Exception as e:
        return f"Error deleting todo: {str(e)}"

@tool
def list_todos() -> str:
    """List all todos."""
    try:
        print("DEBUG: list_todos() function called")
        data = _load_todos()
        todos = data.get("todos", [])
        if not todos:
            return "No todos found"
        result = "Here are your todos:\n"
        for todo in todos:
            result += f"ID: {todo['id']}\n"
            result += f"Title: {todo['title']}\n"
            result += f"Description: {todo['description']}\n"
            result += f"Due Date: {todo['due_date']}\n"
            result += f"Priority: {todo['priority']}\n"
            result += f"Category: {todo['category']}\n"
            result += f"Status: {todo['status']}\n"
            result += f"Created At: {todo['created_at']}\n"
            result += f"Updated At: {todo['updated_at']}\n"
            result += f"Notes: {todo['notes']}\n"
            result += f"Location: {todo['location']}\n"
            result += f"Assigned To: {todo['assigned_to']}\n"
            result += "-----------------------------------\n"
        return result
    except Exception as e:
        return f"Error listing todos: {str(e)}"

@tool
def clear_all_todos() -> str:
    """Clear all todos."""
    try:
        print("DEBUG: clear_all_todos() function called")
        data = _load_todos()
        data["todos"] = []
        _save_todos(data)
        return "All todos have been cleared"
    except Exception as e:
        return f"Error clearing todos: {str(e)}"

@tool
def update_todo(
    todo_id: str,
    title: str = "",
    description: str = "",
    due_date: str = "",
    priority: str = "",
    category: str = "",
    is_completed: bool = False,
    status: str = "",
    notes: str = "",
    location: str = "",
    assigned_to: str = ""
) -> str:
    """Update a todo item by ID."""
    try:
        print(f"DEBUG: update_todo() called with todo_id: {todo_id}")
        data = _load_todos()
        todos = data.get("todos", [])
        todo_to_update = next((todo for todo in todos if todo["id"] == todo_id), None)
        if todo_to_update:
            if title:
                todo_to_update["title"] = title
            if description:
                todo_to_update["description"] = description
            if due_date:
                todo_to_update["due_date"] = due_date
            if priority:
                todo_to_update["priority"] = priority
            if category:
                todo_to_update["category"] = category
            if is_completed:
                todo_to_update["is_completed"] = is_completed
            if status:
                todo_to_update["status"] = status
            if notes:
                todo_to_update["notes"] = notes
            if location:
                todo_to_update["location"] = location
            if assigned_to:
                todo_to_update["assigned_to"] = assigned_to
            todo_to_update["updated_at"] = _get_iso_datetime()
            _save_todos(data)
            return f"Todo '{todo_to_update['title']}' updated successfully"
        else:
            return f"Todo with ID '{todo_id}' not found"
    except Exception as e:
        return f"Error updating todo: {str(e)}"



@tool
def mark_all_todos_completed() -> str:
    """Mark all todos as completed in a single operation."""
    try:
        print("DEBUG: mark_all_todos_completed() called")
        data = _load_todos()
        current_time = _get_iso_datetime()
        
        for todo in data["todos"]:
            todo["status"] = "completed"
            todo["is_completed"] = True
            todo["updated_at"] = current_time
        
        _save_todos(data)
        return f"Marked {len(data['todos'])} todos as completed"
    except Exception as e:
        return f"Error completing all todos: {str(e)}"

@tool
def mark_all_task_uncompleted() -> str:
    """Mark all todos as uncompleted."""
    try:
        print("DEBUG: mark_all_todos_uncompleted() called")
        data = _load_todos()
        current_time = _get_iso_datetime()
        
        for todo in data["todos"]:
            todo["status"] = "pending"
            todo["is_completed"] = False
            todo["updated_at"] = current_time
        
        _save_todos(data)
        return f"Marked {len(data['todos'])} todos as uncompleted"  
    except Exception as e:
        return f"Error marking all todos as uncompleted: {str(e)}"


