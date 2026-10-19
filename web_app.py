#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
YouTube Downloader Pro - نسخه وب و موبایل (Mobile & Web UI)
قابل اجرا در مرورگر گوشی (اندروید و آیفون)، Termux و سرورهای ابری
"""

import json
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template_string, request, send_file

app = Flask(__name__)

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# نگهداری وضعیت کارها در حافظه
JOBS = {}
JOBS_LOCK = threading.Lock()


def validate_url(url: str) -> bool:
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
    if not proxy_type or proxy_type == "None" or not proxy_addr or not proxy_addr.strip():
        return ""
    addr = proxy_addr.strip()
    addr = re.sub(r"^(https?|socks4a?|socks5h?)://", "", addr, flags=re.IGNORECASE)
    if addr.startswith("-") or not re.match(r"^[a-zA-Z0-9._:@\-]+$", addr):
        return ""
    scheme_map = {"HTTP": "http", "SOCKS4": "socks4", "SOCKS5": "socks5"}
    scheme = scheme_map.get(proxy_type.upper(), "")
    return f"{scheme}://{addr}" if scheme else ""


def format_duration(seconds) -> str:
    if not seconds or not isinstance(seconds, (int, float)):
        return "نامشخص"
    seconds = int(seconds)
    hrs, rem = divmod(seconds, 3600)
    mins, secs = divmod(rem, 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs > 0 else f"{mins:02d}:{secs:02d}"


def format_bytes(num_bytes) -> str:
    if not num_bytes or not isinstance(num_bytes, (int, float)) or num_bytes <= 0:
        return "نامشخص"
    for unit in ["B", "KiB", "MiB", "GiB"]:
        if num_bytes < 1024.0 or unit == "GiB":
            return f"{num_bytes:.1f} {unit}" if unit != "B" else f"{int(num_bytes)} B"
        num_bytes /= 1024.0
    return "نامشخص"


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>دانلودر یوتیوب موبایل | YouTube Downloader Pro</title>
    <style>
        :root {
            --bg: #0f172a;
            --card: #1e293b;
            --border: #334155;
            --text: #f8fafc;
            --muted: #94a3b8;
            --primary: #0284c7;
            --primary-hover: #0369a1;
            --success: #059669;
            --purple: #7c3aed;
            --danger: #dc2626;
            --accent: #38bdf8;
        }
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: "Vazirmatn", "Segoe UI", Tahoma, sans-serif;
        }
        body {
            background-color: var(--bg);
            color: var(--text);
            min-height: 100vh;
            padding: 14px;
            line-height: 1.6;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
        }
        .header {
            background: linear-gradient(135deg, #1e293b, #0f172a);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 16px;
            text-align: center;
            margin-bottom: 14px;
            box-shadow: 0 8px 20px rgba(0,0,0,0.3);
        }
        .header h1 {
            font-size: 1.25rem;
            color: var(--accent);
            margin-bottom: 4px;
        }
        .header p {
            font-size: 0.85rem;
            color: var(--muted);
        }
        .card {
            background-color: var(--card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 16px;
            margin-bottom: 14px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.25);
        }
        .card-title {
            font-size: 0.95rem;
            font-weight: bold;
            color: var(--accent);
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        label {
            display: block;
            font-size: 0.85rem;
            color: #cbd5e1;
            margin-bottom: 6px;
        }
        input[type="text"], select {
            width: 100%;
            background-color: var(--bg);
            color: var(--text);
            border: 1px solid #475569;
            border-radius: 10px;
            padding: 11px 12px;
            font-size: 0.92rem;
            outline: none;
            transition: border 0.2s;
        }
        input[type="text"]:focus, select:focus {
            border-color: var(--accent);
        }
        .ltr {
            direction: ltr;
            text-align: left;
        }
        .url-row {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
        }
        .url-row input {
            flex: 1;
        }
        .btn {
            border: none;
            border-radius: 10px;
            padding: 11px 14px;
            font-size: 0.92rem;
            font-weight: bold;
            color: #fff;
            cursor: pointer;
            transition: opacity 0.2s, transform 0.1s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            text-decoration: none;
            width: 100%;
        }
        .btn:active {
            transform: scale(0.98);
        }
        .btn:disabled {
            background-color: #334155 !important;
            color: #64748b !important;
            cursor: not-allowed;
        }
        .btn-primary { background-color: var(--primary); }
        .btn-success { background-color: var(--success); }
        .btn-purple { background-color: var(--purple); }
        .btn-danger { background-color: var(--danger); }
        .btn-secondary {
            background-color: #334155;
            border: 1px solid #475569;
            width: auto;
            white-space: nowrap;
        }
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 10px;
        }
        .preview-box {
            display: none;
            background-color: var(--bg);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 12px;
        }
        .preview-box img {
            width: 100%;
            max-height: 210px;
            object-fit: cover;
            border-radius: 8px;
            margin-bottom: 8px;
        }
        .preview-title {
            font-weight: bold;
            font-size: 0.95rem;
            margin-bottom: 4px;
        }
        .preview-meta {
            font-size: 0.8rem;
            color: var(--muted);
        }
        .progress-wrap {
            background-color: var(--bg);
            border: 1px solid var(--border);
            border-radius: 10px;
            height: 26px;
            overflow: hidden;
            position: relative;
            margin: 12px 0;
        }
        .progress-bar {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, #0284c7, #10b981);
            transition: width 0.3s ease;
        }
        .progress-text {
            position: absolute;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.82rem;
            font-weight: bold;
        }
        .stats-row {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-bottom: 10px;
        }
        .stat-chip {
            background-color: var(--bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 6px;
            text-align: center;
            font-size: 0.78rem;
            color: var(--accent);
            font-weight: bold;
        }
        .log-box {
            background-color: var(--bg);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 10px;
            font-family: monospace;
            font-size: 0.78rem;
            color: #cbd5e1;
            max-height: 150px;
            overflow-y: auto;
            direction: ltr;
            text-align: left;
            white-space: pre-wrap;
        }
        .download-ready {
            display: none;
            margin-top: 12px;
            padding: 12px;
            border-radius: 10px;
            background-color: rgba(16, 185, 129, 0.12);
            border: 1px solid #10b981;
            text-align: center;
        }
        details {
            margin-top: 10px;
            background-color: var(--bg);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 10px;
        }
        summary {
            cursor: pointer;
            font-size: 0.85rem;
            color: var(--muted);
            font-weight: bold;
        }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>▶ دانلودر حرفه‌ای یوتیوب (نسخه موبایل و وب)</h1>
        <p>دانلود مستقیم ویدیو و MP3 در گوشی بدون نیاز به نصب برنامه سنگین</p>
    </div>

    <div class="card">
        <div class="card-title">
            <span>۱. لینک ویدیو و تنظیمات</span>
        </div>
        <label>لینک ویدیوی یوتیوب:</label>
        <div class="url-row">
            <input type="text" id="urlInput" class="ltr" placeholder="https://www.youtube.com/watch?v=...">
            <button type="button" class="btn btn-secondary" onclick="pasteClipboard()">الصاق</button>
        </div>

        <label>انتخاب کیفیت یا فرمت:</label>
        <select id="qualitySelect">
            <option value="bestvideo[height<=720]+bestaudio/best[height<=720]/best">★ کیفیت 720p HD (پیشنهادی موبایل - MP4)</option>
            <option value="bestvideo[height<=1080]+bestaudio/best[height<=1080]/best">★ کیفیت 1080p Full HD (MP4)</option>
            <option value="bestvideo+bestaudio/best">★ بهترین کیفیت ممکن (Best Video)</option>
            <option value="bestvideo[height<=480]+bestaudio/best[height<=480]/best">★ کیفیت 480p (کم‌حجم - MP4)</option>
            <option value="bestvideo[height<=360]+bestaudio/best[height<=360]/best">★ کیفیت 360p (بسیار کم‌حجم)</option>
            <option value="AUDIO_MP3">♪ فقط صدا - MP3 (کیفیت عالی 320kbps)</option>
            <option value="AUDIO_M4A">♪ فقط صدا - M4A (بدون افت کیفیت)</option>
        </select>

        <details>
            <summary>⚙ تنظیمات پیشرفته (پروکسی و زیرنویس)</summary>
            <div class="grid-2" style="margin-top: 10px;">
                <div>
                    <label>نوع پروکسی:</label>
                    <select id="proxyType" class="ltr">
                        <option value="None">None</option>
                        <option value="HTTP">HTTP</option>
                        <option value="SOCKS5">SOCKS5</option>
                        <option value="SOCKS4">SOCKS4</option>
                    </select>
                </div>
                <div>
                    <label>آدرس پروکسی:</label>
                    <input type="text" id="proxyAddr" class="ltr" placeholder="127.0.0.1:10808">
                </div>
            </div>
        </details>
    </div>

    <div class="card">
        <div class="card-title">
            <span>۲. پیش‌نمایش و شروع دانلود</span>
        </div>

        <div id="previewBox" class="preview-box">
            <img id="thumbImg" src="" alt="Thumbnail">
            <div id="videoTitle" class="preview-title"></div>
            <div id="videoMeta" class="preview-meta"></div>
        </div>

        <button id="infoBtn" class="btn btn-primary" onclick="fetchInfo()" style="margin-bottom: 10px;">
            🔍 بررسی لینک و مشاهده پیش‌نمایش ویدیو
        </button>

        <div class="grid-2">
            <button id="dlVideoBtn" class="btn btn-success" onclick="startDownload(false)">
                ▼ دانلود ویدیو
            </button>
            <button id="dlAudioBtn" class="btn btn-purple" onclick="startDownload(true)">
                ♪ دانلود مستقیم MP3
            </button>
        </div>

        <button id="cancelBtn" class="btn btn-danger" onclick="cancelJob()" style="margin-top: 10px; display: none;">
            ■ توقف عملیات دانلود
        </button>

        <div id="readyBox" class="download-ready">
            <div style="margin-bottom: 8px; font-weight: bold; color: #10b981;">✔ فایل شما آماده شد!</div>
            <a id="savePhoneLink" href="#" class="btn btn-success">📥 ذخیره فایل در حافظه گوشی</a>
        </div>
    </div>

    <div class="card">
        <div class="card-title">
            <span>۳. وضعیت لحظه‌ای دانلود</span>
        </div>
        <div class="stats-row">
            <div id="speedStat" class="stat-chip">⚡ سرعت: -</div>
            <div id="etaStat" class="stat-chip">◷ زمان: -</div>
            <div id="sizeStat" class="stat-chip">▣ حجم: -</div>
        </div>
        <div class="progress-wrap">
            <div id="progBar" class="progress-bar"></div>
            <div id="progText" class="progress-text">0%</div>
        </div>
        <div id="logBox" class="log-box">آماده به کار. لینک یوتیوب را وارد کنید...</div>
    </div>
</div>

<script>
let currentJobId = null;
let pollTimer = null;

async function pasteClipboard() {
    try {
        const text = await navigator.clipboard.readText();
        if (text) document.getElementById('urlInput').value = text.trim();
    } catch (e) {
        alert('لطفاً لینک را به صورت دستی در کادر جای‌گذاری (Paste) کنید.');
    }
}

function setBusy(busy) {
    document.getElementById('infoBtn').disabled = busy;
    document.getElementById('dlVideoBtn').disabled = busy;
    document.getElementById('dlAudioBtn').disabled = busy;
    document.getElementById('cancelBtn').style.display = busy ? 'inline-flex' : 'none';
}

async function fetchInfo() {
    const url = document.getElementById('urlInput').value.trim();
    if (!url) { alert('لطفاً ابتدا لینک ویدیو را وارد کنید.'); return; }

    setBusy(true);
    document.getElementById('logBox').textContent = 'در حال دریافت اطلاعات ویدیو از یوتیوب...';

    try {
        const res = await fetch('/api/info', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                url: url,
                proxy_type: document.getElementById('proxyType').value,
                proxy_addr: document.getElementById('proxyAddr').value
            })
        });
        const data = await res.json();
        setBusy(false);

        if (!data.ok) {
            document.getElementById('logBox').textContent = data.error || 'خطا در دریافت اطلاعات';
            return;
        }

        const box = document.getElementById('previewBox');
        box.style.display = 'block';
        document.getElementById('thumbImg').src = data.thumbnail || '';
        document.getElementById('videoTitle').textContent = data.title;
        document.getElementById('videoMeta').textContent =
            `کانال: ${data.uploader} | مدت زمان: ${data.duration} | بازدید: ${data.views}`;

        const sel = document.getElementById('qualitySelect');
        // حذف فرمت‌های پویا قبلی
        while (sel.options.length > 7) sel.remove(7);
        (data.formats || []).forEach(f => {
            const opt = document.createElement('option');
            opt.value = f.selector;
            opt.textContent = '• ' + f.label;
            sel.appendChild(opt);
        });

        document.getElementById('logBox').textContent = '✔ اطلاعات ویدیو با موفقیت دریافت شد. اکنون روی دانلود بزنید.';
    } catch (err) {
        setBusy(false);
        document.getElementById('logBox').textContent = 'خطا در ارتباط با سرور: ' + err;
    }
}

async function startDownload(forceMp3) {
    const url = document.getElementById('urlInput').value.trim();
    if (!url) { alert('لطفاً ابتدا لینک ویدیو را وارد کنید.'); return; }

    document.getElementById('readyBox').style.display = 'none';
    document.getElementById('progBar').style.width = '0%';
    document.getElementById('progText').textContent = '0%';
    document.getElementById('logBox').textContent = 'در حال شروع فرآیند دانلود...';
    setBusy(true);

    const selector = forceMp3 ? 'AUDIO_MP3' : document.getElementById('qualitySelect').value;

    try {
        const res = await fetch('/api/download', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                url: url,
                selector: selector,
                proxy_type: document.getElementById('proxyType').value,
                proxy_addr: document.getElementById('proxyAddr').value
            })
        });
        const data = await res.json();
        if (!data.ok) {
            setBusy(false);
            document.getElementById('logBox').textContent = data.error || 'خطا در شروع دانلود';
            return;
        }
        currentJobId = data.job_id;
        pollTimer = setInterval(pollStatus, 1000);
    } catch (e) {
        setBusy(false);
        document.getElementById('logBox').textContent = 'خطا: ' + e;
    }
}

async function pollStatus() {
    if (!currentJobId) return;
    try {
        const res = await fetch('/api/status/' + currentJobId);
        const st = await res.json();
        document.getElementById('progBar').style.width = st.progress + '%';
        document.getElementById('progText').textContent = st.progress + '%';
        document.getElementById('speedStat').textContent = '⚡ سرعت: ' + (st.speed || '-');
        document.getElementById('etaStat').textContent = '◷ زمان: ' + (st.eta || '-');
        document.getElementById('sizeStat').textContent = '▣ حجم: ' + (st.size || '-');
        document.getElementById('logBox').textContent = (st.logs || []).join('\\n');
        const lb = document.getElementById('logBox');
        lb.scrollTop = lb.scrollHeight;

        if (st.state === 'done' || st.state === 'error' || st.state === 'cancelled') {
            clearInterval(pollTimer);
            pollTimer = null;
            setBusy(false);
            if (st.state === 'done' && st.file_ready) {
                const readyBox = document.getElementById('readyBox');
                const link = document.getElementById('savePhoneLink');
                link.href = '/api/file/' + currentJobId;
                readyBox.style.display = 'block';
            }
        }
    } catch (e) {}
}

async function cancelJob() {
    if (!currentJobId) return;
    await fetch('/api/cancel/' + currentJobId, {method: 'POST'});
}
</script>
</body>
</html>
"""


