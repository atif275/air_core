import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

class SearchField extends StatefulWidget {
  final ValueChanged<String> onChanged; // Callback for search input
  const SearchField({Key? key, required this.onChanged}) : super(key: key);

  @override
  State<SearchField> createState() => _SearchFieldState();
}

class _SearchFieldState extends State<SearchField> {
  final TextEditingController _searchController = TextEditingController();
  bool _isFocused = false;
  bool _hasText = false;

  void _onClear() {
    setState(() {
      _searchController.clear();
      _hasText = false;
      widget.onChanged('');
    });
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      duration: const Duration(milliseconds: 500),
      padding: const EdgeInsets.all(1),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(15),
        gradient: _isFocused
            ? const LinearGradient(
                colors: [
                  Colors.purpleAccent,
                  Colors.pinkAccent,
                ],
              )
            : null,
      ),
      child: TextFormField(
        controller: _searchController,
        onTap: () {
          setState(() {
            _isFocused = true;
          });
        },
        onTapOutside: (_) {
          setState(() {
            _isFocused = false;
          });
        },
        onChanged: (value) {
          setState(() {
            _hasText = value.isNotEmpty;
          });
          widget.onChanged(value);
        },
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w400,
        ),
        decoration: InputDecoration(
          filled: true,
          prefixIcon: Container(
            margin: const EdgeInsets.symmetric(horizontal: 10),
            padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 10),
            child: SvgPicture.asset(
              'assets/icons/search.svg', // Path to your search icon
              height: 20,
              width: 20,
              color: Colors.grey,
            ),
          ),
          suffixIcon: _hasText
              ? GestureDetector(
                  onTap: _onClear,
                  child: const Icon(
                    Icons.clear,
                    color: Colors.white70,
                  ),
                )
              : const SizedBox(),
          fillColor: Colors.blueGrey[800], // Background fill color
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(15),
            borderSide: BorderSide.none,
          ),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 30,
            vertical: 20,
          ),
          hintText: 'Search ...',
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
