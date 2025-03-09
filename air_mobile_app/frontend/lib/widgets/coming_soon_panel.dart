import 'package:flutter/material.dart';
import 'package:air/widgets/camera_overlay.dart';
import 'package:air/services/camera_service.dart';
import 'package:air/services/robot_camera_service.dart';

class ComingSoonPanel extends StatefulWidget {
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
  State<ComingSoonPanel> createState() => _ComingSoonPanelState();
}

class _ComingSoonPanelState extends State<ComingSoonPanel> {
  final RobotCameraService _robotCameraService = RobotCameraService();

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 400,
      decoration: BoxDecoration(
        color: Colors.black54,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.3)),
      ),
      child: Stack(
        children: [
          if (!widget.showCamera)
            const Center(
              child: Text(
                'Camera Stream',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          if (widget.showCamera)
            CameraOverlay(
              cameraService: widget.cameraService,
              onClose: widget.onCameraClose,
            ),
        ],
      ),
    );
  }
} 