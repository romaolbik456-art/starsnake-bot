import logging
import json
import os
import random
import string
import asyncio
import aiohttp
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
BOT_TOKEN  = "8635694534:AAHxYWfNaUCpUUkcF9v60plWlD5b0Ol0HDc"
GAME_URL   = "https://musical-sunflower-f1ad5f.netlify.app"
ADMIN_ID   = 8562699254
# ══════════════════════════════════════════════

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DB_FILE = "players.json"


# ─── База данных ──────────────────────────────
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def get_player(user_id):
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        db[uid] = {"stars": 0.0, "lives": 0, "games_played": 0, "stars_withdrawn": 0.0}
        save_db(db)
    return db[uid]

def update_player(user_id, data):
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        db[uid] = {"stars": 0.0, "lives": 0, "games_played": 0, "stars_withdrawn": 0.0}
    db[uid].update(data)
    save_db(db)

def player_exists(user_id):
    db = load_db()
    return str(user_id) in db


# ─── Меню ─────────────────────────────────────
def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🐍 Играть в змейку",    callback_data="play")],
        [InlineKeyboardButton("❤️ Купить жизни",       callback_data="shop")],
        [InlineKeyboardButton("💎 Вывести звёзды",     callback_data="withdraw_menu")],
        [InlineKeyboardButton("🔤 Найти свободный юз", callback_data="find_username")],
        [InlineKeyboardButton("👤 Личный кабинет",     callback_data="profile")],
    ])

def main_text(user):
    return (
        f"👋 Привет, <b>{user.first_name}</b>!\n\n"
        "🐍 <b>Star Snake</b> — собирай звёзды и выводи их!\n\n"
        "⭐ За каждую звезду: <b>+0.025</b>\n"
        "💀 Смерть: <b>штраф −0.5 ⭐</b>\n"
        "🏆 Минимальный вывод: <b>15 ⭐</b>\n\n"
        "Выбери действие:"
    )


# ─── /start ───────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_new = not player_exists(user.id)
    get_player(user.id)

    # Уведомление админу о новом игроке
    if is_new:
        username = f"@{user.username}" if user.username else user.first_name
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"👤 <b>Новый игрок!</b>\n\n"
                    f"Имя: <b>{user.first_name}</b>\n"
                    f"Юзернейм: <b>{username}</b>\n"
                    f"🆔 ID: <code>{user.id}</code>"
                ),
                parse_mode="HTML"
            )
        except:
            pass

    text = main_text(user)
    kb   = main_kb()
    if update.message:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        except:
            await update.callback_query.message.reply_text(text, reply_markup=kb, parse_mode="HTML")


# ─── /menu ────────────────────────────────────
async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ─── /help ────────────────────────────────────
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 <b>Как играть в Star Snake</b>\n\n"
        "🐍 Управляй змейкой и собирай ⭐ звёзды\n\n"
        "⭐ За каждую звезду: <b>+0.025</b>\n"
        "💀 Смерть: штраф <b>−0.5 ⭐</b>\n"
        "❤️ Жизни спасают от штрафа\n"
        "💎 Минимум для вывода: <b>15 ⭐</b>\n\n"
        "📌 Команды:\n"
        "/start — главное меню\n"
        "/menu — открыть меню\n"
        "/help — эта справка",
        parse_mode="HTML"
    )


# ─── Играть ───────────────────────────────────
async def play_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    player = get_player(query.from_user.id)
    lives  = player.get("lives", 0)
    stars  = player.get("stars", 0.0)
    url    = f"{GAME_URL}?lives={lives}&stars={stars:.3f}&uid={query.from_user.id}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Запустить игру", web_app=WebAppInfo(url=url))],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")],
    ])
    await query.edit_message_text(
        "🐍 <b>Star Snake</b>\n\n"
        "Нажми кнопку — игра откроется прямо в Telegram!\n\n"
        f"❤️ Жизней: <b>{lives}</b>\n"
        f"⭐ Баланс: <b>{stars:.3f}</b>",
        reply_markup=kb, parse_mode="HTML"
    )


# ─── Магазин ──────────────────────────────────
async def shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("5 ❤️  —  10 ⭐", callback_data="buy_5")],
        [InlineKeyboardButton("10 ❤️  —  25 ⭐", callback_data="buy_10")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")],
    ])
    await query.edit_message_text(
        "❤️ <b>Магазин жизней</b>\n\n"
        "Купи жизни — при смерти жизнь спасёт от штрафа и продолжит игру! 🛡️",
        reply_markup=kb, parse_mode="HTML"
    )

async def buy_5_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await context.bot.send_invoice(
        chat_id=query.message.chat_id,
        title="5 ❤️ Жизней",
        description="5 жизней в Star Snake — спасают от штрафа!",
        payload="lives_5", currency="XTR",
        prices=[LabeledPrice("5 жизней", 10)],
        provider_token="",
    )

