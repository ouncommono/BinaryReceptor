# BinaryReceptor v3.6.0

> **The ultra-lightweight, zero-latency desktop companion server for [BinaryEye](https://github.com/markusfisch/BinaryEye) on Android.**  
> Native Windows architecture with Bluetooth RFCOMM, HTTP webhook listener, low-level Win32 `SendInput` Unicode keyboard wedge, global HID intervention hook, and dynamic token compiler.

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?logo=windows&logoColor=white)](https://microsoft.com/windows)
[![Release](https://img.shields.io/badge/Release-v3.6.0-10B981)](https://github.com/ouncommono/BinaryReceptor/releases)
[![Build Status](https://github.com/ouncommono/BinaryReceptor/actions/workflows/build_release.yml/badge.svg)](https://github.com/ouncommono/BinaryReceptor/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🌐 Languages / زبان‌ها
- [English Documentation](#-english-documentation)
- [راهنمای جامع فارسی (Persian Documentation)](#-راهنمای-جامع-فارسی-persian-documentation)

---

# 🇺🇸 English Documentation

## Overview & System Architecture
**BinaryReceptor** is the official production-grade Windows companion server for the open-source Android barcode scanner [BinaryEye](https://github.com/markusfisch/BinaryEye). It instantly turns any Android smartphone running BinaryEye into an industrial-grade, zero-latency wireless barcode scanner for Windows workstations.

Whenever a 1D linear barcode (EAN-13, Code 128, UPC-A, Code 39) or 2D matrix code (QR Code, DataMatrix, Aztec, PDF417) is scanned, BinaryReceptor captures the payload instantaneously over **Bluetooth RFCOMM**, **Wi-Fi / LAN HTTP**, or **both simultaneously in Hybrid mode**. The scanned data is wedged directly into the active Windows application (Excel, ERP systems, accounting software, Point of Sale, web browsers, Notepad) using low-level Win32 `SendInput` Unicode code points (bypassing the host keyboard layout) or instant clipboard paste (`Ctrl+V`).

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

## ⚡ Core Features & Capabilities

| Feature | Technical Implementation | Benefit to User |
| :--- | :--- | :--- |
| **Native Bluetooth RFCOMM & SDP** | Windows Sockets `AF_BTH` RFCOMM listener with Win32 SDP UUID registration (`8a8478c9-2ca8-404b-a0de-101f34ab71ae`). | Zero network setup and zero virtual COM ports or third-party drivers needed. Connects directly to BinaryEye via Bluetooth. |
| **Sub-Millisecond HTTP Listener** | Asynchronous HTTP server returning immediate `200 OK` JSON responses with `Content-Type: application/json; charset=utf-8`. | Completely eliminates Android client timeout beeps during rapid continuous scanning over Wi-Fi. |
| **Layout-Independent Unicode Typing** | Keystroke synthesis exclusively via `ctypes.windll.user32.SendInput` using `KEYEVENTF_UNICODE` (`wVk=0`, `wScan=UTF-16 code point`). | Eliminates character garbling when non-English layouts (e.g. Persian/Farsi, Arabic, Russian) are active on Windows. |
| **Global HID Intervention & Deduplication** | Low-level `WH_KEYBOARD_LL` Windows hook monitoring high-speed barcode scanner bursts (< 45ms). | Suppresses raw OS keystrokes to prevent double-typing when BinaryEye forwards over both Bluetooth and HTTP. |
| **Universal Output Modes** | Flexible dispatch engine supporting `type` (simulated typing), `paste` (Ctrl+V), `copy_only` (clipboard only), and `log_only`. | Adapts seamlessly to spreadsheets, ERP input forms, web applications, or background auditing. |
| **Dynamic Prefix & Suffix Token Engine** | Token compiler replacing `{ENTER}`, `{TAB}`, `{DATE}`, `{TIME}`, `{SPACE}`, `{BACKSPACE}`, and `{DOWN}`. | Automatically tabs to the next field, submits rows, or timestamps inventory logs upon scan. |
| **Dynamic Pairing Assistant (QR Code)** | In-memory pure Python QR matrix generator outputting live LAN IP connection strings and configuration deep links. | Scan the on-screen QR code with BinaryEye to configure forwarding in a single second. |
| **Audio Confirmation Synthesis** | Native Win32 dual-tone PCM audio synthesizer (`1800Hz` rising to `2400Hz`) with zero external sound files. | Provides physical scanner auditory feedback upon successful reception. |
| **100% Bilingual RTL / LTR UI** | Full dual-language localization in English (Left-to-Right) and Persian (راست‌به‌چپ - RTL) with dynamic theme switching. | Native language ergonomics and accessibility for international and bilingual deployments. |
| **Deterministic Hot-Reload Settings** | Live INI watcher reloading `settings.ini` alongside `BinaryReceptor.exe` within 1 second. | Enables centralized mass configuration via IT deployment scripts without restarting the service. |

---

## 📱 Step-by-Step Pairing Guide with BinaryEye

### Method A: Bluetooth RFCOMM (Zero-Network Wireless)
Ideal for locations without local Wi-Fi, air-gapped workstations, or mobile field operations.

1. **Pair Phone and PC**:
   - Open Windows **Settings → Bluetooth & devices** and ensure Bluetooth is turned On.
   - On Android, open **Settings → Bluetooth** and pair your smartphone with your Windows PC.
2. **Configure BinaryEye**:
   - Open **BinaryEye** on your Android device.
   - Tap **Settings** (gear icon) and scroll to **Forwarding**.
   - Enable **Forward scans with Bluetooth**.
   - Select your paired Windows PC name from the device list.
3. **Start BinaryReceptor**:
   - Launch `BinaryReceptor.exe` on your PC.
   - Set **Operation Mode** to `Hybrid Simultaneous` or `Bluetooth RFCOMM Only`.
   - Click **Start Server**. The Bluetooth status pill will display `Listening` (or `Connected`).
4. **Scan**:
   - Point BinaryEye at any barcode. Scanned data is received and injected directly into your active window.

---

### Method B: Wi-Fi / Local Area Network (HTTP Forwarding)
Ideal for office networks, warehouse Wi-Fi, or high-volume multi-device environments.

1. **Network Connectivity**:
   - Ensure your Android smartphone and Windows workstation are connected to the same Wi-Fi network or subnet.
2. **Launch & Retrieve URL**:
   - In BinaryReceptor, set **Operation Mode** to `Hybrid Simultaneous` or `HTTP Server Only`.
   - Click **Start Server**. The active connection URL is displayed (e.g., `http://192.168.1.100:24234/`).
3. **Configure BinaryEye via QR Code**:
   - Navigate to the **Connection / QR Code** tab in BinaryReceptor.
   - In BinaryEye, simply scan the displayed **Connection Helper QR Code**.
   - Or configure manually in **BinaryEye → Settings → Forwarding**:
     - **Forward scans**: Enabled
     - **Request type**: `POST application/json` (Recommended)
     - **URL**: `http://<YOUR_PC_IP>:24234/`
4. **Supported BinaryEye HTTP Request Types**:
   - **`POST application/json`** *(Best)*: Sends JSON payload containing `content`, `format`, `raw`, and `scanId`.
   - **`POST application/x-www-form-urlencoded`**: Sends form urlencoded parameters.
   - **`GET with full query string`**: Appends `?content=...&format=...&raw=...&scanId=...`.
   - **`GET and simply add content`**: Appends scanned data directly to URL (`/?content=...` or `/?result={RESULT}`).

---

## ⌨️ Keystroke Injection & Output Modes

BinaryReceptor provides four distinct output modes configured via the UI or `settings.ini`:

1. **Simulated Typing (`type`)**:
   - Injects characters individually using Win32 `SendInput` with `KEYEVENTF_UNICODE`.
   - Bypasses active Windows keyboard layouts (such as Persian, Arabic, or German), guaranteeing that English barcode characters are never converted to non-Latin glyphs.
2. **Instant Clipboard Paste (`paste`)**:
   - Copies barcode text to the Windows clipboard and synthesizes `Ctrl+V`.
   - Recommended for long 2D matrix codes (URLs, DataMatrix, PDF417) to achieve instant insertion.
3. **Copy to Clipboard Only (`copy_only`)**:
   - Copies text to the Windows clipboard without typing or pressing any keys.
   - Intercepts and suppresses raw Bluetooth HID scanner bursts so zero unwanted keystrokes hit the screen.
4. **Log / History Only (`log_only`)**:
   - Records the barcode inside BinaryReceptor's live activity dashboard without altering the clipboard or active window.

---

## 📝 Prefix & Suffix Token Reference

Format incoming scans by adding navigation tokens and dynamic timestamps to the **Prefix** and **Suffix** fields:

| Token | Win32 Virtual Key / Value | Typical Application |
| :--- | :--- | :--- |
| `{ENTER}` | `VK_RETURN` (Enter key) | Automatically submits an input form or advances to the next spreadsheet row |
| `{TAB}` | `VK_TAB` (Tab key) | Advances focus to the next column or input field in ERP / CRM forms |
| `{SPACE}` | `VK_SPACE` (Space key) | Inserts spacing between barcode segments |
| `{BACKSPACE}` | `VK_BACK` (Backspace key) | Trims unwanted prefix or checksum characters |
| `{ESC}` | `VK_ESCAPE` (Escape key) | Clears modal dialogs or search boxes before/after entry |
| `{DOWN}` | `VK_DOWN` (Down arrow key) | Moves cursor downward in grid-based inventory tables |
| `{DATE}` | Current Date (`YYYY-MM-DD`) | Appends ISO 8601 datestamp to inventory records |
| `{TIME}` | Current Time (`HH:MM:SS`) | Appends live timestamp to log entries |

---

## ⚙️ Configuration Reference (`settings.ini`)

`settings.ini` is located in the same directory as `BinaryReceptor.exe` and is automatically hot-reloaded upon modification:

| Section | Parameter | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `[Server]` | `mode` | `both` | Operational mode: `both` (Hybrid), `http`, or `bluetooth`. |
| `[Server]` | `http_host` | `0.0.0.0` | Bind IP address for the local HTTP companion server. |
| `[Server]` | `http_port` | `24234` | Port number for incoming BinaryEye HTTP webhooks. |
| `[Server]` | `service_uuid`| `8a8478c9-2ca8-404b-a0de-101f34ab71ae` | Bluetooth RFCOMM SDP service UUID for BinaryEye. |
| `[Server]` | `service_name`| `BinaryReceptor` | Windows Bluetooth SDP service advertisement name. |
| `[Server]` | `auto_start` | `false` | Automatically starts listeners when BinaryReceptor launches. |
| `[Typing]` | `output_mode`| `type` | Output action: `type`, `paste`, `copy_only`, or `log_only`. |
| `[Typing]` | `prefix` | *(empty)* | Keystroke tokens or text injected before the barcode. |
| `[Typing]` | `suffix` | `{ENTER}` | Keystroke tokens or text injected after the barcode. |
| `[Typing]` | `inter_key_delay_ms` | `2` | Delay in milliseconds between consecutive keystrokes. |
| `[Typing]` | `pre_typing_delay_ms` | `10` | Wait time in milliseconds before initiating typing. |
| `[Filter]` | `deduplication_enabled` | `true` | Suppresses rapid duplicate scans across protocols. |
| `[Filter]` | `deduplication_window_ms` | `1500` | Cooldown window in milliseconds for identical scans. |
| `[General]`| `language` | `en` | GUI language: `en` (English LTR) or `fa` (Persian RTL). |
| `[General]`| `theme` | `dark` | Visual theme: `dark`, `light`, or `system`. |
| `[General]`| `start_minimized` | `false` | Starts directly in the Windows System Tray on launch. |
| `[General]`| `sound_enabled` | `true` | Plays dual-tone confirmation beep on successful scan. |

---

## 🚀 Quick Start & Installation

### Option 1: Standalone Portable Executable (Recommended)
1. Download `BinaryReceptor-v3.6.0-win64.zip` from [GitHub Releases](https://github.com/ouncommono/BinaryReceptor/releases/latest).
2. Extract the archive into any preferred folder.
3. Run `BinaryReceptor.exe`.
4. Click **Start Server** and scan barcodes.

### Option 2: Running from Source
```powershell
# Clone the repository
git clone https://github.com/ouncommono/BinaryReceptor.git
cd BinaryReceptor

# Install required dependencies
pip install -r requirements.txt

# Launch application
python run.py
```

---

## 🔧 Troubleshooting & FAQ

- **Android Client Error Beeps during HTTP forwarding?**  
  BinaryReceptor v3.6.0 responds in sub-millisecond time with a `200 OK` JSON header before asynchronous keystroke processing, eliminating Android client timeout beeps. Ensure your phone and PC can reach each other over your local Wi-Fi.
- **Bluetooth Server shows "Adapter Off"?**  
  Ensure Windows Bluetooth is toggled On in Windows Settings. Verify that your PC has an active Bluetooth radio adapter.
- **Persian/Farsi Keyboard Layout Typing Garbled Text?**  
  BinaryReceptor bypasses virtual-key layout translation by sending UTF-16 code points via `KEYEVENTF_UNICODE`. Text arrives cleanly regardless of the active language on Windows.
- **Windows Defender SmartScreen warning on first launch?**  
  Click *More info* and select *Run anyway*. The binary is built transparently via GitHub Actions CI/CD directly from this open-source repository.

---

## 📜 License & Credits

This project is licensed under the [MIT License](LICENSE).  
Architecture, modernization, and version 3.6.0 engineering by **ouncommono**.  
Original upstream repository: [KamaleiZestri/BinaryReceptor](https://github.com/KamaleiZestri/BinaryReceptor).  
Android Scanner Client: [BinaryEye](https://github.com/markusfisch/BinaryEye) by Markus Fisch.

---

# 🇮🇷 راهنمای جامع فارسی (Persian Documentation)

## معرفی و معماری سیستم
**باینری‌رسپتور (BinaryReceptor)** نرم‌افزار حرفه‌ای، فوق‌سریع و بدون خطای سرور همراه برای اپلیکیشن بارکدخوان متن‌باز [BinaryEye](https://github.com/markusfisch/BinaryEye) در سیستم‌عامل اندروید است. این برنامه گوشی هوشمند شما را به یک بارکدخوان بی‌سیم صنعتی با تأخیر نزدیک به صفر برای رایانه‌های ویندوزی تبدیل می‌کند.

با اسکن هرگونه بارکد خطی تک‌بعدی (EAN-13، Code 128، UPC-A، Code 39) یا کدهای دوبعدی ماتریکسی (QR Code، DataMatrix، Aztec، PDF417)، باینری‌رسپتور داده‌ها را بلافاصله از طریق **بلوتوث (RFCOMM)**، **شبکه وای‌فای / شبکه محلی (HTTP)** یا **هر دو به صورت همزمان در حالت ترکیبی (Hybrid)** دریافت می‌کند. داده‌های اسکن‌شده مستقیماً در نرم‌افزار فعال ویندوز (اکسل، نرم‌افزارهای حسابداری و مالی، سیستم‌های انبارداری ERP، اتوماسیون، مرورگرهای وب یا نوت‌پد) با استفاده از کدهای یونیکد Win32 `SendInput` (بدون تأثیرپذیری از زبان فعال کیبورد ویندوز) یا الصاق فوری کلیپ‌بورد (`Ctrl+V`) تایپ می‌شوند.

```
 +-------------------------+              +-----------------------------------+
 |  دستگاه اندروید          |              |  رایانه ویندوز                    |
 |  (markusfisch/BinaryEye)|              |  (سرور دسکتاپ BinaryReceptor)      |
 |                         |    بلوتوث    |                                   |
 |  دوربین / موتور اسکن     | -----------> |  سرور بلوتوث وینساک (AF_BTH)      |
 |                         |    RFCOMM    |                 |                 |
 |                         |              |                 v                 |
 |  موتور ارسال تحت وب     | -----------> |  دریافت‌کننده HTTP فوق‌سریع (:24234)|
 |  (POST / GET / JSON)    |  وای‌فای/شبکه |  (پاسخ آنی 200 OK + کد رهگیری)   |
 +-------------------------+              +-----------------+-----------------+
                                                            |
                                             قلاب سطح پایین صفحه‌کلید ویندوز
                                             (WH_KEYBOARD_LL و مهار فوران HID)
                                                            |
                                                            v
                                             فیلتر هوشمند حذف اسکن‌های تکراری
                                             (همگام‌سازی پروتکل‌ها و تطبیق scanId)
                                                            |
                                                            v
                                             موتور کامپایلر پیشوند و پسوند
                                             ({ENTER}، {TAB}، {DATE}، {TIME})
                                                            |
                                                            v
                                             موتور تزریق یونیکد Win32 SendInput
                                             (wVk=0، کاراکترهای مستقیم UTF-16)
                                             (پنجره فعال: اکسل، نرم‌افزار حسابداری)
```

---

## ⚡ قابلیت‌ها و ویژگی‌های کلیدی

| قابلیت | پیاده‌سازی فنی | مزیت برای کاربر |
| :--- | :--- | :--- |
| **سرور بومی بلوتوث RFCOMM و SDP** | شنونده سوکت وینساک `AF_BTH` با ثبت سرویس SDP در ویندوز (`8a8478c9-2ca8-404b-a0de-101f34ab71ae`). | عدم نیاز به اتصال اینترنت، درایورهای جانبی یا پورت‌های مجازی COM. اتصال مستقیم گوشی به رایانه با بلوتوث. |
| **دریافت‌کننده فوق‌سریع HTTP** | سرور ناهمگام HTTP با ارسال پاسخ آنی `200 OK` در کسری از میلی‌ثانیه با هدر استاندارد JSON. | حذف کامل بوق خطای گوشی در اسکن‌های سریع و پشت سر هم از طریق وای‌فای. |
| **تایپ یونیکد مستقل از زبان کیبورد** | سنتز کلیدها منحصراً از طریق `SendInput` با فلگ `KEYEVENTF_UNICODE` (`wVk=0`, `wScan=کد یونیکد UTF-16`). | رفع کامل مشکل تایپ کاراکترهای نامفهوم و به‌هم‌ریخته هنگامی که زبان کیبورد ویندوز روی فارسی یا زبان‌های غیرانگلیسی است. |
| **مداخله در ورودی HID و حذف تکرار** | قلاب سراسری و سطح پایین `WH_KEYBOARD_LL` برای پایش فوران ورودی‌های بارکدخوان فیزیکی (< ۴۵ میلی‌ثانیه). | مهار کلیدهای خام سیستم‌عامل برای جلوگیری از دوبار تایپ شدن بارکد هنگام ارسال همزمان از بلوتوث و شبکه. |
| **حالت‌های خروجی چندگانه** | موتور توزیع منعطف با پشتیبانی از شبیه‌سازی تایپ (`type`)، الصاق کلیپ‌بورد (`paste`)، فقط کپی (`copy_only`) و ثبت تاریخچه (`log_only`). | سازگاری کامل با نرم‌افزارهای اداری، فرم‌های وب، نرم‌افزارهای انبارداری یا ذخیره تاریخچه اسکن‌ها. |
| **موتور توکن‌های پیشوند و پسوند** | کامپایلر خودکار برای جایگزینی توکن‌های کلیدی مانند `{ENTER}`، `{TAB}`، `{DATE}`، `{TIME}` و `{SPACE}`. | پرش خودکار به فیلد بعدی، ثبت سطرها یا درج تاریخ و ساعت ثبت رکورد بلافاصله پس از اسکن. |
| **دستیار هوشمند اتصال سریع (QR Code)** | تولیدکننده کد QR درون‌حافظه‌ای پایتون با نمایش آدرس‌های فعال شبکه محلی و لینک‌های مستقیم تنظیمات. | اتصال و پیکربندی اپلیکیشن گوشی تنها در یک ثانیه با اسکن بارکد روی صفحه مانیتور. |
| **سنتز صوتی بوق اسکنر** | شبیه‌ساز صوتی دوگانه بومی ویندوز PCM (`1800Hz` به `2400Hz`) بدون نیاز به فایل‌های صوتی خارجی. | ارائه بازخورد صوتی شبیه به دستگاه‌های بارکدخوان فیزیکی پس از دریافت موفق اسکن. |
| **رابط کاربری ۱۰۰٪ دو زبانه (RTL / LTR)** | بومی‌سازی کامل زبان‌های انگلیسی و فارسی (راست‌به‌چپ واقعی) همراه با تعویض پویای پوسته روشن و تیره. | ارگونومی عالی، زیبایی بصری و خوانایی بالا در محیط‌های کاری و سازمانی فارسی‌زبان. |
| **بازخوانی آنی تنظیمات (`settings.ini`)** | پایشگر زنده فایل پیکربندی در کنار فایل اجرایی با بازخوانی خودکار تغییرات در کمتر از ۱ ثانیه. | امکان پیکربندی دسته‌جمعی و سریع توسط مدیران شبکه بدون نیاز به راه‌اندازی مجدد برنامه. |

---

## 📱 راهنمای گام‌به‌گام اتصال و جفت‌سازی با BinaryEye

### روش اول: بلوتوث RFCOMM (بدون نیاز به شبکه و اینترنت)
مناسب برای رایانه‌های فاقد شبکه، لپ‌تاپ‌های همراه یا محیط‌های ایزوله صنعتی.

۱. **جفت‌سازی بلوتوث گوشی و رایانه**:
   - در ویندوز وارد بخش **Settings → Bluetooth & devices** شوید و بلوتوث را روشن کنید.
   - در گوشی اندروید وارد تنظیمات بلوتوث شده و گوشی را با رایانه خود جفت (Pair) کنید.
۲. **تنظیم اپلیکیشن BinaryEye در گوشی**:
   - برنامه **BinaryEye** را باز کنید.
   - آیکون چرخ‌دنده (تنظیمات) را لمس کرده و به بخش **ارسال (Forwarding)** بروید.
   - گزینه **Forward scans with Bluetooth** را فعال کنید.
   - از لیست دستگاه‌ها، نام رایانه ویندوزی خود را انتخاب نمایید.
۳. **شروع به کار باینری‌رسپتور**:
   - برنامه `BinaryReceptor.exe` را در ویندوز اجرا کنید.
   - حالت کارکرد را روی **ترکیبی همزمان (Hybrid)** یا **فقط بلوتوث (Bluetooth Only)** بگذارید.
   - دکمه **شروع سرور** را بزنید. وضعیت بلوتوث به حالت `آماده دریافت (Listening)` تغییر می‌کند.
۴. **اسکن بارکد**:
   - با دوربین گوشی هر بارکدی را اسکن کنید؛ محتوای آن فوراً در نرم‌افزار فعال ویندوز تایپ می‌شود.

---

### روش دوم: شبکه وای‌فای / شبکه محلی (ارسال از طریق HTTP)
مناسب برای شبکه‌های اداری، فروشگاه‌ها، انبارها و استفاده از چند گوشی به صورت همزمان.

۱. **اتصال به شبکه یکسان**:
   - اطمینان حاصل کنید که گوشی اندروید و رایانه ویندوز هر دو به یک مودم یا شبکه وای‌فای متصل هستند.
۲. **دریافت آدرس اتصال**:
   - در باینری‌رسپتور، حالت کارکرد را روی **ترکیبی همزمان (Hybrid)** یا **فقط سرور وب (HTTP Only)** قرار دهید.
   - دکمه **شروع سرور** را بزنید. آدرس فعال شما نمایش داده می‌شود (مثال: `http://192.168.1.100:24234/`).
۳. **پیکربندی خودکار با کد QR**:
   - در باینری‌رسپتور وارد تب **اتصال / کد QR** شوید.
   - در برنامه BinaryEye، کد QR نمایش داده شده روی صفحه مانیتور را اسکن کنید تا تنظیمات به صورت خودکار اعمال شوند.
   - یا در تنظیمات **BinaryEye → Forwarding** مقادیر زیر را به صورت دستی وارد کنید:
     - **Forward scans**: فعال
     - **Request type**: گزینه `POST application/json` (پیشنهادی)
     - **URL**: آدرس آی‌پی کامپیوتر شما مانند `http://192.168.1.100:24234/`
۴. **فرمت‌های پشتیبانی‌شده در BinaryEye**:
   - **`POST application/json`** *(بهترین گزینه)*: ارسال آبجکت استاندارد حاوی محتوا، فرمت و شناسه اسکن.
   - **`POST application/x-www-form-urlencoded`**: ارسال پارامترهای فرم اینترنتی.
   - **`GET with full query string`**: ارسال پارامترها در آدرس به شکل `?content=...&format=...`.
   - **`GET and simply add content`**: اضافه کردن مستقیم متن بارکد به انتهای آدرس (`/?content=...`).

---

## 📝 حالت‌های خروجی و تزریق کلیدها

باینری‌رسپتور چهار روش مجزا برای درج داده‌های اسکن‌شده در اختیار شما قرار می‌دهد:

۱. **تایپ شبیه‌سازی‌شده (`type`)**:
   - تزریق تک‌تک کاراکترها با استفاده از کدهای مستقیم یونیکد Win32 `SendInput`.
   - این روش کاملاً مستقل از زبان کیبورد فعال ویندوز عمل می‌کند؛ حتی اگر زبان کیبورد روی فارسی باشد، حروف انگلیسی بارکد به صورت صحیح و دقیق تایپ می‌شوند.
۲. **الصاق فوری از کلیپ‌بورد (`paste`)**:
   - کپی متن بارکد در حافظه کلیپ‌بورد و شبیه‌سازی کلید میانبر `Ctrl+V`.
   - بسیار مناسب برای بارهای داده‌ای طولانی (مانند آدرس‌های اینترنتی طولانی یا کدهای DataMatrix و PDF417).
۳. **فقط کپی در حافظه کلیپ‌بورد (`copy_only`)**:
   - قرار دادن متن در کلیپ‌بورد ویندوز بدون فشردن هیچ کلیدی روی صفحه‌کلید.
   - در این حالت، داده‌های خام اسکنرهای سخت‌افزاری بلوتوث نیز به طور کامل مهار می‌شوند تا هیچ کلید ناخواسته‌ای روی صفحه فشرده نشود.
۴. **فقط ثبت در تاریخچه (`log_only`)**:
   - ذخیره و نمایش بارکد در جدول فعالیت‌های زنده برنامه، بدون دستکاری کلیپ‌بورد یا فوکوس پنجره‌های فعال.

---

## ⌨️ مرجع توکن‌های پیشوند و پسوند

شما می‌توانید با اضافه کردن توکن‌های استاندارد در فیلدهای **پیشوند (Prefix)** و **پسوند (Suffix)**، رفتار اسکنر را سفارشی‌سازی کنید:

| توکن | کلید معادل در ویندوز / مقدار | کاربرد متداول |
| :--- | :--- | :--- |
| `{ENTER}` | کلید اینتر (`VK_RETURN`) | ثبت نهایی فرم یا رفتن خودکار به سطر بعدی در اکسل |
| `{TAB}` | کلید تب (`VK_TAB`) | انتقال فوکوس به ستون بعدی یا فیلد اطلاعاتی بعدی در فرم‌های حسابداری |
| `{SPACE}` | کلید فاصله (`VK_SPACE`) | درج فاصله میان بخش‌های مختلف بارکد |
| `{BACKSPACE}` | کلید پاک‌کردن (`VK_BACK`) | حذف ارقام کنترلی یا کاراکترهای اضافی از ابتدا یا انتهای بارکد |
| `{ESC}` | کلید انصراف (`VK_ESCAPE`) | بستن کادرهای جستجو یا پیام‌های بازشو قبل یا بعد از اسکن |
| `{DOWN}` | کلید جهت‌نمای پایین (`VK_DOWN`) | جابه‌جایی مکان‌نما به سمت پایین در جدول‌های انبارداری |
| `{DATE}` | تاریخ جاری شمسی/میلادی (`YYYY-MM-DD`) | ثبت خودکار تاریخ اسکن در نرم‌افزارهای آماری و انبار |
| `{TIME}` | ساعت جاری (`HH:MM:SS`) | ثبت زمان دقیق رویداد اسکن |

---

## ⚙️ مرجع تنظیمات نرم‌افزار (`settings.ini`)

فایل `settings.ini` در پوشه برنامه در کنار فایل اجرایی قرار دارد و تغییرات آن در کمتر از یک ثانیه به صورت خودکار در برنامه اعمال می‌شود:

| بخش | نام متغیر | مقدار پیش‌فرض | توضیحات فنی |
| :--- | :--- | :--- | :--- |
| `[Server]` | `mode` | `both` | حالت کارکرد: `both` (ترکیبی)، `http` (سرور وب) یا `bluetooth` (بلوتوث). |
| `[Server]` | `http_host` | `0.0.0.0` | آدرس آی‌پی برای گوش دادن سرور وب محلی. |
| `[Server]` | `http_port` | `24234` | شماره پورت وب‌هوک برای دریافت درخواست‌های BinaryEye. |
| `[Server]` | `service_uuid`| `8a8478c9-2ca8-404b-a0de-101f34ab71ae` | شناسه اختصاصی سرویس بلوتوث RFCOMM برای BinaryEye. |
| `[Server]` | `service_name`| `BinaryReceptor` | نام نمایشی سرویس بلوتوث در ویندوز. |
| `[Server]` | `auto_start` | `false` | راه‌اندازی خودکار سرورها بلافاصله پس از باز شدن برنامه. |
| `[Typing]` | `output_mode`| `type` | روش ارسال خروجی: `type`، `paste`، `copy_only` یا `log_only`. |
| `[Typing]` | `prefix` | *(خالی)* | متن یا توکن‌های کلیدی که پیش از بارکد ارسال می‌شوند. |
| `[Typing]` | `suffix` | `{ENTER}` | متن یا توکن‌های کلیدی که بلافاصله پس از بارکد ارسال می‌شوند. |
| `[Typing]` | `inter_key_delay_ms` | `2` | فاصله زمانی بین فشرده شدن هر کلید به میلی‌ثانیه. |
| `[Typing]` | `pre_typing_delay_ms` | `10` | مکث پیش از آغاز تایپ بارکد به میلی‌ثانیه. |
| `[Filter]` | `deduplication_enabled` | `true` | فعال‌سازی فیلتر حذف اسکن‌های تکراری در ارسال همزمان. |
| `[Filter]` | `deduplication_window_ms` | `1500` | بازه زمانی مجاز برای مهار اسکن‌های مشابه به میلی‌ثانیه. |
| `[General]`| `language` | `fa` | زبان رابط کاربری: `fa` (فارسی راست‌به‌چپ) یا `en` (انگلیسی). |
| `[General]`| `theme` | `dark` | پوسته ظاهری برنامه: `dark` (تیره)، `light` (روشن) یا `system`. |
| `[General]`| `start_minimized` | `false` | اجرای مستقیم در سینی سیستم ویندوز (System Tray) هنگام شروع. |
| `[General]`| `sound_enabled` | `true` | پخش بوق صوتی تایید پس از دریافت موفق بارکد. |

---

## 🚀 راهنمای نصب و اجرای سریع

### روش اول: نسخه مستقل بدون نیاز به نصب (پیشنهادی)
۱. بسته فشرده `BinaryReceptor-v3.6.0-win64.zip` را از بخش [انتشارهای گیت‌هاب (Releases)](https://github.com/ouncommono/BinaryReceptor/releases/latest) دانلود کنید.  
۲. فایل را در پوشه دلخواه خود استخراج نمایید.  
۳. فایل `BinaryReceptor.exe` را اجرا کنید.  
۴. روی دکمه **شروع سرور** کلیک کنید و بارکدها را اسکن نمایید.

### روش دوم: اجرا از طریق کدهای منبع (Source Code)
```powershell
# دریافت کدهای مخزن
git clone https://github.com/ouncommono/BinaryReceptor.git
cd BinaryReceptor

# نصب پیش‌نیازها
pip install -r requirements.txt

# اجرای برنامه
python run.py
```

---

## 🔧 عیب‌یابی و پرسش‌های متداول

- **پخش بوق خطا در اپلیکیشن گوشی هنگام اسکن تحت شبکه (HTTP)؟**  
  باینری‌رسپتور نسخه ۳.۶.۰ پاسخ `200 OK` را در کسری از میلی‌ثانیه پیش از پردازش کلیدها ارسال می‌کند تا هیچ خطایی در گوشی ثبت نشود. اطمینان حاصل کنید فایروال ویندوز دسترسی پورت ۲۴۲۳۴ را مسدود نکرده باشد.
- **وضعیت بلوتوث روی "Adapter Off" مانده است؟**  
  مطمئن شوید بلوتوث ویندوز روشن بوده و سخت‌افزار بلوتوث دستگاه شما به درستی فعال است.
- **تایپ حروف انگلیسی بارکد به صورت حروف فارسی در ویندوز؟**  
  باینری‌رسپتور از موتور تایپ مستقیم کد یونیکد استفاده می‌کند که ساختار چینش زبان فعال ویندوز را نادیده گرفته و همیشه بارکد را به شکل استاندارد تایپ می‌کند.
- **پیام Windows Defender SmartScreen در اولین اجرا؟**  
  روی گزینه *More info* و سپس *Run anyway* کلیک کنید. این فایل به صورت خودکار و شفاف توسط پایپ‌لاین CI/CD گیت‌هاب از روی کدهای همین مخزن ساخته شده است.

---

## 📜 پروانه نرم‌افزار و حقوق نشر (License & Credits)

این پروژه تحت مجوز آزاد بین‌المللی [MIT License](LICENSE) منتشر شده است.  
طراحی معماری، بازنویسی مدرن و توسعه نسخه ۳.۶.۰ توسط **ouncommono**.  
پروژه پایه و مخزن اصلی: [KamaleiZestri/BinaryReceptor](https://github.com/KamaleiZestri/BinaryReceptor).  
اپلیکیشن کلاینت اندروید: [BinaryEye](https://github.com/markusfisch/BinaryEye) اثر Markus Fisch.
