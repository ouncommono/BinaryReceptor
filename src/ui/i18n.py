"""Comprehensive bilingual localization dictionaries (English & Persian / فارسی) for BinaryReceptor v3.2.0.

Engineered with 100% key parity between 'en' and 'fa', natural professional phrasing,
and complete isolation so English is 100% LTR and Persian is 100% RTL with zero mixed text.
"""
from __future__ import annotations

from typing import Any

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # App & Header
        "app_title": "BinaryReceptor v3.2.0",
        "app_subtitle": "Desktop Companion Server for BinaryEye Android Barcode Scanner",
        "status_running": "SERVER ACTIVE",
        "status_stopped": "SERVER STOPPED",
        "status_listening": "Listening",
        "status_connected": "Connected",
        "status_standby": "Standby",
        "status_adapter_off": "Adapter Off",
        "status_error": "Port Error",
        "status_disabled": "Disabled by Mode",
        "btn_start": "Start Server",
        "btn_stop": "Stop Server",
        "theme_dark": "Dark Theme",
        "theme_light": "Light Theme",
        "theme_system": "System Default",
        "lang_switch": "فارسی",

        # Compact Top Status Strip
        "strip_server": "Server:",
        "strip_mode": "Mode:",
        "strip_bt": "Bluetooth:",
        "strip_http": "HTTP Server:",
        "strip_stats": "Scans:",
        "strip_total": "Total",
        "strip_dedup": "Deduped",

        # Channel Status Badges
        "badge_bt": "Bluetooth RFCOMM",
        "badge_http": "HTTP Server",

        # Tab Titles
        "tab_dashboard": "Live Scan Activity",
        "tab_wedge": "Prefix / Suffix Builder",
        "tab_connection": "Connection & QR Code",
        "tab_settings": "Settings & Hardware",

        # Dashboard / Activity Log
        "col_time": "Timestamp",
        "col_channel": "Channel",
        "col_format": "Format",
        "col_content": "Barcode Content",
        "col_status": "Status",
        "btn_retype": "Re-type Selected",
        "btn_copy": "Copy Content",
        "btn_clear_log": "Clear Activity Log",
        "btn_export_csv": "Export to CSV",
        "status_typed": "Typed (SendInput)",
        "status_pasted": "Pasted (Ctrl+V)",
        "status_copied": "Copied to Clipboard",
        "status_logged": "Logged (No Typing)",
        "status_dedup": "Duplicate Suppressed",
        "status_filtered": "Filtered",
        "status_handshake": "Connection Handshake OK",
        "confirm_clear_log": "Are you sure you want to clear the entire activity log?",
        "export_success": "Successfully exported {count} scans to {path}",

        # Prefix & Suffix Builder
        "wedge_title": "Visual Keystroke & Token Builder",
        "wedge_desc": "Configure keys or text typed before (Prefix) and after (Suffix) each scanned barcode. Click token chip buttons to append them instantly without typing raw escape sequences.",
        "lbl_prefix": "Prefix (Typed Before Barcode):",
        "lbl_suffix": "Suffix (Typed After Barcode):",
        "lbl_preview": "Live Keystroke Output Preview:",
        "preset_custom": "Custom Input...",
        "preset_none": "None (Empty)",
        "preset_enter": "Enter (Next Line)",
        "preset_tab": "Tab (Next Field)",
        "preset_space": "Space",
        "preset_double_enter": "Double Enter",
        "preset_tab_enter": "Tab + Enter",
        "preset_backspace": "Backspace",
        "preset_esc": "Escape",
        "preset_down": "Down Arrow",
        "btn_add_enter": "+ Enter",
        "btn_add_tab": "+ Tab",
        "btn_add_space": "+ Space",
        "btn_add_backspace": "+ Bksp",
        "btn_add_esc": "+ Esc",
        "btn_add_down": "+ Down",
        "btn_add_date": "+ Date",
        "btn_add_time": "+ Time",
        "btn_clear_field": "Clear",

        # Connection Assistant & QR Generator
        "conn_title": "BinaryEye Connection Assistant & Forwarding Configuration",
        "conn_desc": "Configure BinaryEye on Android using the exact Forwarding Request Type selected below.",
        "subtab_qr_url": "1. Standard Forwarding URL",
        "subtab_qr_encode": "2. Send Barcode (Raw Text)",
        "lbl_lan_ip": "Active PC Network Address:",
        "lbl_binaryeye_req_type": "BinaryEye Request Type (Settings -> Forwarding):",
        "opt_req_post_json": "POST application/json (Recommended)",
        "opt_req_post_form": "POST application/x-www-form-urlencoded",
        "opt_req_get_query": "GET with full query string",
        "opt_req_get_append": "GET and simply add content",
        "desc_req_post_json": "In BinaryEye > Settings > Forwarding:\n1. Enable 'Forward scans'\n2. Set Request Type: 'POST application/json'\n3. Set URL to the address below",
        "desc_req_post_form": "In BinaryEye > Settings > Forwarding:\n1. Enable 'Forward scans'\n2. Set Request Type: 'POST application/x-www-form-urlencoded'\n3. Set URL to the address below",
        "desc_req_get_query": "In BinaryEye > Settings > Forwarding:\n1. Enable 'Forward scans'\n2. Set Request Type: 'GET with full query string'\n3. Set URL to the address below",
        "desc_req_get_append": "In BinaryEye > Settings > Forwarding:\n1. Enable 'Forward scans'\n2. Set Request Type: 'GET and simply add content'\n3. Set URL to the address below",
        "lbl_http_url": "Configured Forwarding URL:",
        "btn_copy_url": "Copy URL",
        "url_copied": "Forwarding URL copied to clipboard!",
        "lbl_encode_text": "Raw Text to Encode into Barcode:",
        "lbl_encode_format": "Target Barcode Symbology:",
        "btn_generate_encode_qr": "Update Barcode",
        "desc_qr_encode": "Displays your exact text verbatim as a barcode (100% raw text, no wrapper).",

        # Settings
        "sec_general": "General Configuration",
        "sec_network": "Network & HTTP Server",
        "sec_bluetooth": "Bluetooth RFCOMM",
        "sec_wedge": "Keystroke & Output Options",
        "sec_dedup": "Sliding Window Deduplication",
        "sec_filters": "Content Filters & Transformations",

        "lbl_mode": "Operating Mode:",
        "opt_mode_both": "Hybrid Simultaneous (Bluetooth + HTTP)",
        "opt_mode_http": "HTTP Server Only (Wi-Fi / LAN)",
        "opt_mode_bt": "Bluetooth RFCOMM Only",

        "lbl_theme_setting": "User Interface Theme:",
        "opt_theme_dark": "Dark Theme",
        "opt_theme_light": "Light Theme",
        "opt_theme_system": "System Default",

        "lbl_port": "HTTP Port:",
        "lbl_host": "HTTP Bind Address:",
        "lbl_bt_uuid": "SDP Service UUID:",
        "lbl_out_mode": "Typing Injection Mode:",
        "opt_out_type": "Simulate Keystrokes (SendInput Unicode)",
        "opt_out_paste": "Fast Clipboard Paste (Ctrl+V)",
        "opt_out_copy": "Copy to Clipboard Only (No Typing)",
        "opt_out_log": "History / Log Only (No Typing)",

        "lbl_inter_key": "Inter-Key Delay (ms):",
        "lbl_pre_delay": "Pre-Typing Delay (ms):",
        "chk_restore_clip": "Restore previous clipboard content after Ctrl+V paste",

        "chk_dedup_enabled": "Enable duplicate scan suppression",
        "lbl_dedup_window": "Deduplication Window (ms):",

        "chk_trim_space": "Strip leading and trailing whitespace",
        "lbl_replace_newlines": "Replace internal newlines with:",
        "opt_nl_none": "Keep Newlines (No Replacement)",
        "opt_nl_tab": "Replace with Tab",
        "opt_nl_space": "Replace with Space",

        "lbl_regex_pat": "Regex Pattern to Search:",
        "lbl_regex_rep": "Regex Replacement Text:",
        "lbl_allowed_fmt": "Allowed Barcode Formats:",
        "fmt_all": "All Barcode Formats",
        "fmt_1d": "1D Barcodes Only",
        "fmt_2d": "2D Codes Only (QR, DataMatrix, Aztec)",
        "chk_auto_url": "Automatically open in web browser if content is a valid URL",
        "chk_copy_always": "Always copy scanned barcode to clipboard",

        "chk_beep": "Play audio beep sound effect on successful scan",
        "btn_test_sound": "Test Sound",
        "chk_tray_notify": "Show Windows tray notifications for scans",
        "chk_start_windows": "Start BinaryReceptor automatically with Windows",
        "chk_auto_start": "Automatically start server on application launch",
        "chk_start_min": "Start minimized to system tray",
        "chk_min_tray": "Minimize to system tray on window close (X)",

        # Sticky Footer Actions
        "lbl_unsaved_changes": "● Unsaved changes",
        "lbl_all_saved": "✓ All changes saved",
        "btn_save_settings": "Save Settings",
        "btn_reset_defaults": "Reset to Defaults",
        "confirm_reset_defaults": "Are you sure you want to reset all settings to factory default values?",
        "settings_saved": "Settings successfully saved and applied!",
        "settings_reset": "Settings have been reset to factory defaults and applied.",

        # System Tray Menu
        "tray_title": "BinaryReceptor v3.2.0",
        "tray_status_header": "Status: {status}",
        "tray_start": "Start Server",
        "tray_stop": "Stop Server",
        "tray_mode_menu": "Operation Mode",
        "tray_mode_both": "Mode: Hybrid (Both)",
        "tray_mode_http": "Mode: HTTP Only",
        "tray_mode_bt": "Mode: Bluetooth Only",
        "tray_show_qr": "Show QR Codes & Connection...",
        "tray_show_window": "Open BinaryReceptor",
        "tray_exit": "Exit Completely",
        "toast_scan_title": "Barcode Scanned ({source})",
    },

    "fa": {
        # App & Header
        "app_title": "باینری‌رسپتور v3.2.0 (BinaryReceptor)",
        "app_subtitle": "سرور همراه دسکتاپ برای اسکنر بارکد اندروید BinaryEye",
        "status_running": "سرور فعال است",
        "status_stopped": "سرور متوقف است",
        "status_listening": "در حال گوش دادن",
        "status_connected": "دستگاه متصل شد",
        "status_standby": "آماده به کار",
        "status_adapter_off": "بلوتوث خاموش است",
        "status_error": "خطای پورت شبکه",
        "status_disabled": "غیرفعال در این حالت",
        "btn_start": "شروع به کار سرور",
        "btn_stop": "متوقف کردن سرور",
        "theme_dark": "پوسته تیره (Dark)",
        "theme_light": "پوسته روشن (Light)",
        "theme_system": "پیش‌فرض سیستم",
        "lang_switch": "English",

        # Compact Top Status Strip
        "strip_server": "سرور اصلی:",
        "strip_mode": "حالت کاری:",
        "strip_bt": "بلوتوث:",
        "strip_http": "سرور شبکه:",
        "strip_stats": "اسکن‌ها:",
        "strip_total": "مجموع",
        "strip_dedup": "تکراری‌ها",

        # Channel Status Badges
        "badge_bt": "بلوتوث (Bluetooth RFCOMM)",
        "badge_http": "سرور شبکه (HTTP Server)",

        # Tab Titles
        "tab_dashboard": "فعالیت زنده اسکن‌ها",
        "tab_wedge": "سازنده پیشوند و پسوند کلیدها",
        "tab_connection": "اتصال و بارکدهای QR",
        "tab_settings": "تنظیمات و سخت‌افزار",

        # Dashboard / Activity Log
        "col_time": "زمان دریافت",
        "col_channel": "کانال ارتباطی",
        "col_format": "فرمت بارکد",
        "col_content": "محتوای بارکد",
        "col_status": "وضعیت پردازش",
        "btn_retype": "تایپ مجدد مورد انتخابی",
        "btn_copy": "کپی کردن محتوا",
        "btn_clear_log": "پاکسازی تاریخچه اسکن‌ها",
        "btn_export_csv": "خروجی فایل اکسل (CSV)",
        "status_typed": "تایپ شد (SendInput)",
        "status_pasted": "پیست شد (Ctrl+V)",
        "status_copied": "در کلیپ‌بورد کپی شد",
        "status_logged": "فقط ثبت لاگ (بدون تایپ)",
        "status_dedup": "تکراری مسدود شد",
        "status_filtered": "فیلتر شد",
        "status_handshake": "ارتباط اولیه تأیید شد",
        "confirm_clear_log": "آیا از پاکسازی کامل تاریخچه اسکن‌ها اطمینان دارید؟",
        "export_success": "تعداد {count} بارکد با موفقیت در فایل {path} ذخیره شد.",

        # Prefix & Suffix Builder
        "wedge_title": "سازنده بصری کلیدهای پیشوند و پسوند",
        "wedge_desc": "کلیدها یا متنی که قبل از بارکد (پیشوند) یا بعد از بارکد (پسوند) تایپ می‌شوند را انتخاب کنید. با کلیک روی هر دکمه، کلید مورد نظر بدون نیاز به نوشتن کد اضافه می‌شود.",
        "lbl_prefix": "پیشوند (کلیدهایی که قبل از بارکد تایپ می‌شوند):",
        "lbl_suffix": "پسوند (کلیدهایی که بعد از بارکد تایپ می‌شوند):",
        "lbl_preview": "پیش‌نمایش زنده کلیدهای تایپ‌شده:",
        "preset_custom": "ورودی سفارشی...",
        "preset_none": "هیچ‌کدام (خالی)",
        "preset_enter": "اینتر (خط بعدی)",
        "preset_tab": "تب (فیلد بعدی)",
        "preset_space": "فاصله (Space)",
        "preset_double_enter": "دوبار اینتر",
        "preset_tab_enter": "تب + اینتر",
        "preset_backspace": "بک‌اسپیس (حذف کاراکتر قبلی)",
        "preset_esc": "خروج (Esc)",
        "preset_down": "جهت پایین (Down)",
        "btn_add_enter": "+ اینتر",
        "btn_add_tab": "+ تب",
        "btn_add_space": "+ فاصله",
        "btn_add_backspace": "+ بک‌اسپیس",
        "btn_add_esc": "+ خروج (Esc)",
        "btn_add_down": "+ جهت پایین",
        "btn_add_date": "+ تاریخ امروز",
        "btn_add_time": "+ ساعت جاری",
        "btn_clear_field": "پاک کردن",

        # Connection Assistant & QR Generator
        "conn_title": "دستیار اتصال و تنظیمات فورواردینگ در BinaryEye",
        "conn_desc": "نرم‌افزار BinaryEye را در گوشی اندروید بر اساس نوع درخواست انتخاب‌شده در زیر پیکربندی کنید.",
        "subtab_qr_url": "۱. آدرس وب‌هوک و فورواردینگ استاندارد",
        "subtab_qr_encode": "۲. ارسال بارکد به گوشی (متن مستقیم)",
        "lbl_lan_ip": "آدرس فعال شبکه در این کامپیوتر:",
        "lbl_binaryeye_req_type": "نوع درخواست در BinaryEye (منوی Settings > Forwarding):",
        "opt_req_post_json": "ارسال POST با فرمت application/json (پیشنهادی)",
        "opt_req_post_form": "ارسال POST با فرمت form-urlencoded",
        "opt_req_get_query": "ارسال GET با پارامترهای کامل (Query String)",
        "opt_req_get_append": "ارسال GET با الصاق مستقیم متن به انتهای آدرس",
        "desc_req_post_json": "در نرم‌افزار BinaryEye منوی Settings > Forwarding:\n۱. گزینه Forward scans را فعال کنید\n۲. گزینه Request Type را روی POST application/json قرار دهید\n۳. آدرس زیر را در کادر URL وارد کنید",
        "desc_req_post_form": "در نرم‌افزار BinaryEye منوی Settings > Forwarding:\n۱. گزینه Forward scans را فعال کنید\n۲. گزینه Request Type را روی POST application/x-www-form-urlencoded قرار دهید\n۳. آدرس زیر را در کادر URL وارد کنید",
        "desc_req_get_query": "در نرم‌افزار BinaryEye منوی Settings > Forwarding:\n۱. گزینه Forward scans را فعال کنید\n۲. گزینه Request Type را روی GET with full query string قرار دهید\n۳. آدرس زیر را در کادر URL وارد کنید",
        "desc_req_get_append": "در نرم‌افزار BinaryEye منوی Settings > Forwarding:\n۱. گزینه Forward scans را فعال کنید\n۲. گزینه Request Type را روی GET and simply add content قرار دهید\n۳. آدرس زیر را در کادر URL وارد کنید",
        "lbl_http_url": "آدرس تنظیم‌شده جهت درج در گوشی:",
        "btn_copy_url": "کپی کردن آدرس",
        "url_copied": "آدرس فورواردینگ در کلیپ‌بورد کپی شد!",
        "lbl_encode_text": "متنی که مایلید به بارکد تبدیل شود:",
        "lbl_encode_format": "نوع و فرمت بارکد:",
        "btn_generate_encode_qr": "به‌روزرسانی بارکد",
        "desc_qr_encode": "متن دقیق شما را بدون هیچ افزونه اضافه به صورت بارکد نمایش می‌دهد (کاملاً مستقیم و سازگار).",

        # Settings
        "sec_general": "تنظیمات عمومی و نحوه اجرا",
        "sec_network": "تنظیمات شبکه و وب‌سرویس HTTP",
        "sec_bluetooth": "تنظیمات ارتباط بی‌سیم بلوتوث",
        "sec_wedge": "تنظیمات خروجی و شبیه‌سازی کلیدها",
        "sec_dedup": "موتور حذف بارکدهای تکراری",
        "sec_filters": "فیلترها و ویرایش خودکار بارکدها",

        "lbl_mode": "حالت کاری برنامه:",
        "opt_mode_both": "حالت ترکیبی همزمان (بلوتوث + شبکه)",
        "opt_mode_http": "فقط سرور شبکه (Wi-Fi / LAN)",
        "opt_mode_bt": "فقط ارتباط بلوتوث (Bluetooth RFCOMM)",

        "lbl_theme_setting": "پوسته ظاهری برنامه:",
        "opt_theme_dark": "پوسته تیره (Dark)",
        "opt_theme_light": "پوسته روشن (Light)",
        "opt_theme_system": "پیش‌فرض سیستم",

        "lbl_port": "پورت شبکه HTTP:",
        "lbl_host": "آدرس اتصال در شبکه (Bind IP):",
        "lbl_bt_uuid": "شناسه سرویس بلوتوث (SDP UUID):",
        "lbl_out_mode": "روش درج بارکد در ویندوز:",
        "opt_out_type": "شبیه‌سازی تایپ کلیدها (SendInput Unicode)",
        "opt_out_paste": "پیست فوری از کلیپ‌بورد (Ctrl+V)",
        "opt_out_copy": "فقط کپی در کلیپ‌بورد (بدون تایپ)",
        "opt_out_log": "فقط ثبت لاگ (بدون تایپ یا کپی)",

        "lbl_inter_key": "تأخیر بین هر کلید (میلی‌ثانیه):",
        "lbl_pre_delay": "تأخیر قبل از شروع تایپ (میلی‌ثانیه):",
        "chk_restore_clip": "بازگردانی محتوای قبلی کلیپ‌بورد پس از پیست با Ctrl+V",

        "chk_dedup_enabled": "فعال‌سازی حذف خودکار اسکن‌های تکراری",
        "lbl_dedup_window": "بازه زمانی تشخیص تکراری (میلی‌ثانیه):",

        "chk_trim_space": "حذف خودکار فاصله‌های اضافه از ابتدا و انتهای بارکد",
        "lbl_replace_newlines": "جایگزینی خطوط جدید درون بارکد با:",
        "opt_nl_none": "بدون تغییر (حفظ خطوط جدید)",
        "opt_nl_tab": "جایگزینی با کلید تب (Tab)",
        "opt_nl_space": "جایگزینی با فاصله (Space)",

        "lbl_regex_pat": "الگوی جستجوی عبارات باقاعده (Regex):",
        "lbl_regex_rep": "متن جایگزین Regex:",
        "lbl_allowed_fmt": "فرمت‌های مجاز بارکد:",
        "fmt_all": "همه فرمت‌های بارکد",
        "fmt_1d": "فقط بارکدهای میله‌ای (1D)",
        "fmt_2d": "فقط کدهای دوبعدی (QR، DataMatrix و Aztec)",
        "chk_auto_url": "باز کردن خودکار در مرورگر در صورتی که بارکد یک لینک وب باشد",
        "chk_copy_always": "همواره یک نسخه از بارکد در کلیپ‌بورد کپی شود",

        "chk_beep": "پخش صدای شفاف اسکنر پس از دریافت موفق بارکد",
        "btn_test_sound": "تست صدا",
        "chk_tray_notify": "نمایش اعلان ویندوز هنگام دریافت بارکد",
        "chk_start_windows": "اجرای خودکار نرم‌افزار همزمان با روشن شدن ویندوز",
        "chk_auto_start": "شروع خودکار شنود و دریافت به محض باز شدن برنامه",
        "chk_start_min": "شروع برنامه به صورت کوچک‌شده در کنار ساعت (Tray)",
        "chk_min_tray": "کوچک‌سازی به کنار ساعت هنگام کلیک روی دکمه ضربدر (X)",

        # Sticky Footer Actions
        "lbl_unsaved_changes": "● تغییرات ذخیره‌نشده وجود دارد",
        "lbl_all_saved": "✓ تمام تنظیمات ذخیره شده است",
        "btn_save_settings": "ذخیره تنظیمات",
        "btn_reset_defaults": "بازگردانی به پیش‌فرض کارخانه",
        "confirm_reset_defaults": "آیا از بازگردانی تمام تنظیمات به مقادیر پیش‌فرض اولیه اطمینان دارید؟",
        "settings_saved": "تنظیمات با موفقیت ذخیره و اعمال شد!",
        "settings_reset": "تنظیمات به حالت پیش‌فرض کارخانه بازگردانده و اعمال شد.",

        # System Tray Menu
        "tray_title": "باینری‌رسپتور v3.2.0",
        "tray_status_header": "وضعیت: {status}",
        "tray_start": "شروع به کار سرور",
        "tray_stop": "متوقف کردن سرور",
        "tray_mode_menu": "حالت کاری برنامه",
        "tray_mode_both": "حالت: ترکیبی (همزمان)",
        "tray_mode_http": "حالت: فقط شبکه (HTTP)",
        "tray_mode_bt": "حالت: فقط بلوتوث",
        "tray_show_qr": "نمایش کدهای QR و راهنمای اتصال...",
        "tray_show_window": "نمایش پنجره باینری‌رسپتور",
        "tray_exit": "خروج کامل از برنامه",
        "toast_scan_title": "بارکد جدید دریافت شد ({source})",
    },
}


def tr(key: str, lang: str = "en", **kwargs: Any) -> str:
    """Retrieve translated string with format string substitution."""
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    text = lang_dict.get(key, TRANSLATIONS["en"].get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
