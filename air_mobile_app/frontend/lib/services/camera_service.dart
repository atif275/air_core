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

class CameraService {
  CameraController? controller;
  bool isStreaming = false;
  WebSocketChannel? _channel;
  DateTime? _lastFrameTime;
  int _reconnectAttempts = 0;
  bool _serverReady = false;
  
  static const int MAX_RECONNECT_ATTEMPTS = 5;
  static const Duration RECONNECT_DELAY = Duration(seconds: 2);
  static const Duration FRAME_INTERVAL = Duration(milliseconds: 500);
  static const int MAX_IMAGE_DIMENSION = 640;
  static const int JPEG_QUALITY = 70;
  
  String get serverUrl {
    final host = dotenv.env['WEBSOCKET_HOST'] ?? '192.168.56.31';
    final port = dotenv.env['WEBSOCKET_PORT'] ?? '8765';
    return 'ws://$host:$port';
  }

  Future<bool> initializeCamera() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        print('No cameras available');
        return false;
      }

      controller = CameraController(
        cameras.firstWhere(
          (camera) => camera.lensDirection == CameraLensDirection.front,
          orElse: () => cameras.first,
        ),
        ResolutionPreset.low, // Lower initial resolution
        enableAudio: false,
        imageFormatGroup: Platform.isIOS 
            ? ImageFormatGroup.bgra8888 
            : ImageFormatGroup.jpeg,
      );

      await controller!.initialize();
      // Disable flash
      await controller!.setFlashMode(FlashMode.off);
      print('Camera initialized successfully');
      return true;
    } catch (e) {
      print('Error in camera initialization: $e');
      return false;
    }
  }

  Future<void> startStreaming() async {
    if (controller == null || !controller!.value.isInitialized) {
      print('Camera not initialized');
      return;
    }

    try {
      await _connectToWebSocket();
      isStreaming = true;
      _reconnectAttempts = 0;

      await controller!.startImageStream((CameraImage image) async {
        if (!isStreaming || !_serverReady) {
          print('Waiting for server ready signal...');
          return;
        }

        // Frame rate limiting
        final now = DateTime.now();
        if (_lastFrameTime != null && 
            now.difference(_lastFrameTime!) < FRAME_INTERVAL) {
          return;
        }
        _lastFrameTime = now;

        try {
          List<int>? imageBytes;
          
          if (Platform.isIOS) {
            // For iOS: Convert BGRA to JPEG
            final img.Image? capturedImage = img.Image.fromBytes(
              width: image.width,
              height: image.height,
              bytes: image.planes[0].bytes.buffer,
              order: img.ChannelOrder.bgra,
            );
            
            if (capturedImage != null) {
              final img.Image resized = img.copyResize(
                capturedImage,
                width: MAX_IMAGE_DIMENSION,
                height: (MAX_IMAGE_DIMENSION * image.height ~/ image.width),
              );
              imageBytes = img.encodeJpg(resized, quality: JPEG_QUALITY);
            } else {
              print('Failed to process iOS image');
              return;
            }
          } else {
            // For Android: Take a picture instead of using image stream
            final XFile picture = await controller!.takePicture();
            final bytes = await picture.readAsBytes();
            final img.Image? capturedImage = img.decodeImage(bytes);
            
            if (capturedImage != null) {
              final img.Image resized = img.copyResize(
                capturedImage,
                width: MAX_IMAGE_DIMENSION,
                height: (MAX_IMAGE_DIMENSION * image.height ~/ image.width),
              );
              imageBytes = img.encodeJpg(resized, quality: JPEG_QUALITY);
              await File(picture.path).delete(); // Clean up temporary file
            } else {
              print('Failed to process Android image');
              return;
            }
          }

          if (imageBytes != null) {
            print('Processed image size: ${imageBytes.length} bytes');
            final base64Image = base64Encode(imageBytes);
            print('Base64 size: ${base64Image.length} bytes');

            if (_channel != null && _channel!.sink != null) {
              _channel!.sink.add(jsonEncode({
                'type': 'image',
                'image': base64Image,
                'timestamp': DateTime.now().millisecondsSinceEpoch,
              }));
              print('Frame sent to server');
            }
          }
        } catch (e) {
          print('Error processing image: $e');
        }
      });

    } catch (e) {
      print('Error starting stream: $e');
      isStreaming = false;
      _reconnect();
    }
  }

  Future<void> _connectToWebSocket() async {
    try {
      _channel = WebSocketChannel.connect(Uri.parse(serverUrl));
      print('Connected to WebSocket server');
      _setupWebSocketListeners();
    } catch (e) {
      print('Error connecting to WebSocket: $e');
      throw e;
    }
  }

  void _setupWebSocketListeners() {
    _channel!.stream.listen(
      (message) {
        try {
          final data = jsonDecode(message);
          print('Received message from server: ${data['type']}');
          
          if (data['type'] == 'ready') {
            _serverReady = true;
            print('Server is ready to receive frames');
          } else if (data['type'] == 'frame_ack') {
            print('Frame ${data['frame_number']} acknowledged');
          } else if (data['type'] == 'error') {
            print('Server error: ${data['message']}');
          }
        } catch (e) {
          print('Error processing server message: $e');
        }
      },
      onError: (error) {
        print('WebSocket error: $error');
        _reconnect();
      },
      onDone: () {
        print('WebSocket connection closed');
        _reconnect();
      },
    );
  }

  Future<void> _reconnect() async {
    if (!isStreaming || _reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      if (_reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        print('Max reconnection attempts reached');
        await stopStreaming();
      }
      return;
    }

    _reconnectAttempts++;
    print('Reconnection attempt $_reconnectAttempts of $MAX_RECONNECT_ATTEMPTS');
    
    await Future.delayed(RECONNECT_DELAY);
    await stopStreaming();
    await startStreaming();
  }

  Future<void> stopStreaming() async {
    isStreaming = false;
    _serverReady = false;
    _lastFrameTime = null;
    await controller?.stopImageStream();
    await _channel?.sink.close();
    _channel = null;
    print('Stopped streaming');
  }

  void dispose() {
    stopStreaming();
    controller?.dispose();
    print('Camera controller disposed');
  }
} 
 