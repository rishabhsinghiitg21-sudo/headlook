"""Webcam head-pose tracking via MediaPipe FaceLandmarker.

Returns head orientation as (yaw, pitch, roll) in degrees. We rely on
MediaPipe's facial transformation matrix, which gives a full 4x4 pose of
the canonical face model in camera space; we pull Euler angles out of its
rotation block.
"""
import math
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision


def _rotation_to_euler(R):
    """Decompose a 3x3 rotation matrix into (pitch, yaw, roll) degrees.

    Convention is arbitrary here: we calibrate a neutral pose and only ever
    use angles *relative* to it, so absolute conventions don't matter as long
    as yaw and pitch move independently and monotonically.
    """
    sy = math.sqrt(R[0, 0] ** 2 + R[1, 0] ** 2)
    if sy > 1e-6:
        pitch = math.atan2(R[2, 1], R[2, 2])
        yaw = math.atan2(-R[2, 0], sy)
        roll = math.atan2(R[1, 0], R[0, 0])
    else:  # gimbal-lock fallback
        pitch = math.atan2(-R[1, 2], R[1, 1])
        yaw = math.atan2(-R[2, 0], sy)
        roll = 0.0
    return math.degrees(pitch), math.degrees(yaw), math.degrees(roll)


class HeadTracker:
    def __init__(self, model_path):
        base = mp_python.BaseOptions(model_asset_path=model_path)
        opts = vision.FaceLandmarkerOptions(
            base_options=base,
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            output_facial_transformation_matrixes=True,
            output_face_blendshapes=False,
        )
        self.landmarker = vision.FaceLandmarker.create_from_options(opts)
        self.landmarks = None   # last frame's (x, y) normalized points, for preview

    def process(self, frame_rgb, timestamp_ms):
        """frame_rgb: HxWx3 uint8 RGB. Returns (pitch, yaw, roll) or None.

        Also stashes the detected landmarks in self.landmarks for drawing.
        """
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        result = self.landmarker.detect_for_video(mp_image, timestamp_ms)
        self.landmarks = (
            [(p.x, p.y) for p in result.face_landmarks[0]]
            if result.face_landmarks else None
        )
        if not result.facial_transformation_matrixes:
            return None
        mat = np.array(result.facial_transformation_matrixes[0]).reshape(4, 4)
        if not np.isfinite(mat).all():
            return None
        return _rotation_to_euler(mat[:3, :3])

    def close(self):
        self.landmarker.close()
