from PyQt5.QtCore import QFile


def load_stylesheet(file_path):
    """Load QSS stylesheet from file."""
    file_path = file_path.replace('/', '\\')
    qss_file = QFile(file_path)
    if qss_file.exists():
        qss_file.open(QFile.ReadOnly)
        stylesheet = str(qss_file.readAll(), encoding='utf-8')
        return stylesheet
    return ""
