import 'package:flutter/material.dart';
import 'package:air/services/robot_camera_service.dart';
import 'package:air/models/monitoring_data.dart';

class RobotProfilePage extends StatefulWidget {
  const RobotProfilePage({Key? key}) : super(key: key);

  @override
  State<RobotProfilePage> createState() => _RobotProfilePageState();
}

class _RobotProfilePageState extends State<RobotProfilePage> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool isConnected = false;
  MonitoringData? _monitoringData;
  String robotStatus = 'Disconnected';
  bool isMonitoring = false;
  String lastSync = 'Never';
  final RobotCameraService _robotCameraService = RobotCameraService();

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    
    // Check initial connection state
    setState(() {
      isConnected = _robotCameraService.isConnected;
      isMonitoring = _robotCameraService.isMonitoring;
      robotStatus = isConnected ? 'Connected' : 'Disconnected';
    });
    
    _setupListeners();
  }

  void _setupListeners() {
    _robotCameraService.onConnectionStatus = (status) {
      if (mounted) {
        setState(() {
          isConnected = _robotCameraService.isConnected;
          robotStatus = 'Connected';
          print('Robot connected to profile page');
        });
      }
    };

    _robotCameraService.onDisconnected = () {
      if (mounted) {
        setState(() {
          isConnected = false;
          isMonitoring = false;
          robotStatus = 'Disconnected';
          _monitoringData = null;
          print('Robot disconnected from profile page');
        });
      }
    };

    // Handle regular status updates (10s polling)
    _robotCameraService.onSystemStatusUpdate = (data) {
      if (mounted) {
        setState(() {
          _monitoringData = data;
          print('Profile received status update from polling');
        });
      }
    };

    // Handle monitoring updates (1s updates)
    _robotCameraService.onMonitoringUpdate = (data) {
      if (mounted && isMonitoring) {
        setState(() {
          _monitoringData = data;
          print('Profile received monitoring update');
        });
      }
    };
  }

  @override
  void dispose() {
    _robotCameraService.detachListeners();
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return WillPopScope(
      onWillPop: () async {
        return true;
      },
      child: Scaffold(
        appBar: AppBar(
          title: const Text('AIR Profile'),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => Navigator.pop(context),
          ),
          bottom: TabBar(
            controller: _tabController,
            tabs: const [
              Tab(icon: Icon(Icons.info), text: "Status"),
              Tab(icon: Icon(Icons.settings_remote), text: "Control"),
              Tab(icon: Icon(Icons.palette), text: "Appearance"),
              Tab(icon: Icon(Icons.settings), text: "Settings"),
            ],
          ),
        ),
        body: TabBarView(
          controller: _tabController,
          children: [
            _buildStatusTab(),
            _buildControlTab(),
            _buildAppearanceTab(),
            _buildSettingsTab(),
          ],
        ),
        floatingActionButton: FloatingActionButton.extended(
          onPressed: _connectToRobot,
          icon: Icon(isConnected ? Icons.link : Icons.link_off),
          label: Text(isConnected ? "Connected" : "Connect"),
          backgroundColor: isConnected ? Colors.green : Colors.blue,
        ),
      ),
    );
  }

  Widget _buildStatusTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildStatusCard(),
          const SizedBox(height: 16),
          _buildDiagnosticsCard(),
          const SizedBox(height: 16),
          _buildSensorsCard(),
        ],
      ),
    );
  }

  Widget _buildStatusCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Robot Status',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                ),
                if (isMonitoring)
                  const Chip(
                    label: Text('Live'),
                    backgroundColor: Colors.green,
                    labelStyle: TextStyle(color: Colors.white),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            _buildStatusRow('Connection', robotStatus),
            _buildStatusRow(
              'Battery', 
              isConnected && _monitoringData != null 
                ? '${_monitoringData!.basicStatus.battery.level}%'
                : "Unknown"
            ),
            _buildStatusRow(
              'Power Source',
              isConnected && _monitoringData != null
                ? (_monitoringData!.basicStatus.battery.powerPlugged ? 'Charging' : 'Battery')
                : 'Unknown'
            ),
            _buildStatusRow(
              'System Health',
              isConnected && _monitoringData != null
                ? '${_monitoringData!.basicStatus.systemHealth}%'
                : 'Unknown'
            ),
            _buildStatusRow(
              'Last Sync',
              isConnected && _monitoringData != null
                ? _monitoringData!.basicStatus.network.lastSync
                : 'Never'
            ),
            _buildStatusRow(
              'Operating Time',
              isConnected && _monitoringData != null
                ? _monitoringData!.basicStatus.operatingTime
                : 'Unknown'
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label),
          Text(
            value,
            style: TextStyle(
              color: value == 'Offline' ? Colors.red : Colors.green,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildControlTab() {
    return GridView.count(
      padding: const EdgeInsets.all(16.0),
      crossAxisCount: 2,
      childAspectRatio: 1.5,
      mainAxisSpacing: 16,
      crossAxisSpacing: 16,
      children: [
        _buildControlCard('Movement Control', Icons.control_camera),
        _buildControlCard('Voice Commands', Icons.mic),
        _buildControlCard('Gesture Control', Icons.gesture),
        _buildControlCard('Task Scheduling', Icons.schedule),
        _buildControlCard('Emergency Stop', Icons.stop_circle),
        _buildControlCard('Behavior Mode', Icons.psychology),
      ],
    );
  }

  Widget _buildControlCard(String title, IconData icon) {
    return Card(
      child: InkWell(
        onTap: () {
          // TODO: Implement control actions
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('$title coming soon')),
          );
        },
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 40),
            const SizedBox(height: 8),
            Text(title, textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }

  Widget _buildAppearanceTab() {
    return ListView(
      padding: const EdgeInsets.all(16.0),
      children: [
        _build3DModelPreview(),
        const SizedBox(height: 16),
        _buildColorCustomization(),
        const SizedBox(height: 16),
        _buildAnimationControls(),
      ],
    );
  }

  Widget _build3DModelPreview() {
    return Card(
      child: Container(
        height: 200,
        alignment: Alignment.center,
        child: const Text('3D Model Preview\nComing Soon'),
      ),
    );
  }

  Widget _buildColorCustomization() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Color Customization',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            // Add color pickers here
          ],
        ),
      ),
    );
  }

  Widget _buildAnimationControls() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Animation Controls',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            // Add animation controls here
          ],
        ),
      ),
    );
  }

  Widget _buildSettingsTab() {
    return ListView(
      padding: const EdgeInsets.all(16.0),
      children: [
        _buildSettingsSection('Connection Settings', [
          'Bluetooth Configuration',
          'Wi-Fi Setup',
          'Remote Access',
        ]),
        const SizedBox(height: 16),
        _buildSettingsSection('Robot Settings', [
          'Movement Speed',
          'Voice Volume',
          'Power Management',
          'Safety Controls',
        ]),
        const SizedBox(height: 16),
        _buildSettingsSection('Updates', [
          'System Updates',
          'Feature Updates',
          'Security Patches',
        ]),
      ],
    );
  }

  Widget _buildSettingsSection(String title, List<String> settings) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            ...settings.map((setting) => ListTile(
              title: Text(setting),
              trailing: const Icon(Icons.chevron_right),
              onTap: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('$setting coming soon')),
                );
              },
            )),
          ],
        ),
      ),
    );
  }

  Widget _buildDiagnosticsCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Diagnostics',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            LinearProgressIndicator(
              value: isConnected && _monitoringData != null 
                ? _monitoringData!.basicStatus.systemHealth / 100
                : 0.0,
              backgroundColor: Colors.grey[300],
              valueColor: AlwaysStoppedAnimation<Color>(
                isConnected ? Colors.green : Colors.grey
              ),
            ),
            const SizedBox(height: 8),
            Text(
              isConnected && _monitoringData != null
                ? 'System Health: ${_monitoringData!.basicStatus.systemHealth}%'
                : 'System Health: Unknown',
              style: const TextStyle(fontSize: 16),
            ),
            const SizedBox(height: 16),
            _buildDiagnosticRow(
              'Temperature',
              isConnected && _monitoringData != null
                ? '${_monitoringData!.sensorReadings.temperature}°C'
                : 'Unknown'
            ),
            _buildDiagnosticRow(
              'Network Latency',
              isConnected && _monitoringData != null
                ? '${_monitoringData!.basicStatus.network.latency}ms'
                : 'Unknown'
            ),
            _buildDiagnosticRow(
              'Motor Load',
              isConnected && _monitoringData != null
                ? '${_monitoringData!.motorMetrics.load}%'
                : 'Unknown'
            ),
            _buildDiagnosticRow(
              'Memory Usage',
              isConnected && _monitoringData != null
                ? '${_monitoringData!.performanceMetrics.memory.percent}%'
                : 'Unknown'
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDiagnosticRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label),
          Text(
            value,
            style: TextStyle(
              color: value == 'Offline' ? Colors.red : Colors.green,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSensorsCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Sensor Readings',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            Text('Temperature: ${isConnected && _monitoringData != null ? "${_monitoringData!.sensorReadings.temperature}°C" : "Null"}'),
            Text('Humidity: ${isConnected && _monitoringData != null ? "${_monitoringData!.sensorReadings.humidity}%" : "Null"}'),
            Text('Proximity: ${isConnected && _monitoringData != null ? _monitoringData!.sensorReadings.proximity : "Null"}'),
            Text('Light Level: ${isConnected && _monitoringData != null ? _monitoringData!.sensorReadings.lightLevel : "Null"}'),
          ],
        ),
      ),
    );
  }

  Future<void> _connectToRobot() async {
    if (_robotCameraService.isConnected) {
      _robotCameraService.disconnect();
      setState(() {
        isConnected = false;
        robotStatus = "Disconnected";
      });
      return;
    }

    try {
      await _robotCameraService.connect();
      setState(() {
        isConnected = true;
        robotStatus = "Online";
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Successfully connected to robot!'),
            backgroundColor: Colors.green,
          ),
        );
      });
    } catch (e) {
      setState(() {
        isConnected = false;
        robotStatus = "Offline";
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to connect to robot: $e'),
            backgroundColor: Colors.red,
          ),
        );
      });
    }
  }
} 