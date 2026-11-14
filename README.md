# BinaryReceptor v3.4.0

> **The ultra-lightweight, zero-bug, high-performance desktop companion server for [BinaryEye](https://github.com/markusfisch/BinaryEye) on Android.**  
> Native Windows architecture with Bluetooth RFCOMM, HTTP webhook listener, low-level Win32 `SendInput` Unicode keyboard wedge, global HID deduplication hook, and visual token builder.

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?logo=windows&logoColor=white)](https://microsoft.com/windows)
[![Release](https://img.shields.io/badge/Release-v3.4.0-10B981)](https://github.com/ouncommono/BinaryReceptor/releases)
[![Build Status](https://github.com/ouncommono/BinaryReceptor/actions/workflows/build_release.yml/badge.svg)](https://github.com/ouncommono/BinaryReceptor/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🌐 Languages / زبان‌ها
- [English Documentation](#-english-documentation)
- [راهنمای جامع فارسی (Persian Documentation)](#-راهنمای-جامع-فارسی-persian-documentation)

---

# 🇬🇧 English Documentation

## Executive Overview & Architecture
**BinaryReceptor v3.4.0** is the production-grade desktop companion server for the open-source Android barcode scanner [BinaryEye](https://github.com/markusfisch/BinaryEye). It transforms any Android smartphone running BinaryEye into an industrial-grade, zero-latency wireless barcode scanner for Windows workstations.

Whenever a 1D linear barcode (EAN-13, Code 128, UPC-A, Code 39) or 2D matrix code (QR Code, DataMatrix, Aztec, PDF417) is scanned on mobile, BinaryReceptor captures the payload instantaneously over **Bluetooth RFCOMM**, **Wi-Fi / LAN HTTP**, or **both simultaneously in Hybrid mode**. The scanned data is wedged directly into the active Windows application (Excel, ERP systems, accounting software, Point of Sale, web browsers, Notepad) using low-level Win32 `SendInput` Unicode code points (bypassing the host keyboard layout) or instant clipboard paste (`Ctrl+V`).

```
 +-------------------------+              +-----------------------------------+
 |  Android Device         |              |  Windows PC                       |
 |  (markusfisch/BinaryEye)|              |  (BinaryReceptor Desktop Server)  |
 |                         |  Bluetooth   |                                   |
 |  Camera / Scan Engine   | -----------> |  Winsock RFCOMM Server (AF_BTH)   |
 |                         |    RFCOMM    |                 |                 |
 |                         |              |                 v                 |
 |  HTTP Forwarding Engine | -----------> |  Sub-ms HTTP Listener (:24234)    |
 |  (POST / GET / JSON)    |  Wi-Fi / LAN |  (Returns 200 OK + scanId)        |
 +-------------------------+              +-----------------+-----------------+
                                                            |
                                             Global Low-Level Keyboard Hook
                                             (WH_KEYBOARD_LL & HID Burst Gate)
                                                            |
                                                            v
                                             Time-Interval Cooldown Deduplicator
                                             (Cross-Protocol & scanId Matching)
                                                            |
                                                            v
                                             Prefix / Suffix Token Compiler
                                             ({ENTER}, {TAB}, {DATE}, {TIME})
                                                            |
                                                            v
                                             Win32 SendInput Unicode Engine
                                             (wVk=0, wScan=UTF-16 Code Point)
                                             (Active Window: Excel, ERP, CRM)
```

---

## ⚡ Key Architectural Features

| Capability | Description |
| :--- | :--- |
| **Bluetooth RFCOMM Server** | Native Windows `AF_BTH` Winsock RFCOMM listener with Win32 SDP service UUID advertisement (`8a8478c9-2ca8-404b-a0de-101f34ab71ae`). Zero external drivers or virtual COM ports required. |
| **Universal Sub-ms HTTP Server** | Multi-threaded HTTP listener supporting all BinaryEye forwarding formats (POST JSON, POST Form, GET Query, GET Append, GET Custom Template) with sub-millisecond immediate 200 OK JSON responses. |
| **Strict Operation Mode Isolation** | When HTTP Server Only is configured, Bluetooth listeners are cleanly stopped and redundant HTTP injection pathways are actively discarded if incoming HID input is detected. |
| **Global Low-Level Keyboard Hook** | Native Win32 `WH_KEYBOARD_LL` hook detecting high-speed physical/HID barcode scanner bursts (< 50ms), preventing double-typing across simultaneous protocols. |
| **Hardware Copy-to-Clipboard Routing** | In `Copy to clipboard only` mode, raw HID keystrokes are intercepted, blocked from typing into the focused window, and routed directly to the Windows clipboard. |
| **Keyboard Layout Independence** | Keystroke injection exclusively invokes Win32 `SendInput` with `KEYEVENTF_UNICODE` (`wVk=0`, `wScan=UTF-16 code point`), completely eliminating garbled characters under Persian (Farsi) or non-English Windows layouts. |
| **Visual Prefix / Suffix Builder** | Scrollable, responsive keystroke wedge editor with interactive chip buttons (`{ENTER}`, `{TAB}`, `{SPACE}`, `{DATE}`, `{TIME}`, `{BACKSPACE}`, `{ESC}`, `{DOWN}`). |
| **Audio Scanner Chime** | In-memory 16-bit PCM WAV synthesized dual-tone chime (1800Hz → 2400Hz) with zero external audio assets or DLL dependencies. |
| **QR Connection Assistant** | Dynamic QR code generator displaying active network interface IPs, request mode selector, and 1-click URL copying. |
| **Standalone Barcode Generator** | Encode arbitrary text into 11 barcode symbologies (QR Code, Code 128, DataMatrix, EAN-13, Aztec, PDF417) containing raw text verbatim. |
| **Dedicated Scans Statistics Header**| Live KPI metrics (Total Scans, Bluetooth Scans, HTTP Scans, Duplicates Blocked) integrated cleanly into the top header of the Live Scan Activity page. |
| **100% Bilingual RTL / LTR UI** | Complete Persian (فارسی - RTL) and English (LTR) localization with exact dictionary parity across all dropdowns, chips, section headers, and dialogs. |
| **Live Hot-Reloading `settings.ini`** | INI file located deterministically alongside `BinaryReceptor.exe` that reloads configuration changes automatically within 1 second. |

---

## 🚀 Quick Start Guide

### Option 1: Standalone Executable (Recommended)
1. Download `BinaryReceptor-v3.4.0-win64.zip` from [GitHub Releases](https://github.com/ouncommono/BinaryReceptor/releases/latest).
2. Extract the archive to any folder on your Windows workstation.
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
4. Scan any barcode with BinaryEye; it is injected into the focused Windows window instantaneously.

---

### Method 2: Wi-Fi / LAN HTTP Forwarding
In BinaryEye, navigate to **Settings → Forwarding** and enable **Forward scans**. BinaryReceptor natively supports all standard request formats:

#### Mode 1: POST application/json (Recommended)
- **BinaryEye Request Type**: `POST application/json`
- **Configured URL in Phone**: `http://<YOUR_PC_IP>:24234/`
- BinaryReceptor parses JSON keys (`content`, `format`, `raw`, `scanId`) with instant sub-millisecond 200 OK responses.

#### Mode 2: POST application/x-www-form-urlencoded
- **BinaryEye Request Type**: `POST application/x-www-form-urlencoded`
- **Configured URL in Phone**: `http://<YOUR_PC_IP>:24234/`
- BinaryEye sends form urlencoded body with `content`, `format`, `raw`.

#### Mode 3: GET with full query string
- **BinaryEye Request Type**: `GET with full query string`
- **Configured URL in Phone**: `http://<YOUR_PC_IP>:24234/`
- BinaryEye automatically appends `?content=<BARCODE>&raw=<HEX>&format=<FORMAT>&scanId=<ID>`.

#### Mode 4: GET and simply add content
- **BinaryEye Request Type**: `GET and simply add content`
- **Configured URL in Phone**: `http://<YOUR_PC_IP>:24234/?content=` (or `http://<YOUR_PC_IP>:24234/`)
- BinaryEye appends the scanned content directly to the end of the URL.
- Optional Template: `http://<YOUR_PC_IP>:24234/?content={RESULT}&format={FORMAT}&raw={RESULT_BYTES}`

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
| `[bluetooth]` | `bt_enabled` | `true` | Enable native Windows Bluetooth RFCOMM listener. |
| `[bluetooth]` | `service_uuid` | `8a8478c9-...` | BinaryEye standard Bluetooth Service SDP UUID. |
| `[wedge]` | `output_mode` | `type` | Wedge mode: `type` (SendInput), `paste` (Ctrl+V), `copy_only`, `log_only`. |
| `[wedge]` | `inter_key_delay_ms` | `0` | Micro-delay between keystrokes to ensure ERP compatibility. |
| `[wedge]` | `prefix` | `""` | Keys/tokens typed before scanned barcode. |
| `[wedge]` | `suffix` | `{ENTER}` | Keys/tokens typed after scanned barcode. |
| `[deduplication]` | `deduplication_enabled` | `true` | Prevent duplicate scans within the cooldown window. |
| `[deduplication]` | `deduplication_window_ms`| `1500` | Duplicate suppression cooldown interval in milliseconds. |

---

## 🔧 Troubleshooting & FAQ

- **Port Conflict (Error binding :24234)**: If another application uses port 24234, change the port in Settings (e.g., 25000) and click Save Settings.
- **Bluetooth Adapter Off**: Ensure Bluetooth is enabled in Windows Settings and that your PC has a functional Bluetooth adapter.
- **Double-typing in Hybrid Mode**: The integrated WH_KEYBOARD_LL hook and cooldown gate automatically suppress duplicate scans. Ensure Duplicate Protection is enabled in Settings.
- **Scans Not Typing in Target Program**: Run BinaryReceptor with standard user privileges matching your target application (or run as Administrator if typing into elevated windows).

---

## 🏗️ Building Standalone Windows Executable

To compile the standalone, portable `BinaryReceptor.exe` with aggressive binary size optimization:

```powershell
# Install build dependencies
pip install -r requirements-build.txt

# Run automated build script
python build.py
```

The build script compiles an optimized single-file executable `dist/BinaryReceptor.exe` (with dead Qt module stripping and bytecode optimization), copies `settings.ini`, and executes an automated post-build smoke test (`BinaryReceptor.exe --self-test`).

---

## 🧪 Testing

Run the comprehensive test suite verifying all architectural specifications:

```powershell
pytest -v tests/
```

---

## 📜 License & Credits

This project is licensed under the [MIT License](LICENSE).  
Architecture, modernization, and version 3.4.0 engineering by **ouncommono**.  
Original upstream repository: [KamaleiZestri/BinaryReceptor](https://github.com/KamaleiZestri/BinaryReceptor).  
Android Scanner Client: [BinaryEye](https://github.com/markusfisch/BinaryEye) by Markus Fisch.

---

# 🇮🇷 راهنمای جامع فارسی (Persian Documentation)

## معرفی و معماری نرم‌افزار
**باینری‌رسپتور نسخه ۳.۴.۰ (BinaryReceptor v3.4.0)** نرم‌افزار حرفه‌ای سرور همراه و واسط شبیه‌ساز صفحه‌کلید (Keyboard Wedge) برای اپلیکیشن متن‌باز [BinaryEye](https://github.com/markusfisch/BinaryEye) در سیستم‌عامل اندروید است. این برنامه گوشی هوشمند شما را به یک بارکدخوان بی‌سیم صنعتی، فوق‌سریع و بدون خطای تایپ برای کامپیوترهای ویندوز تبدیل می‌کند.

با اسکن هرگونه بارکد میله‌ای (EAN-13، Code 128، UPC-A، Code 39) یا کدهای دوبعدی (QR Code، DataMatrix، Aztec، PDF417) توسط دوربین گوشی، داده‌های اسکن‌شده به صورت آنی از طریق **بلوتوث (RFCOMM)**، **شبکه محلی (HTTP)** و یا **حالت ترکیبی همزمان (Hybrid)** به کامپیوتر منتقل شده و مستقیماً در نرم‌افزار فعال ویندوز (اکسل، نرم‌افزارهای مالی و حسابداری، انبارداری، مرورگر، نوت‌پد) با کدهای استاندارد یونیکد Win32 `SendInput` (بدون تأثیرپذیری از کیبورد فارسی یا انگلیسی ویندوز) تایپ یا پیست (`Ctrl+V`) می‌شود.

```
 +-------------------------+              +-----------------------------------+
 |  Android Device         |              |  Windows PC                       |
 |  (markusfisch/BinaryEye)|              |  (BinaryReceptor Desktop Server)  |
 |                         |  Bluetooth   |                                   |
 |  Camera / Scan Engine   | -----------> |  Winsock RFCOMM Server (AF_BTH)   |
 |                         |    RFCOMM    |                 |                 |
 |                         |              |                 v                 |
 |  HTTP Forwarding Engine | -----------> |  Sub-ms HTTP Listener (:24234)    |
 |  (POST / GET / JSON)    |  Wi-Fi / LAN |  (پاسخ آنی 200 OK همراه scanId)   |
 +-------------------------+              +-----------------+-----------------+
                                                            |
                                             Global Low-Level Keyboard Hook
                                             (شنود و کنترل مستقیم ورودی‌های HID)
                                                            |
                                                            v
                                             Time-Interval Cooldown Deduplicator
                                             (فیلتر ضدتکرار هوشمند با تطبیق scanId)
                                                            |
                                                            v
                                             Prefix / Suffix Token Compiler
                                             ({ENTER}, {TAB}, {DATE}, {TIME})
                                                            |
                                                            v
                                             Win32 SendInput Unicode Engine
                                             (wVk=0, wScan=کد یونیکد UTF-16)
                                             (پنجره فعال: اکسل، نرم‌افزار حسابداری)
```

---

## ⚡ جدول جامع قابلیت‌ها و ویژگی‌های کلیدی

| قابلیت | شرح فنی و عملکردی |
| :--- | :--- |
| **سرور بلوتوث RFCOMM** | شنود مستقیم سوکت‌های RFCOMM ویندوز (`AF_BTH`) با ثبت شناسه سرویس SDP اختصاصی BinaryEye (`8a8478c9-2ca8-404b-a0de-101f34ab71ae`) بدون نیاز به درایور پورت سریال مجازی. |
| **سرور فوق‌سریع HTTP** | سرور چندنخی سریع با پشتیبانی کامل از هر ۴ حالت ارسال BinaryEye (ارسال JSON، ارسال فرم، متد GET با پرسمان، و افزودن مستقیم مقدار) با پاسخگویی آنی زیر میلی‌ثانیه با هدر استاندارد `application/json; charset=utf-8`. |
| **جداسازی کامل حالت‌های کاری** | در حالت فقط شبکه، پورت بلوتوث بسته شده و در صورت تشخیص ورودی همزمان HID، مسیرهای تکراری به صورت خودکار نادیده گرفته می‌شوند تا از رفتار ناخواسته ترکیبی جلوگیری شود. |
| **هوک سراسری سطح پایین کیبورد** | هوک سیستمی `WH_KEYBOARD_LL` ویندوز جهت شناسایی شلیک‌های پرسرعت بارکدخوان فیزیکی یا بلوتوث (< ۵۰ میلی‌ثانیه) و جلوگیری کامل از تایپ دوگانه (The Double-Typing Bug). |
| **هدایت مستقیم به کلیپ‌بورد در حالت HID** | در حالت «فقط کپی در کلیپ‌بورد»، ورودی خام ارسالی از بلوتوث HID رهگیری شده، از تایپ آن در پنجره فعال جلوگیری می‌شود و متن مستقیماً در حافظه کلیپ‌بورد کپی می‌گردد. |
| **استقلال کامل از زبان کیبورد ویندوز** | بازنویسی کامل موتور تزریق کلیدها با استفاده انحصاری از `KEYEVENTF_UNICODE` با `wVk=0` و کد پوینت UTF-16 در `wScan`؛ تضمین عدم به‌هم‌ریختگی حروف انگلیسی هنگام فعال بودن کیبورد فارسی ویندوز. |
| **سازنده بصری پیشوند و پسوند** | رابط کاربری اسکرول‌پذیر و واکنش‌گرا با دکمه‌های چیپ تعاملی برای درج کلیدهای اینتر (`{ENTER}`)، تب (`{TAB}`)، فاصله (`{SPACE}`)، بک‌اسپیس، خروج، تاریخ و ساعت جاری. |
| **صدای زنگ اسکنر (Audio Chime)** | تولید درون‌برنامه‌ای صدای دوگانه استاندارد اسکنر صنعتی (۱۸۰۰ تا ۲۴۰۰ هرتز) در حافظه رم با فرمت ۱۶ بیتی PCM WAV بدون نیاز به فایل صوتی خارجی. |
| **دستیار هوشمند اتصال و QR Code** | تولید کد QR پویا با قابلیت انتخاب کارت شبکه، انتخاب نوع درخواست BinaryEye و دکمه کپی فوری نشانی در کلیپ‌بورد. |
| **تولیدکننده بارکد استاندارد** | تبدیل هرگونه متن دلخواه به ۱۱ فرمت بارکد استاندارد (کد QR، Code 128، DataMatrix، EAN-13، Aztec، PDF417) به صورت متن خام جهت اسکن آزمایشی. |
| **کارت‌های اختصاصی آمار اسکن** | نمایش زنده تعداد کل اسکن‌ها، اسکن‌های بلوتوث، اسکن‌های شبکه و تکراری‌های مسدودشده در بالای صفحه گزارش زنده اسکن‌ها. |
| **رابط کاربری دوزبانه استاندارد** | پشتیبانی ۱۰۰٪ کامل از زبان فارسی (RTL راست‌به‌چپ) و انگلیسی (LTR چپ‌به‌راست) با همترازی دقیق واژگان، سربرگ‌ها و منوها بدون تداخل چیدمان. |
| **بارگذاری زنده `settings.ini`** | فایل تنظیمات استاندارد در کنار فایل اجرایی با قابلیت خواندن و اعمال خودکار تغییرات ظرف کمتر از ۱ ثانیه پس از ویرایش دستی. |

---

## 🚀 راهنمای شروع سریع

### روش ۱: فایل اجرایی پرتابل بدون نیاز به نصب (پیشنهادی)
۱. بسته فشرده `BinaryReceptor-v3.4.0-win64.zip` را از بخش [انتشارهای گیت‌هاب (Releases)](https://github.com/ouncommono/BinaryReceptor/releases/latest) دانلود کنید.  
۲. محتویات فایل زیپ را در یک پوشه دلخواه استخراج کنید.  
۳. فایل `BinaryReceptor.exe` را اجرا کنید.  
۴. روی دکمه **شروع به کار سرور** کلیک نمایید.

### روش ۲: اجرا از سورس‌کد
```powershell
# کلون مخزن گیت
git clone https://github.com/ouncommono/BinaryReceptor.git
cd BinaryReceptor

# نصب پیش‌نیازها
pip install -r requirements.txt

# اجرای برنامه
python run.py
```

---

## 📱 راهنمای گام‌به‌گام اتصال و تنظیم گوشی (BinaryEye)

### روش ۱: اتصال از طریق بلوتوث RFCOMM (بدون نیاز به شبکه و مودم)
۱. در بخش تنظیمات بلوتوث ویندوز، گوشی اندروید خود را جفت (Pair) کنید.  
۲. در برنامه **BinaryEye** گوشی به مسیر **تنظیمات (Settings) ← بلوتوث (Bluetooth)** بروید.  
۳. گزینه **ارسال اسکن از طریق بلوتوث** را روشن کرده و نام کامپیوتر خود را انتخاب کنید.  
۴. در برنامه BinaryReceptor، حالت کاری را روی **ترکیبی همزمان** یا **فقط بلوتوث** قرار دهید.  
۵. هر بارکدی را اسکن کنید؛ بلافاصله در پنجره فعال کامپیوتر تایپ خواهد شد.

---

### روش ۲: اتصال از طریق شبکه محلی و وای‌فای (HTTP Forwarding)
در برنامه BinaryEye به مسیر **تنظیمات ← ارسال (Forwarding)** رفته و گزینه **ارسال اسکن‌ها** را فعال کنید. چهار حالت استاندارد زیر پشتیبانی می‌شوند:

#### حالت اول: POST application/json (پیشنهادی)
- **نوع درخواست در گوشی**: `POST application/json`
- **نشانی سرور در گوشی**: `http://<IP_کامپیوتر>:24234/`
- برنامه باینری‌رسپتور ساختار JSON را با کلیدهای `content`، `format`، `raw`، `scanId` بلافاصله پردازش کرده و پاسخ 200 OK را در کسری از میلی‌ثانیه بازمی‌گرداند.

#### حالت دوم: POST application/x-www-form-urlencoded
- **نوع درخواست در گوشی**: `POST application/x-www-form-urlencoded`
- **نشانی سرور در گوشی**: `http://<IP_کامپیوتر>:24234/`
- داده‌ها در قالب فرم اینترنتی استاندارد به سرور ارسال می‌شوند.

#### حالت سوم: GET with full query string
- **نوع درخواست در گوشی**: `GET with full query string`
- **نشانی سرور در گوشی**: `http://<IP_کامپیوتر>:24234/`
- برنامه BinaryEye به صورت خودکار پارامترهای `?content=...&raw=...&format=...&scanId=...` را به انتهای نشانی می‌افزاید.

#### حالت چهارم: GET and simply add content
- **نوع درخواست در گوشی**: `GET and simply add content`
- **نشانی سرور در گوشی**: `http://<IP_کامپیوتر>:24234/?content=` (یا `http://<IP_کامپیوتر>:24234/`)
- بارکد اسکن‌شده مستقیماً به انتهای آدرس اضافه می‌شود.
- الگوی سفارشی اختیاری: `http://<IP_کامپیوتر>:24234/?content={RESULT}&format={FORMAT}&raw={RESULT_BYTES}`

---

## ⌨️ جدول جامع توکن‌های پیشوند و پسوند (Prefix & Suffix)

| توکن | کلید معادل در ویندوز | کاربرد متداول |
| :--- | :--- | :--- |
| `{ENTER}` | کلید Enter (`VK_RETURN`) | ثبت فرم، رفتن به سطر بعدی یا ارسال داده |
| `{TAB}` | کلید Tab (`VK_TAB`) | انتقال مکان‌نما به فیلد یا ستون بعدی در اکسل یا نرم‌افزار حسابداری |
| `{SPACE}` | کلید فاصله Space | درج فاصله میان کدهای متوالی |
| `{BACKSPACE}`| کلید Backspace (`VK_BACK`) | حذف کاراکترهای اضافی یا ارقام کنترلی ناخواسته |
| `{ESC}` | کلید خروج Escape | بستن پنجره‌های بازشو پیش یا پس از اسکن |
| `{DOWN}` | کلید فلش رو به پایین | حرکت به ردیف پایینی در جدول انبارداری |
| `{DATE}` | تاریخ روز جاری | درج خودکار تاریخ سیستم (`YYYY-MM-DD`) |
| `{TIME}` | ساعت جاری | درج خودکار زمان دقیق ثبت (`HH:MM:SS`) |
| `{TIMESTAMP}`| برچسب زمانی کامل | ثبت دقیق تاریخ و ساعت استاندارد بین‌المللی |

---

## ⚙️ مرجع کامل تنظیمات نرم‌افزار (`settings.ini`)

فایل تنظیمات `settings.ini` همواره در کنار فایل اجرایی برنامه قرار داشته و در صورت ویرایش دستی با نوت‌پد، ظرف کمتر از ۱ ثانیه به صورت خودکار در برنامه بارگذاری مجدد می‌شود:

| بخش | کلید | پیش‌فرض | شرح عملکرد |
| :--- | :--- | :--- | :--- |
| `[general]` | `mode` | `both` | حالت کاری: `both` (ترکیبی)، `http` (فقط شبکه)، یا `bluetooth` (فقط بلوتوث). |
| `[general]` | `language` | `en` | زبان محیط کاربری: `en` (انگلیسی - LTR) یا `fa` (فارسی - RTL). |
| `[general]` | `theme` | `dark` | پوسته نرم‌افزار: `dark` (تیره)، `light` (روشن)، یا `system` (همگام با ویندوز). |
| `[general]` | `auto_start` | `false` | روشن شدن خودکار سرور در بدو اجرای برنامه (پیش‌فرض: خاموش). |
| `[general]` | `start_minimized` | `false` | اجرای برنامه به صورت کمینه در کنار ساعت سیستم (System Tray). |
| `[general]` | `minimize_to_tray` | `true` | کمینه‌سازی در کنار ساعت هنگام کلیک روی دکمه ضربدر بستن پنجره. |
| `[general]` | `audio_feedback` | `true` | پخش صدای شفاف بیپ پس از دریافت موفق اسکن بارکد. |
| `[general]` | `tray_notifications` | `true` | نمایش اعلان‌های بالونی یا نوتیفیکیشن ویندوز پس از اسکن. |
| `[network]` | `http_host` | `0.0.0.0` | آی‌پی شنود سرور تحت شبکه (`0.0.0.0` برای شنود روی تمامی کارت‌های شبکه). |
| `[network]` | `http_port` | `24234` | پورت شنود سرور برای دریافت درخواست‌های فوروارد BinaryEye. |
| `[bluetooth]` | `bt_enabled` | `true` | فعال‌سازی شنود سوکت‌های بلوتوث RFCOMM ویندوز. |
| `[bluetooth]` | `service_uuid` | `8a8478c9-...` | شناسه سرویس بلوتوث SDP استاندارد نرم‌افزار BinaryEye. |
| `[wedge]` | `output_mode` | `type` | حالت شبیه‌سازی: `type` (تایپ کلیدها)، `paste` (پیست)، `copy_only`، `log_only`. |
| `[wedge]` | `inter_key_delay_ms` | `0` | وقفه زمانی میان تایپ کلیدها به میلی‌ثانیه جهت سازگاری با سیستم‌های مالی. |
| `[wedge]` | `prefix` | `""` | کلیدها یا توکن‌هایی که قبل از بارکد به طور خودکار تایپ می‌شوند. |
| `[wedge]` | `suffix` | `{ENTER}` | کلیدها یا توکن‌هایی که پس از بارکد به طور خودکار تایپ می‌شوند. |
| `[deduplication]` | `deduplication_enabled` | `true` | فعال‌سازی جلوگیری از ورود اسکن‌های تکراری در بازه زمانی تعیین‌شده. |
| `[deduplication]` | `deduplication_window_ms`| `1500` | بازه زمانی جلوگیری از اسکن تکراری به میلی‌ثانیه (Cooldown). |

---

## 🔧 عیب‌یابی و پرسش‌های متداول (Troubleshooting)

- **خطای پورت در شبکه (Error binding :24234)**: چنانچه برنامه دیگری از پورت 24234 استفاده می‌کند، در تب تنظیمات پورت را تغییر دهید (مثلاً 25000) و دکمه ذخیره تنظیمات را بزنید.
- **خاموش بودن آداپتور بلوتوث (Adapter Off)**: مطمئن شوید بلوتوث در تنظیمات ویندوز روشن است و دانگل یا سخت‌افزار بلوتوث سیستم فعال است.
- **تایپ دوگانه در حالت ترکیبی**: هوک سراسری سطح پایین و فیلتر Cooldown Gate به صورت خودکار مانع تایپ مجدد می‌شوند. مطمئن شوید گزینه فیلتر ضدتکرار در تنظیمات روشن است.
- **تایپ نشدن در پنجره هدف**: برنامه باینری‌رسپتور را با دسترسی مشابه با نرم‌افزار مقصد اجرا کنید (در صورت تایپ در برنامه‌های با دسترسی ادمین، باینری‌رسپتور را نیز با Run as Administrator اجرا فرمایید).

---

## 🏗️ راهنمای ساخت فایل اجرایی بهینه‌سازی‌شده ویندوز (Build .exe)

جهت کامپایل و تولید فایل پرتابل تک‌باینری `BinaryReceptor.exe` با حداقل حجم اجرایی:

```powershell
# نصب پیش‌نیازهای کامپایل
pip install -r requirements-build.txt

# اجرای اسکریپت خودکار ساخت
python build.py
```

این اسکریپت یک فایل مستقل تک‌باینری بهینه‌سازی‌شده `dist/BinaryReceptor.exe` تولید کرده، ماژول‌های بلااستفاده کیوت را حذف و بایت‌کدها را فشرده می‌سازد، فایل `settings.ini` را در کنار آن قرار می‌دهد و تست خودکار اولیه (`BinaryReceptor.exe --self-test`) را اعتبارسنجی می‌کند.

---

## 🧪 آزمون‌های خودکار و تضمین کیفیت (Testing)

اجرای مجموعه تست‌های جامع واحد و یکپارچگی پروژه:

```powershell
pytest -v tests/
```

---

## 📜 پروانه نرم‌افزار و حقوق نشر (License & Credits)

این پروژه تحت مجوز آزاد بین‌المللی [MIT License](LICENSE) منتشر شده است.  
طراحی معماری، بازنویسی مدرن و توسعه نسخه ۳.۴.۰ توسط **ouncommono**.  
پروژه پایه و مخزن اصلی: [KamaleiZestri/BinaryReceptor](https://github.com/KamaleiZestri/BinaryReceptor).  
اپلیکیشن کلاینت اندروید: [BinaryEye](https://github.com/markusfisch/BinaryEye) اثر Markus Fisch.
