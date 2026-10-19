#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
YouTube Downloader Pro (PyQt6 + yt-dlp + ffmpeg)
یک ابزار گرافیکی پیشرفته، امن و پایدار برای دانلود ویدیو، پلی‌لیست، زیرنویس و صدا از یوتیوب
"""

import json
import os
import re
import shutil
import subprocess
import sys
from urllib.parse import urlparse

import requests
from PyQt6.QtCore import QSettings, Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QFont, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# ========================== استایل مدرن برنامه ==========================
STYLESHEET = """
QWidget {
    background-color: #0f172a;
    color: #f1f5f9;
    font-family: "Vazirmatn", "Segoe UI", "Tahoma", "Arial", sans-serif;
    font-size: 10pt;
}
QGroupBox {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 16px;
    font-weight: bold;
    color: #38bdf8;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 2px 14px;
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
}
QLabel {
    background-color: transparent;
    color: #e2e8f0;
}
QTextEdit, QComboBox, QLineEdit {
    background-color: #0f172a;
    color: #f8fafc;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 6px 8px;
    selection-background-color: #0284c7;
}
QTextEdit:focus, QComboBox:focus, QLineEdit:focus {
    border: 1px solid #38bdf8;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #1e293b;
    color: #f8fafc;
    selection-background-color: #0284c7;
    border: 1px solid #475569;
}
QCheckBox {
    background-color: transparent;
    color: #e2e8f0;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #64748b;
    background-color: #0f172a;
}
QCheckBox::indicator:checked {
    background-color: #0284c7;
    border-color: #38bdf8;
}
QPushButton {
    background-color: #0284c7;
    color: #ffffff;
    border: none;
    padding: 8px 14px;
    border-radius: 6px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #0369a1;
}
QPushButton:pressed {
    background-color: #075985;
}
QPushButton:disabled {
    background-color: #334155;
    color: #64748b;
}
QPushButton#btnSuccess {
    background-color: #059669;
}
QPushButton#btnSuccess:hover {
    background-color: #047857;
}
QPushButton#btnSuccess:disabled {
    background-color: #334155;
    color: #64748b;
}
QPushButton#btnPurple {
    background-color: #7c3aed;
}
QPushButton#btnPurple:hover {
    background-color: #6d28d9;
}
QPushButton#btnPurple:disabled {
    background-color: #334155;
    color: #64748b;
}
QPushButton#btnDanger {
    background-color: #dc2626;
}
QPushButton#btnDanger:hover {
    background-color: #b91c1c;
}
QPushButton#btnDanger:disabled {
    background-color: #334155;
    color: #64748b;
}
QPushButton#btnSecondary {
    background-color: #334155;
    color: #e2e8f0;
    border: 1px solid #475569;
}
QPushButton#btnSecondary:hover {
    background-color: #475569;
}
QProgressBar {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    text-align: center;
    color: #f8fafc;
    font-weight: bold;
    min-height: 22px;
}
QProgressBar::chunk {
    background-color: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #0284c7, stop: 1 #10b981
    );
    border-radius: 5px;
}
QFrame#statCard {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 4px 8px;
}
QScrollBar:vertical {
    background: #0f172a;
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #334155;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #475569;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

# گزینه‌های پیش‌فرض کیفیت (همیشه در دسترس حتی بدون واکشی قبلی)
DEFAULT_QUALITY_PRESETS = [
    ("بهترین کیفیت ممکن (Best Video + Audio)", "bestvideo+bestaudio/best"),
    ("کیفیت 1080p Full HD (MP4)", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"),
    ("کیفیت 720p HD (MP4)", "bestvideo[height<=720]+bestaudio/best[height<=720]/best"),
    ("کیفیت 480p SD (MP4)", "bestvideo[height<=480]+bestaudio/best[height<=480]/best"),
    ("کیفیت 360p (کم‌حجم)", "bestvideo[height<=360]+bestaudio/best[height<=360]/best"),
    ("فقط صدا - MP3 (320kbps)", "AUDIO_MP3"),
    ("فقط صدا - M4A (Original Audio)", "AUDIO_M4A"),
]


# ========================== توابع کمکی و امنیتی ==========================
def validate_url(url: str) -> bool:
    """
    اعتبارسنجی ایمن آدرس اینترنتی برای جلوگیری از تزریق آرگومان (Argument Injection)
    """
    if not url or not isinstance(url, str):
        return False
    u = url.strip()
    if u.startswith("-") or any(c in u for c in ("\n", "\r", "\0")):
        return False
    try:
        parsed = urlparse(u)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def build_proxy_url(proxy_type: str, proxy_addr: str) -> str:
    """ساخت و اعتبارسنجی آدرس کامل پروکسی از نوع و آدرس وارد شده توسط کاربر"""
    if proxy_type == "None" or not proxy_addr or not proxy_addr.strip():
        return ""
    addr = proxy_addr.strip()
    addr = re.sub(r"^(https?|socks4a?|socks5h?)://", "", addr, flags=re.IGNORECASE)
    if addr.startswith("-") or not re.match(r"^[a-zA-Z0-9._:@\-]+$", addr):
        return ""
    scheme_map = {
        "HTTP": "http",
        "SOCKS4": "socks4",
        "SOCKS5": "socks5",
    }
    scheme = scheme_map.get(proxy_type.upper(), "")
    return f"{scheme}://{addr}" if scheme else ""


def build_base_cmd(
    browser: str,
    proxy_url: str,
    allow_playlist: bool = False,
    sub_enabled: bool = False,
    sub_langs: str = "fa,en",
    embed_subs: bool = False,
) -> list:
    """ساخت لیست آرگومان‌های پایه yt-dlp به صورت امن (بدون shell=True)"""
    cmd = ["yt-dlp", "--newline"]

    if proxy_url:
        cmd.extend(["--proxy", proxy_url])

    if browser and browser.lower() != "none":
        cmd.extend(["--cookies-from-browser", browser.lower()])

    if allow_playlist:
        cmd.append("--yes-playlist")
    else:
        cmd.append("--no-playlist")

    if sub_enabled:
        cmd.extend(["--write-subs", "--write-auto-subs", "--sub-langs", sub_langs])
        if embed_subs:
            cmd.append("--embed-subs")

    cmd.extend([
        "--retries", "50",
        "--fragment-retries", "50",
        "--http-chunk-size", "10M",
    ])
    return cmd


def format_duration(seconds) -> str:
    """تبدیل ثانیه به فرمت خوانا HH:MM:SS یا MM:SS"""
    if not seconds or not isinstance(seconds, (int, float)):
        return "نامشخص"
    seconds = int(seconds)
    hrs, rem = divmod(seconds, 3600)
    mins, secs = divmod(rem, 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def format_bytes(num_bytes) -> str:
    """تبدیل بایت به فرمت خوانا MiB / GiB"""
    if not num_bytes or not isinstance(num_bytes, (int, float)) or num_bytes <= 0:
        return "نامشخص"
    for unit in ["B", "KiB", "MiB", "GiB"]:
        if num_bytes < 1024.0 or unit == "GiB":
            return f"{num_bytes:.1f} {unit}" if unit != "B" else f"{int(num_bytes)} B"
        num_bytes /= 1024.0
    return "نامشخص"


def terminate_process_safely(proc: subprocess.Popen):
    """توقف ایمن پروسه در ویندوز و لینوکس"""
    if proc is None or proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
    except Exception:
        pass


# ====================== ترد دریافت اطلاعات ویدیو ======================
class GetFormatsThread(QThread):
    finished = pyqtSignal(str, list)          # (متن لاگ جدول فرمت‌ها، لیست فرمت‌های استخراج‌شده)
    metadata = pyqtSignal(dict)               # اطلاعات کامل ویدیو (عنوان، کانال، زمان، بازدید، تامبنیل)
    error_signal = pyqtSignal(str)

    def __init__(self, url: str, browser: str, proxy_url: str):
        super().__init__()
        self.url = url
        self.browser = browser
        self.proxy_url = proxy_url

    def run(self):
        if not validate_url(self.url):
            self.error_signal.emit("خطا: آدرس لینک وارد شده معتبر نیست (باید با http یا https شروع شود).")
            return

        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        cmd = build_base_cmd(self.browser, self.proxy_url, allow_playlist=False)
        cmd.extend(["--dump-single-json", "--", self.url])

        try:
            output = subprocess.check_output(
                cmd, text=True, stderr=subprocess.STDOUT, creationflags=creationflags
            )
            json_line = ""
            for line in reversed(output.strip().splitlines()):
                if line.strip().startswith("{") and line.strip().endswith("}"):
                    json_line = line.strip()
                    break
            if not json_line:
                json_line = output.strip()

            data = json.loads(json_line)
            title = data.get("title") or "عنوان نامشخص"
            uploader = data.get("uploader") or data.get("channel") or "نامشخص"
            duration_str = format_duration(data.get("duration"))
            view_count = data.get("view_count")
            views_str = f"{view_count:,}" if isinstance(view_count, int) else "نامشخص"
            thumb_url = data.get("thumbnail")

            self.metadata.emit({
                "title": title,
                "uploader": uploader,
                "duration": duration_str,
                "views": views_str,
                "thumbnail": thumb_url,
            })

            formats = data.get("formats", [])
            parsed_formats = []
            table_lines = [
                f"{'ID':<10} {'EXT':<6} {'RESOLUTION':<14} {'FPS':<6} {'VCODEC':<12} {'SIZE':<12} {'NOTE'}",
                "-" * 78,
            ]

            for f in reversed(formats):
                fmt_id = str(f.get("format_id", ""))
                ext = f.get("ext", "")
                vcodec = f.get("vcodec", "none")
                acodec = f.get("acodec", "none")
                height = f.get("height")
                width = f.get("width")
                fps = f.get("fps") or ""
                filesize = f.get("filesize") or f.get("filesize_approx")
                size_str = format_bytes(filesize)
                note = f.get("format_note", "")

                if vcodec != "none" and height:
                    res_str = f"{width}x{height}" if width else f"{height}p"
                    short_vcodec = vcodec.split(".")[0]
                    fps_str = f"{int(fps)}fps" if fps else ""
                    table_lines.append(
                        f"{fmt_id:<10} {ext:<6} {res_str:<14} {fps_str:<6} {short_vcodec:<12} {size_str:<12} {note}"
                    )
                    label = f"{height}p ({res_str}) | {ext.upper()} [{short_vcodec}] - {size_str} (ID: {fmt_id})"
                    selector = f"{fmt_id}+bestaudio/best" if acodec == "none" else fmt_id
                    parsed_formats.append((label, selector))

            self.finished.emit("\n".join(table_lines), parsed_formats)

        except subprocess.CalledProcessError as e:
            error_output = e.output or str(e)
            if "not available on this app" in error_output or "403" in error_output:
                self.error_signal.emit(
                    "خطا: یوتیوب درخواست را مسدود کرد (403 Forbidden).\n"
                    "پیشنهاد: دکمه «به‌روزرسانی yt-dlp» را بزنید یا از کوکی مرورگر / پروکسی معتبر استفاده کنید."
                )
            else:
                self.error_signal.emit(f"خطا در دریافت اطلاعات ویدیو:\n{error_output}")
        except Exception as e:
            self.error_signal.emit(f"خطای پیش‌بینی نشده در واکشی اطلاعات:\n{e}")


# ====================== ترد دانلود ویدیو و صدا ======================
class DownloadThread(QThread):
    progress = pyqtSignal(int)
    telemetry = pyqtSignal(str, str, str)  # (speed, eta, size)
    message = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)  # (success, canceled_or_msg)

    def __init__(self, cmd_list: list):
        super().__init__()
        self.cmd_list = cmd_list
        self.process = None
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True
        terminate_process_safely(self.process)

    def run(self):
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            self.process = subprocess.Popen(
                self.cmd_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=creationflags,
            )
        except Exception as e:
            self.message.emit(f"خطا در اجرای دستور دانلود: {e}")
            self.finished_signal.emit(False, "error")
            return

        re_progress = re.compile(r"(\d+(?:\.\d+)?)%")
        re_speed = re.compile(r"at\s+([0-9.]+\s*[KMGTP]?i?B/s)", re.IGNORECASE)
        re_eta = re.compile(r"ETA\s+([0-9:]+)", re.IGNORECASE)
        re_size = re.compile(r"of\s+~?\s*([0-9.]+\s*[KMGTP]?i?B)", re.IGNORECASE)

        for line in self.process.stdout:
            if self._is_cancelled:
                break
            clean_line = line.strip()
            if not clean_line:
                continue

            m_prog = re_progress.search(clean_line)
            if m_prog:
                val = min(100, max(0, int(float(m_prog.group(1)))))
                self.progress.emit(val)
                speed = re_speed.search(clean_line)
                eta = re_eta.search(clean_line)
                size = re_size.search(clean_line)
                self.telemetry.emit(
                    speed.group(1) if speed else "-",
                    eta.group(1) if eta else "-",
                    size.group(1) if size else "-",
                )

            self.message.emit(clean_line)

        self.process.wait()

        if self._is_cancelled:
            self.message.emit("[لغو شد] عملیات دانلود توسط کاربر متوقف شد.")
            self.progress.emit(0)
            self.finished_signal.emit(False, "cancelled")
        elif self.process.returncode == 0:
            self.message.emit("✔ دانلود با موفقیت کامل شد!")
            self.progress.emit(100)
            self.telemetry.emit("تمام شد", "00:00", "-")
            self.finished_signal.emit(True, "ok")
        else:
            self.message.emit(f"✖ فرآیند دانلود با کد خطای {self.process.returncode} متوقف شد.")
            self.progress.emit(0)
            self.finished_signal.emit(False, "error")


# ====================== ترد استخراج صدا از فایل محلی ======================
class ExtractAudioThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, cmd_list: list):
        super().__init__()
        self.cmd_list = cmd_list
        self.process = None
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True
        terminate_process_safely(self.process)

    def run(self):
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            self.process = subprocess.Popen(
                self.cmd_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=creationflags,
            )
            _, stderr = self.process.communicate()
            if self._is_cancelled:
                self.error.emit("استخراج صدا توسط کاربر لغو شد.")
                return
            if self.process.returncode == 0:
                self.finished.emit("صدا با موفقیت با کیفیت 320kbps استخراج شد!")
            else:
                error_msg = f"خطا در استخراج صدا:\n{stderr}"
                if "Audio:" not in stderr:
                    error_msg += "\n\nفایل انتخاب‌شده جریان صوتی (Audio Stream) ندارد!"
                self.error.emit(error_msg)
        except Exception as e:
            self.error.emit(f"خطا در اجرای ffmpeg: {e}")


# ====================== ترد به‌روزرسانی yt-dlp ======================
class UpdateYtDlpThread(QThread):
    finished = pyqtSignal(bool, str)

    def run(self):
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            res = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
                capture_output=True,
                text=True,
                creationflags=creationflags,
            )
            if res.returncode == 0:
                self.finished.emit(True, res.stdout.strip())
            else:
                self.finished.emit(False, res.stderr.strip() or res.stdout.strip())
        except Exception as e:
            self.finished.emit(False, str(e))


