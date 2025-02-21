import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:intl/intl.dart';
import '../model/task_model.dart';

class TaskApiService {
  final String baseUrl = dotenv.env['API_URL'] ?? 'http://localhost:5001';

  Future<List<TaskModel>> fetchTasks() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/tasks'));
      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((json) => TaskModel.fromMap(json)).toList();
      } else {
        throw Exception('Failed to load tasks');
      }
    } catch (e) {
      print('Error fetching tasks: $e');
      throw Exception('Failed to connect to server');
    }
  }

  // Get a task by ID
  Future<Map<String, dynamic>> getTaskById(String id) async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/tasks/$id'));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to load task');
      }
    } catch (e) {
      throw Exception('Error fetching task: $e');
    }
  }

  // Create a new task
  Future<bool> createTask(Map<String, dynamic> taskData) async {
    try {
      taskData['date'] = DateFormat('yyyy-MM-dd').format(DateTime.parse(taskData['date']));
      final response = await http.post(
        Uri.parse('$baseUrl/tasks'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(taskData),
      );

      if (response.statusCode == 201) {
        return true;
      } else {
        throw Exception('Failed to create task');
      }
    } catch (e) {
      throw Exception('Error creating task: $e');
    }
  }

  // Update an existing task
  Future<bool> updateTask(String id, Map<String, dynamic> updatedData) async {
    try {
      final response = await http.put(
        Uri.parse('$baseUrl/tasks/$id'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(updatedData),
      );

      if (response.statusCode == 200) {
        return true;
      } else {
        throw Exception('Failed to update task');
      }
    } catch (e) {
      throw Exception('Error updating task: $e');
    }
  }

  // Delete a task by ID
  Future<bool> deleteTask(String id) async {
    try {
      final response = await http.delete(Uri.parse('$baseUrl/tasks/$id'));

      if (response.statusCode == 200) {
        return true;
      } else {
        throw Exception('Failed to delete task');
      }
    } catch (e) {
      throw Exception('Error deleting task: $e');
    }
  }
}
