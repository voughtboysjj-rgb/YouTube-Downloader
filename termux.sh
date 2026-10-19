#!/data/data/com.termux/files/usr/bin/bash
# اسکریپت نصب و اجرای خودکار در اندروید (Termux)

echo "⏳ در حال نصب پیش‌نیازها در Termux..."
pkg update -y && pkg install -y python ffmpeg git
pip install -U flask yt-dlp requests

echo "✅ راه‌اندازی رابط موبایل در آدرس http://127.0.0.1:5000 ..."
termux-open-url "http://127.0.0.1:5000" 2>/dev/null || true
python web_app.py
