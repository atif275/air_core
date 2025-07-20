import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import 'package:model_viewer_plus/model_viewer_plus.dart';
import 'package:air/pages/settings_page.dart';
import 'package:air/pages/logs.dart';
import 'package:air/services/logs_manager.dart';
import 'package:air/pages/chat_page.dart';
import 'package:air/view%20model/controller/voice_assistant_controller.dart';
import 'package:air/widgets/speech_bubble.dart';
import 'package:model_viewer_plus/src/model_viewer_plus.dart' show Loading, TouchAction, InteractionPrompt;
import 'package:air/services/camera_service.dart';
import 'package:air/widgets/camera_stream_panel.dart';
import 'package:air/widgets/swipe_indicator.dart';
import 'package:air/pages/robot_profile_page.dart';
import 'package:air/pages/calendar_page.dart';
import 'package:air/pages/health_page.dart';
import 'package:air/pages/task2_page.dart';

class HomePage extends StatefulWidget {
  final VoidCallback toggleThemeMode;
  final bool isDarkMode;

  const HomePage({Key? key, required this.toggleThemeMode, required this.isDarkMode}) : super(key: key);

  @override
  _HomePageState createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  String cameraOrbit = "-90deg 90deg auto";
  bool isResetting = false;
  bool isLoading = true;
  bool isMuted = true;
  final VoiceAssistantController _voiceController = Get.put(VoiceAssistantController());
  final CameraService _cameraService = CameraService();
  bool _showCamera = false;
  final PageController _pageController = PageController();
  bool _isShowingModel = true;
  bool _isSwipeExpanded = false;
  final GlobalKey<State<ModelViewer>> _modelKey = GlobalKey();

  String status = "Loading AIR...";

  @override
  void initState() {
    super.initState();
    _simulateModelLoading();
  }

