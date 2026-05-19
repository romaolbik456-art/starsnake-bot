import logging
import random
import asyncio
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8635694534:AAHxYWfNaUCpUUkcF9v60plWlD5b0Ol0HDc"

logging.basicConfig(level=logging.INFO)

# ─── Слоги для генерации ──────────────────────
SYLLABLES = [
    'ba','be','bi','bo','bu','bra','bre','bro',
    'ca','co','cu','cra','cro','cru',
    'da','de','di','do','dra','dro','dru',
    'fa','fe','fi','fo','fla','flo','flu',
    'ga','ge','go','gu','gra','gre','gro',
    'ha','he','hi','ho','hu',
    'ka','ke','ki','ko','ku',
    'la','le','li','lo','lu',
    'ma','me','mi','mo','mu',
    'na','ne','ni','no','nu',
    'pa','pe','pi','po','pro','pra',
    'ra','re','ri','ro','ru',
    'sa','se','si','so','su','sha','sho',
    'sta','ste','sto','stu','stra','stro',
    'ta','te','ti','to','tu','tra','tro',
    'va','ve','vi','vo',
    'wa','we','wo',
    'ya','ye','yo','yu',
    'za','ze','zo','zu',
    'al','el','il','ol','ul',
    'ar','er','or','ur',
    'an','en','in','on','un',
]

def gen_word(length: int) -> str:
    """Генерирует читаемое слово точно нужной длины"""
    for _ in range(200):
        word = ''
        while len(word) < length + 2:
            word += random.choice(SYLLABLES)
        # Обрезаем точно до нужной длины
        word = word[:length]
        if len(word) == length and word.isalpha():
            return word.lower()
    # Запасной вариант — просто слоги
    word = ''
    while len(word) < length:
        s = random.choice(SYLLABLES)
        if len(word) + len(s) <= length:
            word += s
    while len(word) < length:
        word += random.choice('aeioursntlm')
    return word[:length].lower()

async def is_free(username: str, bot) -> bool:
    """Проверка через Telegram API и Fragment"""
    # 1. Telegram API
    try:
        await bot.get_chat(f"@{username}")
        return False  # занят
    except Exception as e:
        err = str(e).lower()
        occupied = ("chat not found" not in err and
                    "username not found" not in err and
                    "invalid username" not in err and
                    "peer_id_invalid" not in err)
        if occupied:
            return False

    # 2. Fragment
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"https://fragment.com/username/{username}",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=aiohttp.ClientTimeout(total=7)
            ) as r:
                text = await r.text()
                bad = ["ton_price", "Buy for", "Place a bid",
                       "Unavailable", "unavailable", "auction"]
                if any(x in text for x in bad):
                    return False
    except:
        return False

    return True

async def find_usernames(length: int, bot, count: int = 3) -> list:
    """Ищет свободные юзернеймы нужной длины"""
    found = []
    tried = set()
    rounds = 0
    while len(found) < count and rounds < 50:
        rounds += 1
        # Генерим 4 варианта сразу
        candidates = []
        for _ in range(4):
            w = gen_word(length)
            if w not in tried:
                tried.add(w)
                candidates.append(w)

        # Проверяем параллельно
        tasks = [is_free(w, bot) for w in candidates]
        results = await asyncio.gather(*tasks)
        for w, free in zip(candidates, results):
            if free and w not in found:
                found.append(w)
                if len(found) >= count:
                    break
        await asyncio.sleep(0.3)
    return found

# ─── Handlers ─────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔤 Найти свободный юз", callback_data="find_menu")]
    ])
    await update.message.reply_text(
        "👋 Привет!\n\nЯ помогу найти свободный юзернейм в Telegram!",
        reply_markup=kb
    )

async def find_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("5️⃣ Юз из 5 букв", callback_data="find_5")],
        [InlineKeyboardButton("6️⃣ Юз из 6 букв", callback_data="find_6")],
        [InlineKeyboardButton("7️⃣ Юз из 7 букв", callback_data="find_7")],
    ])
    await query.edit_message_text(
        "🔤 <b>Поиск свободного юзернейма</b>\n\nВыбери сколько букв:",
        reply_markup=kb, parse_mode="HTML"
    )

async def find_by_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    length = int(query.data.split("_")[1])

    kb_back = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Искать ещё", callback_data=f"find_{length}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="find_menu")],
    ])

    await query.edit_message_text(
        f"🔍 Ищу свободные юзернеймы из <b>{length} букв</b>...\n"
        "⏳ Подожди немного, проверяю Telegram и Fragment!",
        parse_mode="HTML"
    )

    usernames = await find_usernames(length, context.bot, count=3)

    if usernames:
        lines = "\n".join([f"✅ <code>@{u}</code>" for u in usernames])
        text = (
            f"🎉 <b>Найдено {len(usernames)} свободных юза из {length} букв:</b>\n\n"
            f"{lines}\n\n"
            f"⚡️ Регистрируй быстро — могут занять!\n"
            f"💡 Нажми на юзернейм чтобы скопировать"
        )
    else:
        text = (
            f"😔 Не удалось найти свободные юзернеймы из {length} букв.\n\n"
            "Попробуй ещё раз!"
        )

    await query.edit_message_text(text, reply_markup=kb_back, parse_mode="HTML")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(find_menu,       pattern="^find_menu$"))
    app.add_handler(CallbackQueryHandler(find_by_length,  pattern="^find_(5|6|7)$"))
    print("✅ Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
