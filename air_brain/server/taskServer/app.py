from flask import Flask, jsonify, request
import json
import os
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)

# Helper functions for working with the JSON file
def load_todos():
    """Load todos from the JSON file"""
    if not os.path.exists('todos.json'):
        return {"todos": []}
    
    with open('todos.json', 'r') as f:
        return json.load(f)

def save_todos(data):
    """Save todos to the JSON file"""
    with open('todos.json', 'w') as f:
        json.dump(data, f, indent=2)

def get_todo_by_id(todo_id):
    """Get a todo by its ID"""
    data = load_todos()
    for todo in data['todos']:
        if todo['id'] == todo_id:
            return todo
    return None

def format_date(date_str):
    """Format date string to ISO format"""
    if not date_str:
        return None
    try:
        # Parse the date string and return ISO format
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date_obj.isoformat().replace('+00:00', 'Z')
    except ValueError:
        return None

# API Routes

# 1. Get All Tasks
@app.route('/api/tasks', methods=['GET'])
def get_all_tasks():
    data = load_todos()
    todos = data['todos']
    
    # Apply filters if provided
    category = request.args.get('category')
    status = request.args.get('status')
    completed = request.args.get('completed')
    due_before = request.args.get('due_before')
    due_after = request.args.get('due_after')
    sort_by = request.args.get('sort_by', 'due_date')
    sort_order = request.args.get('sort_order', 'asc')
    
    filtered_todos = todos.copy()
    
    if category:
        filtered_todos = [todo for todo in filtered_todos if todo['category'] == category]
    
    if status:
        filtered_todos = [todo for todo in filtered_todos if todo['status'] == status]
    
    if completed is not None:
        completed_bool = completed.lower() == 'true'
        filtered_todos = [todo for todo in filtered_todos if todo['is_completed'] == completed_bool]
    
    if due_before:
        filtered_todos = [todo for todo in filtered_todos if todo['due_date'] <= due_before]
    
    if due_after:
        filtered_todos = [todo for todo in filtered_todos if todo['due_date'] >= due_after]
    
    # Sort todos
    reverse_sort = sort_order.lower() == 'desc'
    filtered_todos.sort(key=lambda x: x.get(sort_by, ''), reverse=reverse_sort)
    
    return jsonify({
        'success': True,
        'data': filtered_todos,
        'count': len(filtered_todos),
        'page': 1,
        'total_pages': 1
    })

# 2. Get Task by ID
@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    todo = get_todo_by_id(task_id)
    
    if not todo:
        return jsonify({
            'success': False,
            'error': {
                'code': 'TASK_NOT_FOUND',
                'message': f'Task with ID {task_id} not found'
            }
        }), 404
    
    return jsonify({
        'success': True,
        'data': todo
    })

# 3. Create Task
@app.route('/api/tasks', methods=['POST'])
def create_task():
    data = load_todos()
    request_data = request.get_json()
    
    # Validate required fields
    if not request_data or 'title' not in request_data or 'category' not in request_data:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_INPUT',
                'message': 'Title and category are required fields'
            }
        }), 400
    
    # Create new todo
    current_time = datetime.utcnow().isoformat() + 'Z'
    new_todo = {
        'id': str(uuid.uuid4()),
        'title': request_data['title'],
        'description': request_data.get('description', ''),
        'due_date': format_date(request_data.get('due_date')),
        'priority': request_data.get('priority', 'medium'),
        'category': request_data['category'],
        'is_completed': False,
        'status': request_data.get('status', 'pending'),
        'created_at': current_time,
        'updated_at': current_time,
        'notes': request_data.get('notes', ''),
        'location': request_data.get('location', ''),
        'assigned_to': request_data.get('assigned_to', 'Self')
    }
    
    data['todos'].append(new_todo)
    save_todos(data)
    
    return jsonify({
        'success': True,
        'data': new_todo,
        'message': 'Task created successfully'
    }), 201

