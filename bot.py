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

# Слоги для генерации читаемых слов
SYLLABLES = [
    'ba','be','bi','bo','bu','bra','bre','bro','bru',
    'ca','ce','co','cu','cra','cre','cro','cru',
    'da','de','di','do','du','dra','dre','dro','dru',
    'fa','fe','fi','fo','fu','fla','fle','flo','flu',
    'ga','ge','gi','go','gu','gra','gre','gro','gru',
    'ha','he','hi','ho','hu',
    'ja','je','ji','jo','ju',
    'ka','ke','ki','ko','ku','kra','kre','kro',
    'la','le','li','lo','lu',
    'ma','me','mi','mo','mu',
    'na','ne','ni','no','nu',
    'pa','pe','pi','po','pu','pra','pre','pro','pru',
    'ra','re','ri','ro','ru',
    'sa','se','si','so','su','sha','she','sho','shu','ska','ske','ski','sko',
    'sta','ste','sti','sto','stu','stra','stre','stro',
    'ta','te','ti','to','tu','tra','tre','tro','tru',
    'va','ve','vi','vo','vu',
    'wa','we','wi','wo',
    'xa','xe','xi','xo',
    'ya','ye','yi','yo','yu',
    'za','ze','zi','zo','zu',
    'an','en','in','on','un',
    'al','el','il','ol','ul',
    'ar','er','ir','or','ur',
]

def gen_username():
    """Генерирует слово похожее на настоящее — 5, 6 или 7 букв"""
    while True:
        # Собираем из 1-3 слогов
        num_syllables = random.randint(1, 3)
        word = ''.join(random.choice(SYLLABLES) for _ in range(num_syllables))

        # Обрезаем до нужной длины
        length = random.choice([5, 6, 7])
        if len(word) < length:
            # Добираем буквы
            extras = 'aeioursntlm'
            word += ''.join(random.choice(extras) for _ in range(length - len(word)))
        word = word[:length]

        # Только буквы, минимум 5
        if len(word) >= 5 and word.isalpha():
            return word.lower()

async def check_username_free(username: str, bot) -> bool:
    """Тройная проверка: Telegram API + Fragment + t.me"""

    # Проверка 1 — Telegram API
    try:
        await bot.get_chat(f"@{username}")
        return False  # Нашли — занят
    except Exception as e:
        err = str(e).lower()
        # Если не "не найден" — неизвестная ошибка, считаем занятым
        if ("chat not found" not in err and
            "username not found" not in err and
            "invalid username" not in err and
            "peer_id_invalid" not in err and
            "deactivated" not in err):
            return False

    # Проверка 2 — Fragment.com
    try:
        url = f"https://fragment.com/username/{username}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0",
            "Accept-Language": "en-US,en;q=0.9",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                text = await resp.text()
                if any(x in text for x in [
                    "Unavailable", "unavailable", "ton_price",
                    "Buy for", "Place a bid", "sold", "auction",
                    "tgme_page", "Send Message"
                ]):
                    return False
    except:
        return False  # Не смогли проверить — считаем занятым на всякий случай

    # Проверка 3 — t.me
    try:
        url = f"https://t.me/{username}"
        headers = {"User-Agent": "Mozilla/5.0"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers,
                                   allow_redirects=True,
                                   timeout=aiohttp.ClientTimeout(total=8)) as resp:
                text = await resp.text()
                if any(x in text for x in [
                    "tgme_page_title", "tgme_page_description",
                    "Send Message", "View in Telegram", "og:title"
                ]):
                    return False
    except:
        return False

    return True  # Прошёл все 3 проверки — точно свободен!

async def find_free_usernames(count: int = 5, bot=None) -> list:
    """Ищет юзернеймы параллельно"""
    found = []
    tried = set()
    max_rounds = 20

    for _ in range(max_rounds):
        if len(found) >= count:
            break
        # Проверяем 4 юзернейма одновременно
        batch = []
        for _ in range(4):
            u = gen_username()
            while u in tried:
                u = gen_username()
            tried.add(u)
            batch.append(u)

        results = await asyncio.gather(*[check_username_free(u, bot) for u in batch])
        for u, free in zip(batch, results):
            if free and u not in found:
                found.append(u)
            if len(found) >= count:
                break
        await asyncio.sleep(0.3)

    return found[:count]


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
