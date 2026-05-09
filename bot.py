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
BOT_TOKEN  = "8635694534:AAHxYWfNaUCpUUkcF9v60plWlD5b0Ol0HDc"
GAME_URL   = "https://transcendent-cucurucho-e6d9e9.netlify.app"
BOT_USERNAME = "Zmeyka_Play_Bot"   # ← замени на username своего бота (без @)
REF_BONUS  = 2.0                   # +2 звезды за каждого приглашённого
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
        db[uid] = {
            "stars": 0.0,
            "lives": 0,
            "games_played": 0,
            "stars_withdrawn": 0.0,
            "referrals": 0,
            "referred_by": None
        }
        save_db(db)
    return db[uid]

def update_player(user_id, data):
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        db[uid] = {
            "stars": 0.0,
            "lives": 0,
            "games_played": 0,
            "stars_withdrawn": 0.0,
            "referrals": 0,
            "referred_by": None
        }
    db[uid].update(data)
    save_db(db)

def player_exists(user_id):
    db = load_db()
    return str(user_id) in db


# ─── Клавиатура главного меню ─────────────────
def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🐍 Играть в змейку", callback_data="play")],
        [InlineKeyboardButton("❤️ Купить жизни",    callback_data="shop")],
        [InlineKeyboardButton("💎 Вывести звёзды",  callback_data="withdraw_menu")],
        [InlineKeyboardButton("👥 Пригласить друга", callback_data="referral")],
        [InlineKeyboardButton("👤 Личный кабинет",  callback_data="profile")],
    ])

def main_text(user):
    return (
        f"👋 Привет, <b>{user.first_name}</b>!\n\n"
        "🐍 <b>Star Snake</b> — собирай звёзды и выводи их!\n\n"
        "⭐ За каждую звезду: <b>+0.025</b>\n"
        "💀 Смерть: <b>штраф −0.5 ⭐</b>\n"
        "👥 За приглашённого друга: <b>+2 ⭐</b>\n"
        "🏆 Минимальный вывод: <b>15 ⭐</b>\n\n"
        "Выбери действие:"
    )


# ─── /start ───────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    is_new = not player_exists(user.id)

    # Обработка реферальной ссылки
    if args and args[0].startswith("ref_") and is_new:
        ref_id = args[0][4:]  # убираем "ref_"
        if ref_id != str(user.id):  # нельзя пригласить самого себя
            # Создаём нового игрока
            get_player(user.id)
            update_player(user.id, {"referred_by": ref_id})

            # Начисляем бонус пригласившему
            ref_player = get_player(int(ref_id))
            new_stars = round(ref_player["stars"] + REF_BONUS, 3)
            new_refs  = ref_player["referrals"] + 1
            update_player(int(ref_id), {"stars": new_stars, "referrals": new_refs})

            # Уведомляем пригласившего
            try:
                await context.bot.send_message(
                    chat_id=int(ref_id),
                    text=(
                        f"🎉 <b>Твой друг {user.first_name} присоединился!</b>\n\n"
                        f"⭐ Тебе начислено <b>+{REF_BONUS} ⭐</b>\n"
                        f"💰 Твой баланс: <b>{new_stars:.3f} ⭐</b>"
                    ),
                    parse_mode="HTML"
                )
            except:
                pass

            # Приветствие новому игроку
            text = main_text(user)
            kb   = main_kb()
            if update.message:
                await update.message.reply_text(
                    f"👋 Привет, <b>{user.first_name}</b>!\n\n"
                    f"🎉 Ты пришёл по реферальной ссылке!\n\n"
                    f"🐍 Добро пожаловать в <b>Star Snake</b>!\n\n"
                    "Выбери действие:",
                    reply_markup=kb, parse_mode="HTML"
                )
            return

    get_player(user.id)
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
        "🐍 <b>Цель:</b> управляй змейкой и собирай ⭐ звёзды.\n\n"
        "⭐ <b>Очки:</b> за каждую звезду +0.025\n\n"
        "💀 <b>Смерть:</b> штраф <b>−0.5 ⭐</b>\n\n"
        "❤️ <b>Жизни:</b> купи в боте — спасают от штрафа!\n\n"
        "👥 <b>Рефералы:</b> пригласи друга → получи <b>+2 ⭐</b>\n\n"
        "💎 <b>Вывод:</b> минимум <b>15 ⭐</b>\n\n"
        "🕹 <b>Управление:</b> кнопки под полем\n\n"
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
        "🕹 Управление: кнопки под полем\n"
        f"❤️ Твоих жизней: <b>{lives}</b>\n"
        f"⭐ Твой баланс: <b>{stars:.3f}</b>",
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
        "Отлично! Купи жизни за звёзды Telegram, "
        "чтобы ты смог побыстрее их вывести в большем количестве! ⬇️❤️\n\n"
        "При смерти жизнь спасёт от штрафа и продолжит игру 🛡️",
        reply_markup=kb, parse_mode="HTML"
    )


