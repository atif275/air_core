import 'package:camera/camera.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as path;
import 'dart:io';
import 'dart:io' show Platform;
import 'package:get/get.dart';
import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'dart:convert';
import 'dart:async';
import 'dart:typed_data';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:image/image.dart' as img;
import 'package:air/services/robot_camera_service.dart';

class CameraService {
  CameraController? controller;
  bool isStreaming = false;
  bool isRobotCamera = false;
  bool _serverReady = false;
  DateTime? _lastFrameTime;
  int _reconnectAttempts = 0;
  final RobotCameraService _robotCameraService = RobotCameraService();
  StreamController<Uint8List> _imageStreamController;
  WebSocketChannel? _mlServerChannel;
  bool _isInitialized = false;
  
  static const int MAX_RECONNECT_ATTEMPTS = 5;
  static const Duration RECONNECT_DELAY = Duration(seconds: 2);
  static const Duration FRAME_INTERVAL = Duration(milliseconds: 500);
  static const int MAX_IMAGE_DIMENSION = 640;
  static const int JPEG_QUALITY = 70;
  
  CameraService() : _imageStreamController = StreamController<Uint8List>.broadcast();

  String get mlServerUrl {
    final host = dotenv.env['WEBSOCKET_HOST'] ?? 'localhost';
    final port = dotenv.env['WEBSOCKET_PORT'] ?? '8766';
    return 'ws://$host:$port';
  }

  Future<bool> initializeCamera() async {
    print('Initializing camera...');
    if (_robotCameraService.isConnectionActive()) {
      print('Robot camera is active, setting up stream');
      isRobotCamera = true;
      _isInitialized = true;
      _setupRobotCameraStream();
      print('Robot camera stream setup complete');
      return true;
    }

    print('Using device camera');
    isRobotCamera = false;
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) return false;

      controller = CameraController(
        cameras.firstWhere(
          (camera) => camera.lensDirection == CameraLensDirection.front,
          orElse: () => cameras.first,
        ),
        ResolutionPreset.medium,
        enableAudio: false,
      );

      await controller!.initialize();
      await controller!.setFlashMode(FlashMode.off);
      print('Device camera initialized successfully');
      _isInitialized = true;
      return true;
    } catch (e) {
      print('Error initializing camera: $e');
      return false;
    }
  }

  void _setupRobotCameraStream() {
    print('Setting up robot camera stream handler');
    _robotCameraService.onImageReceived = (imageData) {
      if (!_imageStreamController.isClosed) {
        try {
          print('Processing new frame from robot');
          final bytes = base64Decode(imageData);
          print('Decoded base64 frame, size: ${bytes.length} bytes');
          _imageStreamController.add(bytes);
          _lastFrameTime = DateTime.now();
          print('Frame added to stream successfully at ${_lastFrameTime}');
        } catch (e) {
          print('Error processing robot camera image: $e');
        }
      }
    };

    _robotCameraService.onConnectionStatus = (status) {
      print('Robot camera status: $status');
    };

    _robotCameraService.onDisconnected = () {
      print('Robot camera disconnected, stopping stream');
      stopStreaming();
    };
  }

  Stream<Uint8List> get imageStream {
    if (isRobotCamera) {
      print('Providing robot camera stream');
      if (!_isInitialized) {
        print('Warning: Robot camera not initialized when requesting stream');
      }
      if (_imageStreamController.isClosed) {
        print('Warning: Stream controller is closed, creating new one');
        _imageStreamController = StreamController<Uint8List>.broadcast();
      }
    } else {
      print('Providing device camera stream');
      if (!_serverReady) {
        print('Waiting for server ready signal...');
      }
    }
    return _imageStreamController.stream;
  }

  void startStreaming() {
    print('Starting camera stream...');
    isStreaming = true;
    _reconnectAttempts = 0;
    
    if (isRobotCamera) {
      print('Enabling robot camera stream via RobotCameraService');
      _robotCameraService.startStreaming();
      _setupRobotCameraStream();
      print('Robot camera stream setup completed');
    } else {
      print('Starting device camera stream');
      _connectToMLServer();
      _setupDeviceCameraStream();
    }
  }

  Future<void> _connectToMLServer() async {
    try {
      print('Connecting to ML WebSocket server at ${mlServerUrl}');
      _mlServerChannel = WebSocketChannel.connect(Uri.parse(mlServerUrl));
      print('Connected to ML WebSocket server');
      _setupMLServerListeners();
    } catch (e) {
      print('Error connecting to ML WebSocket server: $e');
      throw e;
    }
  }

  void _setupMLServerListeners() {
    _mlServerChannel!.stream.listen(
      (message) {
        try {
          final data = jsonDecode(message);
          print('Received message from ML server: ${data['type']}');
          
          if (data['type'] == 'ready') {
            _serverReady = true;
            print('ML server is ready to receive frames');
          } else if (data['type'] == 'frame_ack') {
            print('Frame ${data['frame_number']} acknowledged by ML server');
          } else if (data['type'] == 'error') {
            print('ML server error: ${data['message']}');
          }
        } catch (e) {
          print('Error processing ML server message: $e');
        }
      },
      onError: (error) {
        print('ML WebSocket error: $error');
        _reconnect();
      },
      onDone: () {
        print('ML WebSocket connection closed');
        _reconnect();
      },
    );
  }

  void _setupDeviceCameraStream() async {
    if (controller == null) return;

    await controller!.startImageStream((image) async {
      if (!isStreaming || _mlServerChannel == null || !_serverReady) return;

      final now = DateTime.now();
      if (_lastFrameTime != null &&
          now.difference(_lastFrameTime!) < FRAME_INTERVAL) {
        return;
      }
      _lastFrameTime = now;

      try {
        final bytes = await _processImageFrame(image);
        
        if (_mlServerChannel != null && _serverReady) {
          print('Sending frame to ML server');
          _mlServerChannel!.sink.add(jsonEncode({
            'type': 'frame',
            'data': base64Encode(bytes),
            'timestamp': DateTime.now().millisecondsSinceEpoch,
          }));
        }

        if (!_imageStreamController.isClosed) {
          _imageStreamController.add(bytes);
        }
      } catch (e) {
        print('Error processing camera frame: $e');
      }
    });
  }

  Future<Uint8List> _processImageFrame(CameraImage image) async {
    // Implementation of _processImageFrame method
    // This method should return a Uint8List representing the processed image
    throw UnimplementedError();
  }

  void stopStreaming() {
    print('Stopping camera stream...');
    isStreaming = false;
    _serverReady = false;
    _lastFrameTime = null;
    
    if (isRobotCamera) {
      print('Disabling robot camera stream');
      _robotCameraService.stopStreaming();
    } else {
      print('Stopping device camera stream');
      controller?.stopImageStream();
      _mlServerChannel?.sink.close();
      _mlServerChannel = null;
    }
    print('Stream stopped successfully');
  }

  Future<void> _reconnect() async {
    if (!isStreaming || _reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      if (_reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        print('Max reconnection attempts reached');
        stopStreaming();
      }
      return;
    }

    _reconnectAttempts++;
    print('Reconnection attempt $_reconnectAttempts of $MAX_RECONNECT_ATTEMPTS');
    
    await Future.delayed(RECONNECT_DELAY);
    stopStreaming();
    startStreaming();
  }

  void dispose() {
    print('Disposing camera service');
    stopStreaming();
    controller?.dispose();
    _imageStreamController.close();
    _isInitialized = false;
  }
} 
 