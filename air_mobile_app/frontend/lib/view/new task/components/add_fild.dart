import 'package:flutter/material.dart';

const primaryColor = Color(0xff151414); // Primary color constant for the theme

class AddInputField extends StatelessWidget {
  final bool focus; // Determines if the field is focused
  final VoidCallback onTap; // Callback for field tap
  final VoidCallback onTapOutSide; // Callback for tap outside the field
  final String hint; // Hint text for the input field
  final double? width; // Width of the field
  final TextEditingController? controller; // Controller for the input field

  const AddInputField({
    Key? key,
    required this.focus,
    required this.onTap,
    required this.onTapOutSide,
    required this.hint,
    this.width,
    this.controller,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      width: width, // Set the width of the field
      duration: const Duration(milliseconds: 500), // Animation duration
      padding: const EdgeInsets.all(1), // Padding for the container
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(15), // Rounded corners
        gradient: focus // Apply gradient if focused
            ? const LinearGradient(
                colors: [
                  Colors.purpleAccent,
                  Colors.pink,
                ],
              )
            : null,
      ),
      child: TextFormField(
        controller: controller, // Assign controller
        onTap: onTap, // Tap callback
        onTapOutside: (event) {
          FocusScope.of(context).unfocus(); // Unfocus on outside tap
          onTapOutSide(); // Call outside tap callback
        },
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w400,
        ),
        decoration: InputDecoration(
          filled: true,
          fillColor: primaryColor, // Set background color
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(15), // Rounded border
            borderSide: BorderSide.none,
          ),
          hoverColor: Colors.pinkAccent, // Hover color
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 30,
            vertical: 20,
          ),
          hintText: hint, // Set hint text
          hintStyle: const TextStyle(
            color: Colors.grey,
            fontWeight: FontWeight.normal,
            fontSize: 12,
          ),
        ),
      ),
    );
  }
}
