import sys
import random
import pygame
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QFileDialog, QComboBox, QHBoxLayout
from PySide6.QtGui import QPalette, QColor, QPainter, QBrush
import vlc
import librosa

# إعدادات pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.Surface((WIDTH, HEIGHT))  # استخدام سطح بدلاً من نافذة منفصلة
BLACK = (0, 0, 0)

# الألوان النيون
NEON_COLORS = [
    (0, 255, 255),    # أزرق نيون
    (255, 255, 0),    # أصفر نيون
    (255, 0, 255),    # وردي نيون
    (0, 255, 0),      # أخضر نيون
    (150, 0, 255),    # بنفسجي نيون
    (255, 50, 50)     # أحمر نيون
]

# إعدادات الأعمدة
NUM_BARS = 60
BAR_WIDTH = WIDTH // NUM_BARS
MAX_BAR_HEIGHT = HEIGHT - 100

# محاكاة بيانات الصوت (موجات تتحرك)
def get_fake_freq_data(tick):
    return np.abs(np.sin(np.linspace(0, 3 * np.pi, NUM_BARS) + tick)) * MAX_BAR_HEIGHT

class DJVisualizerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎶 DJ Visualizer")
        self.setGeometry(100, 100, 800, 600)
        self.setStyle()

        # إعدادات VLC
        self.instance = vlc.Instance()
        self.media_player = self.instance.media_player_new()

        # واجهة المستخدم
        self.init_ui()

        # Timer لتحديث الألوان
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_background)
        self.timer.start(500)

        # التأثيرات
        self.theme_type = 'static'  # النوع الافتراضي: ثابت (لا يتغير)
        self.last_audio_data = None

        # تفعيل pygame للرؤية في واجهة المستخدم
        self.clock = pygame.time.Clock()
        self.tick = 0
        self.running = True

    def setStyle(self):
        # تعيين الألوان والإعدادات الخاصة بالتطبيق
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(30, 30, 30))  # خلفية داكنة
        palette.setColor(QPalette.WindowText, Qt.white)
        self.setPalette(palette)

    def init_ui(self):
        layout = QVBoxLayout()

        # عنوان التطبيق
        self.title_label = QLabel("🎧 مشغل الفيديو والموسيقى", self)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 24px; color: white;")
        layout.addWidget(self.title_label)

        # زر اختيار الملف
        self.add_btn = self.create_realistic_button("📂 اختيار ملف", "green", self.add_file)
        layout.addWidget(self.add_btn)

        # اسم الملف المحدد
        self.file_label = QLabel("لم يتم اختيار ملف", self)
        self.file_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.file_label)

        # أزرار التحكم الواقعية
        self.control_layout = QVBoxLayout()
        self.play_btn = self.create_realistic_button("▶️ تشغيل", "blue", self.play_media)
        self.control_layout.addWidget(self.play_btn)

        self.pause_btn = self.create_realistic_button("⏸️ إيقاف مؤقت", "orange", self.pause_media)
        self.control_layout.addWidget(self.pause_btn)

        self.stop_btn = self.create_realistic_button("⏹️ إيقاف", "red", self.stop_media)
        self.control_layout.addWidget(self.stop_btn)

        layout.addLayout(self.control_layout)

        # قائمة اختيار الثيم
        self.theme_selector = QComboBox(self)
        self.theme_selector.addItem("🎵 تدرج لوني ثابت")
        self.theme_selector.addItem("🎶 تدرج تفاعلي مع الموسيقى")
        self.theme_selector.addItem("✨ وميض موسيقي")
        self.theme_selector.currentIndexChanged.connect(self.on_theme_changed)
        layout.addWidget(self.theme_selector)

        self.setLayout(layout)

    def create_realistic_button(self, text, color, function):
        """إنشاء زر واقعي مخصص مع تأثيرات تفاعلية"""
        button = QPushButton(text, self)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border-radius: 10px;
                font-size: 18px;
                padding: 12px;
                border: 2px solid {color};
            }}
            QPushButton:hover {{
                background-color: {self.adjust_color(color, 20)};
            }}
            QPushButton:pressed {{
                background-color: {self.adjust_color(color, -20)};
            }}
        """)
        button.clicked.connect(function)
        return button

    def adjust_color(self, color, amount):
        """تعديل اللون بتدرج لزيادة أو تقليل الشدة"""
        color_hex = QColor(color)
        r = max(0, min(255, color_hex.red() + amount))
        g = max(0, min(255, color_hex.green() + amount))
        b = max(0, min(255, color_hex.blue() + amount))
        return QColor(r, g, b).name()

    def add_file(self):
        """اختيار ملف لتشغيله"""
        self.file_path, _ = QFileDialog.getOpenFileName(self, "اختيار ملف", "", "ملفات الوسائط (*.mp3 *.mp4 *.avi *.mkv *.wav)")
        if self.file_path:
            media = self.instance.media_new(self.file_path)
            self.media_player.set_media(media)
            self.file_label.setText(f"📁 الملف: {self.file_path.split('/')[-1]}")
            self.extract_audio_features(self.file_path)

    def play_media(self):
        """تشغيل الوسائط"""
        if self.file_path:
            self.media_player.play()
            self.is_playing = True

    def pause_media(self):
        """إيقاف مؤقت للوسائط"""
        if self.is_playing:
            self.media_player.pause()
            self.is_playing = False

    def stop_media(self):
        """إيقاف الوسائط"""
        self.media_player.stop()
        self.is_playing = False

    def update_background(self):
        """تغيير الخلفية بناءً على الثيم المحدد"""
        if self.theme_type == 'static':
            self.set_static_background()
        elif self.theme_type == 'interactive':
            if self.last_audio_data is not None:
                self.set_interactive_background(self.last_audio_data)
        elif self.theme_type == 'flash':
            self.set_flash_background()

    def set_static_background(self):
        """تطبيق خلفية ثابتة"""
        color = QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        self.setStyleSheet(f"QWidget {{background-color: {color.name()};}}")

    def set_interactive_background(self, audio_data):
        """تطبيق تدرج لوني تفاعلي مع الموسيقى"""
        avg_volume = np.mean(audio_data)
        if avg_volume < 0.1:
            color = QColor(30, 30, 30)  # لون داكن
        elif avg_volume < 0.2:
            color = QColor(100, 100, 100)  # لون أفتح
        else:
            color = QColor(255, 0, 0)  # لون أحمر ساطع
        self.setStyleSheet(f"QWidget {{background-color: {color.name()};}}")

    def set_flash_background(self):
        """تطبيق تأثير وميض الأضواء"""
        color = QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        self.setStyleSheet(f"QWidget {{background-color: {color.name()};}}")

    def on_theme_changed(self):
        """تغيير الثيم بناءً على اختيار المستخدم"""
        current_index = self.theme_selector.currentIndex()
        if current_index == 0:
            self.theme_type = 'static'
        elif current_index == 1:
            self.theme_type = 'interactive'
        elif current_index == 2:
            self.theme_type = 'flash'

    def extract_audio_features(self, file_path):
        """استخراج الميزات الصوتية للموسيقى"""
        y, sr = librosa.load(file_path, sr=None)
        self.last_audio_data = librosa.feature.rms(y=y)[0]  # استخراج قوة الإشارة الصوتية

# بدء التطبيق
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DJVisualizerApp()
    window.show()
    sys.exit(app.exec())
