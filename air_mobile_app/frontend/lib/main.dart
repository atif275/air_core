import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import 'package:model_viewer_plus/model_viewer_plus.dart';
import 'settings_page.dart'; // Import the SettingsPage file
import 'logs.dart'; // Import the LogsPage file
import 'logs_manager.dart'; // Import LogsManager for logging functionality
import 'chat_page.dart'; // Import the ChatPage file
import 'package:air/view/home page/home_page.dart';
import 'package:air/services/task_api_service.dart'; // Import backend API service
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:air/view%20model/controller/voice_assistant_controller.dart';
import 'package:air/widgets/speech_bubble.dart';  // Add this import
import 'package:air/utils/server_checker.dart';
import 'package:air/widgets/error_dialog.dart';
import 'package:model_viewer_plus/src/model_viewer_plus.dart' show Loading, TouchAction, InteractionPrompt;
import 'package:air/services/transcription_service.dart';

//import 'home_page.dart';
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load();
  runApp(const AirApp());
}

class AirApp extends StatefulWidget {
  const AirApp({Key? key}) : super(key: key);

  @override
  _AirAppState createState() => _AirAppState();
}

class _AirAppState extends State<AirApp> {
  bool isDarkMode = true; // Default to dark mode

  void toggleThemeMode() {
    setState(() {
      isDarkMode = !isDarkMode;
    });
  }

  @override
  Widget build(BuildContext context) {
    return GetMaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'AIR App',
      theme: ThemeData.light(), // Light theme
      darkTheme: ThemeData.dark(), // Dark theme
      //home: const TasksHomePage(), // Entry point
      themeMode: isDarkMode ? ThemeMode.dark : ThemeMode.light, // Control theme dynamically
      home: HomePage(
        toggleThemeMode: toggleThemeMode, 
        isDarkMode: isDarkMode,
      ),
    ); 
  }
}

class HomePage extends StatefulWidget {
  final VoidCallback toggleThemeMode; // Function to toggle theme mode
  final bool isDarkMode; // Current theme mode

  const HomePage({Key? key, required this.toggleThemeMode, required this.isDarkMode}) : super(key: key);

  @override
  _HomePageState createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  String cameraOrbit = "-90deg 90deg auto"; // Default position
  bool isResetting = false; // Prevent multiple resets
  bool isLoading = true; // Tracks whether the model is loading
  bool isMuted = true; // Tracks mute/unmute state
  final VoiceAssistantController _voiceController = Get.put(VoiceAssistantController());

  String status = "Loading AIR..."; // Default status text

  @override
  void initState() {
    super.initState();
    _simulateModelLoading();
  }

  void _simulateModelLoading() async {
    // Simulate a loading delay for the 3D model
    await Future.delayed(const Duration(seconds: 4)); // Adjust delay as necessary
    setState(() {
      isLoading = false;
      status = "Status: Ready to Help!"; // Update status text
      LogsManager.addLog(message: "AIR is ready to help!", source: "System");
    });
  }

  void _resetHeadPosition() {
    if (isResetting) {
      print("Reset already in progress.");
      return;
    }

    setState(() {
      isResetting = true;
    });

    print("Resetting robot head orientation...");
    LogsManager.addLog(message: "Robot head reset to initial position", source: "User");

    Future.delayed(const Duration(milliseconds: 300), () {
      setState(() {
        isResetting = false;
        print("Robot head reset to front-facing orientation.");
      });
    });
  }

