from PyQt5.QtCore import QFile
import pyttsx3

def load_stylesheet(file_path):
    """Load QSS stylesheet from file."""
    file_path = file_path.replace('/', '\\')
    qss_file = QFile(file_path)
    if qss_file.exists():
        qss_file.open(QFile.ReadOnly)
        stylesheet = str(qss_file.readAll(), encoding='utf-8')
        return stylesheet
    return ""

def speak(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 170)  # Speed (default is around 200)
    engine.setProperty('volume', 1.0)  # Volume: 0.0 to 1.0
    engine.say(text)
    engine.runAndWait()