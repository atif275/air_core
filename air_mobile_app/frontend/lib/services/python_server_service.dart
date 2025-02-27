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

      if (response.statusCode == 200) {
        final jsonResponse = jsonDecode(response.body);
        final responseText = jsonResponse['response'];
        
        print('\n=== Python Server Response ===');
        print('Status: ${jsonResponse['status']}');
        print('Request: $text\n');
        
        // Extract user info and bot response
        if (responseText.contains('NAME=')) {
          // If response contains user info, it comes first
          final userInfoEnd = responseText.indexOf('\n\n');
          if (userInfoEnd != -1) {
            print('User Info:');
            print(responseText.substring(0, userInfoEnd).trim().split('\n').map((line) => '  $line').join('\n'));
            print('\nBot Response:');
            print('  ${responseText.substring(userInfoEnd + 2).trim()}');
          }
        } else {
          // If no user info, just print bot response
          print('Bot Response:');
          print('  $responseText');
        }
      } else {
        print('\n=== Error ===');
        print('Status Code: ${response.statusCode}');
      }
      
      return response.statusCode == 200;
    } catch (e) {
      print('\nServer Error: $e');
      return false;
    }
  }
} 