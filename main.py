import math
import sys
import cv2
import mediapipe as mp
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QGridLayout,
                             QStackedWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QFile
from PyQt5.QtGui import QImage, QPixmap, QFont

# Initialize MediaPipe Pose
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles


def load_stylesheet(file_path):
    """Load QSS stylesheet from file."""
    file_path = file_path.replace('/', '\\')
    qss_file = QFile(file_path)
    if qss_file.exists():
        qss_file.open(QFile.ReadOnly)
        stylesheet = str(qss_file.readAll(), encoding='utf-8')
        return stylesheet
    return ""


class VideoThread(QThread):
    update_frame = pyqtSignal(QImage, np.ndarray, object)

    def __init__(self, exercise_name, camera_id=0):
        super().__init__()
        self.camera_id = camera_id
        self.running = False
        self.exercise_name = exercise_name

    def run(self):
        self.running = True
        cap = cv2.VideoCapture(self.camera_id)

        # Set up MediaPipe pose detection
        with mp_pose.Pose(
                min_detection_confidence=0.75,
                min_tracking_confidence=0.6) as pose:

            while self.running:
                ret, frame = cap.read()
                if not ret:
                    break

                # Flip the frame horizontally for a mirror effect
                frame = cv2.flip(frame, 1)

                # Convert the BGR image to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Process the frame and get pose results
                results = pose.process(rgb_frame)

                # Draw the pose landmarks
                if results.pose_landmarks:
                    mp_drawing.draw_landmarks(
                        rgb_frame,
                        results.pose_landmarks,
                        mp_pose.POSE_CONNECTIONS,
                        landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style())

                # Create QImage from the RGB frame
                h, w, ch = rgb_frame.shape
                qt_img = QImage(rgb_frame.data, w, h, w * ch, QImage.Format.Format_RGB888)

                # Emit signal with the image and pose data
                self.update_frame.emit(qt_img, frame, results)

        cap.release()

    def stop(self):
        self.running = False
        self.wait()


