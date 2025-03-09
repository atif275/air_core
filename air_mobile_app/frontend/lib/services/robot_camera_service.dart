import 'package:web_socket_channel/web_socket_channel.dart';
import 'dart:convert';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'dart:async';
import 'package:air/models/monitoring_data.dart';

class RobotCameraService {
  // Singleton pattern
  static final RobotCameraService _instance = RobotCameraService._internal();
  factory RobotCameraService() => _instance;
  RobotCameraService._internal();

  WebSocketChannel? _channel;
  Timer? _heartbeatTimer;
  Timer? _statusPollingTimer;
  Timer? _reconnectTimer;
  bool _isDisposed = false;
  bool _isConnected = false;
  bool _isStreamingEnabled = false;
  bool _isMonitoring = false;
  bool _isPollingEnabled = false;
  int _reconnectAttempts = 0;
  bool _manualDisconnect = false;
  
  static const int MAX_RECONNECT_ATTEMPTS = 5;
  static const Duration RECONNECT_DELAY = Duration(seconds: 2);
  static const Duration STATUS_POLLING_INTERVAL = Duration(seconds: 10);
  static const Duration HEARTBEAT_INTERVAL = Duration(seconds: 20);

  // Getters
  bool get isConnected => _isConnected;
  bool get isMonitoring => _isMonitoring;

  // Callbacks
  Function(String)? onImageReceived;
  Function(String)? onConnectionStatus;
  Function()? onDisconnected;
  Function()? onHeartbeatAck;
  Function(MonitoringData)? onMonitoringUpdate;
  Function(MonitoringData)? onSystemStatusUpdate;

  String get serverUrl {
    final host = dotenv.env['ROBOT_WEBSOCKET_HOST'] ?? '192.168.56.31';
    final port = dotenv.env['ROBOT_WEBSOCKET_PORT'] ?? '8765';
    return 'ws://$host:$port';
  }

  Future<void> connect() async {
    if (_channel != null || _isConnected) {
      print('! Already connected or connecting');
      return;
    }

    _manualDisconnect = false;
    try {
      print('> Connecting to WebSocket server at $serverUrl');
      _channel = WebSocketChannel.connect(Uri.parse(serverUrl));
      await _channel!.ready;
      print('> Successfully connected to WebSocket server');
      _setupWebSocketListeners();
      _isConnected = true;
      onConnectionStatus?.call('Connected successfully');
      _startStatusPolling();
    } catch (e) {
      print('! Connection failed: $e');
      _handleDisconnection();
      rethrow;
    }
  }

  void _setupWebSocketListeners() {
    _channel!.stream.listen(
      (message) {
        if (_isDisposed) return;
        try {
          final data = jsonDecode(message);
          print('< Received: ${data['type']}');
          
          switch (data['type']) {
            case 'image':
              if (_isStreamingEnabled && data['image'] != null) {
                print('< Received frame ${data['frame_number']}');
                onImageReceived?.call(data['image']);
              }
              break;
            case 'connection_status':
              print('< Received connection status: ${data['status']} - ${data['message']}');
              onConnectionStatus?.call(data['message']);
              if (data['status'] == 'success') {
                _startStatusPolling();
              }
              break;
            case 'heartbeat_ack':
              print('< Received heartbeat acknowledgment');
              onHeartbeatAck?.call();
              break;
            case 'command_response':
              print('< Received command response: ${data['status']} - ${data['message']}');
              break;
            case 'system_status':
              print('< Received system status update at ${data['timestamp']}');
              print('< System status data: ${jsonEncode(data['data'])}');
              if (data['data'] != null) {
                try {
                  final monitoringData = MonitoringData.fromJson(data['data']);
                  print('< Successfully parsed monitoring data:');
                  print('  - Battery: ${monitoringData.basicStatus.battery.level}');
                  print('  - System Health: ${monitoringData.basicStatus.systemHealth}');
                  print('  - Temperature: ${monitoringData.sensorReadings.temperature}');
                  print('  - CPU Usage: ${monitoringData.performanceMetrics.cpu.percent}%');
                  print('  - Memory Usage: ${monitoringData.performanceMetrics.memory.percent}%');
                  onSystemStatusUpdate?.call(monitoringData);
                } catch (e) {
                  print('! Error parsing monitoring data: $e');
                  print('! Raw data that caused error: ${jsonEncode(data['data'])}');
                }
              }
              break;
            case 'monitoring_update':
              print('< Received monitoring update at ${data['timestamp']}');
              print('< Monitoring data: ${jsonEncode(data['data'])}');
              if (data['data'] != null) {
                try {
                  final monitoringData = MonitoringData.fromJson(data['data']);
                  print('< Successfully parsed monitoring update:');
                  print('  - Battery: ${monitoringData.basicStatus.battery.level}');
                  print('  - System Health: ${monitoringData.basicStatus.systemHealth}');
                  print('  - Temperature: ${monitoringData.sensorReadings.temperature}');
                  print('  - CPU Usage: ${monitoringData.performanceMetrics.cpu.percent}%');
                  print('  - Memory Usage: ${monitoringData.performanceMetrics.memory.percent}%');
                  onMonitoringUpdate?.call(monitoringData);
                } catch (e) {
                  print('! Error parsing monitoring data: $e');
                  print('! Raw data that caused error: ${jsonEncode(data['data'])}');
                }
              }
              break;
            default:
              print('< Received unknown message type: ${data['type']}');
              print('< Unknown message data: $data');
          }
        } catch (e) {
          print('! Error processing message: $e');
          print('! Raw message that caused error: $message');
        }
      },
      onError: (error) {
        print('! WebSocket error: $error');
        _handleDisconnection();
      },
      onDone: () {
        print('! WebSocket connection closed');
        _handleDisconnection();
      },
    );
  }

