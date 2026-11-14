# BinaryReceptor v3.2.0

> **The ultra-lightweight, zero-bug, high-performance desktop companion server for [BinaryEye](https://github.com/markusfisch/BinaryEye) on Android.**  
> Native Windows architecture with Bluetooth RFCOMM, HTTP webhook listener, SendInput keyboard wedge, and visual token builder.

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?logo=windows&logoColor=white)](https://microsoft.com/windows)
[![Version](https://img.shields.io/badge/Release-v3.2.0-10B981)](https://github.com/ouncommono/BinaryReceptor/releases)
[![Build Status](https://github.com/ouncommono/BinaryReceptor/actions/workflows/build_release.yml/badge.svg)](https://github.com/ouncommono/BinaryReceptor/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🌐 Languages / زبان‌ها
- [English Documentation](#-english-documentation)
- [راهنمای جامع فارسی (Persian Documentation)](#-راهنمای-جامع-فارسی-persian-documentation)

---

# 🇬🇧 English Documentation

## Executive Overview
**BinaryReceptor v3.2.0** is the official modern desktop companion server for the Android barcode scanner [BinaryEye](https://github.com/markusfisch/BinaryEye). It transforms any Android smartphone running BinaryEye into an industrial-grade wireless barcode scanner for Windows PCs.

Whenever a 1D barcode (EAN-13, Code 128, UPC-A, Code 39) or 2D code (QR Code, DataMatrix, Aztec, PDF417) is scanned on mobile, BinaryReceptor captures the payload instantaneously over **Bluetooth RFCOMM**, **Wi-Fi / LAN HTTP**, or **both simultaneously in Hybrid mode**. The scanned data is wedged directly into the active Windows application (Excel, ERP systems, accounting software, Point of Sale, web browsers, Notepad) using low-level Win32 `SendInput` Unicode keystrokes or instant clipboard paste (`Ctrl+V`).

BinaryReceptor is engineered in modern Python and native Win32 APIs, compiling into a standalone, portable Windows `.exe` (`BinaryReceptor.exe`) with minimal memory and disk footprint.

---

## ⚡ Key Features

| Capability | Description |
| :--- | :--- |
| **Dual Transport Architecture** | Native Bluetooth RFCOMM (`AF_BTH` / Winsock SDP) and high-speed HTTP listener with sub-5ms response time. |
| **Hybrid Operation Mode** | Listen on both Bluetooth and Wi-Fi simultaneously without interference or dropped packets. |
| **Markusfisch BinaryEye 100% Native** | Direct out-of-the-box support for all 4 BinaryEye HTTP request modes (POST JSON, POST Form, GET Query, GET Append). |
| **Atomic Deduplication** | Thread-safe deduplication engine with canonical CRLF normalization preventing duplicate scans across simultaneous transports. |
| **Responsive Wedge Builder** | Scrollable prefix/suffix builder with interactive chip buttons (`{ENTER}`, `{TAB}`, `{SPACE}`, `{DATE}`, `{TIME}`, `{BACKSPACE}`). |
| **Audio Scanner Chime** | In-memory 16-bit PCM WAV synthesized dual-tone beep (1800Hz → 2400Hz) with zero external audio assets. |
| **Compact Status Header** | Sleek single-row status strip with real-time health pills and live scan counters. |
| **Full Bilingual Support** | 100% feature and label parity between English (LTR) and Persian (فارسی - RTL). |
| **Zero-Install Portable** | Standalone single-file executable requiring no Python runtime, runtimes, or administrator privileges. |

---

## 🚀 Quick Start Guide

### Option 1: Standalone Executable (Recommended)
1. Download `BinaryReceptor-v3.2.0-win64.zip` from [GitHub Releases](https://github.com/ouncommono/BinaryReceptor/releases/latest).
2. Extract the archive anywhere on your PC.
3. Launch `BinaryReceptor.exe`.
4. Click **Start Server** (or enable auto-start in Settings).

### Option 2: Running from Source
```powershell
# Clone the repository
git clone https://github.com/ouncommono/BinaryReceptor.git
cd BinaryReceptor

# Install required dependencies
pip install -r requirements.txt

# Run application
python run.py
```

---

## 📱 Connecting BinaryEye to BinaryReceptor

### Method 1: Bluetooth RFCOMM (Zero Network Setup)
1. In Windows Settings, pair your Android phone via Bluetooth.
2. Open **BinaryEye** on Android:
   - Go to **Settings → Bluetooth**.
   - Enable **Send scan via Bluetooth**.
   - Select your paired Windows PC.
3. In BinaryReceptor, set Operation Mode to **Hybrid (Both)** or **Bluetooth Only**.
4. Scan any barcode; it is typed into your active Windows window immediately.

---

### Method 2: Wi-Fi / LAN HTTP Forwarding
In BinaryEye, navigate to **Settings → Forwarding** and enable **Forward scans**. BinaryReceptor natively supports all 4 request formats:

#### Mode A: POST application/json (Recommended)
- **BinaryEye Request Type:** `POST application/json`
- **Forwarding URL:** `http://<YOUR_PC_IP>:24234/scan`
- **Payload Structure:**
  ```json
  {"content": "9780132350884", "format": "EAN_13", "raw": "..."}
  ```

#### Mode B: POST application/x-www-form-urlencoded
- **BinaryEye Request Type:** `POST application/x-www-form-urlencoded`
- **Forwarding URL:** `http://<YOUR_PC_IP>:24234/scan`
- **Payload Structure:** `content=9780132350884&format=EAN_13`

#### Mode C: GET with full query string
- **BinaryEye Request Type:** `GET with full query string`
- **Forwarding URL:** `http://<YOUR_PC_IP>:24234/scan`
- **Request Generated:** `GET /scan?content=9780132350884&format=EAN_13&raw=...`

#### Mode D: GET and simply add content
- **BinaryEye Request Type:** `GET and simply add content`
- **Forwarding URL:** `http://<YOUR_PC_IP>:24234/scan?content=` (or `http://<YOUR_PC_IP>:24234/`)
- **Request Generated:** `GET /scan?content=9780132350884`

> [!TIP]
> Use the **Connection & QR Code** tab in BinaryReceptor to select your desired request mode and scan the generated QR code directly on your monitor to copy the configuration URL.

---

## ⌨️ Prefix & Suffix Token Reference

BinaryReceptor features a visual token compiler supporting dynamic actions before and after scanned barcodes:

| Token | Keystroke / Effect | Output Example |
| :--- | :--- | :--- |
| `{ENTER}` | Presses the Enter / Return key | Moves to the next line or submits a form |
| `{TAB}` | Presses the Tab key | Moves to the next input field or spreadsheet cell |
| `{SPACE}` | Types a single space | Adds separation |
| `{BACKSPACE}` | Backspaces previous character | Corrects or trims prefixes |
| `{DATE}` | Current system date | `2026-11-14` |
| `{TIME}` | Current system time | `01:30:00` |
| `{TIMESTAMP}` | Full ISO date & time | `2026-11-14 01:30:00` |
| `{ESC}` | Presses Escape key | Dismisses dialogs |
| `{DOWN}` | Down Arrow key | Moves down one row |
| `{F1}` – `{F12}` | Function keys F1 through F12 | Triggers ERP/POS shortcuts |

---

## ⚙️ Configuration Reference (`settings.ini`)

`settings.ini` is located in the same folder as `BinaryReceptor.exe` and hot-reloads within 1 second of any external modification:

| Section | Parameter | Default | Description |
| :--- | :--- | :--- | :--- |
| `[general]` | `mode` | `both` | Active transport: `both`, `http`, or `bluetooth`. |
| `[general]` | `language` | `en` | Interface language: `en` (English) or `fa` (فارسی). |
| `[general]` | `theme` | `dark` | UI theme: `dark`, `light`, or `system`. |
| `[general]` | `auto_start` | `false` | Start listeners automatically on application launch. |
| `[general]` | `minimize_to_tray` | `true` | Minimize to system tray on window close (`X`). |
| `[general]` | `audio_feedback` | `true` | Play audible scanner chime on valid scan. |
| `[network]` | `http_host` | `0.0.0.0` | Binding network IP (`0.0.0.0` for all adapters). |
| `[network]` | `http_port` | `24234` | HTTP server listening port. |
| `[bluetooth]`| `bt_enabled` | `true` | Enable or disable Bluetooth RFCOMM server. |
| `[wedge]` | `output_mode` | `type` | Wedge mode: `type`, `paste` (Ctrl+V), or `copy_only`. |
| `[wedge]` | `prefix` | `""` | Tokens or text typed before barcode. |
| `[wedge]` | `suffix` | `{ENTER}` | Tokens or text typed after barcode. |
| `[deduplication]` | `deduplication_enabled` | `true` | Prevent duplicate scans from dual transports. |
| `[deduplication]` | `deduplication_window_ms` | `1500` | Sliding window in milliseconds. |
| `[filters]` | `trim_whitespace` | `true` | Remove leading and trailing whitespace. |
| `[filters]` | `replace_newlines` | `none` | Replace internal newlines: `none`, `tab`, or `space`. |

---

## 🏗️ Building Standalone Windows Executable

To compile a trimmed, high-performance standalone binary:
```powershell
python build.py
```
This builds `dist/BinaryReceptor.exe` with aggressive stripping of unneeded DLLs (`opengl32sw.dll`, Qt6Qml, Qt6Quick, Qt6Pdf, unused Qt plugins) and UPX compression.

---

## 🧪 Testing

BinaryReceptor features a comprehensive test suite covering all architectural subsystems:
```powershell
python -m pytest -v
```

---

# 🇮🇷 راهنمای جامع فارسی (Persian Documentation)

## معرفی و معماری نرم‌افزار
**باینری‌رسپتور نسخه ۳.۲.۰ (BinaryReceptor v3.2.0)** سرور همراه رسمی، فوق‌العاده سبک و بدون باگ برای اسکنر بارکد اندروید [BinaryEye](https://github.com/markusfisch/BinaryEye) است. با استفاده از این نرم‌افزار، گوشی هوشمند اندرویدی شما مستقیماً به یک بارکدخوان بی‌سیم صنعتی برای کامپیوتر ویندوزی تبدیل می‌شود.

هنگام اسکن هرگونه بارکد میله‌ای (EAN-13، Code 128، UPC) یا کدهای دوبعدی (QR Code، DataMatrix) در گوشی، داده‌ها در کمتر از ۵ میلی‌ثانیه از طریق **بلوتوث (Bluetooth RFCOMM)**، **شبکه وای‌فای / محلی (HTTP)** یا **هر دو به صورت همزمان (حالت هیبریدی)** به کامپیوتر منتقل شده و مستقیماً در نرم‌افزار فعال (اکسل، نرم‌افزارهای مالی، حسابداری، انبارداری، فرم‌های تحت وب و ...) تایپ یا پیست می‌شوند.

---

## 🌟 قابلیت‌ها و مزایای برجسته

- **معماری دوگانه و مستقل:** پشتیبانی کامل از بلوتوث و شبکه با ایزولاسیون دقیق کانال‌های ارتباطی.
- **سازگاری ۱۰۰٪ با ۴ حالت ارسالی BinaryEye:** پشتیبانی بی‌نقص از ارسال‌های JSON، فرم اینترنتی، و متدهای GET.
- **جلوگیری هوشمند از اسکن تکراری (Deduplication):** موتور چندنخی ضدتکرار با نرمال‌سازی کدهای دریافتی مانع از دوباره تایپ شدن بارکدها در ارتباط همزمان بلوتوث و وای‌فای می‌شود.
- **سازنده پیشوند و پسوند اسکرول‌پذیر:** محیط بصری چینش کلیدهای اینتر، تب، فاصله، تاریخ، زمان و کلیدهای تابعی با پشتیبانی کامل از ابعاد کوچک پنجره.
- **صدای شفاف اسکنر:** تولید مستقیم و بدون وقفه صدای اسکنر (۱۸۰۰Hz تا ۲۴۰۰Hz) با فرمت ۱۶-بیت PCM درون حافظه رم.
- **نوار وضعیت جمع‌وجور:** نمایش وضعیت سرور، بلوتوث، شبکه و آمار اسکن در یک ردیف مدرن و مینیمال.
- **پشتیبانی کامل دوزبانه:** ترجمه و چینش دقیق راست‌به‌چپ برای زبان فارسی و چپ‌به‌راست برای زبان انگلیسی.
- **فایل اجرایی پرتابل و بدون نیاز به نصب:** فایل `BinaryReceptor.exe` مستقل، بهینه‌سازی‌شده و آماده اجرا روی ویندوز ۱۰ و ۱۱.

---

## 🚀 راهنمای شروع سریع

### ۱. اجرای فایل آماده پرتابل (پیشنهادی)
۱. بسته فشرده `BinaryReceptor-v3.2.0-win64.zip` را از بخش [GitHub Releases](https://github.com/ouncommono/BinaryReceptor/releases/latest) دریافت کنید.  
۲. محتویات را در پوشه دلخواه استخراج کرده و `BinaryReceptor.exe` را اجرا کنید.  
۳. دکمه **شروع سرور** را کلیک نمایید.

### ۲. اجرا از سورس‌کد
```powershell
git clone https://github.com/ouncommono/BinaryReceptor.git
cd BinaryReceptor
pip install -r requirements.txt
python run.py
```

---

## 📱 راهنمای اتصال گوشی به کامپیوتر

### روش ۱: اتصال از طریق بلوتوث
۱. بلوتوث گوشی و کامپیوتر را روشن کرده و آنها را در تنظیمات ویندوز جفت (Pair) کنید.  
۲. در برنامه **BinaryEye** گوشی به مسیر **تنظیمات (Settings) ← بلوتوث (Bluetooth)** بروید.  
۳. گزینه **ارسال اسکن از طریق بلوتوث** را فعال کرده و نام کامپیوتر خود را انتخاب کنید.  
۴. در برنامه BinaryReceptor، حالت کاری را روی **هر دو (هیبریدی)** یا **فقط بلوتوث** بگذارید.

---

### روش ۲: اتصال از طریق شبکه وای‌فای / HTTP
در برنامه BinaryEye به مسیر **تنظیمات ← ارسال (Forwarding)** رفته و گزینه **ارسال اسکن‌ها** را فعال کنید. چهار حالت استاندارد زیر پشتیبانی می‌شوند:

۱. **حالت POST با ساختار JSON (پیشنهادی):**
   - نوع درخواست در گوشی: `POST application/json`
   - نشانی سرور: `http://<IP_کامپیوتر>:24234/scan`

۲. **حالت POST فرم اینترنتی:**
   - نوع درخواست در گوشی: `POST application/x-www-form-urlencoded`
   - نشانی سرور: `http://<IP_کامپیوتر>:24234/scan`

۳. **حالت GET با پارامترهای کامل:**
   - نوع درخواست در گوشی: `GET with full query string`
   - نشانی سرور: `http://<IP_کامپیوتر>:24234/scan`

۴. **حالت GET با افزودن مستقیم مقدار بارکد:**
   - نوع درخواست در گوشی: `GET and simply add content`
   - نشانی سرور: `http://<IP_کامپیوتر>:24234/scan?content=` (یا `http://<IP_کامپیوتر>:24234/`)

---

## ⌨️ راهنمای توکن‌ها و کلیدهای ویژه

| توکن | کلید معادل در ویندوز | کاربرد |
| :--- | :--- | :--- |
| `{ENTER}` | کلید Enter | ثبت فرم یا رفتن به خط بعدی |
| `{TAB}` | کلید Tab | رفتن به فیلد یا ستون بعدی در اکسل |
| `{SPACE}` | کلید Space | درج فاصله |
| `{BACKSPACE}`| کلید Backspace | حذف کاراکتر قبلی |
| `{DATE}` | تاریخ روز جاری | درج خودکار تاریخ سیستم (`2026-11-14`) |
| `{TIME}` | ساعت جاری | درج خودکار زمان سیستم (`01:30:00`) |
| `{TIMESTAMP}` | تاریخ و ساعت کامل | درج برچسب زمانی جامع |
| `{F1}` تا `{F12}` | کلیدهای F1 تا F12 | اجرای کلیدهای میانبر نرم‌افزارهای حسابداری |

---

## ⚙️ جدول تنظیمات نرم‌افزار (`settings.ini`)

فایل تنظیمات `settings.ini` همواره در کنار فایل اجرایی برنامه قرار داشته و در صورت ویرایش دستی با نوت‌پد، ظرف کمتر از ۱ ثانیه به صورت خودکار در برنامه بارگذاری مجدد می‌شود:

- `mode`: حالت دریافت داده (`both` برای بلوتوث و شبکه، `http` برای فقط شبکه، `bluetooth` برای فقط بلوتوث).
- `language`: زبان محیط کاربری (`fa` فارسی یا `en` انگلیسی).
- `theme`: پوسته نرم‌افزار (`dark` تیره، `light` روشن یا `system` همگام با ویندوز).
- `auto_start`: روشن شدن خودکار سرور در بدو اجرای برنامه (پیش‌فرض: `false`).
- `minimize_to_tray`: کمینه‌سازی در کنار ساعت ویندوز با کلیک روی ضربدر بستن (پیش‌فرض: `true`).
- `audio_feedback`: پخش صدای بیپ پس از دریافت موفق اسکن (پیش‌فرض: `true`).
- `http_port`: پورت شنود سرور تحت شبکه (پیش‌فرض: `24234`).
- `output_mode`: نحوه درج داده در ویندوز (`type` تایپ با کیبورد، `paste` پیست سریع با کلیپ‌بورد، `copy_only` فقط کپی).
- `suffix`: کلیدهایی که پس از بارکد تایپ می‌شوند (پیش‌فرض: `{ENTER}`).
- `deduplication_enabled`: فعال بودن فیلتر ضدتکرار هوشمند (پیش‌فرض: `true`).

---

## 📜 پروانه نرم‌افزار و حقوق نشر (License)

این پروژه تحت مجوز آزاد [MIT License](LICENSE) منتشر شده است.  
توسعه و بازنویسی جامع نسخه ۳ توسط **ouncommono**.  
پروژه اصلی: [KamaleiZestri/BinaryReceptor](https://github.com/KamaleiZestri/BinaryReceptor).  
کلاینت اندروید: [BinaryEye](https://github.com/markusfisch/BinaryEye) اثر Markus Fisch.
