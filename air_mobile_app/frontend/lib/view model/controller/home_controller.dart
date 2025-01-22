import 'package:get/get.dart';
import 'package:flutter/material.dart';
import 'package:air/view/new%20task/components/progress_picker.dart';
import 'package:air/services/task_api_service.dart';

class HomeController extends GetxController {
  var name = 'Atif'.obs; 
  var hasData = false.obs; 
  var taskCount = 0.obs; 
  var list = <Map<String, dynamic>>[].obs; // RxList<Map<String, dynamic>>
  final TaskApiService _taskApiService = TaskApiService();

  HomeController() {
    fetchTasks();  // Fetch tasks from the backend upon initialization
  }

  Future<void> fetchTasks() async {
    try {
      final tasks = await _taskApiService.fetchTasks();
      if (tasks.isNotEmpty) {
        setTasks(tasks);
      }
    } catch (e) {
      print('Error fetching tasks: $e');
    }
  }

  // Accessor for the RxList
  RxList<Map<String, dynamic>> get taskList => list;

  // Method to update the task list from the API response
  void setTasks(List<dynamic> tasks) {
    list.clear(); // Clear existing tasks before updating

    for (var task in tasks) {
      list.add({
        "_id": task['_id'] ?? '',  // Ensure _id is not null
        "show": "yes",
        "title": task['title'] ?? '',
        "category": task['category'] ?? '',
        "progress": (task['progress'] ?? 0).toDouble(),
        "date": task['date'] ?? '',
        "image": task['image'] ?? 'assets/images/task3.jpg',
        "daysLeft": _calculateDaysLeft(task['date']),
      });
    }

    _updateTaskData(); // Update task count and data state
  }

  // Helper function to calculate days left based on task date
  int _calculateDaysLeft(String? dateString) {
    if (dateString == null || dateString.isEmpty) return 0;
    final dueDate = DateTime.parse(dateString);
    final now = DateTime.now();
    return dueDate.difference(now).inDays;
  }

  // Adds a new task to the list
  void addTask(Map<String, dynamic> task) {
    if (task.containsKey('title') && task.containsKey('category')) {
      list.add(task);
      list.refresh();
      _updateTaskData();
    } else {
      throw Exception('Task must contain "title" and "category".');
    }
  }

  // Updates the selected task's data
  void editTask(int index, Map<String, dynamic> updatedTask) async {
    if (index >= 0 && index < list.length) {
      final taskId = list[index]['_id'];

      if (taskId == null || taskId.toString().isEmpty) {
        Get.snackbar("Error", "Invalid task ID");
        return;
      }

      try {
        bool success = await _taskApiService.updateTask(taskId.toString(), updatedTask);
        if (success) {
          list[index] = updatedTask;
          list.refresh();
          _updateTaskData();
          Get.snackbar("Success", "Task updated successfully");
        } else {
          Get.snackbar("Error", "Failed to update task in the database");
        }
      } catch (e) {
        Get.snackbar("Error", "Error updating task: $e");
      }
    }
  }

  // Removes a task from the list
  void deleteTask(int index) async {
    if (index >= 0 && index < list.length) {
      final taskId = list[index]['_id'];

      if (taskId == null || taskId.toString().isEmpty) {
        Get.snackbar("Error", "Invalid task ID");
        return;
      }

      try {
        bool success = await _taskApiService.deleteTask(taskId.toString());
        if (success) {
          list.removeAt(index);
          list.refresh();
          _updateTaskData();
          Get.snackbar("Success", "Task deleted successfully");
        } else {
          Get.snackbar("Error", "Failed to delete task from the database");
        }
      } catch (e) {
        Get.snackbar("Error", "Error deleting task: $e");
      }
    }
  }

  // Handles popup menu actions
  void handlePopupAction(int value, int index, BuildContext context) {
    if (index < 0 || index >= list.length) {
      print("Error: Invalid task index $index");
      return;
    }

    if (value == 1) { // Edit action
      _showEditDialog(index, context);
    } else if (value == 2) { // Delete action
      _showDeleteConfirmation(index, context);
    }
  }

  // Shows a dialog to edit a task
  void _showEditDialog(int index, BuildContext context) {
    final TextEditingController titleController = TextEditingController();
    final TextEditingController categoryController = TextEditingController();

    titleController.text = list[index]['title'];
    categoryController.text = list[index]['category'];

    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Edit Task'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: titleController,
                decoration: const InputDecoration(labelText: 'Title'),
              ),
              TextField(
                controller: categoryController,
                decoration: const InputDecoration(labelText: 'Category'),
              ),
              const SizedBox(height: 10),
              TextButton(
                onPressed: () {
                  ProgressPicker(
                    context,
                    taskIndex: index,
                    initialProgress: list[index]['progress'],
                  );
                },
                child: const Text(
                  'Set Progress',
                  style: TextStyle(color: Colors.pinkAccent),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
              },
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () {
                editTask(index, {
                  ...list[index],
                  'title': titleController.text,
                  'category': categoryController.text,
                });
                Navigator.of(context).pop();
              },
              child: const Text('Save'),
            ),
          ],
        );
      },
    );
  }

  // Shows a confirmation dialog to delete a task
  void _showDeleteConfirmation(int index, BuildContext context) {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Delete Task'),
          content: const Text('Are you sure you want to delete this task?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () {
                deleteTask(index);
                Navigator.of(context).pop();
              },
              child: const Text('Delete'),
            ),
          ],
        );
      },
    );
  }

  void _updateTaskData() {
    taskCount.value = list.length;
    hasData.value = list.isNotEmpty;
  }
}
