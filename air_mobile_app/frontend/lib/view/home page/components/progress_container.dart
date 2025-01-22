import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:get/get.dart'; // Assuming GetX is used for state management.
import 'package:air/view%20model/controller/home_controller.dart'; // Adjust the import to your project structure.

class ProgressContainer extends StatelessWidget {
  final Map<String, dynamic> taskData;
  final int taskIndex;

  const ProgressContainer({Key? key, required this.taskData, required this.taskIndex}) : super(key: key);


  @override
  Widget build(BuildContext context) {
    final controller = Get.find<HomeController>(); // Accessing the controller.

    return Container(
      height: 200,
      width: 160,
      margin: const EdgeInsets.only(left: 20),
      child: Stack(
        children: [
          // Background image
          Positioned.fill(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(20),
              child: Container(
                decoration: BoxDecoration(
                  image: DecorationImage(
                    image: AssetImage(taskData["image"] ?? 'assets/images/task3.jpg'),
                    fit: BoxFit.cover,
                  ),
                ),
              ),
            ),
          ),

          // Blurred overlay
          Positioned(
            height: 150,
            width: 150,
            top: 1,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(20),
              child: BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 1, sigmaY: 1),
                child: const SizedBox(),
              ),
            ),
          ),

          // Content
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      taskData["date"],
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                    SizedBox(
                      height: 15,
                      width: 20,
                      child: PopupMenuButton(
                        padding: EdgeInsets.zero,
                        color: Colors.black,
                        position: PopupMenuPosition.under,
                        
                        onSelected: (value) {
                          if (taskIndex >= 0 && taskIndex < controller.taskList.length) {
                            controller.handlePopupAction(value, taskIndex, context);
                          }
                        },
                        
                        icon: const Icon(
                          Icons.more_vert_rounded,
                          color: Colors.white,
                          size: 20,
                        ),
                        itemBuilder: (context) => [
                          const PopupMenuItem(
                            value: 1,
                            child: Row(
                              children: [
                                Icon(Icons.edit, color: Colors.pinkAccent),
                                SizedBox(width: 5),
                                Text(
                                  "Edit",
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const PopupMenuItem(
                            value: 2,
                            child: Row(
                              children: [
                                Icon(Icons.delete_outline,
                                    color: Colors.pinkAccent),
                                SizedBox(width: 5),
                                Text(
                                  "Delete",
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                Text(
                  taskData["title"] ?? "No Title",
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 17,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  taskData["category"] ?? "Uncategorized",
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 10),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'Progress',
                      style: TextStyle(
                        color: Colors.white70,
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                    Text(
                      '${(taskData["progress"] ?? 0).toInt()}%',
                      style: const TextStyle(
                        color: Colors.white70,
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                ClipRRect(
                  borderRadius: BorderRadius.circular(10),
                  child: LinearProgressIndicator(
                    value: taskData["progress"]/100.0, // This remains as a fraction (0.0 to 1.0)
                    backgroundColor: Colors.deepPurple,
                    color: const Color.fromARGB(255, 255, 255, 255),
                  ),
                ),
                const Spacer(),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      alignment: Alignment.center,
                      height: 30,
                      width: 100,
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        '${taskData["daysLeft"] ?? "N/A"} Days Left',
                        style: const TextStyle(
                          color: Colors.black,
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
