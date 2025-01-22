import 'package:flutter/material.dart';
import 'app_color.dart'; // Ensure this file contains the primaryColor definition.

class PeriorityContainer extends StatelessWidget {
  final VoidCallback onTap;
  final bool focus;
  final String type;

  const PeriorityContainer({
    Key? key,
    required this.onTap,
    required this.focus,
    required this.type,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 43,
        width: 73,
        margin: const EdgeInsets.only(top: 10),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          gradient: focus
              ? const LinearGradient(
                  colors: [Colors.purpleAccent, Colors.pinkAccent],
                )
              : null,
        ),
        child: Padding(
          padding: const EdgeInsets.all(3.0),
          child: Container(
            height: 40,
            width: 70,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              color: primaryColor, // Using the color from app_color.dart
            ),
            child: Text(
              type,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