def run_download_worker(job_id: str, cmd: list, job_dir: str):
    re_progress = re.compile(r"(\d+(?:\.\d+)?)%")
    re_speed = re.compile(r"at\s+([0-9.]+\s*[KMGTP]?i?B/s)", re.IGNORECASE)
    re_eta = re.compile(r"ETA\s+([0-9:]+)", re.IGNORECASE)
    re_size = re.compile(r"of\s+~?\s*([0-9.]+\s*[KMGTP]?i?B)", re.IGNORECASE)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        with JOBS_LOCK:
            JOBS[job_id]["proc"] = proc

        for line in proc.stdout:
            with JOBS_LOCK:
                if JOBS[job_id]["state"] == "cancelled":
                    break
            clean = line.strip()
            if not clean:
                continue

            m_prog = re_progress.search(clean)
            with JOBS_LOCK:
                if m_prog:
                    JOBS[job_id]["progress"] = min(100, max(0, int(float(m_prog.group(1)))))
                    sp = re_speed.search(clean)
                    et = re_eta.search(clean)
                    sz = re_size.search(clean)
                    if sp:
                        JOBS[job_id]["speed"] = sp.group(1)
                    if et:
                        JOBS[job_id]["eta"] = et.group(1)
                    if sz:
                        JOBS[job_id]["size"] = sz.group(1)
                JOBS[job_id]["logs"].append(clean)
                if len(JOBS[job_id]["logs"]) > 40:
                    JOBS[job_id]["logs"] = JOBS[job_id]["logs"][-40:]

        proc.wait()

        with JOBS_LOCK:
            if JOBS[job_id]["state"] == "cancelled":
                JOBS[job_id]["logs"].append("⛔ عملیات دانلود توسط کاربر لغو شد.")
                return

            if proc.returncode == 0:
                files = [
                    os.path.join(job_dir, f)
                    for f in os.listdir(job_dir)
                    if not f.endswith((".part", ".ytdl"))
                ]
                if files:
                    latest_file = max(files, key=os.path.getmtime)
                    JOBS[job_id]["filepath"] = latest_file
                    JOBS[job_id]["file_ready"] = True
                    JOBS[job_id]["progress"] = 100
                    JOBS[job_id]["state"] = "done"
                    JOBS[job_id]["logs"].append("✔ دانلود کامل شد! دکمه «ذخیره فایل در حافظه گوشی» را بزنید.")
                else:
                    JOBS[job_id]["state"] = "error"
                    JOBS[job_id]["logs"].append("✖ فایل خروجی یافت نشد.")
            else:
                JOBS[job_id]["state"] = "error"
                JOBS[job_id]["logs"].append(f"✖ دانلود با کد خطای {proc.returncode} متوقف شد.")
    except Exception as e:
        with JOBS_LOCK:
            JOBS[job_id]["state"] = "error"
            JOBS[job_id]["logs"].append(f"✖ خطا: {e}")


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/info", methods=["POST"])
def api_info():
    body = request.get_json(force=True, silent=True) or {}
    url = (body.get("url") or "").strip()
    if not validate_url(url):
        return jsonify({"ok": False, "error": "لینک وارد شده معتبر نیست (باید با http یا https شروع شود)."})

    proxy_url = build_proxy_url(body.get("proxy_type", "None"), body.get("proxy_addr", ""))
    cmd = ["yt-dlp", "--no-playlist", "--dump-single-json"]
    if proxy_url:
        cmd.extend(["--proxy", proxy_url])
    cmd.extend(["--", url])

    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, timeout=45)
        json_line = next(
            (l.strip() for l in reversed(out.splitlines()) if l.strip().startswith("{")),
            out.strip(),
        )
        data = json.loads(json_line)
        formats_out = []
        for f in reversed(data.get("formats", [])):
            vcodec = f.get("vcodec", "none")
            height = f.get("height")
            fmt_id = str(f.get("format_id", ""))
            ext = f.get("ext", "")
            acodec = f.get("acodec", "none")
            size_str = format_bytes(f.get("filesize") or f.get("filesize_approx"))
            if vcodec != "none" and height:
                selector = f"{fmt_id}+bestaudio/best" if acodec == "none" else fmt_id
                label = f"{height}p ({ext.upper()}) - {size_str} [ID: {fmt_id}]"
                formats_out.append({"label": label, "selector": selector})

        views = data.get("view_count")
        return jsonify({
            "ok": True,
            "title": data.get("title") or "بدون عنوان",
            "uploader": data.get("uploader") or data.get("channel") or "نامشخص",
            "duration": format_duration(data.get("duration")),
            "views": f"{views:,}" if isinstance(views, int) else "نامشخص",
            "thumbnail": data.get("thumbnail") or "",
            "formats": formats_out[:20],
        })
    except subprocess.CalledProcessError as e:
        return jsonify({"ok": False, "error": f"خطا در دریافت اطلاعات از یوتیوب:\n{e.output}"})
    except Exception as e:
        return jsonify({"ok": False, "error": f"خطا: {e}"})


