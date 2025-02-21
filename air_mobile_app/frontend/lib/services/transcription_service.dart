import 'dart:convert';
import 'dart:io';
import 'package:path_provider/path_provider.dart';

class TranscriptionService {
  static const String fileName = 'transcriptions.json';
  
  static Future<void> saveTranscription(String text, String detectedLanguage) async {
    try {
      final directory = await getApplicationDocumentsDirectory();
      final file = File('${directory.path}/transcriptions.json');
      List<Map<String, dynamic>> transcriptions = [];

      if (await file.exists()) {
        final content = await file.readAsString();
        transcriptions = List<Map<String, dynamic>>.from(jsonDecode(content));
      }

      transcriptions.add({
        'text': text,
        'language': detectedLanguage,
        'timestamp': DateTime.now().toIso8601String(),
      });

      const JsonEncoder encoder = JsonEncoder.withIndent('  ');
      await file.writeAsString(encoder.convert(transcriptions));
      print('Transcription saved to: ${file.path}');
    } catch (e) {
      print('Error saving transcription: $e');
    }
  }

  static Future<List<Map<String, dynamic>>> getTranscriptions() async {
    try {
      final directory = await getApplicationDocumentsDirectory();
      final file = File('${directory.path}/transcriptions/$fileName');
      
      if (!await file.exists()) {
        return [];
      }

      final content = await file.readAsString();
      return List<Map<String, dynamic>>.from(jsonDecode(content));
    } catch (e) {
      print('Error reading transcriptions: $e');
      return [];
    }
  }
} 