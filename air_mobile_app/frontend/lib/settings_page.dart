import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:get/get.dart';
import 'package:air/view model/controller/voice_assistant_controller.dart';
import 'logs_manager.dart';
import 'package:air/pages/pc_integration_page.dart';
import 'package:shared_preferences/shared_preferences.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({Key? key}) : super(key: key);

  @override
  _SettingsPageState createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  final VoiceAssistantController _voiceController = Get.find();
  bool pcIntegrationEnabled = false;
  bool whatsappAccess = false;
  bool instagramAccess = false;
  bool twitterAccess = false;
  bool emailAutomationEnabled = false;
  bool faceRecognitionEnabled = true;
  bool privacyControlsEnabled = true;
  final _prefs = SharedPreferences.getInstance();

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await _prefs;
    setState(() {
      pcIntegrationEnabled = prefs.getBool('pc_integration_enabled') ?? false;
    });
  }

  Future<void> _togglePCIntegration(bool value) async {
    final prefs = await _prefs;
    setState(() {
      pcIntegrationEnabled = value;
    });
    await prefs.setBool('pc_integration_enabled', value);

    if (value && mounted) {
      // Navigate to PC Integration page when enabled
      Navigator.push(
        context,
        MaterialPageRoute(builder: (context) => const PCIntegrationPage()),
      ).then((_) {
        // When returning from PC Integration page, check if we should disable the toggle
        if (!pcIntegrationEnabled) {
          setState(() {});
        }
      });
    }
  }

  void _logFeatureToggle(String featureName, bool value) {
    LogsManager.addLog(
      message: "$featureName ${(value ? 'enabled' : 'disabled')}",
      source: "User",
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: ListView(
        children: [
          const Padding(
            padding: EdgeInsets.all(8.0),
            child: Text(
              "Voice Assistant Settings",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
          ),
          Obx(() => SwitchListTile(
            title: const Text("English Translation"),
            subtitle: const Text("Convert all speech to English automatically"),
            value: _voiceController.isEnglishTranslationEnabled.value,
            onChanged: (value) {
              _voiceController.isEnglishTranslationEnabled.value = value;
              if (value) {
                _voiceController.isRomanizationEnabled.value = false;
              }
              _logFeatureToggle("English Translation", value);
            },
            secondary: const Icon(Icons.translate),
          )),

          Obx(() => SwitchListTile(
            title: const Text("Romanize Text"),
            subtitle: const Text("Convert non-English text to Roman script"),
            value: _voiceController.isRomanizationEnabled.value,
            onChanged: _voiceController.canEnableRomanization 
              ? (value) {
                  _voiceController.isRomanizationEnabled.value = value;
                  _logFeatureToggle("Text Romanization", value);
                }
              : null,
            secondary: const Icon(Icons.text_format),
          )),

          const Divider(),

          // PC Integration
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Text(
              'PC Integration',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Colors.grey,
              ),
            ),
          ),
          SwitchListTile(
            title: const Text('Enable PC Integration'),
            subtitle: const Text('Connect and control AIR from your computer'),
            value: pcIntegrationEnabled,
            onChanged: _togglePCIntegration,
            secondary: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Theme.of(context).primaryColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                Icons.computer,
                color: Theme.of(context).primaryColor,
              ),
            ),
          ),
          if (pcIntegrationEnabled)
            ListTile(
              leading: const SizedBox(width: 40),
              title: TextButton(
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => const PCIntegrationPage(),
                    ),
                  );
                },
                child: const Text('Open PC Integration Settings'),
              ),
            ),

          const Divider(),

          // Social Media Access
          const Padding(
            padding: EdgeInsets.all(8.0),
            child: Text(
              "Social Media Access",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
          ),
          SwitchListTile(
            title: const Text("WhatsApp"),
            value: whatsappAccess,
            onChanged: (value) {
              setState(() {
                whatsappAccess = value;
              });
              _logFeatureToggle("WhatsApp Access", value);
            },
            secondary: const FaIcon(FontAwesomeIcons.whatsapp, color: Colors.green),
          ),
          SwitchListTile(
            title: const Text("Instagram"),
            value: instagramAccess,
            onChanged: (value) {
              setState(() {
                instagramAccess = value;
              });
              _logFeatureToggle("Instagram Access", value);
            },
            secondary: const FaIcon(FontAwesomeIcons.instagram, color: Colors.pink),
          ),
          SwitchListTile(
            title: const Text("Twitter"),
            value: twitterAccess,
            onChanged: (value) {
              setState(() {
                twitterAccess = value;
              });
              _logFeatureToggle("Twitter Access", value);
            },
            secondary: const FaIcon(FontAwesomeIcons.twitter, color: Colors.blue),
          ),

          const Divider(),

          // Email Integration
          SwitchListTile(
            title: const Text("Email Automation"),
            subtitle: const Text("Allow AIR App to manage your emails."),
            value: emailAutomationEnabled,
            onChanged: (value) {
              setState(() {
                emailAutomationEnabled = value;
              });
              _logFeatureToggle("Email Automation", value);
            },
            secondary: const Icon(Icons.email),
          ),

          const Divider(),

          // Face Recognition
          SwitchListTile(
            title: const Text("Face Recognition"),
            subtitle: const Text("Enable face recognition and registration."),
            value: faceRecognitionEnabled,
            onChanged: (value) {
              setState(() {
                faceRecognitionEnabled = value;
              });
              _logFeatureToggle("Face Recognition", value);
            },
            secondary: const Icon(Icons.face),
          ),

          const Divider(),

          // Security Settings
          SwitchListTile(
            title: const Text("Privacy Controls"),
            subtitle: const Text("Admin-only health info and privacy settings."),
            value: privacyControlsEnabled,
            onChanged: (value) {
              setState(() {
                privacyControlsEnabled = value;
              });
              _logFeatureToggle("Privacy Controls", value);
            },
            secondary: const Icon(Icons.security),
          ),

          Obx(() => SwitchListTile(
            title: const Text("Real-time Transcription"),
            subtitle: const Text("Transcribe speech in real-time without stopping"),
            value: _voiceController.isRealtimeTranscriptionEnabled.value,
            onChanged: (value) {
              _voiceController.isRealtimeTranscriptionEnabled.value = value;
              _logFeatureToggle("Real-time Transcription", value);
            },
            secondary: const Icon(Icons.speed),
          )),
        ],
      ),
    );
  }
}
