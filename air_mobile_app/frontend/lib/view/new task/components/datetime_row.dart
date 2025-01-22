import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:get/get.dart';
import 'date_time_container.dart';

class DateTimeRow extends StatelessWidget {
  final RxString date = ''.obs; // Reactive variable for date
  final RxString time = ''.obs; // Reactive variable for time

  DateTimeRow({Key? key}) : super(key: key);

  Future<void> pickDate(BuildContext context) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );

    if (picked != null) {
      date.value = "${picked.day}/${picked.month}/${picked.year}";
    }
  }

  Future<void> pickTime(BuildContext context) async {
    final picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.now(),
    );

    if (picked != null) {
      time.value = "${picked.hour}:${picked.minute}";
    }
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceAround,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Date',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 17,
              ),
            ),
            const SizedBox(height: 10),
            Obx(
              () => DateTimeContainer(
                text: date.value.isEmpty ? 'dd/mm/yyyy' : date.value,
                icon: const Icon(
                  FontAwesomeIcons.calendar,
                  color: Colors.white24,
                  size: 20,
                ),
                onTap: () => pickDate(context),
              ),
            ),
          ],
        ),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            RichText(
              text: const TextSpan(
                children: [
                  TextSpan(
                    text: 'Time',
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 17,
                    ),
                  ),
                  TextSpan(
                    text: '   (optional)',
                    style: TextStyle(
                      color: Colors.white30,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 10),
            Obx(
              () => DateTimeContainer(
                text: time.value.isEmpty ? 'hh:mm' : time.value,
                icon: const Icon(
                  Icons.watch,
                  color: Colors.white24,
                  size: 20,
                ),
                onTap: () => pickTime(context),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
