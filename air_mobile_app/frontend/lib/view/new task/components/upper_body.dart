import 'package:flutter/material.dart';

class UpperBody extends StatelessWidget {
  const UpperBody({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(
          height: 20,
        ),
        Align(
          alignment: Alignment.topCenter,
          child: Container(
            height: 3,
            width: 100,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              color: Colors.white12,
            ),
          ),
        ),
        const SizedBox(
          height: 20,
        ),
        
        const SizedBox(
          height: 10,
        ),
      ],
    );
  }
}
