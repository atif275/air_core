import 'package:flutter/material.dart';
import 'periority_container.dart';
import 'add_fild.dart'; // AddInputField module
import 'upper_body.dart'; // UpperBody module
import 'datetime_row.dart'; // DateTimeRow module
import 'image_container_list.dart'; // ImageContainerList module
import 'package:air/services/task_api_service.dart';
import 'package:get/get.dart';

class AddTaskBody extends StatefulWidget {
  final VoidCallback onTaskAdded;
  const AddTaskBody({Key? key, required this.onTaskAdded}) : super(key: key);

  @override
  State<AddTaskBody> createState() => _AddTaskBodyState();
}

class _AddTaskBodyState extends State<AddTaskBody> {
  final TextEditingController titleController = TextEditingController();
  final TextEditingController descriptionController = TextEditingController();
  final TaskApiService _taskApiService = TaskApiService();

  bool titleFocus = false;
  bool descriptionFocus = false;

  String selectedPriority = 'Low'; // Default priority
  void _clearFields() {
    titleController.clear();
    descriptionController.clear();
    setState(() {
      selectedPriority = 'Low';
    });
  }

  @override
  Widget build(BuildContext context) {
    var size = MediaQuery.of(context).size;

    return SingleChildScrollView(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 20),

            // Upper Body Section
            const UpperBody(),
            const SizedBox(height: 20),

            // Image Container List Section
            ImageContainerList(),
            const SizedBox(height: 20),

            // Title Section
            const Text(
              'Add New Task',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 20),

            const Text(
              'Title',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 10),
            AddInputField(
              controller: titleController,
              focus: titleFocus,
              onTap: () {
                setState(() {
                  titleFocus = true;
                });
              },
              onTapOutSide: () {
                setState(() {
                  titleFocus = false;
                });
              },
              hint: 'Enter task title',
              width: size.width,
            ),
            const SizedBox(height: 20),

            // Description Section
            const Text(
              'Description',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 10),
            AddInputField(
              controller: descriptionController,
              focus: descriptionFocus,
              onTap: () {
                setState(() {
                  descriptionFocus = true;
                });
              },
              onTapOutSide: () {
                setState(() {
                  descriptionFocus = false;
                });
              },
              hint: 'Enter task description',
              width: size.width,
            ),
            const SizedBox(height: 20),

            // Date and Time Section
            DateTimeRow(),
            const SizedBox(height: 20),

            // Priority Section
            const Text(
              'Priority',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 10),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                PeriorityContainer(
                  onTap: () {
                    setState(() {
                      selectedPriority = 'Low';
                    });
                  },
                  focus: selectedPriority == 'Low',
                  type: 'Low',
                ),
                PeriorityContainer(
                  onTap: () {
                    setState(() {
                      selectedPriority = 'Medium';
                    });
                  },
                  focus: selectedPriority == 'Medium',
                  type: 'Medium',
                ),
                PeriorityContainer(
                  onTap: () {
                    setState(() {
                      selectedPriority = 'High';
                    });
                  },
                  focus: selectedPriority == 'High',
                  type: 'High',
                ),
              ],
            ),
            const SizedBox(height: 30),

            // Submit Button
            Center(
              child: ElevatedButton(
                onPressed: () async {
                  if (titleController.text.isEmpty ||
                      descriptionController.text.isEmpty) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text("Please fill in all fields"),
                        backgroundColor: Colors.red,
                      ),
                    );
                    return;
                  }

                  final newTask = {
                    "title": titleController.text,
                    "description": descriptionController.text,
                    "category": "General",
                    "priority": selectedPriority,
                    "progress": 0,
                    "date": DateTime.now().toString(),
                    "time": TimeOfDay.now().format(context),
                    "image": "assets/images/task3.jpg",
                    "status": "Pending",
                  };

                  try {
                    bool success = await _taskApiService.createTask(newTask);
                    if (success) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text("Task added successfully"),
                          backgroundColor: Colors.green,
                        ),
                      );
                      // Clear the input fields after successful submission
                      _clearFields();
                    }
                  } catch (e) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text("Error: ${e.toString()}"),
                        backgroundColor: Colors.red,
                      ),
                    );
                  }finally{
                    Get.back();
                  }
                },
                style: ElevatedButton.styleFrom(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 50, vertical: 15),
                  backgroundColor: Colors.pinkAccent,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: const Text(
                  'Add Task',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
