import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'dart:convert';

class PythonServerService {
  final String baseUrl = dotenv.env['PYTHON_SERVER_URL'] ?? 'http://localhost:5000';

  Future<bool> sendTranscribedText(String text) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/transcription'),
        headers: {
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'text': text,
          'timestamp': DateTime.now().toIso8601String(),
        }),
      );

      print('Python server response: ${response.body}');
      return response.statusCode == 200;
    } catch (e) {
      print('Error sending to Python server: $e');
      return false;
    }
  }
} 