"""
Namoz Tracker Telegram Bot
==========================
O'rnatish:
  pip install pyTelegramBotAPI schedule

Ishga tushirish:
  python namoz_bot.py

@BotFather dan token oling va BOT_TOKEN ga yozing.
"""

import telebot
import json
import os
import schedule
import time
import threading
from datetime import datetime, date

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # <-- shu yerga o'z tokeningizni yozing

bot = telebot.TeleBot(BOT_TOKEN)

DATA_FILE = "namoz_data.json"

PRAYERS = ["Bomdod", "Peshin", "Asr", "Shom", "Xufton"]

PRAYER_EMOJI = {
    "Bomdod": "🌅",
    "Peshin": "☀️",
    "Asr":    "🌤",
    "Shom":   "🌇",
    "Xufton": "🌙",
}

# ─── Ma'lumotlarni saqlash ────────────────────────────────────────────────────

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def today_str():
    return date.today().strftime("%Y-%m-%d")

def get_user_today(data, cid):
    cid = str(cid)
    td = today_str()
    if cid not in data:
        data[cid] = {}
    if td not in data[cid]:
        data[cid][td] = {p: False for p in PRAYERS}
    return data[cid][td]

# ─── Statistika ───────────────────────────────────────────────────────────────

def get_stats(data, cid, month_str=None):
    """
    Oylik statistika: o'qildi / o'qilmadi / to'liq kunlar / foiz
    month_str format: "2025-05"
    """
    cid = str(cid)
    if cid not in data:
        return None
    if month_str is None:
        month_str = date.today().strftime("%Y-%m")

    total = 0
    done = 0
    full_days = 0
    days_counted = 0

    for day_key, prayers in data[cid].items():
        if not day_key.startswith(month_str):
            continue
        days_counted += 1
        day_done = 0
        for p in PRAYERS:
            total += 1
            if prayers.get(p, False):
                done += 1
                day_done += 1
        if day_done == 5:
            full_days += 1

    miss = total - done
    pct = round(done / total * 100) if total else 0
    return {
        "total": total,
        "done": done,
        "miss": miss,
        "full_days": full_days,
        "days": days_counted,
        "pct": pct,
    }

# ─── Xabar formatlash ─────────────────────────────────────────────────────────

def format_today(prayers_today):
    lines = ["📋 *Bugungi namozlar:*\n"]
    for p in PRAYERS:
        icon = PRAYER_EMOJI[p]
        status = "✅" if prayers_today.get(p) else "❌"
        lines.append(f"{status} {icon} {p}")
    done = sum(1 for p in PRAYERS if prayers_today.get(p))
    lines.append(f"\n*{done}/5* namoz o'qildi")
    return "\n".join(lines)

def format_stats(stats, month_str):
    if not stats or stats["total"] == 0:
        return "Bu oyda hali ma'lumot yo'q."
    return (
        f"📊 *{month_str} — statistika:*\n\n"
        f"✅ O'qildi: *{stats['done']}* ta\n"
        f"❌ O'qilmadi: *{stats['miss']}* ta\n"
        f"🌟 To'liq kun: *{stats['full_days']}* kun\n"
        f"📅 Hisoblangan kun: *{stats['days']}* kun\n"
        f"📈 Foiz: *{stats['pct']}%*"
    )

# ─── Inline tugmalar ──────────────────────────────────────────────────────────

def make_prayer_keyboard(prayers_today):
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    for p in PRAYERS:
        done = prayers_today.get(p, False)
        icon = PRAYER_EMOJI[p]
        label = f"{'✅' if done else '❌'} {icon} {p} — {'O\'qildi' if done else 'O\'qilmadi'}"
        markup.add(telebot.types.InlineKeyboardButton(label, callback_data=f"toggle_{p}"))
    markup.add(telebot.types.InlineKeyboardButton("📊 Statistika", callback_data="stats"))
    return markup

# ─── Handlers ────────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start", "help"])
def cmd_start(msg):
    bot.send_message(
        msg.chat.id,
        "🕌 *Namoz Tracker Botiga Xush Kelibsiz!*\n\n"
        "Har kuni namozlaringizni belgilab boring.\n\n"
        "📌 *Buyruqlar:*\n"
        "/bugun — Bugungi namozlarni ko'rish va belgilash\n"
        "/statistika — Oylik statistika\n"
        "/eslatma — Kunlik eslatmani yoqish/o'chirish\n"
        "/help — Yordam\n\n"
        "Yoki quyidagi tugmalardan foydalaning 👇",
        parse_mode="Markdown"
    )
    cmd_bugun(msg)