# 4. Update Task
@app.route('/api/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    data = load_todos()
    request_data = request.get_json()
    
    # Find the todo
    todo_index = None
    for i, todo in enumerate(data['todos']):
        if todo['id'] == task_id:
            todo_index = i
            break
    
    if todo_index is None:
        return jsonify({
            'success': False,
            'error': {
                'code': 'TASK_NOT_FOUND',
                'message': f'Task with ID {task_id} not found'
            }
        }), 404
    
    # Update todo fields
    todo = data['todos'][todo_index]
    todo['title'] = request_data.get('title', todo['title'])
    todo['description'] = request_data.get('description', todo['description'])
    todo['due_date'] = format_date(request_data.get('due_date', todo['due_date']))
    todo['priority'] = request_data.get('priority', todo['priority'])
    todo['category'] = request_data.get('category', todo['category'])
    todo['is_completed'] = request_data.get('is_completed', todo['is_completed'])
    todo['status'] = request_data.get('status', todo['status'])
    todo['notes'] = request_data.get('notes', todo['notes'])
    todo['location'] = request_data.get('location', todo['location'])
    todo['assigned_to'] = request_data.get('assigned_to', todo['assigned_to'])
    todo['updated_at'] = datetime.utcnow().isoformat() + 'Z'
    
    # Save changes
    data['todos'][todo_index] = todo
    save_todos(data)
    
    return jsonify({
        'success': True,
        'data': todo,
        'message': 'Task updated successfully'
    })

# 5. Delete Task
@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    data = load_todos()
    
    # Find the todo
    todo_index = None
    for i, todo in enumerate(data['todos']):
        if todo['id'] == task_id:
            todo_index = i
            break
    
    if todo_index is None:
        return jsonify({
            'success': False,
            'error': {
                'code': 'TASK_NOT_FOUND',
                'message': f'Task with ID {task_id} not found'
            }
        }), 404
    
    # Remove the todo
    data['todos'].pop(todo_index)
    save_todos(data)
    
    return jsonify({
        'success': True,
        'message': 'Task deleted successfully'
    })

# 6. Get Tasks by Date Range
@app.route('/api/tasks/date-range', methods=['GET'])
def get_tasks_by_date_range():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_INPUT',
                'message': 'Both start_date and end_date are required'
            }
        }), 400
    
    # Format dates to ISO format for comparison
    start_date = f"{start_date}T00:00:00Z"
    end_date = f"{end_date}T23:59:59Z"
    
    data = load_todos()
    filtered_todos = [
        todo for todo in data['todos'] 
        if todo['due_date'] and start_date <= todo['due_date'] <= end_date
    ]
    
    return jsonify({
        'success': True,
        'data': filtered_todos,
        'count': len(filtered_todos)
    })

# 7. Get Today's Tasks
@app.route('/api/tasks/today', methods=['GET'])
def get_today_tasks():
    today = datetime.utcnow().date().isoformat()
    tomorrow = (datetime.utcnow() + timedelta(days=1)).date().isoformat()
    
    # Format dates to ISO format for comparison
    today_start = f"{today}T00:00:00Z"
    today_end = f"{today}T23:59:59Z"
    
    data = load_todos()
    today_todos = [
        todo for todo in data['todos'] 
        if todo['due_date'] and today_start <= todo['due_date'] <= today_end
    ]
    
    return jsonify({
        'success': True,
        'data': today_todos,
        'count': len(today_todos)
    })

# 8. Toggle Task Completion
@app.route('/api/tasks/<task_id>/toggle-completion', methods=['PATCH'])
def toggle_task_completion(task_id):
    data = load_todos()
    
    # Find the todo
    todo_index = None
    for i, todo in enumerate(data['todos']):
        if todo['id'] == task_id:
            todo_index = i
            break
    
    if todo_index is None:
        return jsonify({
            'success': False,
            'error': {
                'code': 'TASK_NOT_FOUND',
                'message': f'Task with ID {task_id} not found'
            }
        }), 404
    
    # Toggle completion status
    todo = data['todos'][todo_index]
    todo['is_completed'] = not todo['is_completed']
    
    # Update status if needed
    if todo['is_completed'] and todo['status'] != 'completed':
        todo['status'] = 'completed'
    elif not todo['is_completed'] and todo['status'] == 'completed':
        todo['status'] = 'pending'
    
    todo['updated_at'] = datetime.utcnow().isoformat() + 'Z'
    
    # Save changes
    data['todos'][todo_index] = todo
    save_todos(data)
    
    return jsonify({
        'success': True,
        'data': {
            'id': todo['id'],
            'is_completed': todo['is_completed'],
            'status': todo['status'],
            'updated_at': todo['updated_at']
        },
        'message': 'Task completion status updated'
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002) 