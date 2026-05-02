import cv2
import mediapipe as mp
import numpy as np
import time

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose


def calculate_angle(a, b, c):
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - \
              np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180:
        angle = 360 - angle
    return angle


cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)

counter = 0
stage = None
last_rep_time = 0

with mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
) as pose:

    while cap.isOpened():

        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = pose.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        elbow_angle_val = 0
        vertical_span = 0
        torso_tilt = 0
        body_ok = False

        try:
            landmarks = results.pose_landmarks.landmark

            l_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            r_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
            l_hip      = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
            r_hip      = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value]
            l_ankle    = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value]
            r_ankle    = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value]
            l_elbow    = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value]
            r_elbow    = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value]
            l_wrist    = landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value]
            r_wrist    = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value]

            shoulder_y = (l_shoulder.y + r_shoulder.y) / 2
            hip_y      = (l_hip.y + r_hip.y) / 2
            ankle_y    = (l_ankle.y + r_ankle.y) / 2

            vertical_span = abs(ankle_y - shoulder_y)
            torso_tilt    = abs(hip_y - shoulder_y)

            l_elbow_angle = calculate_angle(
                [l_shoulder.x, l_shoulder.y],
                [l_elbow.x,    l_elbow.y],
                [l_wrist.x,    l_wrist.y]
            )
            r_elbow_angle = calculate_angle(
                [r_shoulder.x, r_shoulder.y],
                [r_elbow.x,    r_elbow.y],
                [r_wrist.x,    r_wrist.y]
            )
            elbow_angle_val = (l_elbow_angle + r_elbow_angle) / 2

            # LOOSE thresholds — fix after seeing debug values
            body_ok = vertical_span < 0.55 and torso_tilt < 0.40

            current_time = time.time()

            if body_ok:
                if elbow_angle_val > 150:
                    stage = "up"
                if (elbow_angle_val < 90
                        and stage == "up"
                        and current_time - last_rep_time > 0.8):
                    stage = "down"
                    counter += 1
                    last_rep_time = current_time
            else:
                stage = None

        except Exception as e:
            pass

        h, w = image.shape[:2]

        # ── Rep + Stage ───────────────────────────────────────────────
        cv2.rectangle(image, (0, 0), (200, 80), (20, 20, 20), -1)
        cv2.putText(image, 'REPS', (15, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (180, 180, 180), 1)
        cv2.putText(image, str(counter), (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.2, (255, 255, 255), 3)

        cv2.rectangle(image, (210, 0), (500, 80), (20, 20, 20), -1)
        cv2.putText(image, 'STAGE', (220, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (180, 180, 180), 1)
        cv2.putText(image, stage if stage else 'none', (220, 68),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.8, (255, 255, 255), 2)

        # ── DEBUG panel (right side) ──────────────────────────────────
        debug_x = w - 320
        cv2.rectangle(image, (debug_x - 10, 0), (w, 200), (20, 20, 20), -1)

        cv2.putText(image, f'Elbow Angle : {int(elbow_angle_val)}',
                    (debug_x, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
        cv2.putText(image, f'Vert Span   : {vertical_span:.3f}',
                    (debug_x, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
        cv2.putText(image, f'Torso Tilt  : {torso_tilt:.3f}',
                    (debug_x, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
        cv2.putText(image, f'Body OK     : {body_ok}',
                    (debug_x, 120),cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (0,255,0) if body_ok else (0,100,255), 1)
        cv2.putText(image, f'Stage       : {stage}',
                    (debug_x, 150),cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 1)

        # ── Status bar ────────────────────────────────────────────────
        cv2.rectangle(image, (0, h - 45), (w, h), (20, 20, 20), -1)
        if body_ok:
            cv2.putText(image, 'Position OK — counting reps', (15, h - 13),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
        else:
            cv2.putText(image, f'NOT counting | span={vertical_span:.2f} tilt={torso_tilt:.2f}',
                        (15, h - 13), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 100, 255), 2)

        # ── Skeleton ──────────────────────────────────────────────────
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(
                image,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2),
                mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
            )

        cv2.imshow('Pushup Counter — DEBUG', image)

        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()