# ====================== کلاس اصلی برنامه ======================
class YouTubeDownloader(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("YouTubeDownloaderPro", "Settings")
        self.downloaded_file = None
        self.custom_path = self.settings.value("custom_path", "")
        self.download_queue = []
        self.current_download_index = 0
        self.current_batch_mode = "video"
        self.active_thread = None

        self.initUI()
        self.load_saved_settings()
        self.populate_default_qualities()
        self.check_dependencies()

    def initUI(self):
        self.setWindowTitle("YouTube Downloader Pro v2.0")
        self.setGeometry(80, 50, 1050, 880)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(14, 14, 14, 14)

        # ==================== نوار هدر و وضعیت مسیر ذخیره ====================
        header_frame = QFrame()
        header_frame.setObjectName("statCard")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 8, 12, 8)

        title_lbl = QLabel("▶ دانلودر حرفه‌ای یوتیوب (YouTube Downloader Pro)")
        title_lbl.setStyleSheet("font-size: 12pt; font-weight: bold; color: #38bdf8;")

        self.path_status_lbl = QLabel()
        self.path_status_lbl.setStyleSheet("color: #94a3b8; font-size: 9pt;")
        self.update_path_label()

        self.open_folder_btn = QPushButton("باز کردن پوشه ذخیره")
        self.open_folder_btn.setObjectName("btnSecondary")
        self.open_folder_btn.clicked.connect(self.open_save_folder)

        self.update_ytdlp_btn = QPushButton("به‌روزرسانی هسته yt-dlp")
        self.update_ytdlp_btn.setObjectName("btnSecondary")
        self.update_ytdlp_btn.clicked.connect(self.update_ytdlp)

        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.path_status_lbl)
        header_layout.addWidget(self.open_folder_btn)
        header_layout.addWidget(self.update_ytdlp_btn)
        main_layout.addWidget(header_frame)

        # ==================== مرحله ۱: لینک‌ها و تنظیمات شبکه ====================
        input_group = QGroupBox("مرحله ۱: لینک‌ها، زیرنویس و تنظیمات شبکه")
        input_main_layout = QVBoxLayout()

        url_toolbar = QHBoxLayout()
        url_toolbar.addWidget(QLabel("لینک‌های ویدیو یا پلی‌لیست (هر لینک در یک خط):"))
        url_toolbar.addStretch()

        self.paste_btn = QPushButton("الصاق از کلیپ‌بورد")
        self.paste_btn.setObjectName("btnSecondary")
        self.paste_btn.clicked.connect(self.paste_from_clipboard)

        self.clear_urls_btn = QPushButton("پاک کردن لیست")
        self.clear_urls_btn.setObjectName("btnSecondary")
        self.clear_urls_btn.clicked.connect(lambda: self.url_input.clear())

        url_toolbar.addWidget(self.paste_btn)
        url_toolbar.addWidget(self.clear_urls_btn)
        input_main_layout.addLayout(url_toolbar)

        self.url_input = QTextEdit()
        self.url_input.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.url_input.setPlaceholderText(
            "https://www.youtube.com/watch?v=...\n"
            "هر لینک ویدیو یا پلی‌لیست را در یک خط جداگانه وارد کنید..."
        )
        self.url_input.setFixedHeight(78)
        input_main_layout.addWidget(self.url_input)

        settings_grid = QGridLayout()
        settings_grid.setHorizontalSpacing(14)
        settings_grid.setVerticalSpacing(8)

        self.browser_select = QComboBox()
        self.browser_select.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.browser_select.addItems(
            ["None", "Firefox", "Chrome", "Edge", "Brave", "Opera", "Vivaldi", "Chromium"]
        )

        self.proxy_type = QComboBox()
        self.proxy_type.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.proxy_type.addItems(["None", "HTTP", "SOCKS5", "SOCKS4"])

        self.proxy_address = QLineEdit()
        self.proxy_address.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.proxy_address.setPlaceholderText("127.0.0.1:10808")

        settings_grid.addWidget(QLabel("کوکی مرورگر:"), 0, 0)
        settings_grid.addWidget(self.browser_select, 0, 1)
        settings_grid.addWidget(QLabel("نوع پروکسی:"), 0, 2)
        settings_grid.addWidget(self.proxy_type, 0, 3)
        settings_grid.addWidget(QLabel("آدرس پروکسی:"), 0, 4)
        settings_grid.addWidget(self.proxy_address, 0, 5)

        self.playlist_checkbox = QCheckBox("دانلود کل پلی‌لیست (در صورت وجود در لینک)")
        self.sub_checkbox = QCheckBox("دانلود زیرنویس (Subtitles)")
        self.embed_sub_checkbox = QCheckBox("ادغام زیرنویس داخل ویدیو")

        self.sub_lang_select = QComboBox()
        self.sub_lang_select.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.sub_lang_select.addItems([
            "fa,en (فارسی و انگلیسی)",
            "fa (فقط فارسی)",
            "en (فقط انگلیسی)",
            "all (همه زبان‌ها)",
        ])

        settings_grid.addWidget(self.playlist_checkbox, 1, 0, 1, 2)
        settings_grid.addWidget(self.sub_checkbox, 1, 2)
        settings_grid.addWidget(self.embed_sub_checkbox, 1, 3)
        settings_grid.addWidget(QLabel("زبان زیرنویس:"), 1, 4)
        settings_grid.addWidget(self.sub_lang_select, 1, 5)

        input_main_layout.addLayout(settings_grid)
        input_group.setLayout(input_main_layout)
        main_layout.addWidget(input_group)

        # ==================== مرحله ۲: پیش‌نمایش و عملیات دانلود ====================
        details_group = QGroupBox("مرحله ۲: اطلاعات ویدیو و عملیات دانلود")
        details_layout = QHBoxLayout()
        details_layout.setSpacing(16)

        info_layout = QVBoxLayout()
        self.thumbnail_label = QLabel("پیش‌نمایش تصویر ویدیو")
        self.thumbnail_label.setStyleSheet(
            "border: 1px dashed #475569; background-color: #0f172a; "
            "border-radius: 8px; color: #64748b;"
        )
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setFixedSize(320, 175)

        meta_frame = QFrame()
        meta_frame.setObjectName("statCard")
        meta_layout = QVBoxLayout(meta_frame)
        meta_layout.setSpacing(4)

        self.title_label = QLabel("عنوان ویدیو: -")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-weight: bold; color: #f8fafc;")

        self.meta_info_label = QLabel("کانال: -   |   مدت زمان: -   |   بازدید: -")
        self.meta_info_label.setStyleSheet("color: #94a3b8; font-size: 9pt;")

        meta_layout.addWidget(self.title_label)
        meta_layout.addWidget(self.meta_info_label)

        info_layout.addWidget(self.thumbnail_label, alignment=Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(meta_frame)
        info_layout.addStretch()

        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(8)

        self.get_formats_btn = QPushButton("واکشی اطلاعات و کیفیت‌های دقیق لینک اول")
        actions_layout.addWidget(self.get_formats_btn)

        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("کیفیت / فرمت دانلود:"))
        self.quality_select = QComboBox()
        self.quality_select.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        quality_layout.addWidget(self.quality_select, 1)
        actions_layout.addLayout(quality_layout)

        dl_row1 = QHBoxLayout()
        self.download_btn = QPushButton("▼ دانلود ویدیو (تکی)")
        self.download_btn.setObjectName("btnSuccess")
        self.download_direct_audio_btn = QPushButton("♪ دانلود مستقیم صدا (MP3 320k)")
        self.download_direct_audio_btn.setObjectName("btnPurple")
        dl_row1.addWidget(self.download_btn)
        dl_row1.addWidget(self.download_direct_audio_btn)
        actions_layout.addLayout(dl_row1)

        dl_row2 = QHBoxLayout()
        self.download_batch_btn = QPushButton("▼▼ دانلود دسته‌ای همه لینک‌ها (Batch)")
        self.stop_btn = QPushButton("■ توقف / لغو عملیات")
        self.stop_btn.setObjectName("btnDanger")
        self.stop_btn.setEnabled(False)
        dl_row2.addWidget(self.download_batch_btn)
        dl_row2.addWidget(self.stop_btn)
        actions_layout.addLayout(dl_row2)

        actions_layout.addSpacing(4)

        tools_row = QHBoxLayout()
        self.save_custom_btn = QPushButton("تغییر مسیر ذخیره")
        self.save_custom_btn.setObjectName("btnSecondary")
        self.download_audio_btn = QPushButton("تبدیل فایل ویدیویی محلی به MP3")
        self.download_audio_btn.setObjectName("btnSecondary")
        tools_row.addWidget(self.save_custom_btn)
        tools_row.addWidget(self.download_audio_btn)
        actions_layout.addLayout(tools_row)
        actions_layout.addStretch()

        details_layout.addLayout(info_layout, 5)
        details_layout.addLayout(actions_layout, 7)
        details_group.setLayout(details_layout)
        main_layout.addWidget(details_group)

        # ==================== مرحله ۳: وضعیت پیشرفت و لاگ سیستم ====================
        log_group = QGroupBox("مرحله ۳: وضعیت لحظه‌ای دانلود و گزارش سیستم")
        log_layout = QVBoxLayout()

        telemetry_layout = QHBoxLayout()
        self.speed_label = QLabel("⚡ سرعت دانلود: -")
        self.eta_label = QLabel("◷ زمان باقی‌مانده: -")
        self.size_label = QLabel("▣ حجم کل فایل: -")
        for lbl in (self.speed_label, self.eta_label, self.size_label):
            lbl.setStyleSheet(
                "background-color: #0f172a; border: 1px solid #334155; "
                "border-radius: 5px; padding: 4px 10px; color: #38bdf8; font-weight: bold;"
            )
            telemetry_layout.addWidget(lbl)
        log_layout.addLayout(telemetry_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.progress_bar.setValue(0)
        log_layout.addWidget(self.progress_bar)

        self.formats_list = QTextEdit()
        self.formats_list.setReadOnly(True)
        self.formats_list.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.formats_list.setFont(QFont("DejaVu Sans Mono", 9))
        self.formats_list.setMinimumHeight(140)
        log_layout.addWidget(self.formats_list)

        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group, 1)

        # اتصال سیگنال‌ها
        self.get_formats_btn.clicked.connect(self.start_get_formats)
        self.download_btn.clicked.connect(self.download_video)
        self.download_direct_audio_btn.clicked.connect(self.download_direct_audio)
        self.download_batch_btn.clicked.connect(self.start_batch_download)
        self.stop_btn.clicked.connect(self.cancel_active_operation)
        self.save_custom_btn.clicked.connect(self.set_custom_path)
        self.download_audio_btn.clicked.connect(self.select_file_for_audio_extraction)

        self.browser_select.currentTextChanged.connect(self.save_current_settings)
        self.proxy_type.currentTextChanged.connect(self.save_current_settings)
        self.proxy_address.editingFinished.connect(self.save_current_settings)

    # ------------------------------------------------------------
    def populate_default_qualities(self, dynamic_formats: list = None):
        """پر کردن منوی انتخاب کیفیت با مقادیر پیش‌فرض و فرمت‌های اختصاصی ویدیو"""
        self.quality_select.clear()
        for label, selector in DEFAULT_QUALITY_PRESETS:
            self.quality_select.addItem(f"★ {label}", selector)

        if dynamic_formats:
            self.quality_select.insertSeparator(self.quality_select.count())
            for label, selector in dynamic_formats:
                self.quality_select.addItem(f"• {label}", selector)

        self.quality_select.setCurrentIndex(0)

    def load_saved_settings(self):
        """بارگذاری تنظیمات ذخیره‌شده کاربر از نشست قبلی"""
        browser = self.settings.value("browser", "None")
        idx_b = self.browser_select.findText(browser)
        if idx_b >= 0:
            self.browser_select.setCurrentIndex(idx_b)

        ptype = self.settings.value("proxy_type", "None")
        idx_p = self.proxy_type.findText(ptype)
        if idx_p >= 0:
            self.proxy_type.setCurrentIndex(idx_p)

        self.proxy_address.setText(self.settings.value("proxy_address", ""))

    def save_current_settings(self):
        """ذخیره تنظیمات شبکه و مسیر برای استفاده‌های بعدی"""
        self.settings.setValue("browser", self.browser_select.currentText())
        self.settings.setValue("proxy_type", self.proxy_type.currentText())
        self.settings.setValue("proxy_address", self.proxy_address.text().strip())
        if self.custom_path:
            self.settings.setValue("custom_path", self.custom_path)

    def update_path_label(self):
        folder = self.get_save_dir()
        self.path_status_lbl.setText(f"مسیر ذخیره: {folder}")

    def get_save_dir(self) -> str:
        if self.custom_path and os.path.isdir(self.custom_path):
            return self.custom_path
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        return desktop if os.path.exists(desktop) else os.path.expanduser("~")

    def get_save_path(self, is_playlist: bool = False) -> str:
        base_dir = self.get_save_dir()
        if is_playlist:
            return os.path.join(
                base_dir, "%(playlist_title)s", "%(playlist_index)02d - %(title)s.%(ext)s"
            )
        return os.path.join(base_dir, "%(title)s.%(ext)s")

    def open_save_folder(self):
        folder = self.get_save_dir()
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def paste_from_clipboard(self):
        clip = QApplication.clipboard().text().strip()
        if clip:
            current = self.url_input.toPlainText().strip()
            new_text = f"{current}\n{clip}" if current else clip
            self.url_input.setPlainText(new_text)

    # ------------------------------------------------------------
    def check_dependencies(self):
        """بررسی وجود yt-dlp و ffmpeg در سیستم"""
        self.formats_list.setText("در حال بررسی پیش‌نیازهای سیستم...")
        yt_ok = bool(shutil.which("yt-dlp"))
        ff_ok = bool(shutil.which("ffmpeg"))

        if not yt_ok:
            self.formats_list.append("✖ خطا: yt-dlp یافت نشد! لطفاً با دستور pip install -U yt-dlp نصب کنید.")
        else:
            self.formats_list.append("✔ هسته yt-dlp شناسایی شد.")

        if not ff_ok:
            self.formats_list.append(
                "⚠ هشدار: ffmpeg یافت نشد! برای ترکیب ویدیوهای 1080p+ و تبدیل MP3 نصب ffmpeg ضروری است."
            )
        else:
            self.formats_list.append("✔ ابزار پردازش رسانه ffmpeg شناسایی شد.")

        if yt_ok and ff_ok:
            self.formats_list.append("\n✔ تمامی پیش‌نیازها آماده هستند. لینک ویدیو را وارد کرده و دانلود را آغاز کنید.")

    def get_proxy_url(self) -> str:
        ptype = self.proxy_type.currentText()
        addr = self.proxy_address.text().strip()
        return build_proxy_url(ptype, addr)

    def get_subtitle_langs(self) -> str:
        raw = self.sub_lang_select.currentText()
        return raw.split(" ")[0].strip()

    def build_current_base_cmd(self) -> list:
        return build_base_cmd(
            browser=self.browser_select.currentText().lower(),
            proxy_url=self.get_proxy_url(),
            allow_playlist=self.playlist_checkbox.isChecked(),
            sub_enabled=self.sub_checkbox.isChecked(),
            sub_langs=self.get_subtitle_langs(),
            embed_subs=self.embed_sub_checkbox.isChecked(),
        )

    # ------------------------------------------------------------
    def update_ytdlp(self):
        """به‌روزرسانی خودکار هسته yt-dlp از طریق pip"""
        self.formats_list.setText("در حال بررسی و به‌روزرسانی هسته yt-dlp...")
        self.set_buttons_enabled(False)
        self.progress_bar.setRange(0, 0)

        self.upd_thread = UpdateYtDlpThread()
        self.upd_thread.finished.connect(self.on_update_ytdlp_finished)
        self.upd_thread.start()

    def on_update_ytdlp_finished(self, ok: bool, output: str):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100 if ok else 0)
        self.set_buttons_enabled(True)
        self.formats_list.setText(output)
        if ok:
            QMessageBox.information(self, "به‌روزرسانی موفق", "هسته yt-dlp با موفقیت به آخرین نسخه ارتقا یافت!")
        else:
            QMessageBox.warning(self, "خطا در به‌روزرسانی", f"به‌روزرسانی با خطا مواجه شد:\n{output}")

    # ------------------------------------------------------------
    def start_get_formats(self):
        """دریافت اطلاعات و لیست کیفیت‌های اولین لینک موجود در باکس"""
        urls = [u.strip() for u in self.url_input.toPlainText().splitlines() if u.strip()]
        if not urls:
            QMessageBox.warning(self, "هشدار", "لطفاً ابتدا لینک ویدیو را وارد کنید.")
            return

        url = urls[0]
        if not validate_url(url):
            QMessageBox.warning(
                self, "لینک نامعتبر", "لطفاً یک لینک معتبر یوتیوب (شروع با http:// یا https://) وارد کنید."
            )
            return

        self.formats_list.setText("در حال دریافت متادیتا و لیست کیفیت‌های ویدیو...")
        self.set_buttons_enabled(False)
        self.progress_bar.setRange(0, 0)

        browser = self.browser_select.currentText().lower()
        proxy_url = self.get_proxy_url()

        self.get_formats_thread = GetFormatsThread(url, browser, proxy_url)
        self.get_formats_thread.metadata.connect(self.on_metadata_received)
        self.get_formats_thread.finished.connect(self.on_get_formats_finished)
        self.get_formats_thread.error_signal.connect(self.on_get_formats_error)
        self.get_formats_thread.start()

    def on_metadata_received(self, meta: dict):
        """نمایش عنوان، کانال، مدت زمان، بازدید و تصویر بندانگشتی"""
        self.title_label.setText(f"عنوان ویدیو: {meta.get('title', '-')}")
        self.meta_info_label.setText(
            f"کانال: {meta.get('uploader', '-')}   |   "
            f"مدت زمان: {meta.get('duration', '-')}   |   "
            f"بازدید: {meta.get('views', '-')}"
        )

        thumb_url = meta.get("thumbnail")
        if thumb_url and validate_url(thumb_url):
            try:
                proxies = {}
                proxy_url = self.get_proxy_url()
                if proxy_url:
                    proxies = {"http": proxy_url, "https": proxy_url}

                response = requests.get(thumb_url, timeout=10, proxies=proxies)
                response.raise_for_status()
                pixmap = QPixmap()
                if pixmap.loadFromData(response.content):
                    self.thumbnail_label.setPixmap(
                        pixmap.scaled(
                            self.thumbnail_label.size(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                else:
                    self.thumbnail_label.setText("پیش‌نمایش تصویر پشتیبانی نشد")
            except Exception as e:
                self.thumbnail_label.setText(f"بارگیری تصویر ناموفق:\n{e}")
        else:
            self.thumbnail_label.setText("تصویر پیش‌نمایش در دسترس نیست")

    def on_get_formats_finished(self, table_text: str, parsed_formats: list):
        self.formats_list.setText(table_text)
        self.populate_default_qualities(parsed_formats)
        self.set_buttons_enabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

    def on_get_formats_error(self, err_msg: str):
        self.formats_list.setText(err_msg)
        self.set_buttons_enabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        QMessageBox.warning(self, "خطا در واکشی اطلاعات", err_msg)

    # ------------------------------------------------------------
    def set_custom_path(self):
        """انتخاب پوشه ذخیره‌سازی دلخواه"""
        path = QFileDialog.getExistingDirectory(self, "پوشه ذخیره را انتخاب کنید", self.get_save_dir())
        if path:
            self.custom_path = path
            self.save_current_settings()
            self.update_path_label()
            QMessageBox.information(self, "مسیر ذخیره", f"مسیر ذخیره‌سازی تغییر یافت:\n{self.custom_path}")

    def build_download_cmd_for_url(self, url: str, force_audio_mp3: bool = False) -> list:
        """ساخت دستور کامل دانلود برای یک لینک"""
        save_path = self.get_save_path(is_playlist=self.playlist_checkbox.isChecked())
        cmd = self.build_current_base_cmd()

        selector = "AUDIO_MP3" if force_audio_mp3 else (self.quality_select.currentData() or "bestvideo+bestaudio/best")

        if selector == "AUDIO_MP3":
            cmd.extend([
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "--embed-thumbnail",
                "--add-metadata",
                "-o", save_path,
                "--", url,
            ])
        elif selector == "AUDIO_M4A":
            cmd.extend([
                "-x",
                "--audio-format", "m4a",
                "--audio-quality", "0",
                "--embed-thumbnail",
                "--add-metadata",
                "-o", save_path,
                "--", url,
            ])
        else:
            cmd.extend([
                "-f", selector,
                "--merge-output-format", "mp4",
                "-o", save_path,
                "--", url,
            ])
        return cmd

    # ------------------------------------------------------------
    def download_video(self):
        """دانلود اولین لینک بر اساس کیفیت انتخاب شده در کمبوباکس"""
        urls = [u.strip() for u in self.url_input.toPlainText().splitlines() if u.strip()]
        if not urls:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا لینک ویدیو را وارد کنید!")
            return
        url = urls[0]
        if not validate_url(url):
            QMessageBox.warning(self, "خطا", "لینک وارد شده معتبر نیست!")
            return

        cmd = self.build_download_cmd_for_url(url, force_audio_mp3=False)
        self.formats_list.setText(f"▶ شروع دانلود در پوشه:\n{self.get_save_dir()}\n")
        self.start_download(cmd, is_batch=False)

    def download_direct_audio(self):
        """دانلود مستقیم صدای لینک(ها) با فرمت MP3 320kbps"""
        urls = [u.strip() for u in self.url_input.toPlainText().splitlines() if u.strip()]
        if not urls:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا لینک ویدیو را وارد کنید!")
            return

        invalid = [u for u in urls if not validate_url(u)]
        if invalid:
            QMessageBox.warning(self, "لینک نامعتبر", f"لینک زیر معتبر نیست:\n{invalid[0]}")
            return

        if len(urls) == 1:
            cmd = self.build_download_cmd_for_url(urls[0], force_audio_mp3=True)
            self.formats_list.setText(f"♪ شروع دانلود مستقیم فایل صوتی (MP3 320kbps) در:\n{self.get_save_dir()}\n")
            self.start_download(cmd, is_batch=False)
        else:
            self.download_queue = urls
            self.current_download_index = 0
            self.current_batch_mode = "audio"
            self.set_buttons_enabled(False)
            self.process_next_in_queue()

    # ------------------------------------------------------------
    def start_batch_download(self):
        """شروع دانلود پشت سر هم تمام لینک‌ها با کیفیت انتخاب شده"""
        urls = [u.strip() for u in self.url_input.toPlainText().splitlines() if u.strip()]
        if not urls:
            QMessageBox.warning(self, "خطا", "هیچ لینکی برای دانلود دسته‌ای وارد نشده است!")
            return

        invalid = [u for u in urls if not validate_url(u)]
        if invalid:
            QMessageBox.warning(self, "لینک نامعتبر", f"لینک زیر معتبر نیست:\n{invalid[0]}")
            return

        self.download_queue = urls
        self.current_download_index = 0
        self.current_batch_mode = "video"
        self.set_buttons_enabled(False)
        self.process_next_in_queue()

    def process_next_in_queue(self):
        if self.current_download_index < len(self.download_queue):
            url = self.download_queue[self.current_download_index]
            total = len(self.download_queue)
            idx = self.current_download_index + 1
            self.formats_list.append(
                f"\n{'=' * 55}\n▶ دانلود مورد {idx} از {total}:\n{url}\n{'=' * 55}"
            )
            cmd = self.build_download_cmd_for_url(
                url, force_audio_mp3=(self.current_batch_mode == "audio")
            )
            self.start_download(cmd, is_batch=True)
        else:
            self.set_buttons_enabled(True)
            self.formats_list.append("\n✔ تمام لینک‌های موجود در صف با موفقیت پردازش شدند.")
            QMessageBox.information(
                self, "پایان دانلود دسته‌ای", "تمام لینک‌های موجود در صف با موفقیت دانلود شدند!"
            )

    def on_batch_item_finished(self, success: bool, status: str):
        if status == "cancelled":
            self.download_queue = []
            self.set_buttons_enabled(True)
            return
        self.current_download_index += 1
        self.process_next_in_queue()

    # ------------------------------------------------------------
    def select_file_for_audio_extraction(self):
        """انتخاب فایل ویدیویی از دیسک برای تبدیل به MP3"""
        video_file, _ = QFileDialog.getOpenFileName(
            self,
            "فایل ویدیویی را برای تبدیل به MP3 انتخاب کنید",
            self.get_save_dir(),
            "Video Files (*.mp4 *.mkv *.webm *.avi *.mov *.flv)",
        )
        if video_file:
            self.extract_audio_from_file(video_file)

    def extract_audio_from_file(self, video_file: str):
        """استخراج MP3 با کیفیت 320k از فایل ویدیویی با ffmpeg"""
        audio_file = os.path.splitext(video_file)[0] + ".mp3"
        self.formats_list.setText(
            f"♪ در حال تبدیل ویدیو به MP3 (320kbps):\nورودی: {video_file}\nخروجی: {audio_file}"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", video_file,
            "-vn",
            "-c:a", "libmp3lame",
            "-b:a", "320k",
            "--", audio_file,
        ]

        self.progress_bar.setRange(0, 0)
        self.set_buttons_enabled(False)
        self.extract_thread = ExtractAudioThread(cmd)
        self.active_thread = self.extract_thread
        self.extract_thread.finished.connect(self.on_extract_audio_finished)
        self.extract_thread.error.connect(self.on_extract_audio_error)
        self.extract_thread.start()

    def on_extract_audio_finished(self, message: str):
        self.active_thread = None
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.set_buttons_enabled(True)
        self.formats_list.append(f"\n✔ {message}")
        QMessageBox.information(self, "عملیات موفق", message)

    def on_extract_audio_error(self, error_message: str):
        self.active_thread = None
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.set_buttons_enabled(True)
        self.formats_list.append(f"\n✖ {error_message}")
        QMessageBox.critical(self, "خطا در استخراج صدا", error_message)

    # ------------------------------------------------------------
    def start_download(self, cmd_list: list, is_batch: bool = False):
        """شروع ترد دانلود با دستور داده شده"""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.on_telemetry_update("-", "-", "-")
        self.set_buttons_enabled(False)

        self.download_thread = DownloadThread(cmd_list)
        self.active_thread = self.download_thread
        self.download_thread.progress.connect(self.progress_bar.setValue)
        self.download_thread.telemetry.connect(self.on_telemetry_update)
        self.download_thread.message.connect(self.on_download_message)

        if is_batch:
            self.download_thread.finished_signal.connect(self.on_batch_item_finished)
        else:
            self.download_thread.finished_signal.connect(self.on_single_download_finished)

        self.download_thread.start()

    def cancel_active_operation(self):
        """لغو دانلود یا استخراج در حال اجرا"""
        if self.active_thread and hasattr(self.active_thread, "cancel"):
            self.active_thread.cancel()

    def on_telemetry_update(self, speed: str, eta: str, size: str):
        self.speed_label.setText(f"⚡ سرعت دانلود: {speed}")
        self.eta_label.setText(f"◷ زمان باقی‌مانده: {eta}")
        self.size_label.setText(f"▣ حجم کل فایل: {size}")

    def on_download_message(self, message: str):
        self.formats_list.append(message)
        if "Destination:" in message:
            self.downloaded_file = message.split("Destination:")[-1].strip()
        elif "[Merger] Merging formats into" in message:
            m = re.search(r'into\s+"(.+?)"', message)
            if m:
                self.downloaded_file = m.group(1)

    def on_single_download_finished(self, success: bool, status: str):
        self.active_thread = None
        self.set_buttons_enabled(True)
        if success:
            path_info = self.downloaded_file or self.get_save_dir()
            QMessageBox.information(
                self,
                "دانلود کامل شد",
                f"فایل با موفقیت دانلود و ذخیره شد!\n\nمسیر:\n{path_info}",
            )

    # ------------------------------------------------------------
    def set_buttons_enabled(self, enabled: bool):
        self.download_btn.setEnabled(enabled)
        self.download_direct_audio_btn.setEnabled(enabled)
        self.download_batch_btn.setEnabled(enabled)
        self.get_formats_btn.setEnabled(enabled)
        self.download_audio_btn.setEnabled(enabled)
        self.update_ytdlp_btn.setEnabled(enabled)
        self.stop_btn.setEnabled(not enabled)


# ========================== اجرای برنامه ==========================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = YouTubeDownloader()
    window.show()
    sys.exit(app.exec())
