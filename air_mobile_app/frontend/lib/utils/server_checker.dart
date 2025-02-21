import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';

class ServerChecker {
  static Future<bool> isServerRunning() async {
    try {
      final baseUrl = dotenv.env['API_URL'] ?? 'http://localhost:5001';
      print('Checking server at: $baseUrl/tasks');
      
      final response = await http.get(
        Uri.parse('$baseUrl/tasks'),
        headers: {'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 5));
      
      print('Server response status: ${response.statusCode}');
      print('Server response body: ${response.body}');
      
      return response.statusCode == 200;
    } catch (e) {
      print('Server check error: $e');
      return false;
    }
  }
} 