import 'package:flutter/material.dart';
import 'package:air/widgets/camera_overlay.dart';
import 'package:air/services/camera_service.dart';

class ComingSoonPanel extends StatelessWidget {
  final CameraService cameraService;
  final bool showCamera;
  final VoidCallback onCameraClose;

  const ComingSoonPanel({
    Key? key,
    required this.cameraService,
    required this.showCamera,
    required this.onCameraClose,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 400, // Same height as 3D model container
      decoration: BoxDecoration(
        color: Colors.black54,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.3)),
      ),
      child: Stack(
        children: [
          const Center(
            child: Text(
              'Coming Soon',
              style: TextStyle(
                color: Colors.white,
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          if (showCamera)
            CameraOverlay(
              cameraService: cameraService,
              onClose: onCameraClose,
            ),
        ],
      ),
    );
  }
} 