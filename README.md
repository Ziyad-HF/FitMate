
<p align="center">
  <img src="media/banner.png" alt="AI Fitness Trainer Banner" width="800">
</p>

# AI Fitness Trainer (Desktop App)

## 📚 Overview
Welcome to **FitMate** — a real-time desktop application that analyzes your exercises using AI-based pose estimation.  
Get **instant feedback**, **count your reps**, and **improve your form** using cutting-edge 3D body tracking technology powered by **MediaPipe**.

---

## 🎯 Supported Exercises
- 💪 **Bicep Curl**
- 🏋️ **Lunge**
- 🏋️ **Squat**
- 🤸 **Push-Ups**
- 🏋️‍♂️ **Shoulder Press**
- 🏋️‍♂️ **Deadlift**

Each exercise provides real-time feedback and tracks reps based on your movement and joint angles.

---

## 🛠️ Technologies Used
- Python 3
- OpenCV
- PyQt5 (for GUI)
- MediaPipe Pose (3D Landmark Model)
- NumPy

---

## 🚀 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Ziyad-HF/FitMate.git
   cd FitMate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python main.py
   ```

---

## 🎥 Screenshots & Demos

| Exercise | Demo |
| :--- | :--- |
| Bicep Curl | ![](media/bicep.gif) |
| Squat | ![](media/squat.gif) |
| Lunge | ![](media/lunge.gif) |
| Push-Ups | ![](media/pushup.gif) |
| Shoulder Press | ![](media/shoulder_press.gif) |
| Deadlift | ![](media/deadlift.gif) |

---

## ⚡ How It Works

- Real-time webcam capture
- Detects **3D body landmarks** using MediaPipe
- Calculates important joint angles for each exercise
- Gives immediate feedback if your form needs adjustment
- Counts the number of correct repetitions automatically

---

## 📢 Notes
- Make sure your **full body is visible** in the camera.
- Use a **well-lit environment** for better pose detection.
- Supports both **frontal** and **side views** depending on the exercise.

---

