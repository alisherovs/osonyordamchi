from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database as db
from config import ADMIN_IDS
from states import AdminAddGroup

admin_router = Router()

# 🛑 ENG ASOSIY TO'G'RILANISH: Ro'yxatni tekshirish uchun .in_() ishlatiladi!
admin_router.message.filter(F.from_user.id.in_(ADMIN_IDS))
admin_router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))

# ==========================================
# 🎛 TUGMALAR (KEYBOARDS)
# ==========================================
def get_admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Guruh qo'shish"), KeyboardButton(text="🏢 Guruhlar")],
            [KeyboardButton(text="🚚 Kuryerlar ro'yxati"), KeyboardButton(text="📊 Statistika")]
        ], resize_keyboard=True
    )

def get_cancel_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], 
        resize_keyboard=True
    )

# ==========================================
# 👨‍💻 ASOSIY MENU VA BEKOR QILISH
# ==========================================
@admin_router.message(CommandStart())
@admin_router.message(Command("admin"))
async def admin_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("👋 Assalomu alaykum, \n👨‍💻 <b>Bot boshqaruv paneliga xush kelibsiz.</b>", parse_mode="HTML", reply_markup=get_admin_menu())

@admin_router.message(F.text == "❌ Bekor qilish", StateFilter("*"))
async def cancel_action(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🚫 Amal bekor qilindi.", reply_markup=get_admin_menu())

# ==========================================
# ➕ GURUH QO'SHISH TIZIMI
# ==========================================
@admin_router.message(F.text == "➕ Guruh qo'shish")
async def add_group_start(message: Message, state: FSMContext):
    await message.answer("🏢 <b>Yangi guruh uchun nom kiriting:</b>\n<i>(Masalan: Toshkent Filiali)</i>", parse_mode="HTML", reply_markup=get_cancel_menu())
    await state.set_state(AdminAddGroup.name)

@admin_router.message(AdminAddGroup.name)
async def add_group_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("🔗 <b>Endi guruh ID raqamini yoki linkini kiriting:</b>\n<i>(Masalan: -100123456789)</i>", parse_mode="HTML", reply_markup=get_cancel_menu())
    await state.set_state(AdminAddGroup.chat_id)

@admin_router.message(AdminAddGroup.chat_id)
async def add_group_chat_id(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        await db.add_group(data['name'], message.text)
        await message.answer(f"✅ <b>Guruh qo'shildi!</b>\n\n🏷 Nomi: {data['name']}\n🆔 ID: {message.text}", parse_mode="HTML", reply_markup=get_admin_menu())
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi:\n{e}", reply_markup=get_admin_menu())
    await state.clear()

# ==========================================
# 👥 KURYER TASDIQLASH VA RAD ETISH
# ==========================================
@admin_router.callback_query(F.data.startswith("approve_") | F.data.startswith("reject_"))
async def handle_approval(call: CallbackQuery):
    action, user_id = call.data.split("_")[0], int(call.data.split("_")[1])
    
    if action == "approve":
        await db.update_user_status(user_id, "approved")
        await call.message.edit_text(call.message.html_text + "\n\n✅ <b>Tasdiqlandi!</b>", parse_mode="HTML", reply_markup=None)
        try:
            await call.bot.send_message(user_id, "🎉 <b>Tabriklaymiz!</b> Arizangiz tasdiqlandi! /start ni bosing.", parse_mode="HTML")
        except: pass
    else:
        await db.update_user_status(user_id, "rejected")
        await call.message.edit_text(call.message.html_text + "\n\n❌ <b>Rad etildi!</b>", parse_mode="HTML", reply_markup=None)
        try:
            await call.bot.send_message(user_id, "❌ Kechirasiz, arizangiz rahbariyat tomonidan rad etildi.")
        except: pass
        
    await call.answer()

# ==========================================
# 🚚 KURYERLARNI BOSHQARISH
# ==========================================
async def send_couriers_list(message: Message, is_edit=False):
    couriers = await db.get_all_couriers()
    if not couriers:
        return await (message.edit_text if is_edit else message.answer)("🤷‍♂️ Tizimda tasdiqlangan kuryerlar yo'q.")
        
    builder = InlineKeyboardBuilder()
    for c in couriers: 
        builder.button(text=f"👤 {c[1]}", callback_data=f"c_view_{c[0]}")
    builder.adjust(1)
    
    text = "🚚 <b>Kuryerlar ro'yxati:</b>\n<i>Batafsil ma'lumot uchun kuryerni tanlang:</i>"
    if is_edit:
        await message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@admin_router.message(F.text == "🚚 Kuryerlar ro'yxati")
async def show_couriers(message: Message): 
    await send_couriers_list(message)

@admin_router.callback_query(F.data == "back_to_couriers")
async def back_couriers(call: CallbackQuery): 
    await send_couriers_list(call.message, True)

@admin_router.callback_query(F.data.startswith("c_view_"))
async def view_courier(call: CallbackQuery):
    user_id = int(call.data.split("_")[2])
    user = await db.get_user_details(user_id)
    
    if not user:
        return await call.answer("Kuryer topilmadi!", show_alert=True)
        
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Chetlatish", callback_data=f"c_del_{user_id}")
    builder.button(text="⬅️ Ortga", callback_data="back_to_couriers")
    builder.adjust(1, 1)
    
    await call.message.edit_text(f"📋 <b>Kuryer ma'lumotlari:</b>\n\n👤 Ism: {user[0]}\n📞 Tel: {user[1]}\n📍 Hudud: {user[2]}", reply_markup=builder.as_markup(), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("c_del_"))
async def del_courier(call: CallbackQuery):
    user_id = int(call.data.split("_")[2])
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, chetlatish", callback_data=f"c_confirm_{user_id}")
    builder.button(text="❌ Bekor qilish", callback_data=f"c_view_{user_id}")
    builder.adjust(1, 1)
    await call.message.edit_text("⚠️ <b>Ushbu kuryerni rostdan ham chetlatmoqchimisiz?</b>", reply_markup=builder.as_markup(), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("c_confirm_"))
async def exec_del_courier(call: CallbackQuery):
    user_id = int(call.data.split("_")[2])
    await db.delete_courier(user_id)
    await call.answer("✅ Kuryer tizimdan chetlatildi!", show_alert=True)
    await send_couriers_list(call.message, True)

# ==========================================
# 🏢 GURUHLARNI BOSHQARISH
# ==========================================
async def send_groups_list(message: Message, is_edit=False):
    groups = await db.get_all_groups()
    if not groups:
        return await (message.edit_text if is_edit else message.answer)("🤷‍♂️ Tizimda ulangan guruhlar yo'q.")
        
    builder = InlineKeyboardBuilder()
    for g in groups: 
        builder.button(text=f"🏢 {g[1]}", callback_data=f"g_view_{g[0]}")
    builder.adjust(1)
    
    text = "🏢 <b>Guruhlar ro'yxati:</b>\n<i>Batafsil ko'rish uchun tanlang:</i>"
    if is_edit:
        await message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@admin_router.message(F.text == "🏢 Guruhlar")
async def show_groups(message: Message): 
    await send_groups_list(message)

@admin_router.callback_query(F.data == "back_to_groups")
async def back_groups(call: CallbackQuery): 
    await send_groups_list(call.message, True)

@admin_router.callback_query(F.data.startswith("g_view_"))
async def view_group(call: CallbackQuery):
    group_id = int(call.data.split("_")[2])
    group = await db.get_group_details(group_id)
    
    if not group:
        return await call.answer("Guruh topilmadi!", show_alert=True)
        
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 O'chirish", callback_data=f"g_del_{group_id}")
    builder.button(text="⬅️ Ortga", callback_data="back_to_groups")
    builder.adjust(1, 1)
    
    await call.message.edit_text(f"📋 <b>Guruh ma'lumotlari:</b>\n\n🏷 Nomi: {group[0]}\n🆔 ID: {group[1]}", reply_markup=builder.as_markup(), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("g_del_"))
async def del_group(call: CallbackQuery):
    group_id = int(call.data.split("_")[2])
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, o'chirish", callback_data=f"g_confirm_{group_id}")
    builder.button(text="❌ Bekor qilish", callback_data=f"g_view_{group_id}")
    builder.adjust(1, 1)
    await call.message.edit_text("⚠️ <b>Ushbu guruhni rostdan ham o'chirmoqchimisiz?</b>", reply_markup=builder.as_markup(), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("g_confirm_"))
async def exec_del_group(call: CallbackQuery):
    group_id = int(call.data.split("_")[2])
    await db.delete_group(group_id)
    await call.answer("✅ Guruh tizimdan o'chirildi!", show_alert=True)
    await send_groups_list(call.message, True)

# ==========================================
# 📊 STATISTIKA BO'LIMI
# ==========================================
@admin_router.message(F.text == "📊 Statistika")
async def stats(message: Message):
    couriers = await db.get_all_couriers()
    groups = await db.get_all_groups()
    
    c_count = len(couriers) if couriers else 0
    g_count = len(groups) if groups else 0
    
    text = (
        "📊 <b>Tizim statistikasi:</b>\n\n"
        f"🚚 Faol kuryerlar soni: <b>{c_count} ta</b>\n"
        f"🏢 Ulangan guruhlar: <b>{g_count} ta</b>"
    )
    await message.answer(text, parse_mode="HTML")