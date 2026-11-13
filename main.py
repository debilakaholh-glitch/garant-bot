import asyncio
import random
import string
import os
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- НАСТРОЙКИ ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "9278766476:AAEPrRJ_iniLMnqBZ-Flh4jrNnOqv80r1_4")
BOT_USERNAME = "TrusstDealBot"  # <--- ТВОЙ НИК ВСТАВЛЕН СЮДА
GUARANT_ID = 5666389646         # <--- ТВОЙ ID ВСТАВЛЕН СЮДА

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

users_db = {}
deals_db = {} 

class DealState(StatesGroup):
    waiting_role = State()
    waiting_item = State()
    waiting_payment_method = State()
    waiting_amount = State()
    waiting_contact = State()

def generate_deal_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👛 Добавить/изменить кошелёк", callback_data="wallet")],
        [InlineKeyboardButton(text="📄 Создать сделку", callback_data="create_deal")],
        [InlineKeyboardButton(text="🔗 Реферальная ссылка", callback_data="ref_link")],
        [InlineKeyboardButton(text="🌐 Сменить язык", callback_data="change_lang")],
        [InlineKeyboardButton(text="📞 Поддержка", url="https://t.me/your_support")]
    ])

def get_role_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Я Покупатель", callback_data="role_buyer")],
        [InlineKeyboardButton(text="📦 Я Продавец", callback_data="role_seller")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ])

def get_payment_methods_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇦 Укр карты", callback_data="pay_Укр карты")],
        [InlineKeyboardButton(text="🇷🇺 РФ карты", callback_data="pay_РФ карты")],
        [InlineKeyboardButton(text="⭐ Звезды", callback_data="pay_Звезды")],
        [InlineKeyboardButton(text="💎 Тоны", callback_data="pay_Тоны")],
        [InlineKeyboardButton(text="🌍 Межд. карты", callback_data="pay_Межд. карты")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_item")]
    ])

def back_to_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")]])

START_TEXT = "🛡 <b>P2P-Гарант</b>\n\nБезопасные сделки.\nВыберите раздел:"

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandStart):
    await state.clear()
    user_id = message.from_user.id
    if user_id not in users_db:
        users_db[user_id] = {"ref_count": 0, "ref_earned": 0.0}

    payload = command.args
    if payload and payload.startswith("deal_"):
        deal_id = payload.replace("deal_", "")
        if deal_id in deals_db:
            deal = deals_db[deal_id]
            
            if deal['role_creator'] == "Покупатель":
                deal['seller_id'] = user_id
                deal['seller_username'] = message.from_user.username
            else:
                deal['buyer_id'] = user_id
                deal['buyer_username'] = message.from_user.username
                
            await message.answer(f"✅ Вы успешно подключены к сделке <code>{deal_id}</code>!\n\nОжидайте карточку заказа.")
            try:
                await bot.send_message(deal['creator_id'], f"🔔 Вторая сторона подключилась к сделке <code>{deal_id}</code>!")
            except: pass
            
            if deal['role_creator'] == "Продавец":
                await send_deal_card(deal['buyer_id'], deal_id)
            return

    await message.answer(START_TEXT, reply_markup=get_main_menu())

@dp.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(START_TEXT, reply_markup=get_main_menu())
    await callback.answer()

@dp.callback_query(F.data == "create_deal")
async def start_deal(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DealState.waiting_role)
    await callback.message.edit_text("👤 <b>Шаг 1 из 5</b>\n\nКем вы являетесь?", reply_markup=get_role_kb())

@dp.callback_query(DealState.waiting_role, F.data.startswith("role_"))
async def process_role(callback: CallbackQuery, state: FSMContext):
    role = "Покупатель" if callback.data == "role_buyer" else "Продавец"
    await state.update_data(role=role)
    await state.set_state(DealState.waiting_item)
    await callback.message.edit_text(f"✅ Роль: <b>{role}</b>\n\n📝 <b>Шаг 2 из 5</b>\nВведите предмет сделки:")

@dp.message(DealState.waiting_item)
async def process_item(message: Message, state: FSMContext):
    await state.update_data(item=message.text)
    await state.set_state(DealState.waiting_payment_method)
    await message.answer("💳 <b>Шаг 3 из 5</b>\nВыберите способ оплаты:", reply_markup=get_payment_methods_kb())

