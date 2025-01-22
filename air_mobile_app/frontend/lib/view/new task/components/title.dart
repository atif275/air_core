import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'periority_container.dart';
import 'add_fild.dart'; // Reference to AddInputField

class TitlePeriority extends StatelessWidget {
  final TextEditingController titleController = TextEditingController();
  final RxBool isTitleFocused = false.obs;
  final RxBool isLowPriority = true.obs;

  TitlePeriority({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Title',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 17,
              ),
            ),
            const SizedBox(height: 10),
            Obx(
              () => AddInputField(
                focus: isTitleFocused.value,
                onTap: () {
                  isTitleFocused.value = true;
                },
                onTapOutSide: () {
                  isTitleFocused.value = false;
                  FocusScope.of(context).unfocus();
                },
                hint: 'Enter task title',
                width: size.width / 2.2,
                controller: titleController,
              ),
            ),
          ],
        ),
        const SizedBox(width: 20),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Priority',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 17,
              ),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Obx(
                  () => PeriorityContainer(
                    onTap: () => isLowPriority.value = true,
                    focus: isLowPriority.value,
                    type: 'Low',
                  ),
                ),
                const SizedBox(width: 10),
                Obx(
                  () => PeriorityContainer(
                    onTap: () => isLowPriority.value = false,
                    focus: !isLowPriority.value,
                    type: 'High',
                  ),
                ),
              ],
            ),
          ],
        ),
      ],
    );
  }
}
