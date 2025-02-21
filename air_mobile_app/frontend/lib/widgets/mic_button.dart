import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:air/view model/controller/voice_assistant_controller.dart';
import 'package:permission_handler/permission_handler.dart';

class MicButton extends StatefulWidget {
  const MicButton({Key? key}) : super(key: key);

  @override
  State<MicButton> createState() => _MicButtonState();
}

class _MicButtonState extends State<MicButton> {
  final VoiceAssistantController _voiceController = Get.find();
  
  @override
  Widget build(BuildContext context) {
    return IconButton(
      icon: Obx(() => Icon(
        _voiceController.isListening.value ? Icons.mic : Icons.mic_none,
      )),
      onPressed: () async {
        if (_voiceController.isListening.value) {
          await _voiceController.stopListening();
        } else {
          final status = await Permission.microphone.status;
          if (status.isDenied) {
            // Show dialog explaining why we need microphone access
            await showDialog(
              context: context,
              builder: (context) => AlertDialog(
                title: const Text('Microphone Permission'),
                content: const Text('We need microphone access for voice commands. Please grant permission in settings.'),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Cancel'),
                  ),
                  TextButton(
                    onPressed: () async {
                      Navigator.pop(context);
                      await _voiceController.startListening();
                    },
                    child: const Text('Continue'),
                  ),
                ],
              ),
            );
          } else {
            await _voiceController.startListening();
          }
        }
      },
    );
  }
} 