async def buy_10_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await context.bot.send_invoice(
        chat_id=query.message.chat_id,
        title="10 ❤️ Жизней",
        description="10 жизней в Star Snake — спасают от штрафа!",
        payload="lives_10", currency="XTR",
        prices=[LabeledPrice("10 жизней", 25)],
        provider_token="",
    )


# ─── Вывод ────────────────────────────────────
async def withdraw_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    player = get_player(query.from_user.id)
    stars  = player.get("stars", 0.0)
    MIN    = 15.0

    def make_btn(amount):
        label = f"✅ {amount} ⭐" if stars >= amount else f"🔒 {amount} ⭐"
        return InlineKeyboardButton(label, callback_data=f"withdraw_{amount}")

    kb = InlineKeyboardMarkup([
        [make_btn(15), make_btn(25)],
        [make_btn(50), make_btn(100)],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")],
    ])
    status = "✅ Можешь выводить!" if stars >= MIN else f"❌ Не хватает <b>{MIN - stars:.3f} ⭐</b>"
    await query.edit_message_text(
        f"💎 <b>Вывод звёзд</b>\n\n"
        f"Твой баланс: <b>{stars:.3f} ⭐</b>\n"
        f"Минимум: <b>15 ⭐</b>\n\n{status}\n\nВыбери сумму:",
        reply_markup=kb, parse_mode="HTML"
    )

async def withdraw_amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    amount = float(query.data.split("_")[1])
    player = get_player(query.from_user.id)
    stars  = player.get("stars", 0.0)
    if stars < amount:
        await query.answer(f"❌ Недостаточно! У тебя {stars:.3f} ⭐", show_alert=True)
        return
    await query.answer()
    username = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"💎 <b>Заявка на вывод!</b>\n\n"
                f"👤 Игрок: <b>{username}</b>\n"
                f"🆔 ID: <code>{query.from_user.id}</code>\n"
                f"💰 Баланс: <b>{stars:.3f} ⭐</b>\n"
                f"💎 Сумма: <b>{amount} ⭐</b>"
            ),
            parse_mode="HTML"
        )
    except:
        pass
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В меню", callback_data="back_main")]])
    await query.edit_message_text(
        f"✅ <b>Заявка принята!</b>\n\n"
        f"💎 Сумма: <b>{amount} ⭐</b>\n"
        f"📊 Баланс: <b>{stars:.3f} ⭐</b>\n\n"
        "Ожидай — администратор отправит тебе Stars в ближайшее время 😊",
        reply_markup=kb, parse_mode="HTML"
    )


# ─── Личный кабинет ───────────────────────────
async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    player = get_player(query.from_user.id)
    stars     = player.get("stars", 0.0)
    lives     = player.get("lives", 0)
    games     = player.get("games_played", 0)
    withdrawn = player.get("stars_withdrawn", 0.0)
    MIN       = 15.0
    needed    = max(0.0, MIN - stars)
    status    = "✅ Можно выводить!" if stars >= MIN else f"⏳ Не хватает <b>{needed:.3f} ⭐</b>"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]])
    await query.edit_message_text(
        f"👤 <b>Личный кабинет</b>\n{'─'*26}\n\n"
        f"🎮 Игр сыграно: <b>{games}</b>\n"
        f"⭐ На счётчике: <b>{stars:.3f} ⭐</b>\n"
        f"❤️ Жизней куплено: <b>{lives}</b>\n"
        f"💸 Выведено: <b>{withdrawn:.3f} ⭐</b>\n\n"
        f"{'─'*26}\n{status}\n\n"
        f"📌 Минимум вывода: <b>15 ⭐</b>",
        reply_markup=kb, parse_mode="HTML"
    )


# ─── Синхронизация счёта из игры ──────────────
async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = json.loads(update.message.web_app_data.data)
        if data.get("action") == "update_stars":
            user_id = update.effective_user.id
            stars = float(data.get("stars", 0))
            lives_count = int(data.get("lives", 0))
            update_player(user_id, {
                "stars": round(stars, 3),
                "lives": lives_count
            })
            logger.info(f"Score synced for {user_id}: {stars} stars, {lives_count} lives")
    except Exception as e:
        logger.error(f"web_app_data error: {e}")


# ─── Pre-checkout ─────────────────────────────
async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


# ─── Успешная оплата ──────────────────────────
async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    payload = update.message.successful_payment.invoice_payload
    player  = get_player(user_id)
    if payload == "lives_5":
        new_lives = player["lives"] + 5
        update_player(user_id, {"lives": new_lives})
        await update.message.reply_text(
            f"✅ <b>Оплата прошла!</b>\n\n❤️ +5 жизней!\nТеперь: <b>{new_lives} ❤️</b>",
            parse_mode="HTML"
        )
    elif payload == "lives_10":
        new_lives = player["lives"] + 10
        update_player(user_id, {"lives": new_lives})
        await update.message.reply_text(
            f"✅ <b>Оплата прошла!</b>\n\n❤️ +10 жизней!\nТеперь: <b>{new_lives} ❤️</b>",
            parse_mode="HTML"
        )


