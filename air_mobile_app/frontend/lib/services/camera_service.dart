import 'package:camera/camera.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as path;
import 'dart:io';
import 'dart:io' show Platform;
import 'package:get/get.dart';
import 'package:flutter/material.dart';

class CameraService {
  CameraController? controller;
  bool isStreaming = false;
  String? saveDirectory;

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
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: Platform.isIOS 
            ? ImageFormatGroup.bgra8888 
            : ImageFormatGroup.yuv420,
      );

      try {
        await controller!.initialize();
        print('Camera initialized successfully');
        return true;
      } on CameraException catch (e) {
        print('Camera error: ${e.code} - ${e.description}');
        if (e.code == 'CameraAccessDenied') {
          return false;
        }
        return false;
      }
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
      await controller!.startVideoRecording();
      isStreaming = true;
      print('Started video streaming');
    } catch (e) {
      print('Error starting video stream: $e');
      isStreaming = false;
    }
  }

  Future<void> stopStreaming() async {
    if (!isStreaming || controller == null) return;

    try {
      final file = await controller!.stopVideoRecording();
      isStreaming = false;
      print('Stopped video streaming: ${file.path}');
      
      await File(file.path).delete();
    } catch (e) {
      print('Error stopping video stream: $e');
    }
  }

  void dispose() {
    stopStreaming();
    controller?.dispose();
    print('Camera controller disposed');
  }
} 
 