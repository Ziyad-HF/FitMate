from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                             QPushButton, QLabel, QGridLayout,
                             QStackedWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from gui.exercises_widget_ui import ExerciseWidget

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