  void navigateToTaskManagement(BuildContext context) async {
    try {
      bool isServerRunning = await ServerChecker.isServerRunning();
      
      if (!isServerRunning) {
        if (context.mounted) {
          await ErrorDialog.show(context);
        }
        return;
      }
      
      if (context.mounted) {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (context) => TasksHomePage()),
        );
      }
    } catch (e) {
      print('Navigation error: $e');
      if (context.mounted) {
        await ErrorDialog.show(context);
      }
    }
  }

  Widget _buildRoundButton({
    required IconData icon,
    required String tooltip,
    required VoidCallback onPressed,
    Color? iconColor,
  }) {
    return SizedBox(
      width: 60, // Fixed width
      height: 60, // Fixed height
      child: GestureDetector(
        onTap: onPressed,
        child: CircleAvatar(
          radius: 30,
          backgroundColor: Colors.blueGrey[800],
          child: Icon(
            icon,
            size: 28,
            color: iconColor ?? Colors.white,
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AIR Home'),
        leading: IconButton(
          icon: const Icon(Icons.settings),
          tooltip: "Settings",
          onPressed: () {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (context) => const SettingsPage()),
            );
            LogsManager.addLog(message: "Opened Settings Page", source: "User");
          },
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 8.0),
            child: IconButton(
              icon: Icon(
                widget.isDarkMode ? Icons.dark_mode : Icons.light_mode,
                color: widget.isDarkMode ? Colors.white : Colors.black,
              ),
              onPressed: () {
                widget.toggleThemeMode();
                LogsManager.addLog(
                  message: widget.isDarkMode
                      ? "Switched to Dark Mode"
                      : "Switched to Light Mode",
                  source: "User",
                );
              },
              tooltip: widget.isDarkMode ? "Switch to Light Mode" : "Switch to Dark Mode",
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          // 3D Robot Head and Reset Button
          Padding(
            padding: const EdgeInsets.only(top: 8.0), // Reduced top padding
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start, // Align elements to the left
              children: [
                // 3D Model Viewer with Loading State
                SizedBox(
                  height: 400,
                  child: Stack(
                    children: [
                      if (isLoading)
                        const Center(
                          child: SpinKitCircle(
                            color: Colors.white,
                            size: 50.0,
                          ),
                        ),
                      Opacity(
                        opacity: isLoading ? 0.0 : 1.0,
                        child: ModelViewer(
                          key: ValueKey(cameraOrbit),
                          src: 'assets/Air3.glb',
                          alt: "A 3D model of the AIR robot head",
                          autoRotate: false,
                          cameraControls: true,
                          cameraOrbit: cameraOrbit,
                          loading: Loading.eager,
                          ar: false,
                          exposure: 1.0,
                          shadowIntensity: 0,
                          backgroundColor: Colors.transparent,
                          disableZoom: true,
                          disablePan: true,
                          touchAction: TouchAction.panY,
                          minCameraOrbit: "auto auto auto",
                          maxCameraOrbit: "auto auto auto",
                          onWebViewCreated: (controller) {
                            print("WebView Created Successfully");
                            Future.delayed(Duration(milliseconds: 500), () {
                              setState(() {
                                isLoading = false;
                              });
                            });
                          },
                        ),
                      ),

                      // Add speech bubble overlay here
                      Obx(() => _voiceController.isListening.value
                        ? Positioned(
                            bottom: 100,
                            left: 20,
                            right: 20,
                            child: SpeechBubble(
                              text: _voiceController.userSpeech.value.isEmpty 
                                  ? "Listening..." 
                                  : _voiceController.userSpeech.value,
                            ),
                          )
                        : const SizedBox(),
                      ),
                    ],
                  ),
                ),

                // Reset Button Below 3D Model
                Padding(
                  padding: const EdgeInsets.only(left: 16.0, top: 0.0),
                  child: IconButton(
                    onPressed: _resetHeadPosition,
                    icon: Icon(Icons.refresh, color: Colors.white, size: 28),
                    tooltip: "Reset Head Orientation",
                  ),
                ),
              ],
            ),
          ),

          // Status Indicator
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8.0),
            child: Text(
              status,
              style: TextStyle(
                fontSize: 16,
                color: widget.isDarkMode ? Colors.white70 : Colors.black87, // Dynamic text color
              ),
            ),
          ),

          const SizedBox(height: 8), // Adjusted space above first row

          // First Row Buttons
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween, // Align buttons to the left, middle, and right
          children: [
            Padding(
              padding: const EdgeInsets.only(left: 24.0), // Add padding for left alignment
              child: _buildRoundButton(
                icon: Icons.list_alt,
                tooltip: "Logs",
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => LogsPage()),
                  );
                  LogsManager.addLog(message: "Opened Logs Page", source: "User");
                },
              ),
            ),
            IconButton(
              icon: Icon(
                isMuted ? Icons.mic_off : Icons.mic,
                size: 30,
                color: isMuted
                    ? Colors.red
                    : (widget.isDarkMode ? Colors.white : Colors.black),
              ),
              onPressed: () async {
                if (_voiceController.isListening.value) {
                  await _voiceController.stopListening();
                  setState(() {
                    isMuted = true;
                  });
                } else {
                  await _voiceController.startListening();
                  setState(() {
                    isMuted = false;
                  });
                }
                LogsManager.addLog(
                  message: isMuted ? "Voice Assistant Muted" : "Voice Assistant Activated",
                  source: "User"
                );
              },
            ),

            Padding(
              padding: const EdgeInsets.only(right: 24.0), // Add padding for right alignment
              child: _buildRoundButton(
                icon: Icons.keyboard,
                tooltip: "Text Chat",
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => const ChatPage()),
                  );
                  LogsManager.addLog(message: "Opened Text Chat", source: "User");
                },
              ),
            ),
          ],
        ),

          const SizedBox(height: 8), // Reduced space between rows

          // Second Row Buttons
          // Second Row Buttons
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween, // Align to the left and right
            children: [
              Padding(
                padding: const EdgeInsets.only(left: 24.0), // Add padding for left alignment
                child: _buildRoundButton(
                  icon: Icons.check_circle,
                  tooltip: "Tasks",
                  onPressed: () => navigateToTaskManagement(context),
                ),
              ),
              Padding(
                padding: const EdgeInsets.only(right: 24.0), // Add padding for right alignment
                child: _buildRoundButton(
                  icon: Icons.health_and_safety,
                  tooltip: "Health",
                  onPressed: () {
                    LogsManager.addLog(message: "Opened Health Page", source: "User");
                  },
                ),
              ),
            ],
          ),

          const SizedBox(height: 8), // Space between second and third rows

          // Third Row Buttons
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween, // Align to the left and right
            children: [
              Padding(
                padding: const EdgeInsets.only(left: 24.0), // Add padding for left alignment
                child: _buildRoundButton(
                  icon: Icons.calendar_today,
                  tooltip: "Calendar",
                  onPressed: () {
                    LogsManager.addLog(message: "Opened Calendar Page", source: "User");
                  },
                ),
              ),
              Padding(
                padding: const EdgeInsets.only(right: 24.0), // Add padding for right alignment
                child: _buildRoundButton(
                  icon: Icons.person,
                  tooltip: "Profile",
                  onPressed: () {
                    LogsManager.addLog(message: "Opened Profile Page", source: "User");
                  },
                ),
              ),
            ],
          ),

        ],
      ),
    );
  }
}