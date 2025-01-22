import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'progress_container.dart';
import 'package:air/view%20model/controller/home_controller.dart';

class ProgressTask extends StatelessWidget {
  ProgressTask({Key? key}) : super(key: key) {
    _fetchTasks();
  }

  final HomeController controller = Get.find(); // Access the HomeController instance

  void _fetchTasks() async {
    await controller.fetchTasks();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 200,
      child: Obx(() => ListView.builder(
            scrollDirection: Axis.horizontal,
            itemCount: controller.taskList.length,
            itemBuilder: (context, index) {
              final task = controller.taskList[index]; // Use taskList from the controller
              return ProgressContainer(
                taskData: task,
                taskIndex: index,
              );
            },
          )),
    );
  }
}
