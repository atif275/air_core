import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'image_container.dart';
import '../../../res/assets/app_images.dart';
import 'package:air/view%20model/controller/add_task_controller.dart';

class ImageContainerList extends StatelessWidget {
  ImageContainerList({Key? key}) : super(key: key);
  final controller = Get.put(AddTaskController());

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Obx(
          () => ImageContainer(
            onTap: () => controller.setImage(1),
            image: AppImage.back2,
            focus: controller.selectedImageIndex.value == 1,
          ),
        ),
        Obx(
          () => ImageContainer(
            onTap: () => controller.setImage(2),
            image: AppImage.back3,
            focus: controller.selectedImageIndex.value == 2,
          ),
        ),
        Obx(
          () => ImageContainer(
            onTap: () => controller.setImage(3),
            image: AppImage.back1,
            focus: controller.selectedImageIndex.value == 3,
          ),
        ),
      ],
    );
  }
}