  void _handleDisconnection() {
    print('! Handling disconnection');
    _cleanup();
    
    if (!_manualDisconnect && !_isDisposed) {
      _reconnectAttempts++;
      if (_reconnectAttempts <= MAX_RECONNECT_ATTEMPTS) {
        print('> Attempting reconnection #$_reconnectAttempts in ${RECONNECT_DELAY.inSeconds}s');
        _reconnectTimer = Timer(RECONNECT_DELAY, () {
          connect();
        });
      } else {
        print('! Max reconnection attempts reached');
        _manualDisconnect = true;
      }
    }
  }

  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(HEARTBEAT_INTERVAL, (timer) {
      if (isConnected) {
        try {
          print('> Sending heartbeat');
          _channel!.sink.add(jsonEncode({'type': 'heartbeat'}));
        } catch (e) {
          print('! Heartbeat failed: $e');
          _handleDisconnection();
        }
      }
    });
  }

  void startStreaming() {
    if (!isConnected) {
      print('Cannot start streaming: not connected');
      return;
    }
    try {
      print('Sending start_streaming command to server');
      final command = {
        'type': 'command',
        'action': 'start_streaming'
      };
      print('Command to send: ${jsonEncode(command)}');
      _channel!.sink.add(jsonEncode(command));
      _isStreamingEnabled = true;
      print('Robot camera streaming command sent successfully');
    } catch (e) {
      print('Error sending start streaming command: $e');
    }
  }

  void stopStreaming() {
    try {
      print('Sending stop_streaming command to server');
      final command = {
        'type': 'command',
        'action': 'stop_streaming'
      };
      print('Command to send: ${jsonEncode(command)}');
      _channel!.sink.add(jsonEncode(command));
      _isStreamingEnabled = false;
      print('Robot camera stop streaming command sent successfully');
    } catch (e) {
      print('Error sending stop streaming command: $e');
    }
  }

  void _stopHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
  }

  void disconnect() {
    _manualDisconnect = true;
    print('> Manual disconnect requested');
    _cleanup();
  }

  void reattachListeners({
    Function(String)? onImageReceived,
    Function(String)? onConnectionStatus,
    Function()? onDisconnected,
    Function()? onHeartbeatAck,
    Function(MonitoringData)? onMonitoringUpdate,
    Function(MonitoringData)? onSystemStatusUpdate,
  }) {
    if (onImageReceived != null) this.onImageReceived = onImageReceived;
    if (onConnectionStatus != null) this.onConnectionStatus = onConnectionStatus;
    if (onDisconnected != null) this.onDisconnected = onDisconnected;
    if (onHeartbeatAck != null) this.onHeartbeatAck = onHeartbeatAck;
    if (onMonitoringUpdate != null) this.onMonitoringUpdate = onMonitoringUpdate;
    if (onSystemStatusUpdate != null) this.onSystemStatusUpdate = onSystemStatusUpdate;
  }

  void detachListeners() {
    onImageReceived = null;
    onConnectionStatus = null;
    onDisconnected = null;
    onHeartbeatAck = null;
    onMonitoringUpdate = null;
    onSystemStatusUpdate = null;
  }

  void dispose() {
    _isDisposed = true;
    print('> Disposing RobotCameraService');
    _cleanup();
    detachListeners();
  }

  void reset() {
    _isDisposed = false;
  }

  Future<bool> startMonitoring() async {
    if (!isConnected) return false;
    
    try {
      print('> Sending start_monitoring command');
      _channel!.sink.add(jsonEncode({
        'type': 'command',
        'action': 'start_monitoring'
      }));
      _isMonitoring = true;
      return true;
    } catch (e) {
      print('! Error starting monitoring: $e');
      return false;
    }
  }

  void stopMonitoring() {
    if (!_isMonitoring) return;
    
    try {
      print('> Sending stop_monitoring command');
      _channel!.sink.add(jsonEncode({
        'type': 'command',
        'action': 'stop_monitoring'
      }));
      _isMonitoring = false;
    } catch (e) {
      print('! Error stopping monitoring: $e');
    }
  }

  Future<void> _getSystemStatus() async {
    if (!isConnected) return;
    
    try {
      print('> Sending get_system_status command');
      _channel!.sink.add(jsonEncode({
        'type': 'command',
        'action': 'get_system_status'
      }));
    } catch (e) {
      print('! Error getting system status: $e');
    }
  }

  void _startStatusPolling() {
    if (_isPollingEnabled) return;
    
    print('> Starting system status polling (${STATUS_POLLING_INTERVAL.inSeconds}s interval)');
    _statusPollingTimer?.cancel();
    _statusPollingTimer = Timer.periodic(STATUS_POLLING_INTERVAL, (timer) {
      _getSystemStatus();
    });
    _isPollingEnabled = true;
    
    // Get initial status immediately
    _getSystemStatus();
  }

  void _stopStatusPolling() {
    print('> Stopping system status polling');
    _statusPollingTimer?.cancel();
    _statusPollingTimer = null;
    _isPollingEnabled = false;
  }

  void _cleanup() {
    _heartbeatTimer?.cancel();
    _stopStatusPolling();
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _channel = null;
    _isConnected = false;
    _isStreamingEnabled = false;
    _isMonitoring = false;
    _isPollingEnabled = false;
    onDisconnected?.call();
    print('> Cleanup completed');
  }

  bool isConnectionActive() {
    return _isConnected && _channel != null;
  }
} 