@app.route("/api/download", methods=["POST"])
def api_download():
    body = request.get_json(force=True, silent=True) or {}
    url = (body.get("url") or "").strip()
    selector = (body.get("selector") or "bestvideo[height<=720]+bestaudio/best[height<=720]/best").strip()

    if not validate_url(url):
        return jsonify({"ok": False, "error": "لینک وارد شده معتبر نیست."})
    if selector.startswith("-"):
        return jsonify({"ok": False, "error": "فرمت انتخابی نامعتبر است."})

    job_id = uuid.uuid4().hex[:12]
    job_dir = os.path.join(DOWNLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    out_tmpl = os.path.join(job_dir, "%(title).120s.%(ext)s")

    proxy_url = build_proxy_url(body.get("proxy_type", "None"), body.get("proxy_addr", ""))
    cmd = [
        "yt-dlp",
        "--newline",
        "--no-playlist",
        "--retries", "20",
        "--fragment-retries", "20",
    ]
    if proxy_url:
        cmd.extend(["--proxy", proxy_url])

    if selector == "AUDIO_MP3":
        cmd.extend(["-x", "--audio-format", "mp3", "--audio-quality", "0", "-o", out_tmpl, "--", url])
    elif selector == "AUDIO_M4A":
        cmd.extend(["-x", "--audio-format", "m4a", "--audio-quality", "0", "-o", out_tmpl, "--", url])
    else:
        cmd.extend(["-f", selector, "--merge-output-format", "mp4", "-o", out_tmpl, "--", url])

    with JOBS_LOCK:
        JOBS[job_id] = {
            "state": "running",
            "progress": 0,
            "speed": "-",
            "eta": "-",
            "size": "-",
            "logs": ["شروع دانلود..."],
            "file_ready": False,
            "filepath": None,
            "proc": None,
        }

    t = threading.Thread(target=run_download_worker, args=(job_id, cmd, job_dir), daemon=True)
    t.start()
    return jsonify({"ok": True, "job_id": job_id})


@app.route("/api/status/<job_id>")
def api_status(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"state": "error", "progress": 0, "logs": ["کار مورد نظر یافت نشد."]})
        return jsonify({
            "state": job["state"],
            "progress": job["progress"],
            "speed": job["speed"],
            "eta": job["eta"],
            "size": job["size"],
            "logs": job["logs"],
            "file_ready": job["file_ready"],
        })


@app.route("/api/cancel/<job_id>", methods=["POST"])
def api_cancel(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"ok": False})
        job["state"] = "cancelled"
        proc = job.get("proc")
    if proc and proc.poll() is None:
        try:
            proc.terminate()
        except Exception:
            pass
    return jsonify({"ok": True})


@app.route("/api/file/<job_id>")
def api_file(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        filepath = job.get("filepath") if job else None
    if not filepath or not os.path.isfile(filepath):
        return "فایل یافت نشد", 404
    return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🌐 Mobile & Web UI running on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
