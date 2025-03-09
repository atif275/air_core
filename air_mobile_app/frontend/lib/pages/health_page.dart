import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'dart:math' as math;
import 'package:air/services/robot_camera_service.dart';
import 'package:air/models/monitoring_data.dart';

class HealthPage extends StatefulWidget {
  const HealthPage({Key? key}) : super(key: key);

  @override
  _HealthPageState createState() => _HealthPageState();
}

class _HealthPageState extends State<HealthPage> with TickerProviderStateMixin {
  late TabController _mainTabController;
  late TabController _healthTabController;
  late TabController _performanceTabController;
  final List<double> cpuData = List.generate(24, (index) => math.Random().nextDouble() * 100);
  final List<double> memoryData = List.generate(24, (index) => math.Random().nextDouble() * 100);
  bool isMonitoring = false;
  bool isRobotConnected = false;
  bool isMLServerConnected = false;
  final RobotCameraService _robotCameraService = RobotCameraService();
  MonitoringData? _monitoringData;

  @override
  void initState() {
    super.initState();
    _mainTabController = TabController(length: 2, vsync: this);
    _healthTabController = TabController(length: 2, vsync: this);
    _performanceTabController = TabController(length: 2, vsync: this);

    // Check initial connection state
    setState(() {
      isRobotConnected = _robotCameraService.isConnected;
      isMonitoring = _robotCameraService.isMonitoring;
    });

    _mainTabController.addListener(() {
      if (_mainTabController.indexIsChanging) {
        setState(() {});
      }
    });

    _setupListeners();
  }

  void _setupListeners() {
    _robotCameraService.onConnectionStatus = (status) {
      if (mounted) {
        setState(() {
          isRobotConnected = _robotCameraService.isConnected;
          print('Robot connected, receiving status updates');
        });
      }
    };

    _robotCameraService.onDisconnected = () {
      if (mounted) {
        setState(() {
          isRobotConnected = false;
          isMonitoring = false;
          _monitoringData = null;
          print('Robot disconnected, clearing data');
        });
      }
    };

    // Handle regular status updates (10s polling)
    _robotCameraService.onSystemStatusUpdate = (data) {
      if (mounted) {
        setState(() {
          _monitoringData = data;
          print('Received status update from polling');
        });
      }
    };

    // Handle monitoring updates (1s updates)
    _robotCameraService.onMonitoringUpdate = (data) {
      if (mounted && isMonitoring) {
        setState(() {
          _monitoringData = data;
          print('Received monitoring update');
        });
      }
    };
  }

