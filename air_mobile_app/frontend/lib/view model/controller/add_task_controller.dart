import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';
import 'package:air/model/task_model.dart';
import 'package:air/utils/utils.dart';
import 'package:air/view/new%20task/components/progress_picker.dart';
import 'package:air/view%20model/controller/home_controller.dart';
import 'package:air/services/task_api_service.dart';

class AddTaskController extends GetxController {
  final RxInt selectedImageIndex = 1.obs;
  final RxBool lowPriority = true.obs;
  final RxBool titleFocus = false.obs;
  final RxBool categoryFocus = false.obs;
  final RxBool descriptionFocus = false.obs;
  final RxBool loading = false.obs;
  final RxDouble progress = 0.0.obs;
  final Rx<TextEditingController> title = TextEditingController().obs;
  final Rx<TextEditingController> description = TextEditingController().obs;
  final Rx<TextEditingController> category = TextEditingController().obs;
  final RxString time = ''.obs;
  final RxString date = ''.obs;
  final TaskApiService _taskApiService = TaskApiService();

  // Dummy list to simulate task storage
  final RxList<TaskModel> tasks = <TaskModel>[].obs;

  // Adds a task to the local task list
  Future<void> addTask() async {
  try {
    loading.value = true;
    // print("Formatted Date before sending: ${date.value}");

    final newTask = {
      "title": title.value.text,
      "description": description.value.text,
      "category": category.value.text,
      "priority": lowPriority.value ? 'High' : 'Low',
      "progress": progress.value.toInt(),
      "date": date.value,
      "time": time.value,
      "image": Utils.getImage()[selectedImageIndex.value],
      "status": 'Pending', // Default status
    };

    bool success = await _taskApiService.createTask(newTask);

    if (success) {
      final homeController = Get.find<HomeController>();
      await homeController.fetchTasks(); // Refresh tasks from the backend

      clearFields(); // Clear input fields
      Get.back(); // Close the bottom sheet

      Utils.showSnackBar(
        'Success', 
        'Task added successfully!',
        const Icon(Icons.check_circle, color: Colors.green),
      );
    } else {
      Utils.showSnackBar(
        'Error', 
        'Failed to add task!', 
        const Icon(Icons.error, color: Colors.red),
      );
    }
  } catch (e) {
    Utils.showSnackBar(
      'Error',
      'Failed to add task: $e',
      const Icon(Icons.error, color: Colors.red),
    );
  } finally {
    loading.value = false;
  }
}


  void updateTaskProgress(int taskIndex) {
    final homeController =
        Get.find<HomeController>(); // Access HomeController instance

    if (taskIndex >= 0 && taskIndex < homeController.list.length) {
      homeController.list[taskIndex]['progress'] =
          progress.value.toInt(); // Update progress
      Utils.showSnackBar(
        'Success',
        'Task progress updated!',
        const Icon(Icons.check_circle, color: Colors.green),
      );
      progress.value = 0.0; // Reset progress for future use
    } else {
      Utils.showSnackBar(
        'Error',
        'Invalid task index!',
        const Icon(Icons.error, color: Colors.red),
      );
    }
  }

  // Clears input fields after task submission
  void clearFields() {
    title.value.clear();
    category.value.clear();
    description.value.clear();
    date.value = '';
    time.value = '';
    progress.value = 0.0;
    selectedImageIndex.value = 1;
  }

  // Opens the progress picker
  void showProgressPicker(BuildContext context) {
    if (title.value.text.isEmpty) {
      Utils.showSnackBar(
        'Warning',
        'Add title of your task',
        const Icon(FontAwesomeIcons.triangleExclamation,
            color: Colors.pinkAccent),
      );
      return;
    }
    if (category.value.text.isEmpty) {
      Utils.showSnackBar(
        'Warning',
        'Add category of your task',
        const Icon(FontAwesomeIcons.triangleExclamation,
            color: Colors.pinkAccent),
      );
      return;
    }
    if (date.value.isEmpty) {
      Utils.showSnackBar(
        'Warning',
        'Add date for your task',
        const Icon(FontAwesomeIcons.triangleExclamation,
            color: Colors.pinkAccent),
      );
      return;
    }
    if (int.parse(Utils.getDaysDifference(date.value)) < 0) {
      Utils.showSnackBar(
        'Warning',
        'Please select a correct date',
        const Icon(FontAwesomeIcons.triangleExclamation,
            color: Colors.pinkAccent),
      );
      return;
    }
    ProgressPicker(context);
  }

  // Date picker for tasks
  Future<void> pickDate(BuildContext context) async {
    var pickedDate = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime(2023),
      lastDate: DateTime(2025),
    );
    if (pickedDate != null) {
      date.value = DateFormat('yyyy-MM-dd').format(pickedDate);
    }
  }

  // Time picker for tasks
  Future<void> pickTime(BuildContext context) async {
    TimeOfDay? pickedTime =
        await showTimePicker(context: context, initialTime: TimeOfDay.now());
    if (pickedTime != null) {
      DateFormat dateFormat = DateFormat('hh:mm a');
      time.value = dateFormat
          .format(DateTime(0, 1, 1, pickedTime.hour, pickedTime.minute));
    }
  }

  // Focus methods
  void setTitleFocus() {
    titleFocus.value = true;
    categoryFocus.value = false;
    descriptionFocus.value = false;
  }

  void setCategoryFocus() {
    titleFocus.value = false;
    categoryFocus.value = true;
    descriptionFocus.value = false;
  }

  void setDescriptionFocus() {
    titleFocus.value = false;
    categoryFocus.value = false;
    descriptionFocus.value = true;
  }

  void setPriority(bool value) {
    lowPriority.value = value;
  }

  void setImage(int index) {
    selectedImageIndex.value = index;
  }

  void onTapOutside() {
    titleFocus.value = false;
    categoryFocus.value = false;
    descriptionFocus.value = false;
  }
}