@dp.callback_query(DealState.waiting_payment_method, F.data.startswith("pay_"))
async def process_payment_method(callback: CallbackQuery, state: FSMContext):
    method = callback.data.replace("pay_", "")
    await state.update_data(payment_method=method)
    await state.set_state(DealState.waiting_amount)
    await callback.message.edit_text(f"✅ Выбрано: <b>{method}</b>\n\n💰 <b>Шаг 4 из 5</b>\nВведите сумму:")

@dp.message(DealState.waiting_amount)
async def process_amount(message: Message, state: FSMContext):
    await state.update_data(amount=message.text)
    await state.set_state(DealState.waiting_contact)
    data = await state.get_data()
    role_text = "ПРОДАВЦА" if data['role'] == "Покупатель" else "ПОКУПАТЕЛЯ"
    await message.answer(f"👤 <b>Шаг 5 из 5</b>\nВведите @username <b>{role_text}</b>:")

@dp.message(DealState.waiting_contact)
async def process_contact(message: Message, state: FSMContext):
    contact = message.text.replace("@", "") 
    data = await state.get_data()
    await state.clear()
    
    deal_id = generate_deal_id()
    deals_db[deal_id] = {
        "creator_id": message.from_user.id,
        "role_creator": data['role'],
        "item": data['item'],
        "payment_method": data['payment_method'],
        "amount": data['amount'],
        "contact_username": contact,
        "buyer_id": message.from_user.id if data['role'] == "Покупатель" else None,
        "buyer_username": message.from_user.username if data['role'] == "Покупатель" else contact,
        "seller_id": message.from_user.id if data['role'] == "Продавец" else None,
        "seller_username": message.from_user.username if data['role'] == "Продавец" else contact,
        "status": "waiting_payment"
    }
    
    deal_text = f"⚠️ Чтобы вторая сторона подтвердила сделку, отправьте ей эту ссылку:\n<code>https://t.me/{BOT_USERNAME}?start=deal_{deal_id}</code>"
    await message.answer(deal_text, reply_markup=back_to_menu_kb())
    if data['role'] == "Покупатель":
        await send_deal_card(message.from_user.id, deal_id)

async def send_deal_card(user_id, deal_id):
    deal = deals_db.get(deal_id)
    if not deal: return
    buyer_username = f"@{deal['buyer_username']}" if deal['buyer_username'] else "Ожидание..."
    buyer_id_str = str(deal['buyer_id']) if deal['buyer_id'] else "Неизвестно"
    card_text = (
        f"🎁 Сделка <code>{deal_id}</code>\n"
        f"{deal['item']}\n\n"
        f"💰 Сумма: {deal['amount']} {deal['payment_method']}\n"
        f"👤 Покупатель: {buyer_username}\n"
        f"{buyer_id_str}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"buyer_pay_{deal_id}")]])
    try: await bot.send_message(user_id, card_text, reply_markup=kb)
    except: pass

@dp.callback_query(F.data.startswith("buyer_pay_"))
async def buyer_pay(callback: CallbackQuery):
    deal_id = callback.data.split("_")[2]
    deal = deals_db.get(deal_id)
    if not deal: return
    deal['status'] = "paid_by_buyer"
    done_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⏳ Ожидайте подтверждения гаранта", callback_data="noop")]])
    await callback.message.edit_reply_markup(reply_markup=done_kb)
    if GUARANT_ID:
        try:
            admin_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Деньги у меня (Начать сделку)", callback_data=f"admin_paid_{deal_id}")]])
            await bot.send_message(GUARANT_ID, f"🔥 <b>Покупатель нажал «Подтвердить оплату» по сделке {deal_id}!</b>\n\nПроверьте поступление средств ({deal['amount']} {deal['payment_method']}).", reply_markup=admin_kb)
        except: pass
    await callback.answer("Вы подтвердили оплату! Ожидайте проверки гарантом.", show_alert=True)

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != GUARANT_ID: return 
    if not deals_db:
        await message.answer("Сделок пока нет.")
        return
    await message.answer("👑 <b>Панель гаранта:</b>")
    for deal_id, d in deals_db.items():
        text = f"Сделка <code>{deal_id}</code> | {d['status']} | {d['amount']} {d['payment_method']}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Деньги у меня", callback_data=f"admin_paid_{deal_id}")],
            [InlineKeyboardButton(text="💸 Перевести продавцу", callback_data=f"admin_finish_{deal_id}")]
        ])
        await message.answer(text, reply_markup=kb)