  void _toggleMonitoring() async {
    if (!isRobotConnected) return;

    setState(() {
      isMonitoring = !isMonitoring;
    });

    if (isMonitoring) {
      print('Starting monitoring mode');
      final success = await _robotCameraService.startMonitoring();
      if (!success) {
        setState(() {
          isMonitoring = false;
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Failed to start monitoring')),
          );
        });
      }
    } else {
      print('Stopping monitoring mode');
      _robotCameraService.stopMonitoring();
    }
  }

  @override
  void dispose() {
    if (isMonitoring) {
      _robotCameraService.stopMonitoring();
    }
    _robotCameraService.detachListeners();
    _mainTabController.dispose();
    _healthTabController.dispose();
    _performanceTabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Health Monitor'),
        actions: [
          _buildConnectionIndicator(),
          const SizedBox(width: 16),
        ],
        bottom: TabBar(
          controller: _mainTabController,
          labelStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          tabs: const [
            Tab(
              icon: Icon(Icons.monitor_heart),
              text: "Health",
              height: 64,
            ),
            Tab(
              icon: Icon(Icons.speed),
              text: "Performance",
              height: 64,
            ),
          ],
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.only(bottom: 80.0),
        child: TabBarView(
          controller: _mainTabController,
          children: [
            _buildHealthSection(),
            _buildPerformanceSection(),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: isRobotConnected ? _toggleMonitoring : null,
        backgroundColor: _getMonitoringButtonColor(),
        label: Text(isMonitoring ? 'Stop Monitoring' : 'Start Monitoring'),
        icon: Icon(isMonitoring ? Icons.stop : Icons.play_arrow),
      ),
    );
  }

  Widget _buildHealthSection() {
    return Column(
      children: [
        TabBar(
          controller: _healthTabController,
          labelColor: Colors.blue,
          unselectedLabelColor: Colors.grey,
          labelStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
          unselectedLabelStyle: const TextStyle(fontSize: 14),
          indicatorColor: Colors.blue,
          tabs: const [
            Tab(
              icon: Icon(Icons.android),
              text: "Robot Health",
            ),
            Tab(
              icon: Icon(Icons.phone_android),
              text: "App Health",
            ),
          ],
        ),
        Expanded(
          child: TabBarView(
            controller: _healthTabController,
            children: [
              _buildRobotHealthTab(),
              _buildAppHealthTab(),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildPerformanceSection() {
    return Column(
      children: [
        TabBar(
          controller: _performanceTabController,
          labelColor: Colors.blue,
          unselectedLabelColor: Colors.grey,
          labelStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
          unselectedLabelStyle: const TextStyle(fontSize: 14),
          indicatorColor: Colors.blue,
          tabs: const [
            Tab(
              icon: Icon(Icons.precision_manufacturing),
              text: "Robot Performance",
            ),
            Tab(
              icon: Icon(Icons.memory),
              text: "App Performance",
            ),
          ],
        ),
        Expanded(
          child: TabBarView(
            controller: _performanceTabController,
            children: [
              _buildRobotPerformanceTab(),
              _buildAppPerformanceTab(),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildRobotHealthTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        children: [
          _buildOverallHealthCard(),
          const SizedBox(height: 16),
          _buildComponentsHealthGrid(),
          const SizedBox(height: 16),
          _buildDiagnosticsCard(),
        ],
      ),
    );
  }

  Widget _buildOverallHealthCard() {
    final healthPercentage = isRobotConnected && _monitoringData != null 
        ? _monitoringData!.basicStatus.systemHealth / 100
        : 0.0;

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
                  'Overall System Health',
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
            Center(
              child: SizedBox(
                height: 150,
                width: 150,
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    TweenAnimationBuilder(
                      tween: Tween(begin: 0.0, end: healthPercentage),
                      duration: const Duration(seconds: 1),
                      builder: (context, double value, child) {
                        return CircularProgressIndicator(
                          value: value,
                          strokeWidth: 12,
                          backgroundColor: Colors.grey[300],
                          valueColor: AlwaysStoppedAnimation<Color>(
                            value > 0.7 ? Colors.green : Colors.orange,
                          ),
                        );
                      },
                    ),
                    Positioned.fill(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            isRobotConnected && _monitoringData != null
                                ? _monitoringData!.basicStatus.systemHealth.toString()
                                : '0%',
                            style: const TextStyle(
                              fontSize: 30,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          Text(isRobotConnected && _monitoringData != null
                              ? 'Healthy'
                              : 'Unknown'),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildComponentsHealthGrid() {
    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: 2,
      mainAxisSpacing: 10,
      crossAxisSpacing: 10,
      children: [
        _buildComponentCard(
          'Motors',
          isRobotConnected && _monitoringData != null
              ? _monitoringData!.motorMetrics.load / 100
              : 0.0,
          isRobotConnected ? Colors.green : Colors.grey
        ),
        _buildComponentCard(
          'Network',
          isRobotConnected && _monitoringData != null ? 0.95 : 0.0,
          isRobotConnected ? Colors.green : Colors.grey
        ),
        _buildComponentCard(
          'Battery',
          isRobotConnected && _monitoringData != null
              ? _monitoringData!.basicStatus.battery.level / 100
              : 0.0,
          isRobotConnected ? Colors.green : Colors.grey
        ),
        _buildComponentCard(
          'CPU',
          isRobotConnected && _monitoringData != null
              ? _monitoringData!.performanceMetrics.cpu.percent / 100
              : 0.0,
          isRobotConnected ? Colors.green : Colors.grey
        ),
      ],
    );
  }

  Widget _buildComponentCard(String title, double health, Color color) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              title,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            LinearProgressIndicator(
              value: health,
              backgroundColor: Colors.grey[300],
              valueColor: AlwaysStoppedAnimation<Color>(color),
            ),
            const SizedBox(height: 4),
            Text(isRobotConnected ? '${(health * 100).toInt()}%' : 'Unknown'),
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
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            _buildDiagnosticRow(
              'System Health',
              isRobotConnected && _monitoringData != null
                ? '${_monitoringData!.basicStatus.systemHealth.toStringAsFixed(1)}%'
                : 'Unknown'
            ),
            _buildDiagnosticRow(
              'Temperature',
              isRobotConnected && _monitoringData != null
                ? '${_monitoringData!.sensorReadings.temperature.toStringAsFixed(1)}°C'
                : 'Unknown'
            ),
            _buildDiagnosticRow(
              'Network Latency',
              isRobotConnected && _monitoringData != null
                ? '${_monitoringData!.basicStatus.network.latency.toStringAsFixed(1)}ms'
                : 'Unknown'
            ),
            _buildDiagnosticRow(
              'Motor Load',
              isRobotConnected && _monitoringData != null
                ? '${_monitoringData!.motorMetrics.load.toStringAsFixed(1)}%'
                : 'Unknown'
            ),
            _buildDiagnosticRow(
              'Peak Load',
              isRobotConnected && _monitoringData != null
                ? '${_monitoringData!.motorMetrics.peakLoad.toStringAsFixed(1)}%'
                : 'Unknown'
            ),
            _buildDiagnosticRow(
              'Movement Speed',
              isRobotConnected && _monitoringData != null
                ? '${_monitoringData!.motorMetrics.movementSpeed.toStringAsFixed(2)} m/s'
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
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }

  Widget _buildRobotPerformanceTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        children: [
          _buildPerformanceChart(
            'CPU Usage',
            isRobotConnected && _monitoringData != null
                ? [_monitoringData!.performanceMetrics.cpu.percent]
                : List.generate(24, (index) => 0.0),
            Colors.orange
          ),
          const SizedBox(height: 16),
          _buildPerformanceChart(
            'Memory Usage',
            isRobotConnected && _monitoringData != null
                ? [_monitoringData!.performanceMetrics.memory.percent]
                : List.generate(24, (index) => 0.0),
            Colors.green
          ),
          const SizedBox(height: 16),
          _buildPerformanceMetricsCard(),
        ],
      ),
    );
  }

  Widget _buildPerformanceMetricsCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Performance Details',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            _buildMetricRow(
              'Network Latency',
              isRobotConnected && _monitoringData != null
                  ? '${_monitoringData!.basicStatus.network.latency.toStringAsFixed(1)}ms'
                  : 'Unknown'
            ),
            _buildMetricRow(
              'Motor Load',
              isRobotConnected && _monitoringData != null
                  ? '${_monitoringData!.motorMetrics.load.toStringAsFixed(1)}%'
                  : 'Unknown'
            ),
            _buildMetricRow(
              'Peak Motor Load',
              isRobotConnected && _monitoringData != null
                  ? '${_monitoringData!.motorMetrics.peakLoad.toStringAsFixed(1)}%'
                  : 'Unknown'
            ),
            _buildMetricRow(
              'Movement Speed',
              isRobotConnected && _monitoringData != null
                  ? '${_monitoringData!.motorMetrics.movementSpeed.toStringAsFixed(2)} m/s'
                  : 'Unknown'
            ),
            const Divider(),
            _buildMetricRow(
              'Storage Used',
              isRobotConnected && _monitoringData != null
                  ? '${(_monitoringData!.performanceMetrics.disk.used / 1024 / 1024).toStringAsFixed(2)} GB'
                  : 'Unknown'
            ),
            _buildMetricRow(
              'Storage Free',
              isRobotConnected && _monitoringData != null
                  ? '${(_monitoringData!.performanceMetrics.disk.free / 1024 / 1024).toStringAsFixed(2)} GB'
                  : 'Unknown'
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAppHealthTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        children: [
          _buildAppStatusCard(),
          const SizedBox(height: 16),
          _buildBatteryAnalyticsCard(),
          const SizedBox(height: 16),
          _buildAppDiagnosticsCard(),
          const SizedBox(height: 16),
          _buildConnectionStatusCard(),
        ],
      ),
    );
  }

  Widget _buildAppStatusCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'App Status',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            _buildMetricRow('Version', '1.0.0'),
            _buildMetricRow('Last Update', '2 days ago'),
            _buildMetricRow('Storage Used', '245 MB'),
            _buildMetricRow('Cache Size', '32 MB'),
          ],
        ),
      ),
    );
  }

  Widget _buildConnectionStatusCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Connection Status',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            _buildMetricRow('Websocket', 'Connected'),
            _buildMetricRow('Latency', '45ms'),
            _buildMetricRow('Signal Strength', 'Strong'),
            _buildMetricRow('Protocol Version', 'v2.1'),
          ],
        ),
      ),
    );
  }

  Widget _buildAppPerformanceTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        children: [
          _buildPerformanceChart('CPU Usage', cpuData, Colors.blue),
          const SizedBox(height: 16),
          _buildPerformanceChart('Memory Usage', memoryData, Colors.purple),
          const SizedBox(height: 16),
          _buildAppPerformanceMetricsCard(),
        ],
      ),
    );
  }

  Widget _buildAppPerformanceMetricsCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'App Performance Metrics',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            _buildMetricRow('Frame Rate', '60 FPS'),
            _buildMetricRow('Memory Usage', '245 MB'),
            _buildMetricRow('CPU Usage', '15%'),
            _buildMetricRow('Battery Impact', 'Low'),
            const Divider(),
            const Text(
              'Resource Usage Averages',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            _buildMetricRow('Avg. Battery Drain', '2.5%/hour'),
            _buildMetricRow('Avg. CPU Usage', '12%'),
            _buildMetricRow('Peak CPU Usage', '23%'),
            _buildMetricRow('Background Usage', '3%'),
          ],
        ),
      ),
    );
  }

  Widget _buildBatteryAnalyticsCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Battery Analytics',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            _buildMetricRow('Current Drain Rate', '2.5%/hour'),
            _buildMetricRow('Screen Impact', '1.2%/hour'),
            _buildMetricRow('Background Impact', '0.3%/hour'),
            _buildMetricRow('Network Impact', '0.5%/hour'),
            _buildMetricRow('Estimated Runtime', '8.5 hours'),
            const Divider(),
            const Text(
              'Usage Pattern',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            _buildMetricRow('Heavy Usage', '3.5%/hour'),
            _buildMetricRow('Normal Usage', '2.0%/hour'),
            _buildMetricRow('Light Usage', '0.8%/hour'),
          ],
        ),
      ),
    );
  }

  Widget _buildAppDiagnosticsCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'App Diagnostics',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            _buildDiagnosticItem(
              DiagnosticItem('App running normally', DiagnosticSeverity.good),
            ),
            _buildDiagnosticItem(
              DiagnosticItem('Background services: Active', DiagnosticSeverity.good),
            ),
            _buildDiagnosticItem(
              DiagnosticItem('Cache size: Normal', DiagnosticSeverity.good),
            ),
            _buildDiagnosticItem(
              DiagnosticItem('Storage space: 75% free', DiagnosticSeverity.good),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDiagnosticItem(DiagnosticItem item) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(item.message),
          Icon(item.severity.icon, color: item.severity.color),
        ],
      ),
    );
  }

  Widget _buildMetricRow(String label, dynamic value) {
    String displayValue = '';
    if (value is double) {
      displayValue = value.toStringAsFixed(1);
    } else if (value is int) {
      displayValue = value.toString();
    } else {
      displayValue = value?.toString() ?? 'Unknown';
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label),
          Text(
            displayValue,
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }

  Widget _buildPerformanceChart(String title, List<double> data, Color color) {
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
            SizedBox(
              height: 200,
              child: LineChart(
                LineChartData(
                  gridData: FlGridData(show: true),
                  titlesData: FlTitlesData(show: false),
                  borderData: FlBorderData(show: true),
                  minY: 0,
                  maxY: 100,
                  lineBarsData: [
                    LineChartBarData(
                      spots: data.asMap().entries.map((e) {
                        return FlSpot(e.key.toDouble(), e.value);
                      }).toList(),
                      isCurved: true,
                      color: isRobotConnected ? color : Colors.grey,
                      barWidth: 3,
                      dotData: FlDotData(show: false),
                    ),
                  ],
                ),
              ),
            ),
            if (!isRobotConnected)
              const Padding(
                padding: EdgeInsets.only(top: 8.0),
                child: Center(
                  child: Text(
                    'No data available - Robot disconnected',
                    style: TextStyle(
                      color: Colors.grey,
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildConnectionIndicator() {
    return Tooltip(
      message: 'Connection Status',
      child: InkWell(
        onTap: () {
          showDialog(
            context: context,
            builder: (context) => AlertDialog(
              title: const Text('Connection Status'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildStatusLegendItem(
                    'Left Half',
                    'Robot Server Connection',
                    isRobotConnected,
                  ),
                  const SizedBox(height: 16),
                  _buildStatusLegendItem(
                    'Right Half',
                    'ML Server Connection',
                    isMLServerConnected,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Note: ML Server connection is only active when normal camera mode is initiated.',
                    style: TextStyle(
                      fontSize: 12,
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Close'),
                ),
              ],
            ),
          );
        },
        child: Row(
          children: [
            CustomPaint(
              size: const Size(20, 20),
              painter: SplitDotPainter(
                leftConnected: isRobotConnected,
                rightConnected: isMLServerConnected,
              ),
            ),
            const SizedBox(width: 4),
            const Icon(
              Icons.help_outline,
              size: 16,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusLegendItem(String title, String description, bool isConnected) {
    return Row(
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isConnected ? Colors.green : Colors.red,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              Text(
                description,
                style: const TextStyle(fontSize: 12),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // Helper method to format bytes to human readable format
  String _formatBytes(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    if (bytes < 1024 * 1024 * 1024) return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
  }

  Color _getMonitoringButtonColor() {
    if (!isRobotConnected) return Colors.grey;
    return isMonitoring ? Colors.red : Colors.green;
  }
}

class DiagnosticItem {
  final String message;
  final DiagnosticSeverity severity;

  DiagnosticItem(this.message, this.severity);
}

enum DiagnosticSeverity {
  good(Icons.check_circle, Colors.green),
  warning(Icons.warning, Colors.orange),
  error(Icons.error, Colors.red);

  final IconData icon;
  final Color color;

  const DiagnosticSeverity(this.icon, this.color);
}

class SplitDotPainter extends CustomPainter {
  final bool leftConnected;
  final bool rightConnected;

  SplitDotPainter({
    required this.leftConnected,
    required this.rightConnected,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final Paint leftPaint = Paint()
      ..color = leftConnected ? Colors.green : Colors.red;
    final Paint rightPaint = Paint()
      ..color = rightConnected ? Colors.green : Colors.red;

    final double radius = size.width / 2;
    final Rect rect = Rect.fromCircle(
      center: Offset(radius, radius),
      radius: radius,
    );

    // Draw left half
    canvas.save();
    canvas.clipRect(Rect.fromLTRB(0, 0, size.width / 2, size.height));
    canvas.drawCircle(Offset(radius, radius), radius, leftPaint);
    canvas.restore();

    // Draw right half
    canvas.save();
    canvas.clipRect(Rect.fromLTRB(size.width / 2, 0, size.width, size.height));
    canvas.drawCircle(Offset(radius, radius), radius, rightPaint);
    canvas.restore();

    // Draw border
    final Paint borderPaint = Paint()
      ..color = Colors.grey
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;
    canvas.drawCircle(Offset(radius, radius), radius, borderPaint);
  }

  @override
  bool shouldRepaint(SplitDotPainter oldDelegate) {
    return leftConnected != oldDelegate.leftConnected ||
        rightConnected != oldDelegate.rightConnected;
  }
} 