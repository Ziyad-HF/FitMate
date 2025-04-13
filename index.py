import sys
import cv2
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QGridLayout,
                             QFrame, QStackedWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QSize
from PyQt5.QtGui import QImage, QPixmap, QFont, QIcon


class VideoThread(QThread):
    update_frame = pyqtSignal(QImage)

    def __init__(self, camera_id=0):
        super().__init__()
        self.camera_id = camera_id
        self.running = False

    def run(self):
        self.running = True
        cap = cv2.VideoCapture(self.camera_id)

        while self.running:
            ret, frame = cap.read()
            if not ret:
                break

            # Convert the frame to RGB format
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape

            # Create QImage from the RGB frame
            qt_img = QImage(rgb_frame.data, w, h, w * ch, QImage.Format.Format_RGB888)

            # Emit signal with the image
            self.update_frame.emit(qt_img)

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
        self.initUI()

    def initUI(self):
        # Main layout
        layout = QVBoxLayout()

        # Title
        title_label = QLabel(f"{self.exercise_name} - AI Trainer")
        title_label.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Camera Feed Frame
        self.video_label = QLabel()
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: #333333;")

        # Controls
        controls_layout = QHBoxLayout()

        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_video)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_video)
        self.stop_button.setEnabled(False)

        self.back_button = QPushButton("Back to Menu")
        self.back_button.clicked.connect(self.go_back)

        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.back_button)

        # Stats layout - Placeholder for future implementation
        stats_layout = QVBoxLayout()
        stats_frame = QFrame()
        stats_frame.setFrameShape(QFrame.Shape.StyledPanel)
        stats_frame.setStyleSheet("background-color: #f0f0f0;")

        stats_label = QLabel("Exercise Statistics (Coming Soon)")
        stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_inner_layout = QVBoxLayout()
        stats_inner_layout.addWidget(stats_label)
        stats_frame.setLayout(stats_inner_layout)
        stats_layout.addWidget(stats_frame)

        # Add all widgets to main layout
        layout.addWidget(title_label)
        layout.addWidget(self.video_label)
        layout.addLayout(controls_layout)
        layout.addLayout(stats_layout)

        self.setLayout(layout)

    def start_video(self):
        self.video_thread = VideoThread()
        self.video_thread.update_frame.connect(self.update_frame)
        self.video_thread.start()

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_video(self):
        if self.video_thread is not None:
            self.video_thread.stop()
            self.video_thread = None

        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    @pyqtSlot(QImage)
    def update_frame(self, qt_img):
        # This is where we'll eventually integrate MediaPipe pose detection
        # For now, just display the raw frame
        self.video_label.setPixmap(QPixmap.fromImage(qt_img).scaled(
            self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio))

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
        self.setWindowTitle("AI Fitness Trainer")
        self.setMinimumSize(800, 600)

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
        title_label = QLabel("AI Fitness Trainer")
        title_label.setFont(QFont('Arial', 24, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QLabel("Select an exercise to begin:")
        subtitle_label.setFont(QFont('Arial', 14))
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
            button.setMinimumSize(180, 120)
            button.setFont(QFont('Arial', 12))
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
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()