# ─── Поиск свободных юзернеймов ──────────────
VOWELS = 'aeiou'
CONSONANTS = 'bcdfghjklmnpqrstvwxyz'

def gen_username():
    """Генерирует красивый юзернейм из 5 букв"""
    patterns = [
        # CVCVC - самый читаемый паттерн
        lambda: (random.choice(CONSONANTS) + random.choice(VOWELS) +
                 random.choice(CONSONANTS) + random.choice(VOWELS) +
                 random.choice(CONSONANTS)),
        # CVCCV
        lambda: (random.choice(CONSONANTS) + random.choice(VOWELS) +
                 random.choice(CONSONANTS) + random.choice(CONSONANTS) +
                 random.choice(VOWELS)),
        # VCCVC
        lambda: (random.choice(VOWELS) + random.choice(CONSONANTS) +
                 random.choice(CONSONANTS) + random.choice(VOWELS) +
                 random.choice(CONSONANTS)),
    ]
    return random.choice(patterns)()

async def check_username_free(username: str, bot) -> bool:
    """Двойная проверка: Telegram API + Fragment"""
    # Проверка 1 — Telegram API
    try:
        await bot.get_chat(f"@{username}")
        return False  # Занят в Telegram
    except Exception as e:
        err = str(e).lower()
        if "chat not found" not in err and "username not found" not in err and "invalid" not in err:
            return False  # Другая ошибка — пропускаем

    # Проверка 2 — Fragment.com
    try:
        url = f"https://fragment.com/username/{username}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                text = await resp.text()
                # Если на Fragment есть листинг — занят или продаётся
                if "Unavailable" in text or "unavailable" in text:
                    return False
                if "ton_price" in text or "Buy for" in text or "Place a bid" in text:
                    return False  # Продаётся на Fragment
                if "Available" in text:
                    return True  # Свободен!
    except:
        pass

    return True  # Не найден нигде — свободен!

async def find_free_usernames(count: int = 5, bot=None) -> list:
    """Ищет count свободных юзернеймов"""
    found = []
    tried = set()
    attempts = 0
    while len(found) < count and attempts < 100:
        attempts += 1
        username = gen_username()
        if username in tried:
            continue
        tried.add(username)
        if await check_username_free(username, bot):
            found.append(username)
        await asyncio.sleep(0.5)
    return found


# ─── Callback: найти юзернейм ─────────────────
async def find_username_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]])
    await query.edit_message_text(
        "🔤 <b>Поиск свободных юзернеймов</b>\n\n"
        "⏳ Ищем свободные юзернеймы из 5 букв...\n"
        "Это займёт около 30 секунд, подожди!",
        reply_markup=kb, parse_mode="HTML"
    )
    # Ищем юзернеймы
    usernames = await find_free_usernames(5, context.bot)
    if usernames:
        result = "\n".join([f"✅ <code>@{u}</code>  →  t.me/{u}" for u in usernames])
        text = (
            f"🔤 <b>Свободные юзернеймы найдены!</b>\n\n"
            f"{result}\n\n"
            f"💡 Нажми на юзернейм чтобы скопировать!\n"
            f"⚡️ Регистрируй быстро — их могут занять!"
        )
    else:
        text = (
            "😔 <b>Не удалось найти свободные юзернеймы.</b>\n\n"
            "Попробуй ещё раз!"
        )
    kb2 = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Искать ещё", callback_data="find_username")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")],
    ])
    await query.edit_message_text(text, reply_markup=kb2, parse_mode="HTML")


# ─── Назад ────────────────────────────────────
async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ─── Запуск ───────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu",  menu_cmd))
    app.add_handler(CommandHandler("help",  help_cmd))
    app.add_handler(CallbackQueryHandler(play_callback,            pattern="^play$"))
    app.add_handler(CallbackQueryHandler(shop_callback,            pattern="^shop$"))
    app.add_handler(CallbackQueryHandler(buy_5_callback,           pattern="^buy_5$"))
    app.add_handler(CallbackQueryHandler(buy_10_callback,          pattern="^buy_10$"))
    app.add_handler(CallbackQueryHandler(withdraw_menu_callback,   pattern="^withdraw_menu$"))
    app.add_handler(CallbackQueryHandler(withdraw_amount_callback, pattern="^withdraw_(15|25|50|100)$"))
    app.add_handler(CallbackQueryHandler(profile_callback,         pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(find_username_callback,   pattern="^find_username$"))
    app.add_handler(CallbackQueryHandler(back_main,                pattern="^back_main$"))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    print("✅ Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
