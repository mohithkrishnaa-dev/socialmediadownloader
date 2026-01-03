# Video Downloader Backend

A Flask-based backend service that allows users to download videos from supported platforms such as **YouTube, Instagram, Facebook, and X (Twitter)** using `yt-dlp`.

The project includes rate limiting, file size limits, disk space checks, and concurrent download control to prevent abuse.

---

## ⚠️ Disclaimer

This project is created **for educational and personal use only**.

The author does **not encourage copyright infringement**.  
Users are responsible for ensuring they have the legal right to download any content.

---

## ✨ Features

- Supports YouTube, Instagram, Facebook, and X (Twitter)
- Built using Flask + yt-dlp
- Rate limiting per IP
- Concurrent download limit
- Maximum video size enforcement
- Disk space safety check
- Automatic cleanup after download
- Simple dark-themed UI
- Ready for deployment on Vercel / VPS

---

## 🧰 Tech Stack

- Python 3
- Flask
- yt-dlp
- HTML/CSS (inline template)
- psutil (disk monitoring)

---

## 📦 Installation

```bash
pip install -r requirements.txt
