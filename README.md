# BinaryReceptor v3.2.0

> **The ultra-lightweight, zero-bug, high-performance desktop companion server for [BinaryEye](https://github.com/markusfisch/BinaryEye) on Android.**  
> Native Windows architecture with Bluetooth RFCOMM, HTTP webhook listener, SendInput keyboard wedge, and visual token builder.

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?logo=windows&logoColor=white)](https://microsoft.com/windows)
[![Release](https://img.shields.io/badge/Release-v3.2.0-10B981)](https://github.com/ouncommono/BinaryReceptor/releases)
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

```
 +-------------------------+              +-----------------------------------+
 |  Android Device         |              |  Windows PC                       |
 |  (markusfisch/BinaryEye)|              |  (BinaryReceptor Desktop Server)  |
 |                         |  Bluetooth   |                                   |
 |  Camera / Scan Engine   | -----------> |  Winsock RFCOMM Server (AF_BTH)   |
 |                         |    RFCOMM    |                 |                 |
 |                         |              |                 v                 |
 |  HTTP Forwarding Engine | -----------> |  Thread-Safe HTTP Listener (:24234|
 |  (POST / GET / JSON)    |  Wi-Fi / LAN |                 |                 |
 +-------------------------+              +-----------------+-----------------+
                                                            |
                                             Atomic Deduplication Engine
                                             (CRLF Normalization & Sliding Window)
                                                            |
                                                            v
                                             Prefix / Suffix Token Compiler
                                             ({ENTER}, {TAB}, {DATE}, {TIME})
                                                            |
                                                            v
                                             Win32 SendInput Keystroke Wedge
                                             (Active Window: Excel, ERP, CRM)
```

---

## ⚡ Full Features List

| Capability | Description |
| :--- | :--- |
| **Bluetooth RFCOMM Server** | Native Windows `AF_BTH` Winsock RFCOMM listener with Win32 SDP service UUID advertisement (`8a8478c9-2ca8-404b-a0de-101f34ab71ae`). Zero external drivers or virtual COM ports required. |
| **Universal HTTP Server** | Multi-threaded HTTP listener supporting all 4 markusfisch/BinaryEye forwarding options (POST JSON, POST Form, GET Query, GET Append, GET Custom Template) with sub-20ms instant 200 OK responses. |
| **Simultaneous Hybrid Mode** | Listen on both Bluetooth and Wi-Fi simultaneously with seamless automatic failover if one transport disconnects. |
| **Atomic Deduplication** | Thread-safe deduplication engine with canonical CRLF normalization preventing duplicate scans across simultaneous transports. |
| **Visual Prefix / Suffix Builder** | Scrollable, responsive keystroke builder with interactive chip buttons (`{ENTER}`, `{TAB}`, `{SPACE}`, `{DATE}`, `{TIME}`, `{BACKSPACE}`, `{ESC}`, `{DOWN}`). |
| **Keyboard Wedge & Clipboard** | Low-level Win32 `SendInput` Unicode keystroke emulation, rapid clipboard paste (`Ctrl+V`), copy-only mode, and silent log-only mode. |
| **Audio Scanner Chime** | In-memory 16-bit PCM WAV synthesized dual-tone beep (1800Hz → 2400Hz) with zero external audio assets or DLLs. |
| **QR Connection Assistant** | Dynamic QR code generator displaying active network IPs, request mode selector, and 1-click URL copying. |
| **Standalone Barcode Generator** | Encode arbitrary text into 11 barcode symbologies (QR Code, Code 128, DataMatrix, EAN-13, Aztec, PDF417) containing only raw text. |
| **Compact Status Header** | Sleek single-row status strip with real-time health pills and live scan counters taking only 10%–14% of window height. |
| **System Tray & Background Mode**| Minimize to notification area on launch or close, two-way tray status sync, and Windows balloon/toast notifications. |
| **Bilingual RTL / LTR UI** | 100% complete Persian (فارسی - RTL) and English (LTR) localization with exact dictionary parity across all dropdowns, chips, and dialogs. |
| **Live Hot-Reloading settings.ini** | INI file located deterministically alongside `BinaryReceptor.exe` that reloads configuration changes automatically within 1 second. |

---

## 🚀 Quick Start Guide

### Option 1: Standalone Executable (Recommended)
1. Download `BinaryReceptor-v3.2.0-win64.zip` from [GitHub Releases](https://github.com/ouncommono/BinaryReceptor/releases/latest).
2. Extract the archive to any folder on your Windows PC.
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

## 📱 Step-by-Step BinaryEye Setup Guide

### Method 1: Bluetooth RFCOMM (Zero Network Setup)
1. In Windows Settings, pair your Android smartphone via Bluetooth.
2. Open **BinaryEye** on Android:
   - Navigate to **Settings → Bluetooth**.
   - Enable **Send scan via Bluetooth**.
   - Select your paired Windows PC name from the list.
3. In BinaryReceptor, set Operation Mode to **Hybrid Simultaneous** or **Bluetooth Only**.
4. Scan any barcode with BinaryEye; it is typed into the focused Windows window instantaneously.

---

### Method 2: Wi-Fi / LAN HTTP Forwarding
In BinaryEye, navigate to **Settings → Forwarding** and enable **Forward scans**. BinaryReceptor natively supports all 4 request formats:

#### Mode 1: POST - JSON / Form (Recommended)
- **BinaryEye Request Type**: `POST application/json` or `POST application/x-www-form-urlencoded`
- **Configured URL in Phone**: `http://<YOUR_PC_IP>:24234/`
- BinaryReceptor parses JSON keys (`content`, `format`, `raw`, `scanId`) or form url-encoded bodies instantly.

#### Mode 2: GET - Full Query String
- **BinaryEye Request Type**: `GET with full query string`
- **Configured URL in Phone**: `http://<YOUR_PC_IP>:24234/`
- BinaryEye automatically appends `?content=<BARCODE>&raw=<HEX>&format=<FORMAT>`.

#### Mode 3: GET - Simply Add Content (Prefix Query)
- **BinaryEye Request Type**: `GET and simply add content`
- **Configured URL in Phone**: `http://<YOUR_PC_IP>:24234/?content=` (or `http://<YOUR_PC_IP>:24234/`)
- BinaryEye appends the scanned content directly to the end of the URL.

#### Mode 4: GET - Custom Template
- **BinaryEye Request Type**: `GET with custom URL`
- **Configured URL in Phone**: `http://<YOUR_PC_IP>:24234/?content={RESULT}&format={FORMAT}&raw={RESULT_BYTES}`
- BinaryEye substitutes the template variables `{RESULT}`, `{FORMAT}`, and `{RESULT_BYTES}` dynamically.

---

## ⌨️ Prefix & Suffix Token Reference

| Token | Keystroke / Output | Common Use Case |
| :--- | :--- | :--- |
| `{ENTER}` | `VK_RETURN` (Enter) | Submitting an input form or advancing to the next row |
| `{TAB}` | `VK_TAB` (Tab) | Advancing to the next column or text field in Excel/ERP |
| `{SPACE}` | `VK_SPACE` (Space) | Inserting delimiter spaces between scans |
| `{BACKSPACE}`| `VK_BACK` (Backspace) | Deleting unwanted checksum or prefix characters |
| `{ESC}` | `VK_ESCAPE` (Escape) | Dismissing dialogs before or after scanning |
| `{DOWN}` | `VK_DOWN` (Down Arrow) | Navigating downward in grid-based inventory tables |
| `{DATE}` | Current Date (`YYYY-MM-DD`) | Automatic timestamping of scans |
| `{TIME}` | Current Time (`HH:MM:SS`) | Timestamping inspection or arrival times |
| `{TIMESTAMP}`| Full ISO Timestamp | Traceability and audit trails |

---

## ⚙️ Configuration Reference (`settings.ini`)

The `settings.ini` configuration file resides alongside `BinaryReceptor.exe` and hot-reloads within 1 second upon editing:

| Section | Key | Default | Description |
| :--- | :--- | :--- | :--- |
| `[general]` | `mode` | `both` | Operating mode: `both` (Hybrid), `http`, or `bluetooth`. |
| `[general]` | `language` | `en` | UI language: `en` (English - LTR) or `fa` (Persian - RTL). |
| `[general]` | `theme` | `dark` | UI theme: `dark`, `light`, or `system`. |
| `[general]` | `auto_start` | `false` | Automatically start listeners upon launch (Disabled by default). |
| `[general]` | `start_minimized` | `false` | Start minimized to system tray. |
| `[general]` | `minimize_to_tray` | `true` | Minimize window to tray when closing (X). |
| `[general]` | `audio_feedback` | `true` | Synthesize scanner audio chime on successful scan. |
| `[general]` | `tray_notifications` | `true` | Show Windows tray notification on scan. |
| `[network]` | `http_host` | `0.0.0.0` | IP to bind HTTP listener (`0.0.0.0` binds all interfaces). |
| `[network]` | `http_port` | `24234` | Port for BinaryEye forwarding requests. |
| `[keystroke]` | `output_mode` | `type` | Wedge mode: `type` (SendInput), `paste` (Ctrl+V), `copy_only`, `log_only`. |
| `[keystroke]` | `inter_key_delay_ms` | `2` | Micro-delay between keystrokes to ensure ERP compatibility. |
| `[keystroke]` | `prefix` | `""` | Keys/tokens typed before scanned barcode. |
| `[keystroke]` | `suffix` | `{ENTER}` | Keys/tokens typed after scanned barcode. |
| `[filtering]` | `deduplication_enabled` | `true` | Prevent duplicate scans within the sliding time window. |
| `[filtering]` | `deduplication_window_ms`| `1500` | Duplicate rejection threshold in milliseconds. |

---

## 🏗️ Building Standalone Windows Executable

To build the standalone, portable `BinaryReceptor.exe`:

```powershell
# Install build dependencies
pip install -r requirements-build.txt

# Run automated build script
python build.py
# Or run: .\build.bat
```

The resulting binary `dist/BinaryReceptor.exe` and default `dist/settings.ini` are generated with aggressive DLL stripping, resulting in a lightweight, single-file distribution package.

---

## 🧪 Testing

Run the comprehensive test suite verifying all architectural specifications:

```powershell
pytest -v tests/
```

---

# 🇮🇷 راهنمای جامع فارسی (Persian Documentation)

## معرفی و معماری نرم‌افزار
**باینری‌رسپتور نسخه ۳.۲.۰ (BinaryReceptor v3.2.0)** نرم‌افزار سرور همراه و واسط صفحه‌کلید (Keyboard Wedge) برای اپلیکیشن محبوب و متن‌باز [BinaryEye](https://github.com/markusfisch/BinaryEye) در گوشی‌های اندروید است. این برنامه گوشی هوشمند شما را به یک بارکدخوان بی‌سیم صنعتی و فوق‌سریع برای کامپیوترهای ویندوز تبدیل می‌کند.

با اسکن هرگونه بارکد میله‌ای (EAN-13، Code 128، UPC) یا کدهای دوبعدی (QR Code، DataMatrix، Aztec) با دوربین گوشی، محتوای اسکن‌شده به صورت آنی از طریق **بلوتوث (RFCOMM)** یا **شبکه وای‌فای (HTTP)** و یا **هر دو به صورت همزمان (حالت هیبریدی)** به کامپیوتر منتقل شده و مستقیماً در نرم‌افزار فعال ویندوز (اکسل، نرم‌افزارهای حسابداری، انبارداری، مرورگر، نوت‌پد) تایپ می‌شود.

---

## 🌟 قابلیت‌ها و مزایای برجسته

- **پشتیبانی کامل از بلوتوث و شبکه:** پشتیبانی همزمان از سوکت مستقیم بلوتوث RFCOMM بدون نیاز به پورت سریال مجازی، و سرور فوق‌سریع HTTP با پاسخگویی زیر ۲۰ میلی‌ثانیه.
- **سازگاری ۱۰۰٪ با ۴ حالت ارسال BinaryEye:** پشتیبانی کامل از حالت‌های POST با ساختار JSON، فرم x-www-form-urlencoded، متد GET با رشته پرسمان کامل، افزودن مستقیم مقدار، و الگوهای سفارشی.
- **سیستم فیلتر هوشمند ضدتکرار (Deduplication):** جلوگیری از ورود داده‌های تکراری حاصل از اسکن‌های ناخواسته همزمان از هر دو کانال شبکه و بلوتوث.
- **سازنده بصری پیشوند و پسوند (Prefix/Suffix Builder):** رابط کاربری روان و اسکرول‌پذیر با دکمه‌های درج آسان کلیدهای اینتر، تب، فاصله، پاک کردن، تاریخ و ساعت جاری.
- **شبیه‌سازی حرفه‌ای صفحه‌کلید و کلیپ‌بورد:** تایپ از طریق APIهای سطح پایین `SendInput` یونیکد، پیست فوری با `Ctrl+V`، و حالت فقط کپی در کلیپ‌بورد.
- **صدای شفاف اسکنر (Audio Chime):** تولید درون‌برنامه‌ای صدای استاندارد بارکدخوان صنعتی (۱۸۰۰ تا ۲۴۰۰ هرتز) بدون نیاز به فایل‌های صوتی جانبی.
- **نوار وضعیت فشرده و کارآمد:** طراحی مدرن تک‌سطری نوار وضعیت با نشانگرهای رنگی زنده که فضای مفید صفحه را برای پنجره اصلی آزاد نگه می‌دارد.
- **رابط کاربری دوزبانه استاندارد:** طراحی راست‌به‌چپ (RTL) کاملاً طبیعی برای زبان فارسی و چپ‌به‌راست (LTR) برای انگلیسی با ترجمه دقیق تمامی منوها، دکمه‌ها و پنجره‌ها.
- **فایل اجرایی پرتابل بدون نیاز به نصب:** تولید نسخه نهایی در قالب یک فایل تکی `BinaryReceptor.exe` با حجم بهینه بدون نیاز به نصب پایتون یا پیش‌نیازهای اضافه.

---

## 🚀 راهنمای شروع سریع

### ۱. اجرای فایل آماده پرتابل (پیشنهادی)
۱. بسته فشرده `BinaryReceptor-v3.2.0-win64.zip` را از بخش [انتشارهای گیت‌هاب (Releases)](https://github.com/ouncommono/BinaryReceptor/releases/latest) دانلود کنید.  
۲. محتویات فایل زیپ را در یک پوشه دلخواه استخراج کنید.  
۳. فایل `BinaryReceptor.exe` را اجرا کنید.  
۴. روی دکمه **شروع به کار سرور** کلیک نمایید.

### ۲. اجرا از سورس‌کد
```powershell
git clone https://github.com/ouncommono/BinaryReceptor.git
cd BinaryReceptor
pip install -r requirements.txt
python run.py
```

---

## 📱 راهنمای گام‌به‌گام اتصال گوشی به کامپیوتر

### روش ۱: اتصال از طریق بلوتوث (بدون نیاز به شبکه و روتر)
۱. در بخش تنظیمات بلوتوث ویندوز، گوشی اندروید خود را جفت (Pair) کنید.  
۲. در برنامه **BinaryEye** گوشی به مسیر **تنظیمات (Settings) ← بلوتوث (Bluetooth)** بروید.  
۳. گزینه **ارسال اسکن از طریق بلوتوث** را روشن کرده و نام کامپیوتر خود را انتخاب کنید.  
۴. در برنامه BinaryReceptor، حالت کاری را روی **ترکیبی همزمان** یا **فقط بلوتوث** قرار دهید.  
۵. هر بارکدی را اسکن کنید؛ بلافاصله در پنجره فعال کامپیوتر تایپ خواهد شد.

---

### روش ۲: اتصال از طریق شبکه محلی و وای‌فای (HTTP Forwarding)
در برنامه BinaryEye به مسیر **تنظیمات ← ارسال (Forwarding)** رفته و گزینه **ارسال اسکن‌ها** را فعال کنید. چهار حالت استاندارد زیر پشتیبانی می‌شوند:

۱. **حالت اول: POST با ساختار JSON (پیشنهادی)**
   - نوع درخواست در گوشی: `POST application/json`
   - نشانی سرور: `http://<IP_کامپیوتر>:24234/`

۲. **حالت دوم: GET با رشته پرسمان کامل (Full Query String)**
   - نوع درخواست در گوشی: `GET with full query string`
   - نشانی سرور: `http://<IP_کامپیوتر>:24234/`

۳. **حالت سوم: GET با افزودن مستقیم مقدار بارکد (Simply Add Content)**
   - نوع درخواست در گوشی: `GET and simply add content`
   - نشانی سرور: `http://<IP_کامپیوتر>:24234/?content=` (یا `http://<IP_کامپیوتر>:24234/`)

۴. **حالت چهارم: GET با الگوی اختصاصی (Custom Template)**
   - نوع درخواست در گوشی: `GET with custom URL`
   - نشانی سرور: `http://<IP_کامپیوتر>:24234/?content={RESULT}&format={FORMAT}&raw={RESULT_BYTES}`

---

## ⌨️ راهنمای توکن‌ها و کلیدهای ویژه

| توکن | کلید معادل در ویندوز | کاربرد |
| :--- | :--- | :--- |
| `{ENTER}` | کلید Enter | ثبت فرم، رفتن به سطر بعدی یا ارسال داده |
| `{TAB}` | کلید Tab | انتقال مکان‌نما به فیلد یا ستون بعدی در اکسل |
| `{SPACE}` | کلید Space | درج فاصله میان کدهای متوالی |
| `{BACKSPACE}`| کلید Backspace | حذف کاراکترهای اضافی یا ارقام کنترلی ناخواسته |
| `{ESC}` | کلید Escape | بستن پنجره‌های بازشو پیش یا پس از اسکن |
| `{DOWN}` | کلید فلش رو به پایین | حرکت به ردیف پایینی در جدول انبارداری |
| `{DATE}` | تاریخ روز جاری | درج خودکار تاریخ سیستم (`YYYY-MM-DD`) |
| `{TIME}` | ساعت جاری | درج خودکار زمان دقیق ثبت (`HH:MM:SS`) |
| `{TIMESTAMP}`| برچسب زمانی کامل | ثبت دقیق تاریخ و ساعت استاندارد بین‌المللی |

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
