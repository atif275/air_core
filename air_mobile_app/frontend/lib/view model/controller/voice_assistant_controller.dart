import 'dart:io';
import 'package:get/get.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:air/services/speech_to_text_service.dart';
import 'package:air/services/text_to_speech_service.dart';
import 'package:air/services/openai_service.dart';
import 'package:air/services/whisper_service.dart';
import 'package:air/services/audio_recorder_service.dart';
import 'package:air/models/chat_entry.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:path_provider/path_provider.dart';
import 'dart:convert';
import 'package:air/services/transcription_service.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'dart:async';
import 'package:air/services/python_server_service.dart';


class VoiceAssistantController extends GetxController {
  final SpeechToTextService _speechService = SpeechToTextService();
  final TextToSpeechService _textToSpeechService = TextToSpeechService();
  final OpenAIService _openAIService = OpenAIService();
  final AudioRecorderService _audioRecorder = AudioRecorderService();
  late final WhisperService _whisperService;
  final PythonServerService _pythonServer = PythonServerService();

  // Observable variables
  final isListening = false.obs;
  final isSpeaking = false.obs;
  final userSpeech = ''.obs;
  final botResponse = ''.obs;
  final isInitialized = false.obs;
  final isEnglishTranslationEnabled = true.obs;
  final isRomanizationEnabled = false.obs;
  final isRealtimeTranscriptionEnabled = false.obs;

  Timer? _transcriptionTimer;

  // Add dependency check
  bool get canEnableRomanization => !isEnglishTranslationEnabled.value;

  @override
  void onInit() {
    super.onInit();
    _initializeServices();
    _whisperService = WhisperService(
      apiKey: dotenv.env['OPENAI_API_KEY'] ?? '',
    );
  }

  Future<void> _initializeServices() async {
    try {
      bool initialized = await _speechService.initSpeech();
      isInitialized.value = initialized;
      print("Speech service initialized: $initialized");
    } catch (e) {
      print("Error initializing speech service: $e");
      isInitialized.value = false;
    }
  }

  Future<void> startListening() async {
    try {
      if (!isInitialized.value) {
        await _initializeServices();
      }

      isListening.value = true;
      userSpeech.value = '';
      
      if (isRealtimeTranscriptionEnabled.value) {
        await _audioRecorder.startRecording(onSilence: () async {
          final audioPath = await _audioRecorder.stopRecording();
          if (audioPath != null) {
            final transcription = await _whisperService.transcribeAudio(
              audioPath,
              translateToEnglish: isEnglishTranslationEnabled.value,
              romanizeText: !isEnglishTranslationEnabled.value && isRomanizationEnabled.value
            );
            if (transcription.isNotEmpty) {
              userSpeech.value = transcription;
              await processUserSpeech(transcription);
              await _audioRecorder.startRecording(onSilence: () {});
            }
          }
        });
      } else {
        await _audioRecorder.startRecording();
      }
    } catch (e) {
      print("Error in startListening: $e");
      isListening.value = false;
    }
  }

  Future<void> stopListening() async {
    try {
      _transcriptionTimer?.cancel();
      isListening.value = false;
      final audioPath = await _audioRecorder.stopRecording();
      
      if (audioPath != null && !isRealtimeTranscriptionEnabled.value) {
        final transcription = await _whisperService.transcribeAudio(
          audioPath,
          translateToEnglish: isEnglishTranslationEnabled.value,
          romanizeText: !isEnglishTranslationEnabled.value && isRomanizationEnabled.value
        );
        userSpeech.value = transcription;
        await processUserSpeech(transcription);
      }
      
      await File(audioPath ?? '').delete();
    } catch (e) {
      print("Error stopping listening: $e");
    }
  }

  Future<void> processUserSpeech(String userInput) async {
    if (userInput.isEmpty) return;

    try {
      final language = _detectLanguage(userInput);
      print("Detected Language: $language");
      
      if (!isEnglishTranslationEnabled.value) {
        // Keep original text
        print("Original Text: $userInput");
        await TranscriptionService.saveTranscription(userInput, language);
      } else {
        // Use Whisper's English translation
        print("Translated Text: $userInput");
        await TranscriptionService.saveTranscription(userInput, 'en');
      }
    } catch (e) {
      print("Error processing speech: $e");
    }
  }

  String _detectLanguage(String text) {
    // Urdu specific characters and patterns
    if (RegExp(r'[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]').hasMatch(text) &&
        RegExp(r'[ں|ہ|ے|ۓ|ؤ|ئ]').hasMatch(text)) {
      return 'ur';
    }
    // Arabic specific characters
    else if (RegExp(r'[\u0600-\u06FF]').hasMatch(text) &&
             !RegExp(r'[ں|ہ|ے|ۓ|ؤ|ئ]').hasMatch(text)) {
      return 'ar';
    }
    // Hindi specific characters
    else if (RegExp(r'[\u0900-\u097F]').hasMatch(text)) {
      return 'hi';
    }
    return 'en';
  }

  void stopSpeaking() async {
    if (isSpeaking.value) {
      await _textToSpeechService.stop();
      isSpeaking.value = false;
    }
  }

  @override
  void onClose() {
    _transcriptionTimer?.cancel();
    _audioRecorder.dispose();
    _speechService.onClose();
    stopSpeaking();
    super.onClose();
  }

  Future<List<ChatEntry>> getChatHistory() async {
    try {
      final directory = await getApplicationDocumentsDirectory();
      final file = File('${directory.path}/chat_sessions.json');
      
      if (!await file.exists()) {
        return [];
      }

      final content = await file.readAsString();
      final List<dynamic> jsonList = jsonDecode(content);
      return jsonList.map((json) => ChatEntry.fromJson(json)).toList();
    } catch (e) {
      print("Error reading chat history: $e");
      return [];
    }
  }

  void toggleTranslation() {
    isEnglishTranslationEnabled.value = !isEnglishTranslationEnabled.value;
    print("Translation ${isEnglishTranslationEnabled.value ? 'enabled' : 'disabled'}");
  }

  Future<void> sendToPythonServer(String transcribedText) async {
    try {
      final success = await _pythonServer.sendTranscribedText(transcribedText);
      if (success) {
        print('Successfully sent to Python server');
      } else {
        print('Failed to send to Python server');
      }
    } catch (e) {
      print('Error in sendToPythonServer: $e');
    }
  }
}