@bot.message_handler(commands=["bugun"])
def cmd_bugun(msg):
    data = load_data()
    prayers_today = get_user_today(data, msg.chat.id)
    text = format_today(prayers_today)
    bot.send_message(
        msg.chat.id,
        text,
        parse_mode="Markdown",
        reply_markup=make_prayer_keyboard(prayers_today)
    )

@bot.message_handler(commands=["statistika"])
def cmd_stats(msg):
    data = load_data()
    month_str = date.today().strftime("%Y-%m")
    stats = get_stats(data, msg.chat.id, month_str)
    text = format_stats(stats, date.today().strftime("%B %Y"))
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=["eslatma"])
def cmd_reminder(msg):
    data = load_data()
    cid = str(msg.chat.id)
    if "reminders" not in data:
        data["reminders"] = {}
    current = data["reminders"].get(cid, True)
    data["reminders"][cid] = not current
    save_data(data)
    status = "✅ yoqildi" if not current else "❌ o'chirildi"
    bot.send_message(
        msg.chat.id,
        f"Kunlik eslatma {status}.\n"
        f"Eslatma vaqtlari: Bomdod, Peshin, Asr, Shom, Xufton vaqtlarida yuboriladi.",
        parse_mode="Markdown"
    )

# ─── Callback (tugma bosilganda) ─────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("toggle_"))
def cb_toggle(call):
    prayer = call.data.replace("toggle_", "")
    if prayer not in PRAYERS:
        return
    data = load_data()
    prayers_today = get_user_today(data, call.message.chat.id)
    prayers_today[prayer] = not prayers_today.get(prayer, False)
    save_data(data)

    text = format_today(prayers_today)
    try:
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=make_prayer_keyboard(prayers_today)
        )
    except Exception:
        pass
    bot.answer_callback_query(call.id, "✅ Saqlandi!" if prayers_today[prayer] else "❌ Bekor qilindi")

@bot.callback_query_handler(func=lambda c: c.data == "stats")
def cb_stats(call):
    data = load_data()
    month_str = date.today().strftime("%Y-%m")
    stats = get_stats(data, call.message.chat.id, month_str)
    text = format_stats(stats, date.today().strftime("%B %Y"))
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# ─── Oddiy matn orqali belgilash ─────────────────────────────────────────────
# Foydalanuvchi "bomdod" deb yozsa ham ishlaydi

@bot.message_handler(func=lambda m: True)
def handle_text(msg):
    text = msg.text.strip().lower()
    matched = None
    for p in PRAYERS:
        if p.lower() in text:
            matched = p
            break

    if matched:
        data = load_data()
        prayers_today = get_user_today(data, msg.chat.id)
        prayers_today[matched] = True
        save_data(data)
        bot.send_message(
            msg.chat.id,
            f"{PRAYER_EMOJI[matched]} *{matched}* namozi belgilandi! ✅",
            parse_mode="Markdown",
            reply_markup=make_prayer_keyboard(prayers_today)
        )
    else:
        bot.send_message(
            msg.chat.id,
            "Namoz nomini yozing yoki /bugun buyrug'ini ishlating.",
            reply_markup=make_prayer_keyboard(
                get_user_today(load_data(), msg.chat.id)
            )
        )

# ─── Eslatma yuboruvchi (scheduled) ─────────────────────────────────────────

REMINDER_TIMES = {
    "Bomdod": "05:00",
    "Peshin": "13:00",
    "Asr":    "16:30",
    "Shom":   "19:30",
    "Xufton": "21:00",
}

def send_reminders(prayer):
    data = load_data()
    reminders = data.get("reminders", {})
    for cid, enabled in reminders.items():
        if not enabled:
            continue
        try:
            prayers_today = get_user_today(data, cid)
            if not prayers_today.get(prayer, False):
                bot.send_message(
                    int(cid),
                    f"{PRAYER_EMOJI[prayer]} *{prayer}* namozi vaqti keldi!\n\n"
                    f"O'qib bo'lsangiz quyidagi tugmani bosing 👇",
                    parse_mode="Markdown",
                    reply_markup=make_prayer_keyboard(prayers_today)
                )
        except Exception as e:
            print(f"Eslatma xatosi {cid}: {e}")

def setup_reminders():
    for prayer, t in REMINDER_TIMES.items():
        schedule.every().day.at(t).do(send_reminders, prayer=prayer)

def run_scheduler():
    setup_reminders()
    while True:
        schedule.run_pending()
        time.sleep(30)

# ─── Start ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Namoz bot ishga tushdi...")
    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()
    bot.infinity_polling()