class ExerciseWidget(QWidget):
    go_back_signal = pyqtSignal()

    def __init__(self, exercise_name):
        super().__init__()
        self.exercise_name = exercise_name
        self.video_thread = None

        # Exercise state tracking
        self.rep_count = 0
        self.last_feedback = ""
        self.feedback_count = 0
        self.position_correct = False

        # State for rep counting
        self.in_rep = False
        self.rep_started = False
        self.current_state = "starting"  # starting, down, up

        # For smoothing angles
        self.angle_history = {}
        self.history_length = 5

        # For deadlift tracking
        self.max_hip_angle = 160
        self.min_hip_angle = 60
        self.max_knee_angle = 160
        self.min_knee_angle = 80

        # Define the correct view for each exercise
        self.exercise_views = {
            "Squat": "Side View",
            "Deadlift": "Side View (preferred) or Frontal View",
            "Bicep Curl": "Side View",
            "Lunge": "Side View",
            "Push-Up": "Side View (preferred) or Frontal View",
            "Shoulder Press": "Frontal View"
        }

        self.initUI()

        # Start video immediately
        self.start_video()

    def initUI(self):
        # Main layout
        layout = QVBoxLayout()

        # Title
        title_label = QLabel(f"{self.exercise_name} - AI Trainer")
        title_label.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # View instruction
        self.view_label = QLabel(f"Required position: {self.exercise_views.get(self.exercise_name, 'Unknown')}")
        self.view_label.setFont(QFont('Arial', 16))
        self.view_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view_label.setStyleSheet("color: #333333; background-color: #FFFFCC; padding: 5px;")

        # Camera Feed Frame
        self.video_label = QLabel()
        self.video_label.setMinimumSize(1120, 840)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: #333333;")

        # Rep counter
        counter_layout = QHBoxLayout()
        counter_label = QLabel("Reps:")
        counter_label.setFont(QFont('Blinker', 36, QFont.Weight.Bold))
        counter_label.setStyleSheet("color: #32c2af;")
        self.rep_counter_label = QLabel("0")
        self.rep_counter_label.setFont(QFont('Blinker', 36, QFont.Weight.Bold))
        self.rep_counter_label.setStyleSheet("color: #32c2af;")
        counter_layout.addWidget(counter_label)
        counter_layout.addWidget(self.rep_counter_label)
        counter_layout.addStretch()

        # Feedback label
        self.feedback_label = QLabel("Get ready to start your exercise...")
        self.feedback_label.setFont(QFont('Blinker', 20))
        self.feedback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feedback_label.setStyleSheet("color: white; background-color: #555555; padding: 8px;")

        # Controls layout with just the back button
        controls_layout = QHBoxLayout()

        self.back_button = QPushButton("Back to Menu")
        self.back_button.setFont(QFont('Blinker', 20))
        self.back_button.clicked.connect(self.go_back)

        controls_layout.addStretch()
        controls_layout.addWidget(self.back_button)
        controls_layout.addStretch()

        # Add all widgets to main layout
        layout.addWidget(title_label)
        layout.addWidget(self.view_label)
        layout.addWidget(self.video_label)
        layout.addLayout(counter_layout)
        layout.addWidget(self.feedback_label)
        layout.addLayout(controls_layout)

        self.setLayout(layout)

    def start_video(self):
        self.video_thread = VideoThread(self.exercise_name)
        self.video_thread.update_frame.connect(self.update_frame)
        self.video_thread.start()

    def stop_video(self):
        if self.video_thread is not None:
            self.video_thread.stop()
            self.video_thread = None

    def calculate_angle(self, a, b, c):
        """
        Calculate the angle between three points
        Args:
            a: first point [x, y]
            b: mid point [x, y]
            c: end point [x, y]
        Returns:
            angle in degrees
        """
        a = np.array(a)
        b = np.array(b)
        c = np.array(c)

        # Calculate vectors
        ba = a - b
        bc = c - b

        # Calculate cosine of angle using dot product
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)  # Ensure within domain of arccos

        # Calculate angle in degrees
        angle = np.arccos(cosine_angle)
        angle = np.degrees(angle)

        return angle

    def smooth_angle(self, angle_id, angle_value):
        """Apply smoothing to angle values to reduce jitter"""
        if angle_id not in self.angle_history:
            self.angle_history[angle_id] = []

        # Add new value
        self.angle_history[angle_id].append(angle_value)

        # Keep history limited to specified length
        if len(self.angle_history[angle_id]) > self.history_length:
            self.angle_history[angle_id].pop(0)

        # Calculate moving average
        return sum(self.angle_history[angle_id]) / len(self.angle_history[angle_id])

    def get_coordinates(self, landmarks, landmark_id):
        """Extract x,y coordinates from a landmark"""
        if landmarks:
            landmark = landmarks[landmark_id]
            return [landmark.x, landmark.y]
        return None

    def check_view_position(self, frame, results):
        """
        Check if the user is in the correct position for the exercise view.
        Returns: (is_position_correct, feedback_message)
        """
        if not results or not results.pose_landmarks:
            return False, "No person detected. Please stand in front of the camera."

        landmarks = results.pose_landmarks.landmark

        # Get necessary landmarks based on the exercise
        if self.exercise_name in ["Squat", "Deadlift", "Bicep Curl", "Shoulder Press", "Lunge"] and "Side" in \
                self.exercise_views[self.exercise_name]:
            # For side view exercises, check if person is standing sideways
            # A basic heuristic: compare shoulder width in pixels
            try:
                # Get shoulder landmarks
                left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
                right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]

                # Calculate distance between shoulders
                shoulder_width = abs(left_shoulder.x - right_shoulder.x)

                # If shoulders appear close together in x-axis, likely side view
                if shoulder_width < 0.2:  # Threshold to be adjusted
                    return True, f"Good! You're in the correct side view position for {self.exercise_name}."
                else:
                    return False, f"Please turn to your side. {self.exercise_name} works best with a side view."

            except Exception as e:
                return False, f"Cannot determine position. Please ensure your full body is visible."

        elif (self.exercise_name in ["Push-Up"] or
              (self.exercise_name == "Deadlift" and "Frontal" in self.exercise_views[self.exercise_name])):
            # For frontal view exercises
            try:
                # Get shoulder landmarks
                left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
                right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]

                # Calculate distance between shoulders
                shoulder_width = abs(left_shoulder.x - right_shoulder.x)

                # If shoulders appear wide apart in x-axis, likely frontal view
                if shoulder_width > 0.2:  # Threshold to be adjusted
                    return True, f"Good! You're in the correct frontal view position for {self.exercise_name}."
                else:
                    required_view = "frontal" if "Side" not in self.exercise_views[
                        self.exercise_name] else "side or frontal"
                    return False, f"Please face the camera directly. {self.exercise_name} works best with a {required_view} view."

            except Exception as e:
                return False, f"Cannot determine position. Please ensure your full body is visible."

        return False, "Checking your position..."

    def analyze_deadlift(self, landmarks):
        """Analyze deadlift form and count reps"""
        feedback = ""
        count_rep = False

        # Get key landmarks
        shoulder = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER.value)
        hip = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_HIP.value)
        knee = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_KNEE.value)
        ankle = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_ANKLE.value)

        if None in [shoulder, hip, knee, ankle]:
            return "Cannot detect all necessary body points. Adjust your position.", False

        # Calculate key angles
        back_angle = self.calculate_angle(shoulder, hip, knee)
        knee_angle = self.calculate_angle(hip, knee, ankle)
        hip_angle = self.calculate_angle(shoulder, hip, knee)

        # Apply smoothing
        back_angle = self.smooth_angle("back", back_angle)
        knee_angle = self.smooth_angle("knee", knee_angle)
        hip_angle = self.smooth_angle("hip", hip_angle)

        # Detect deadlift phases
        if not self.rep_started and hip_angle > self.max_hip_angle and knee_angle > self.max_knee_angle:  # Standing position
            self.rep_started = True
            self.current_state = "starting"
            feedback = "Start your deadlift by hinging at the hips"

        if self.rep_started:
            if self.current_state == "starting" and hip_angle < 130 and knee_angle < 130 and \
                    hip_angle > self.min_hip_angle and knee_angle > self.min_knee_angle:
                # Moving to bottom position
                self.current_state = "down"
                feedback = "Keep your back straight"

            elif self.current_state == "down" and hip_angle > 160:
                # Returning to standing
                self.current_state = "starting"
                feedback = "Good rep! Stand tall at the top"
                count_rep = True

        # Mistakes
        # Knee too bent
        if hip_angle < 140 and knee_angle > 130 and self.current_state == "down":
            feedback = "Bend your knee more"

        # If no specific feedback, give general guidance
        if not feedback:
            if self.current_state == "starting":
                feedback = "Hinge at your hips to begin"
            elif self.current_state == "down":
                feedback = "Drive through heels to stand up"

        return feedback, count_rep

    def analyze_bicep_curl(self, landmarks):
        """Analyze bicep curl form and count reps"""
        feedback = ""
        count_rep = False

        # Get key landmarks - use left side for side view
        shoulder = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER.value)
        elbow = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_ELBOW.value)
        wrist = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_WRIST.value)
        hip = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_HIP.value)

        if None in [shoulder, elbow, wrist]:
            return "Cannot detect arm position. Please ensure your arm is visible.", False

        # Calculate elbow angle
        elbow_angle = self.calculate_angle(shoulder, elbow, wrist)
        elbow_angle = self.smooth_angle("elbow", elbow_angle)

        # Calculate if arm is swinging (optional)
        arm_stable = True
        if hip is not None:
            shoulder_hip_elbow = self.calculate_angle(hip, shoulder, elbow)
            shoulder_hip_elbow = self.smooth_angle("arm_swing", shoulder_hip_elbow)
            # If angle varies too much, arm is swinging
            arm_stable = shoulder_hip_elbow < 40

        # Detect curl phases
        if not self.rep_started and elbow_angle > 150:  # Starting position with arm extended
            self.rep_started = True
            self.current_state = "starting"
            feedback = "Begin the curl by bending your elbow"

        if self.rep_started:
            if self.current_state == "starting" and elbow_angle < 60:
                # Arm curled up
                self.current_state = "up"
                feedback = "Good! Now lower the weight slowly"

            elif self.current_state == "up" and elbow_angle > 150:
                # Arm back to starting position
                self.current_state = "starting"
                feedback = "Good rep! Keep your upper arm still"
                count_rep = True

        # Form feedback
        if not arm_stable:
            feedback = "Keep your upper arm still! Avoid swinging"

        # If no specific feedback, give general guidance
        if not feedback:
            if self.current_state == "starting":
                feedback = "Curl the weight up toward your shoulder"
            elif self.current_state == "up":
                feedback = "Slowly lower the weight back down"

        return feedback, count_rep

    def analyze_lunge(self, landmarks):
        """Analyze lunge form and count reps"""
        feedback = ""
        count_rep = False

        # Get key landmarks - for side view
        hip = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_HIP.value)
        front_knee = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_KNEE.value)
        front_ankle = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_ANKLE.value)
        back_knee = self.get_coordinates(landmarks, mp_pose.PoseLandmark.RIGHT_KNEE.value)
        back_ankle = self.get_coordinates(landmarks, mp_pose.PoseLandmark.RIGHT_ANKLE.value)
        shoulder = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER.value)

        if None in [hip, front_knee, front_ankle] or None in [hip, back_knee, back_ankle]:
            return "Cannot detect leg positions. Ensure both legs are visible.", False

        # Calculate key angles
        front_knee_angle = self.calculate_angle(hip, front_knee, front_ankle)
        back_knee_angle = self.calculate_angle(hip, back_knee, back_ankle)

        # Smooth the angles
        front_knee_angle = self.smooth_angle("front_knee", front_knee_angle)
        back_knee_angle = self.smooth_angle("back_knee", back_knee_angle)

        # Calculate torso angle if shoulder is visible
        torso_straight = True
        if shoulder is not None:
            torso_angle = self.calculate_angle(shoulder, hip, front_knee)
            torso_angle = self.smooth_angle("torso", torso_angle)
            torso_straight = torso_angle > 80  # Check if torso is relatively vertical

        # Detect lunge phases
        if not self.rep_started and front_knee_angle > 160 and back_knee_angle > 160:
            # Starting position - both legs relatively straight
            self.rep_started = True
            self.current_state = "starting"
            feedback = "Begin the lunge by stepping forward"

        if self.rep_started:
            if self.current_state == "starting" and front_knee_angle < 110 and back_knee_angle < 130:
                # In lunge position
                self.current_state = "down"
                if front_knee_angle < 80:
                    feedback = "Watch your front knee! Don't go too deep"
                else:
                    feedback = "Good lunge depth! Push back up when ready"

            elif self.current_state == "down" and front_knee_angle > 160 and back_knee_angle > 160:
                # Back to starting position
                self.current_state = "starting"
                feedback = "Good rep! Prepare for the next lunge"
                count_rep = True

        # Form feedback
        if front_knee_angle < 90 and self.current_state == "down":
            feedback = "Front knee is too bent! Keep it above 90 degrees"
        elif not torso_straight and self.current_state == "down":
            feedback = "Keep your torso upright! Don't lean forward"

        # If no specific feedback, give general guidance
        if not feedback:
            if self.current_state == "starting":
                feedback = "Step forward into your lunge"
            elif self.current_state == "down":
                feedback = "Push through your front heel to stand up"

        return feedback, count_rep

    def analyze_pushup(self, landmarks):
        """Analyze push-up form and count reps"""
        feedback = ""
        count_rep = False

        # Get key landmarks
        shoulder = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER.value)
        elbow = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_ELBOW.value)
        wrist = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_WRIST.value)
        hip = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_HIP.value)
        knee = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_KNEE.value)
        ankle = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_ANKLE.value)

        if None in [shoulder, elbow, wrist, hip]:
            return "Cannot detect all body points. Ensure your full side is visible.", False

        # Calculate key angles
        elbow_angle = self.calculate_angle(shoulder, elbow, wrist)
        elbow_angle = self.smooth_angle("elbow", elbow_angle)

        # Calculate body alignment
        body_straight = True
        if knee is not None and ankle is not None:
            # Check shoulder-hip-ankle alignment for plank form
            alignment_angle1 = self.calculate_angle(shoulder, hip, knee)
            alignment_angle2 = self.calculate_angle(hip, knee, ankle)

            alignment_angle1 = self.smooth_angle("align1", alignment_angle1)
            alignment_angle2 = self.smooth_angle("align2", alignment_angle2)

            # If both angles are close to 180, the body is in a straight line
            body_straight = alignment_angle1 > 160 and alignment_angle2 > 160

        # Detect push-up phases
        if not self.rep_started and elbow_angle > 160:
            # Starting in plank position
            self.rep_started = True
            self.current_state = "up"
            feedback = "Begin the push-up by bending your elbows"

        if self.rep_started:
            if self.current_state == "up" and elbow_angle < 100:
                # Bottom of push-up
                self.current_state = "down"
                feedback = "Good depth! Now push back up"

            elif self.current_state == "down" and elbow_angle > 160:
                # Back to plank position
                self.current_state = "up"
                feedback = "Good rep! Maintain a straight body"
                count_rep = True

        # Form feedback
        if not body_straight:
            feedback = "Keep your body straight! Don't sag your hips"
        elif elbow_angle < 70 and self.current_state == "down":
            feedback = "Don't go too deep! Stop at 90 degrees"

        # If no specific feedback, give general guidance
        if not feedback:
            if self.current_state == "up":
                feedback = "Lower your body with control"
            elif self.current_state == "down":
                feedback = "Push through your palms to come up"

        return feedback, count_rep

    def analyze_shoulder_press(self, landmarks):
        """Analyze overhead shoulder press form and count reps"""
        feedback = ""
        count_rep = False

        # Get key landmarks
        shoulder = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER.value)
        elbow = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_ELBOW.value)
        wrist = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_WRIST.value)
        hip = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_HIP.value)

        if None in [shoulder, elbow, wrist, hip]:
            return "Cannot detect arm position. Please ensure your arm is visible.", False

        # Calculate key angles
        elbow_angle = self.calculate_angle(shoulder, elbow, wrist)
        elbow_angle = self.smooth_angle("elbow", elbow_angle)

        # Calculate shoulder angle relative to hip
        shoulder_angle = self.calculate_angle(hip, shoulder, elbow)
        shoulder_angle = self.smooth_angle("shoulder", shoulder_angle)

        # Detect press phases
        if not self.rep_started and elbow_angle < 110 and shoulder_angle > 70:
            # Starting position - arm at ~90 degrees
            self.rep_started = True
            self.current_state = "starting"
            feedback = "Begin pressing the weight overhead"

        if self.rep_started:
            if self.current_state == "starting" and elbow_angle > 160:
                # Arm extended overhead
                self.current_state = "up"
                feedback = "Good! Now lower the weight with control"

            elif self.current_state == "up" and elbow_angle < 110:
                # Arm back to starting position
                self.current_state = "starting"
                feedback = "Good rep! Keep your core engaged"
                count_rep = True

        # Form feedback
        if shoulder_angle < 70 and self.current_state in ["starting", "up"]:
            feedback = "Keep your elbows forward! Don't let them drift back"

        # Look for arched back (approximation - would be better with more points)
        if hip is not None and shoulder is not None:
            if hip[1] < shoulder[1]:  # If hip y-coordinate is higher than shoulder (leaning back)
                feedback = "Watch your posture! Don't arch your back"

        # If no specific feedback, give general guidance
        if not feedback:
            if self.current_state == "starting":
                feedback = "Press the weight directly overhead"
            elif self.current_state == "up":
                feedback = "Lower the weight with control to shoulder level"

        return feedback, count_rep

    def analyze_squat(self, landmarks):
        """Analyze squat form and count reps"""
        feedback = ""
        count_rep = False

        # Get key landmarks for squat analysis
        hip = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_HIP.value)
        knee = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_KNEE.value)
        ankle = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_ANKLE.value)
        shoulder = self.get_coordinates(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER.value)

        if None in [hip, knee, ankle, shoulder]:
            return "Cannot detect all body points. Ensure your full side is visible.", False

        # Calculate key angles
        knee_angle = self.calculate_angle(hip, knee, ankle)
        knee_angle = self.smooth_angle("knee", knee_angle)

        hip_angle = self.calculate_angle(shoulder, hip, knee)
        hip_angle = self.smooth_angle("hip", hip_angle)

        # Track relative positions for form analysis
        knee_x, knee_y = knee
        ankle_x, ankle_y = ankle
        hip_x, hip_y = hip
        shoulder_x, shoulder_y = shoulder

        # Check if knees are past toes (a common squat mistake)
        knees_past_toes = knee_x > ankle_x + 0.05  # Add threshold to allow slight forward movement

        # Check for rounded back (using shoulder-hip alignment as an approximation)
        back_angle = abs(math.atan2(shoulder_y - hip_y, shoulder_x - hip_x) * 180.0 / math.pi)
        rounded_back = back_angle < 70  # If back is leaning too far forward

        # Detect squat phases
        if not self.rep_started and knee_angle > 160 and hip_angle > 160:
            # Starting in standing position
            self.rep_started = True
            self.current_state = "standing"
            feedback = "Begin the squat by bending your knees and hips"

        if self.rep_started:
            if self.current_state == "standing" and knee_angle < 110 and hip_angle < 110:
                # Bottom of squat
                self.current_state = "squatting"

                # Check depth
                if knee_angle < 90:
                    feedback = "Good depth! Now stand back up"
                else:
                    feedback = "Try to squat deeper - aim for 90° or lower at the knee"

            elif self.current_state == "squatting" and knee_angle > 160 and hip_angle > 160:
                # Back to standing position
                self.current_state = "standing"
                feedback = "Good rep! Keep your back straight"
                count_rep = True

        # Form feedback priority
        if knees_past_toes:
            feedback = "Keep your knees behind your toes! Shift weight to heels"
        elif rounded_back:
            feedback = "Straighten your back! Look forward, chest up"
        elif self.current_state == "squatting" and hip_angle > knee_angle + 30:
            feedback = "Lower your hips more - this looks more like a deadlift"

        # If no specific feedback, give general guidance
        if not feedback:
            if self.current_state == "standing":
                feedback = "Begin squat with hips back, knees in line with feet"
            elif self.current_state == "squatting":
                feedback = "Keep weight in heels, push through legs to stand"

        return feedback, count_rep

    def analyze_exercise(self, frame, results):
        """
        Analyze the exercise form based on the selected exercise.
        Returns: (feedback_message, count_rep)
        """
        if not results or not results.pose_landmarks:
            return "No person detected", False

        landmarks = results.pose_landmarks.landmark

        # Choose the appropriate analysis based on exercise type
        if self.exercise_name == "Deadlift":
            return self.analyze_deadlift(landmarks)
        elif self.exercise_name == "Bicep Curl":
            return self.analyze_bicep_curl(landmarks)
        elif self.exercise_name == "Lunge":
            return self.analyze_lunge(landmarks)
        elif self.exercise_name == "Push-Up":
            return self.analyze_pushup(landmarks)
        elif self.exercise_name == "Shoulder Press":
            return self.analyze_shoulder_press(landmarks)
        elif self.exercise_name == "Squat":
            return self.analyze_squat(landmarks)

        return "Exercise analysis not implemented", False

    @pyqtSlot(QImage, np.ndarray, object)
    def update_frame(self, qt_img, frame, results):
        # Display the frame with pose landmarks
        self.video_label.setPixmap(QPixmap.fromImage(qt_img).scaled(
            self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio))

        # Check if user is in correct position first
        position_correct, position_feedback = self.check_view_position(frame, results)
        self.position_correct = position_correct

        # If position is correct, analyze the exercise
        feedback = position_feedback
        count_rep = False

        if position_correct:
            feedback, count_rep = self.analyze_exercise(frame, results)

        # Update rep counter if a repetition is completed
        if count_rep:
            self.rep_count += 1
            self.rep_counter_label.setText(str(self.rep_count))
        green_feedback = "Good" in feedback or "good" in feedback
        yellow_feedback = "Watch" in feedback or "Keep" in feedback or "Don't" in feedback
        if (self.feedback_count % 60) > 50 or green_feedback or yellow_feedback:
            self.feedback_count = 0
            self.feedback_label.setText(feedback)
            # Update feedback label
            if green_feedback:
                self.feedback_label.setStyleSheet("color: white; background-color: #28a745; padding: 8px;")
            elif yellow_feedback:
                self.feedback_label.setStyleSheet("color: black; background-color: #ffc107; padding: 8px;")
            else:
                self.feedback_label.setStyleSheet("color: white; background-color: #555555; padding: 8px;")

        self.last_feedback = feedback
        self.feedback_count += 1

    def go_back(self):
        self.stop_video()
        self.go_back_signal.emit()

    def closeEvent(self, event):
        self.stop_video()
        event.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("FitMate")
        self.setMinimumSize(1200, 900)

        # Create stacked widget to switch between screens
        self.stacked_widget = QStackedWidget()

        # Create the main menu widget
        self.main_menu = QWidget()
        self.create_main_menu()

        # Add the main menu to the stacked widget
        self.stacked_widget.addWidget(self.main_menu)

        # Set as central widget
        self.setCentralWidget(self.stacked_widget)

    def create_main_menu(self):
        # Main layout
        main_layout = QVBoxLayout()

        # Title
        title_label = QLabel("FitMate")
        title_label.setFont(QFont('Blinker', 36, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QLabel("Let's select an exercise to begin:")
        subtitle_label.setFont(QFont('Blinker', 24))
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(subtitle_label)

        # Exercise buttons in a grid layout
        exercises_layout = QGridLayout()

        # Define exercises
        exercises = [
            "Squat", "Deadlift", "Bicep Curl",
            "Lunge", "Push-Up", "Shoulder Press"
        ]

        # Create buttons for each exercise
        row, col = 0, 0
        for exercise in exercises:
            button = QPushButton(exercise)
            button.setMinimumSize(200, 150)
            button.setFont(QFont('Blinker', 20))
            # Store the exercise name as property to access it when clicked
            button.setProperty("exercise", exercise)
            button.clicked.connect(self.open_exercise)

            exercises_layout.addWidget(button, row, col)

            # Update grid position
            col += 1
            if col > 1:  # 2 columns
                col = 0
                row += 1

        # Add some spacing
        main_layout.addSpacing(20)

        # Add the grid to the main layout
        main_layout.addLayout(exercises_layout)

        # Add some spacing at the bottom
        main_layout.addSpacing(20)

        # Apply the layout to the main menu widget
        self.main_menu.setLayout(main_layout)

    def open_exercise(self):
        # Get the sender button
        button = self.sender()
        exercise_name = button.property("exercise")

        # Create exercise screen
        exercise_widget = ExerciseWidget(exercise_name)
        exercise_widget.go_back_signal.connect(self.show_main_menu)

        # Add to stacked widget and show it
        self.stacked_widget.addWidget(exercise_widget)
        self.stacked_widget.setCurrentWidget(exercise_widget)

    def show_main_menu(self):
        # Return to main menu and remove the exercise widget
        self.stacked_widget.setCurrentWidget(self.main_menu)
        # Remove the last widget (the exercise widget)
        widget = self.stacked_widget.widget(self.stacked_widget.count() - 1)
        self.stacked_widget.removeWidget(widget)
        widget.deleteLater()


def main():
    app = QApplication(sys.argv)
    # Load and apply stylesheet
    stylesheet = load_stylesheet("style.qss")
    if stylesheet:
        app.setStyleSheet(stylesheet)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
