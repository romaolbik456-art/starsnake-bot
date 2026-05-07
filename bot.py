import logging
import json
import os
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    LabeledPrice, WebAppInfo
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    PreCheckoutQueryHandler, MessageHandler, filters,
    ContextTypes
)

# ══════════════════════════════════════════════
#  НАСТРОЙКИ — замени на свои!
# ══════════════════════════════════════════════
BOT_TOKEN = "8635694534:AAH8qnR3CSckrX4w6y264E_bOB3fGAD0Zb0"
GAME_URL   = "https://profound-mousse-176ccc.netlify.app"  # ссылка на игру
# ══════════════════════════════════════════════

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_FILE = "players.json"


# ─── База данных (простой JSON-файл) ──────────
def load_db() -> dict:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(db: dict):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def get_player(user_id: int) -> dict:
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        db[uid] = {"stars": 0.0, "lives": 0, "games_played": 0, "stars_withdrawn": 0.0}
        save_db(db)
    return db[uid]

def update_player(user_id: int, data: dict):
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        db[uid] = {"stars": 0.0, "lives": 0, "games_played": 0, "stars_withdrawn": 0.0}
    db[uid].update(data)
    save_db(db)


# ─── /start — главное меню ─────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_player(user.id)  # создать игрока если нет

    keyboard = [
        [InlineKeyboardButton("🐍 Играть в змейку", callback_data="play")],
        [InlineKeyboardButton("❤️ Купить жизни", callback_data="shop")],
        [InlineKeyboardButton("👤 Личный кабинет", callback_data="profile")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"👋 Привет, <b>{user.first_name}</b>!\n\n"
        "🐍 <b>Star Snake</b> — собирай звёзды и выводи их!\n\n"
        "⭐ За каждую звезду на поле: <b>+0.025</b>\n"
        "💀 Смерть: <b>штраф −0.5 ⭐</b>\n"
        "🏆 Минимальный вывод: <b>15 ⭐</b>\n\n"
        "Выбери действие:"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


# ─── Кнопка «Играть» ──────────────────────────
async def play_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🎮 Запустить игру", web_app=WebAppInfo(url=GAME_URL))],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")],
    ]
    await query.edit_message_text(
        "🐍 <b>Star Snake</b>\n\n"
        "Нажми кнопку ниже — игра откроется прямо в Telegram!\n\n"
        "🕹 <b>Управление:</b> свайп по экрану\n"
        "⭐ Собирай звёзды, избегай стен и себя!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


# ─── Кнопка «Купить жизни» ────────────────────
async def shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("5 ❤️  за  10 ⭐", callback_data="buy_5lives")],
        [InlineKeyboardButton("10 ❤️  за  25 ⭐", callback_data="buy_10lives")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")],
    ]
    await query.edit_message_text(
        "❤️ <b>Магазин жизней</b>\n\n"
        "Отлично! Купи жизни за звёзды Telegram, "
        "чтобы дольше играть и быстрее накопить на вывод!\n\n"
        "⬇️ Выбери пакет:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


# ─── Покупка 5 жизней (10 Stars) ──────────────
async def buy_5lives_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await context.bot.send_invoice(
        chat_id=query.message.chat_id,
        title="5 ❤️ Жизней",
        description="Получи 5 дополнительных жизней в игре Star Snake!",
        payload="lives_5",
        currency="XTR",          # XTR = Telegram Stars
        prices=[LabeledPrice("5 жизней", 10)],  # 10 Stars
        provider_token="",        # для Stars токен не нужен
    )


# ─── Покупка 10 жизней (25 Stars) ─────────────
async def buy_10lives_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await context.bot.send_invoice(
        chat_id=query.message.chat_id,
        title="10 ❤️ Жизней",
        description="Получи 10 дополнительных жизней в игре Star Snake!",
        payload="lives_10",
        currency="XTR",
        prices=[LabeledPrice("10 жизней", 25)],  # 25 Stars
        provider_token="",
    )


# ─── Подтверждение оплаты ─────────────────────
async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


# ─── Успешная оплата ──────────────────────────
async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    payload = update.message.successful_payment.invoice_payload
    player = get_player(user_id)

    if payload == "lives_5":
        new_lives = player["lives"] + 5
        update_player(user_id, {"lives": new_lives})
        await update.message.reply_text(
            f"✅ <b>Оплата прошла!</b>\n\n"
            f"❤️ Ты получил <b>5 жизней</b>!\n"
            f"Теперь у тебя: <b>{new_lives} ❤️</b>\n\n"
            f"🐍 Заходи в игру и используй их!",
            parse_mode="HTML"
        )
    elif payload == "lives_10":
        new_lives = player["lives"] + 10
        update_player(user_id, {"lives": new_lives})
        await update.message.reply_text(
            f"✅ <b>Оплата прошла!</b>\n\n"
            f"❤️ Ты получил <b>10 жизней</b>!\n"
            f"Теперь у тебя: <b>{new_lives} ❤️</b>\n\n"
            f"🐍 Заходи в игру и используй их!",
            parse_mode="HTML"
        )


# ─── Кнопка «Личный кабинет» ──────────────────
async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    player = get_player(user.id)
    stars = player.get("stars", 0.0)
    lives = player.get("lives", 0)
    games = player.get("games_played", 0)
    withdrawn = player.get("stars_withdrawn", 0.0)

    MIN_WITHDRAW = 15.0
    needed = max(0.0, MIN_WITHDRAW - stars)

    if stars >= MIN_WITHDRAW:
        status_line = f"✅ Можно выводить! Нажми «Забрать звёзды» в игре."
    else:
        status_line = f"⏳ До вывода не хватает <b>{needed:.3f} ⭐</b>"

    text = (
        f"👤 <b>Личный кабинет</b>\n"
        f"{'─'*28}\n\n"
        f"🎮 Игр сыграно: <b>{games}</b>\n"
        f"⭐ На счётчике: <b>{stars:.3f} ⭐</b>\n"
        f"❤️ Жизней куплено: <b>{lives}</b>\n"
        f"💸 Выведено всего: <b>{withdrawn:.3f} ⭐</b>\n\n"
        f"{'─'*28}\n"
        f"{status_line}\n\n"
        f"📌 Минимальная сумма вывода: <b>15 ⭐</b>"
    )

    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# ─── Назад в главное меню ─────────────────────
async def back_main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ─── Запуск бота ──────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(play_callback,       pattern="^play$"))
    app.add_handler(CallbackQueryHandler(shop_callback,       pattern="^shop$"))
    app.add_handler(CallbackQueryHandler(buy_5lives_callback,  pattern="^buy_5lives$"))
    app.add_handler(CallbackQueryHandler(buy_10lives_callback, pattern="^buy_10lives$"))
    app.add_handler(CallbackQueryHandler(profile_callback,    pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(back_main_callback,  pattern="^back_main$"))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    print("✅ Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
