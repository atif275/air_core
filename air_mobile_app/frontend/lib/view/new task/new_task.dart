import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'components/addtask_body.dart';
import 'package:air/res/app_color.dart'; // Import your app color file
import 'package:air/services/task_api_service.dart';

class NewTask {
  NewTask(BuildContext context, VoidCallback onTaskAdded) {
    Get.bottomSheet(
      AddTaskBody(onTaskAdded: onTaskAdded), // Pass callback to AddTaskBody
      backgroundColor: primaryColor, // Use a color from `app_color.dart`
      isScrollControlled: true, // Allow full-screen scrolling
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
    );
  }
}