  void _simulateModelLoading() async {
    await Future.delayed(const Duration(seconds: 4));
    setState(() {
      isLoading = false;
      status = "Status: Ready to Help!";
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

  Widget _buildRoundButton({
    required IconData icon,
    required String tooltip,
    required VoidCallback onPressed,
    Color? iconColor,
  }) {
    return SizedBox(
      width: 60,
      height: 60,
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
              MaterialPageRoute(
                builder: (context) => SettingsPage(
                  toggleThemeMode: widget.toggleThemeMode,
                  isDarkMode: widget.isDarkMode,
                ),
              ),
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
            padding: const EdgeInsets.only(top: 8.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 3D Model Viewer with Loading State
                Stack(
                  children: [
                    SizedBox(
                      height: 400,
                      child: PageView(
                        controller: _pageController,
                        physics: _isSwipeExpanded 
                            ? const AlwaysScrollableScrollPhysics()
                            : const NeverScrollableScrollPhysics(),
                        onPageChanged: (index) {
                          setState(() {
                            _isShowingModel = index == 0;
                            _isSwipeExpanded = index == 1;
                          });
                        },
                        children: [
                          // 3D Model Page
                          Stack(
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
                                  key: _modelKey,
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
                                    if (isLoading) {
                                      Future.delayed(Duration(milliseconds: 500), () {
                                        setState(() {
                                          isLoading = false;
                                        });
                                      });
                                    }
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
                          
                          // Camera Stream Panel
                          CameraStreamPanel(
                            cameraService: _cameraService,
                            showCamera: _showCamera,
                            onCameraClose: () {
                              _cameraService.stopStreaming();
                              setState(() => _showCamera = false);
                              LogsManager.addLog(message: "Closed camera stream", source: "System");
                            },
                          ),
                        ],
                      ),
                    ),
                    
                    // Swipe Indicator
                    Positioned(
                      left: _isSwipeExpanded ? 0 : null,
                      right: _isSwipeExpanded ? null : 0,
                      top: 140,
                      child: AnimatedSwitcher(
                        duration: const Duration(milliseconds: 300),
                        child: GestureDetector(
                          key: ValueKey<bool>(_isSwipeExpanded),
                          onHorizontalDragEnd: (details) {
                            if (details.primaryVelocity! < 0 && !_isSwipeExpanded) {
                              _pageController.animateToPage(
                                1,
                                duration: const Duration(milliseconds: 300),
                                curve: Curves.easeOut,
                              );
                            } else if (details.primaryVelocity! > 0 && _isSwipeExpanded) {
                              _pageController.animateToPage(
                                0,
                                duration: const Duration(milliseconds: 300),
                                curve: Curves.easeOut,
                              );
                            }
                          },
                          child: SwipeIndicator(
                            isExpanded: _isSwipeExpanded,
                            shouldBounce: _showCamera,
                            onTap: () {
                              _pageController.animateToPage(
                                _isSwipeExpanded ? 0 : 1,
                                duration: const Duration(milliseconds: 300),
                                curve: Curves.easeOut,
                              );
                            },
                          ),
                        ),
                      ),
                    ),
                  ],
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
                color: widget.isDarkMode ? Colors.white70 : Colors.black87,
              ),
            ),
          ),

          const SizedBox(height: 8),

          // First Row Buttons
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Padding(
                padding: const EdgeInsets.only(left: 24.0),
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
                padding: const EdgeInsets.only(right: 24.0),
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

          const SizedBox(height: 8),

          // Second Row Buttons
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Padding(
                padding: const EdgeInsets.only(left: 24.0),
                child: _buildRoundButton(
                  icon: Icons.assignment,
                  tooltip: "Task Management",
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const Task2Page(),
                      ),
                    );
                    LogsManager.addLog(message: "Opened Task Management Page", source: "User");
                  },
                ),
              ),
              // New Camera Button
              _buildRoundButton(
                icon: _showCamera ? Icons.camera_enhance : Icons.camera_alt,
                tooltip: _showCamera ? "Stop Camera" : "Start Camera",
                onPressed: () async {
                  if (!_showCamera) {
                    final initialized = await _cameraService.initializeCamera();
                    if (initialized) {
                      setState(() => _showCamera = true);
                      if (_cameraService.isRobotCamera) {
                        print('Starting robot camera stream');
                        _cameraService.startStreaming();
                        LogsManager.addLog(message: "Started robot camera stream", source: "System");
                      } else {
                        _cameraService.startStreaming();
                        LogsManager.addLog(message: "Started device camera stream", source: "System");
                      }
                    }
                  } else {
                    _cameraService.stopStreaming();
                    setState(() => _showCamera = false);
                    LogsManager.addLog(message: "Stopped camera stream", source: "System");
                  }
                },
              ),
              Padding(
                padding: const EdgeInsets.only(right: 24.0),
                child: _buildRoundButton(
                  icon: Icons.health_and_safety,
                  tooltip: "Health",
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const HealthPage(),
                      ),
                    );
                    LogsManager.addLog(message: "Opened Health Page", source: "User");
                  },
                ),
              ),
            ],
          ),

          const SizedBox(height: 8),

          // Third Row Buttons
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Padding(
                padding: const EdgeInsets.only(left: 24.0),
                child: _buildRoundButton(
                  icon: Icons.calendar_today,
                  tooltip: "Calendar",
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const CalendarPage(),
                      ),
                    );
                    LogsManager.addLog(message: "Opened Calendar Page", source: "User");
                  },
                ),
              ),
              // Empty space where Task2 button was
              const SizedBox(width: 60, height: 60),
              Padding(
                padding: const EdgeInsets.only(right: 24.0),
                child: _buildRoundButton(
                  icon: Icons.person,
                  tooltip: "Profile",
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const RobotProfilePage(),
                      ),
                    );
                    LogsManager.addLog(message: "Opened Robot Profile Page", source: "User");
                  },
                ),
              ),
            ],
          ),

        ],
      ),
    );
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }
} 