import os
import yt_dlp
from flask import Flask, request, send_file, render_template_string
from werkzeug.utils import secure_filename
import hashlib
import time
import shutil
from functools import wraps
from datetime import datetime, timedelta
import psutil
from queue import Queue
from threading import Lock

app = Flask(__name__)

# Ensure directories exist (relative to the script's directory)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
YOUTUBE_DIR = os.path.join(DOWNLOAD_DIR, "youtube")
INSTAGRAM_DIR = os.path.join(DOWNLOAD_DIR, "instagram")
FACEBOOK_DIR = os.path.join(DOWNLOAD_DIR, "facebook")
TWITTER_DIR = os.path.join(DOWNLOAD_DIR, "twitter")

os.makedirs(YOUTUBE_DIR, exist_ok=True)
os.makedirs(INSTAGRAM_DIR, exist_ok=True)
os.makedirs(FACEBOOK_DIR, exist_ok=True)
os.makedirs(TWITTER_DIR, exist_ok=True)

# Rate limiting (5 requests per minute per IP)
request_counts = {}
REQUEST_LIMIT = 5
REQUEST_WINDOW = timedelta(minutes=1)

# Concurrent download limit
MAX_CONCURRENT_DOWNLOADS = 2
download_queue = Queue()
download_lock = Lock()
active_downloads = 0

# Disk and size limits
MINIMUM_DISK_SPACE_MB = 100
MAX_VIDEO_SIZE_MB = 50

def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        current_time = datetime.now()
        
        if ip not in request_counts:
            request_counts[ip] = []
        
        request_counts[ip] = [t for t in request_counts[ip] if current_time - t < REQUEST_WINDOW]
        
        if len(request_counts[ip]) >= REQUEST_LIMIT:
            return render_template_string(HTML_TEMPLATE, error="Rate limit exceeded. Please try again later.")
        
        request_counts[ip].append(current_time)
        return f(*args, **kwargs)
    return decorated_function

def check_disk_space():
    disk = psutil.disk_usage(BASE_DIR)
    free_space_mb = disk.free / (1024 * 1024)
    if free_space_mb < MINIMUM_DISK_SPACE_MB:
        return False, free_space_mb
    return True, free_space_mb

