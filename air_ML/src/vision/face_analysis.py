import numpy as np

def get_eye_aspect_ratio(landmarks):
    """Calculates eye aspect ratio (EAR) to determine eye contact."""
    left_eye = landmarks[36:42]
    right_eye = landmarks[42:48]

    def aspect_ratio(eye_points):
        A = np.linalg.norm(eye_points[1] - eye_points[5])
        B = np.linalg.norm(eye_points[2] - eye_points[4])
        C = np.linalg.norm(eye_points[0] - eye_points[3])
        return (A + B) / (2.0 * C)

    left_ear = aspect_ratio(left_eye)
    right_ear = aspect_ratio(right_eye)
    return (left_ear + right_ear) / 2.0

def get_mouth_aspect_ratio(landmarks):
    """Calculates mouth aspect ratio (MAR) to detect speech."""
    upper_lip = np.array([landmarks[i] for i in [50, 51, 52, 61, 62, 63]])
    lower_lip = np.array([landmarks[i] for i in [56, 57, 58, 65, 66, 67]])

    A = np.linalg.norm(upper_lip[1] - lower_lip[1])
    B = np.linalg.norm(upper_lip[2] - lower_lip[2])
    C = np.linalg.norm(upper_lip[0] - lower_lip[0])

    mar = (A + B) / (2.0 * C)
    return mar