@dp.callback_query(F.data.startswith("admin_paid_"))
async def admin_paid(callback: CallbackQuery):
    if callback.from_user.id != GUARANT_ID: return
    deal_id = callback.data.split("_")[2]
    deal = deals_db.get(deal_id)
    if not deal: return
    deal['status'] = "paid_to_guarant"
    buyer_text = f"✅ <b>Гарант подтвердил получение ваших денег!</b>\n\nОжидайте, когда продавец передаст вам предмет ({deal['item']})."
    seller_text = f"💰 <b>Покупатель успешно оплатил заказ!</b>\n\nПередайте ему NFT ({deal['item']}), чтобы вам пришла валюта ({deal['payment_method']} - {deal['amount']}).\n\n⚠️ Как только передадите — нажмите кнопку ниже."
    kb_seller = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎁 Я передал NFT", callback_data=f"seller_done_{deal_id}")]])
    if deal['buyer_id']:
        try: await bot.send_message(deal['buyer_id'], buyer_text)
        except: pass
    if deal['seller_id']:
        try: await bot.send_message(deal['seller_id'], seller_text, reply_markup=kb_seller)
        except: pass
    await callback.message.edit_text(f"✅ Вы подтвердили оплату по сделке {deal_id}. Стороны уведомлены.")
    await callback.answer()

@dp.callback_query(F.data.startswith("seller_done_"))
async def seller_done(callback: CallbackQuery):
    deal_id = callback.data.split("_")[2]
    deal = deals_db.get(deal_id)
    if not deal: return
    deal['status'] = "gift_transferred"
    buyer_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Подтвердить получение", callback_data=f"buyer_confirm_{deal_id}")]])
    if deal['buyer_id']:
        try: await bot.send_message(deal['buyer_id'], f"📦 Продавец передал вам NFT по сделке <code>{deal_id}</code>.\n\nПроверьте и подтвердите получение:", reply_markup=buyer_kb)
        except: pass
    await callback.message.edit_text("✅ Вы сообщили, что передали NFT. Ожидайте подтверждения от покупателя.")
    await callback.answer()

@dp.callback_query(F.data.startswith("buyer_confirm_"))
async def buyer_confirm(callback: CallbackQuery):
    deal_id = callback.data.split("_")[2]
    deal = deals_db.get(deal_id)
    if not deal: return
    deal['status'] = "completed"
    if GUARANT_ID:
        try: await bot.send_message(GUARANT_ID, f"🔥 <b>Покупатель подтвердил получение NFT по сделке {deal_id}!</b>\n\nПора перевести {deal['amount']} ({deal['payment_method']}) продавцу.")
        except: pass
    await callback.message.edit_text("✅ Спасибо! Вы подтвердили получение. Ожидайте, гарант переведет деньги продавцу.")
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_finish_"))
async def admin_finish(callback: CallbackQuery):
    if callback.from_user.id != GUARANT_ID: return
    deal_id = callback.data.split("_")[2]
    deal = deals_db.get(deal_id)
    if not deal: return
    deal['status'] = "finished"
    if deal['seller_id']:
        try: await bot.send_message(deal['seller_id'], f"🎉 <b>Сделка {deal_id} завершена!</b>\n\nГарант перевел вам {deal['amount']} ({deal['payment_method']}).")
        except: pass
    if deal['buyer_id']:
        try: await bot.send_message(deal['buyer_id'], f"🎉 <b>Сделка {deal_id} завершена!</b>\n\nСпасибо за использование!")
        except: pass
    await callback.message.edit_text(f"✅ Сделка {deal_id} закрыта.")
    await callback.answer()

# ==========================================
# ФЕЙКОВЫЙ ВЕБ-СЕРВЕР ДЛЯ RENDER
# ==========================================
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_fake_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    t = Thread(target=run_fake_server)
    t.daemon = True
    t.start()
    asyncio.run(main())