def limit_concurrent_downloads(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        global active_downloads
        with download_lock:
            if active_downloads >= MAX_CONCURRENT_DOWNLOADS:
                return render_template_string(HTML_TEMPLATE, error="Too many downloads in progress. Please try again later.")
            active_downloads += 1
        
        try:
            return f(*args, **kwargs)
        finally:
            with download_lock:
                active_downloads -= 1
    return decorated_function

def generate_unique_filename(base_dir, url):
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    timestamp = int(time.time())
    return os.path.join(base_dir, f"{url_hash}_{timestamp}")

def download_youtube_video(url):
    ydl_opts = {
        'outtmpl': os.path.join(YOUTUBE_DIR, '%(title)s.%(ext)s'),
        'format': 'best',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'retries': 10,
        'fragment_retries': 10,
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if not os.path.exists(filename):
            raise Exception(f"Downloaded file not found: {filename}")
        file_size_mb = os.path.getsize(filename) / (1024 * 1024)
        if file_size_mb > MAX_VIDEO_SIZE_MB:
            raise Exception(f"Video size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({MAX_VIDEO_SIZE_MB} MB)")
        return filename

def download_instagram_post(url):
    unique_dir = generate_unique_filename(INSTAGRAM_DIR, url)
    if os.path.exists(unique_dir):
        shutil.rmtree(unique_dir)
    os.makedirs(unique_dir, exist_ok=True)

    ydl_opts = {
        'outtmpl': os.path.join(unique_dir, '%(title)s.%(ext)s'),
        'format': 'best',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'retries': 10,
        'fragment_retries': 10,
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        'no_merge': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if not os.path.exists(filename):
            raise Exception(f"Downloaded file not found: {filename}")
        file_size_mb = os.path.getsize(filename) / (1024 * 1024)
        if file_size_mb > MAX_VIDEO_SIZE_MB:
            raise Exception(f"Video size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({MAX_VIDEO_SIZE_MB} MB)")
        return filename

def download_facebook_video(url):
    ydl_opts = {
        'outtmpl': os.path.join(FACEBOOK_DIR, '%(id)s.%(ext)s'),
        'format': 'best',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'retries': 10,
        'fragment_retries': 10,
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        for f in os.listdir(FACEBOOK_DIR):
            if f.endswith('.part'):
                os.remove(os.path.join(FACEBOOK_DIR, f))
        if not os.path.exists(filename):
            raise Exception(f"Downloaded file not found: {filename}")
        file_size_mb = os.path.getsize(filename) / (1024 * 1024)
        if file_size_mb > MAX_VIDEO_SIZE_MB:
            raise Exception(f"Video size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({MAX_VIDEO_SIZE_MB} MB)")
        return filename

def download_twitter_video(url):
    ydl_opts = {
        'outtmpl': os.path.join(TWITTER_DIR, '%(title)s.%(ext)s'),
        'format': 'best',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'retries': 10,
        'fragment_retries': 10,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if not os.path.exists(filename):
            raise Exception(f"Downloaded file not found: {filename}")
        file_size_mb = os.path.getsize(filename) / (1024 * 1024)
        if file_size_mb > MAX_VIDEO_SIZE_MB:
            raise Exception(f"Video size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({MAX_VIDEO_SIZE_MB} MB)")
        return filename

# Updated UI Template with New Color Scheme
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VIDEO DOWNLODER</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Arial', 'Helvetica', sans-serif;
        }

        body {
            background: black; /* Dark gray background */
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            color: #fff; /* White text */
            line-height: 1.6;
        }

        header {
            width: 100%;
            background: black; 
            padding: 2rem 0;
            text-align: center;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5); /* Semi-transparent black shadow */
            border-bottom: 1px solid #ccc; /* Light gray border */
        }

        header h1 {
            font-size: 2.0rem;
            font-weight: 500;
            letter-spacing: 1px;
        }

        .container {
            max-width: 500px;
            width: 90%;
            margin: 40px auto;
            background: black;
            padding: 2.5rem;
            border-radius: 12px;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.5); /* Semi-transparent black shadow */
            text-align: center;
            border: 2px solid #ccc; /* Light gray border */
        }

        .container h2 {
            font-size: 1.8rem;
            color: #fff; /* White text */
            margin-bottom: 1.5rem;
            font-weight: 600;
        }

        .input-group {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            margin-bottom: 1.5rem;
        }

        input[type="text"] {
            padding: 1rem;
            font-size: 1.1rem;
            border: 2px solid ; /* Light gray border */
            border-radius: 8px;
            outline: none;
            background: #121212; /* Dark gray background */
            color: #fff; /* White text */
            transition: border-color 0.3s ease, box-shadow 0.3s ease;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.5); /* Semi-transparent black shadow */
        }

        input[type="text"]::placeholder {
            color: #ccc; /* Light gray placeholder */
            font-style: italic;
            opacity: 0.7;
        }

        input[type="text"]:focus {
            border-color: #fff; /* White border on focus */
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5); /* Semi-transparent black shadow */
        }

        button {
            padding: 1rem 2rem;
            font-size: 1.1rem;
            font-weight: 600;
            color: #121212; /* Dark gray text */
            background: #fff; /* White background */
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: background-color 0.3s ease, transform 0.2s ease;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5); /* Semi-transparent black shadow */
        }

        button:hover {
            background: #ccc; /* Light gray on hover */
            color: #121212; /* Dark gray text */
            transform: translateY(-2px);
        }

        .message {
            color: #fff; /* White text */
            margin-top: 1rem;
            font-size: 1rem;
            font-weight: 700;
            background: #121212; /* Dark gray background */
            padding: 0.5rem;
            border: 1px solid #ccc; /* Light gray border */
        }

        .loader {
            display: none;
            border: 5px solid #ccc; /* Light gray border */
            border-top: 5px solid #fff; /* White spinner */
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 1.5rem auto;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        footer {
            margin-top: auto;
            padding: 1.5rem 0;
            text-align: center;
            color: #ccc; /* Light gray text */
            font-size: 0.95rem;
            width: 100%;
            background: #121212; /* Dark gray background */
            border-top: 1px solid #ccc; /* Light gray border */
        }

        footer p {
            margin: 0;
        }

        footer span {
            font-weight: 700;
        }

        @media (max-width: 500px) {
            header h1 {
                font-size: 2rem;
            }

            .container {
                padding: 1.5rem;
                margin: 20px auto;
            }

            .container h2 {
                font-size: 1.5rem;
            }

            input[type="text"], button {
                font-size: 1rem;
            }

            .loader {
                width: 30px;
                height: 30px;
            }
        }
    </style>
</head>
<body>
    <header>
        <h1>VIDEO DOWNLOADER </h1>
    </header>

    <div class="container">
        <h2>DOWNLOAD VIDEOS BY EASILY  </h2>
        <form id="download-form" method="POST" action="/download">
            <div class="input-group">
                <input type="text" name="url" placeholder="Enter video URL (YouTube, Instagram, Facebook, Twitter)" required>
                <button type="submit">DOWNLOAD</button>
            </div>
        </form>
        <div class="loader" id="loader"></div>
        {% if error %}
            <p class="message">{{ error }}</p>
        {% else %}
            <p class="message" id="success-message" style="display: none;">Download started successfully!</p>
        {% endif %}
    </div>

    <footer>
        <p>© 2025 Video Downloader. All rights reserved. <span>MADE BY  MK</span></p>
    </footer>

    <script>
        const form = document.getElementById('download-form');
        const loader = document.getElementById('loader');
        const successMessage = document.getElementById('success-message');

        form.addEventListener('submit', () => {
            loader.style.display = 'block';
            successMessage.style.display = 'none';
        });

        {% if not error and request.method == 'POST' %}
            loader.style.display = 'none';
            successMessage.style.display = 'block';
        {% endif %}
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, error=None)

@app.route('/download', methods=['POST'])
@rate_limit
@limit_concurrent_downloads
def download_video():
    has_space, free_space_mb = check_disk_space()
    if not has_space:
        return render_template_string(HTML_TEMPLATE, error=f"Insufficient disk space. Only {free_space_mb:.2f} MB free. Need at least {MINIMUM_DISK_SPACE_MB} MB.")

    url = request.form.get('url')

    if not url:
        return render_template_string(HTML_TEMPLATE, error="No URL provided")

    unique_dir = None
    file_path = None
    try:
        if "youtube.com" in url or "youtu.be" in url:
            file_path = download_youtube_video(url)
        elif "instagram.com" in url:
            file_path = download_instagram_post(url)
        elif "facebook.com" in url:
            file_path = download_facebook_video(url)
        elif "twitter.com" in url or "x.com" in url:
            file_path = download_twitter_video(url)
        else:
            return render_template_string(HTML_TEMPLATE, error="Unsupported platform")

        unique_dir = os.path.dirname(file_path)
        return send_file(file_path, as_attachment=True, download_name=secure_filename(os.path.basename(file_path)), mimetype='video/mp4')
    except Exception as e:
        return render_template_string(HTML_TEMPLATE, error=str(e))
    finally:
        if unique_dir and os.path.exists(unique_dir):
            shutil.rmtree(unique_dir, ignore_errors=True)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
