import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import '../services/camera_service.dart';
import 'package:permission_handler/permission_handler.dart';

class CameraOverlay extends StatefulWidget {
  final CameraService cameraService;
  final VoidCallback onClose;

  const CameraOverlay({
    Key? key,
    required this.cameraService,
    required this.onClose,
  }) : super(key: key);

  @override
  State<CameraOverlay> createState() => _CameraOverlayState();
}

class _CameraOverlayState extends State<CameraOverlay> {
  bool _isFlashOn = false;

  @override
  Widget build(BuildContext context) {
    return Positioned(
      top: MediaQuery.of(context).size.height * 0.00, // Adjusted from 0.05 to 0.02
      left: 0,
      right: 0,
      child: Center(
        child: Container(
          width: 300,
          height: 400,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: Colors.white.withOpacity(0.5), width: 2),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.3),
                blurRadius: 10,
                spreadRadius: 2,
              ),
            ],
          ),
          child: Stack(
            children: [
              // Camera Preview
              ClipRRect(
                borderRadius: BorderRadius.circular(18),
                child: widget.cameraService.controller != null
                    ? CameraPreview(widget.cameraService.controller!)
                    : Container(
                        color: Colors.black87,
                        child: const Center(
                          child: Text(
                            'Initializing camera...',
                            style: TextStyle(color: Colors.white),
                          ),
                        ),
                      ),
              ),
              
              // Controls Overlay
              Positioned(
                top: 0,
                left: 0,
                right: 0,
                child: Container(
                  height: 50,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        Colors.black.withOpacity(0.7),
                        Colors.transparent,
                      ],
                    ),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      // Close Button
                      IconButton(
                        icon: const Icon(Icons.close, color: Colors.white),
                        onPressed: widget.onClose,
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
} 