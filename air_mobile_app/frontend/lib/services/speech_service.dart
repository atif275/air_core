import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import '../models/chat_entry.dart';

class SpeechService {
  final stt.SpeechToText _speech = stt.SpeechToText();
  Timer? _silenceTimer;
  final List<ChatEntry> _currentSession = [];
  DateTime? _lastSpeechTime;
  bool _isInitialized = false;
  
  // Supported languages
  final Map<String, String> _supportedLocales = {
    'en': 'en-US',
    'ur': 'ur-PK',
  };

  Future<void> initialize() async {
    if (!_isInitialized) {
      _isInitialized = await _speech.initialize(
        onStatus: _handleStatus,
        onError: _handleError,
      );
    }
  }

  void _handleStatus(String status) {
    if (status == 'done') {
      _checkSilence();
    }
  }

  void _handleError(dynamic error) {
    print('Speech recognition error: $error');
  }

  void _checkSilence() {
    _silenceTimer?.cancel();
    _silenceTimer = Timer(const Duration(seconds: 3), () {
      if (_lastSpeechTime != null) {
        _saveCurrentSession();
      }
    });
  }

  Future<void> startListening(Function(String) onResult) async {
    if (!_isInitialized) await initialize();

    await _speech.listen(
      onResult: (result) {
        _lastSpeechTime = DateTime.now();
        String recognizedText = result.recognizedWords;
        
        if (recognizedText.isNotEmpty) {
          onResult(recognizedText);
          _currentSession.add(ChatEntry(
            text: recognizedText,
            timestamp: _lastSpeechTime!,
            isUserMessage: true,
            language: _detectLanguage(recognizedText),
          ));
        }
      },
      localeId: _supportedLocales['en'], // Default to English
      listenMode: stt.ListenMode.dictation,
      cancelOnError: false,
      partialResults: true,
    );
  }

  String _detectLanguage(String text) {
    // Enhanced language detection
    if (RegExp(r'[\u0600-\u06FF]').hasMatch(text)) {
      return 'ar'; // Arabic
    } else if (RegExp(r'[۰-۹آ-ی]').hasMatch(text)) {
      return 'ur'; // Urdu
    } else if (RegExp(r'[\u0900-\u097F]').hasMatch(text)) {
      return 'hi'; // Hindi
    }
    return 'en'; // Default to English
  }

  Future<void> _saveCurrentSession() async {
    if (_currentSession.isEmpty) return;

    final directory = await getApplicationDocumentsDirectory();
    final file = File('${directory.path}/chat_sessions.json');
    
    List<Map<String, dynamic>> existingSessions = [];
    if (await file.exists()) {
      final content = await file.readAsString();
      existingSessions = List<Map<String, dynamic>>.from(jsonDecode(content));
    }

    existingSessions.addAll(_currentSession.map((entry) => entry.toJson()));
    await file.writeAsString(jsonEncode(existingSessions));
    
    _currentSession.clear();
  }

  Future<void> stopListening() async {
    await _speech.stop();
    _checkSilence();
  }

  void dispose() {
    _silenceTimer?.cancel();
    _speech.cancel();
  }
} 