# ─── Купить жизни ─────────────────────────────
async def buy_5_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await context.bot.send_invoice(
        chat_id=query.message.chat_id,
        title="5 ❤️ Жизней",
        description="5 дополнительных жизней в Star Snake!",
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
        description="10 дополнительных жизней в Star Snake!",
        payload="lives_10", currency="XTR",
        prices=[LabeledPrice("10 жизней", 25)],
        provider_token="",
    )


# ─── Вывод звёзд ──────────────────────────────
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
        f"Минимум для вывода: <b>15 ⭐</b>\n\n"
        f"{status}\n\nВыбери сумму:",
        reply_markup=kb, parse_mode="HTML"
    )

async def withdraw_amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    amount = float(query.data.split("_")[1])
    player = get_player(query.from_user.id)
    stars  = player.get("stars", 0.0)
    if stars < amount:
        await query.answer(f"❌ Недостаточно! У тебя {stars:.3f} ⭐", show_alert=True)
        return
    await query.answer()
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В меню", callback_data="back_main")]])
    await query.edit_message_text(
        f"✅ <b>Заявка принята!</b>\n\n"
        f"💎 Сумма: <b>{amount} ⭐</b>\n"
        f"📊 Баланс: <b>{stars:.3f} ⭐</b>\n\n"
        "Заявка отправлена на обработку!",
        reply_markup=kb, parse_mode="HTML"
    )


# ─── Рефералы ─────────────────────────────────
async def referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user   = query.from_user
    player = get_player(user.id)
    refs   = player.get("referrals", 0)
    stars  = player.get("stars", 0.0)
    link   = f"https://t.me/{BOT_USERNAME}?start=ref_{user.id}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Поделиться ссылкой", url=f"https://t.me/share/url?url={link}&text=Играй%20в%20Star%20Snake%20и%20зарабатывай%20звёзды!")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")],
    ])
    await query.edit_message_text(
        f"👥 <b>Пригласи друга — получи +{REF_BONUS} ⭐</b>\n\n"
        f"Твоя реферальная ссылка:\n"
        f"<code>{link}</code>\n\n"
        f"📊 Приглашено друзей: <b>{refs}</b>\n"
        f"⭐ Заработано на рефералах: <b>{refs * REF_BONUS:.1f} ⭐</b>\n"
        f"💰 Твой баланс: <b>{stars:.3f} ⭐</b>\n\n"
        "Поделись ссылкой — когда друг зайдёт в бота, тебе сразу придёт <b>+2 ⭐</b>!",
        reply_markup=kb, parse_mode="HTML"
    )


# ─── Личный кабинет ───────────────────────────
async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    user   = query.from_user
    player = get_player(user.id)
    stars     = player.get("stars", 0.0)
    lives     = player.get("lives", 0)
    games     = player.get("games_played", 0)
    withdrawn = player.get("stars_withdrawn", 0.0)
    refs      = player.get("referrals", 0)
    MIN       = 15.0
    needed    = max(0.0, MIN - stars)
    status    = "✅ Можно выводить!" if stars >= MIN else f"⏳ До вывода не хватает <b>{needed:.3f} ⭐</b>"

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]])
    await query.edit_message_text(
        f"👤 <b>Личный кабинет</b>\n"
        f"{'─'*26}\n\n"
        f"🎮 Игр сыграно: <b>{games}</b>\n"
        f"⭐ На счётчике: <b>{stars:.3f} ⭐</b>\n"
        f"❤️ Жизней куплено: <b>{lives}</b>\n"
        f"👥 Приглашено друзей: <b>{refs}</b>\n"
        f"💸 Выведено всего: <b>{withdrawn:.3f} ⭐</b>\n\n"
        f"{'─'*26}\n"
        f"{status}\n\n"
        f"📌 Минимум вывода: <b>15 ⭐</b>",
        reply_markup=kb, parse_mode="HTML"
    )


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
            f"✅ <b>Оплата прошла!</b>\n\n❤️ +5 жизней!\nТеперь у тебя: <b>{new_lives} ❤️</b>\n\n🐍 Заходи в игру!",
            parse_mode="HTML"
        )
    elif payload == "lives_10":
        new_lives = player["lives"] + 10
        update_player(user_id, {"lives": new_lives})
        await update.message.reply_text(
            f"✅ <b>Оплата прошла!</b>\n\n❤️ +10 жизней!\nТеперь у тебя: <b>{new_lives} ❤️</b>\n\n🐍 Заходи в игру!",
            parse_mode="HTML"
        )


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
    app.add_handler(CallbackQueryHandler(referral_callback,        pattern="^referral$"))
    app.add_handler(CallbackQueryHandler(profile_callback,         pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(back_main,                pattern="^back_main$"))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    print("✅ Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
