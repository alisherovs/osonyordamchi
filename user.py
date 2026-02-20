from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database as db
from config import ADMIN_IDS  # E'tibor bering, ADMIN_IDS chaqirilyapti
from states import CourierReg, CreateOrder, GroupReply, CourierReply

user_router = Router()

# ==========================================
# 🎛 TUGMALAR (KEYBOARDS)
# ==========================================
def get_user_main_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📦 Yangi buyurtma yuborish")]], resize_keyboard=True)

def get_cancel_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True)

def get_skip_cancel_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭ O'tkazib yuborish")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ], resize_keyboard=True
    )

def get_reasons_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1. Telga javob bermadi")],
            [KeyboardButton(text="2. Atkaz / puli yo'q")],
            [KeyboardButton(text="3. Manzilga chaqirib tel ko'tarmadi")],
            [KeyboardButton(text="4. Mahsulot to'g'ri kelmadi (yoqmadi)")],
            [KeyboardButton(text="5. Noto'g'ri nomer")],
            [KeyboardButton(text="✍️ Boshqa sabab")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ], resize_keyboard=True
    )

# ==========================================
# 👤 ASOSIY VA RO'YXATDAN O'TISH
# ==========================================
@user_router.message(F.text == "❌ Bekor qilish", StateFilter("*"))
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_user(message.from_user.id)
    await message.answer("🚫 Amal bekor qilindi.", reply_markup=get_user_main_menu() if user and user[0] == 'approved' else ReplyKeyboardRemove())

@user_router.message(CommandStart(), F.chat.type == "private")
async def start_cmd(message: Message, state: FSMContext):
    # 🛑 ADMINLARNI TO'SISH (Ular admin.py ga o'tadi)
    if message.from_user.id in ADMIN_IDS:
        return 

    await state.clear()
    user = await db.get_user(message.from_user.id)
    
    if not user:
        await message.answer("👋 Kuryerlar tizimiga xush kelibsiz.\n👤 <b>Ism va Familiyangizni kiriting:</b>", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        await state.set_state(CourierReg.full_name)
    elif user[0] == 'pending':
        await message.answer("⏳ Arizangiz ko'rib chiqilmoqda.")
    elif user[0] == 'rejected':
        await message.answer("❌ Arizangiz rad etilgan.")
    elif user[0] == 'approved':
        await message.answer(f"Salom, <b>{user[1]}</b>! 👋", parse_mode="HTML", reply_markup=get_user_main_menu())

@user_router.message(CourierReg.full_name, F.chat.type == "private")
async def reg_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("📱 <b>Telefon raqamingizni kiriting:</b>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)]], resize_keyboard=True))
    await state.set_state(CourierReg.phone)

@user_router.message(CourierReg.phone, F.chat.type == "private")
async def reg_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number if message.contact else message.text)
    await message.answer("📍 <b>Qaysi hududda ishlaysiz?</b>", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
    await state.set_state(CourierReg.region)

@user_router.message(CourierReg.region, F.chat.type == "private")
async def reg_region(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.add_user(message.from_user.id, data['full_name'], data['phone'], message.text)
    await message.answer("✅ Arizangiz adminga yuborildi. Tasdiqlanishini kuting.")
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash", callback_data=f"approve_{message.from_user.id}")
    builder.button(text="❌ Rad etish", callback_data=f"reject_{message.from_user.id}")
    
    # 🔄 Barcha adminlarga xabar yuborish
    for admin_id in ADMIN_IDS:
        try: 
            await message.bot.send_message(
                chat_id=admin_id, 
                text=f"🆕 <b>YANGI KURYER!</b>\n👤 {data['full_name']}\n📞 {data['phone']}\n📍 {message.text}", 
                reply_markup=builder.as_markup(), 
                parse_mode="HTML"
            )
        except Exception: 
            pass

# ==========================================
# 📦 BUYURTMA YUBORISH JARAYONI
# ==========================================
@user_router.message(F.text == "📦 Yangi buyurtma yuborish", F.chat.type == "private")
async def new_order(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or user[0] != 'approved': return
    
    groups = await db.get_all_groups()
    if not groups: return await message.answer("⚠️ Hozircha guruhlar mavjud emas.")
    
    builder = InlineKeyboardBuilder()
    for g in groups: 
        builder.button(text=f"🏢 {g[1]}", callback_data=f"sel_group_{g[0]}")
    builder.adjust(1)
    
    await message.answer("🏢 <b>Qaysi guruhga yuboramiz?</b>", reply_markup=builder.as_markup(), parse_mode="HTML")

@user_router.callback_query(F.data.startswith("sel_group_"))
async def select_group(call: CallbackQuery, state: FSMContext):
    group = await db.get_group_details(int(call.data.split("_")[2]))
    if not group: return await call.answer("Guruh topilmadi.", show_alert=True)
    
    await state.update_data(target_chat_id=group[1])
    await call.message.delete()
    await call.message.answer("📸 <b>1-qadam:</b> Mahsulot rasmini yuboring (yoki o'tkazib yuboring):", parse_mode="HTML", reply_markup=get_skip_cancel_menu())
    await state.set_state(CreateOrder.photo)

@user_router.message(CreateOrder.photo)
async def get_photo(message: Message, state: FSMContext):
    if message.text == "⏭ O'tkazib yuborish": 
        await state.update_data(photo_id=None)
    elif message.photo: 
        await state.update_data(photo_id=message.photo[-1].file_id)
    else: 
        return await message.answer("⚠️ Iltimos, rasm yuboring yoki o'tkazib yuborish tugmasini bosing.", reply_markup=get_skip_cancel_menu())
        
    await message.answer("🆔 <b>2-qadam:</b> Mahsulot ID/Nomini kiriting:", parse_mode="HTML", reply_markup=get_skip_cancel_menu())
    await state.set_state(CreateOrder.product_id)

@user_router.message(CreateOrder.product_id)
async def get_prod_id(message: Message, state: FSMContext):
    await state.update_data(product_id="Kiritilmagan" if message.text == "⏭ O'tkazib yuborish" else message.text)
    await message.answer("📱 <b>3-qadam:</b> Mijoz raqamini kiriting:", parse_mode="HTML", reply_markup=get_skip_cancel_menu())
    await state.set_state(CreateOrder.client_phone)

@user_router.message(CreateOrder.client_phone)
async def get_client_phone(message: Message, state: FSMContext):
    await state.update_data(client_phone="Kiritilmagan" if message.text == "⏭ O'tkazib yuborish" else message.text)
    await message.answer("📋 <b>4-qadam:</b> Holatni (sababni) tanlang:", parse_mode="HTML", reply_markup=get_reasons_menu())
    await state.set_state(CreateOrder.reason)

@user_router.message(CreateOrder.reason)
async def get_reason(message: Message, state: FSMContext):
    if message.text == "✍️ Boshqa sabab":
        await message.answer("📝 Sababni yozib yuboring yoki 🎤 <b>Ovozli xabar (Voice)</b> qoldiring:", parse_mode="HTML", reply_markup=get_cancel_menu())
        await state.set_state(CreateOrder.custom_reason)
        return
        
    await state.update_data(reason=message.text, voice_id=None)
    await generate_and_send_confirmation(message, state)

@user_router.message(CreateOrder.custom_reason, F.content_type.in_({'text', 'voice'}))
async def get_custom_reason(message: Message, state: FSMContext):
    if message.voice:
        await state.update_data(reason="🎤 Ovozli xabar orqali tushuntirilgan ⬇️", voice_id=message.voice.file_id)
    else:
        await state.update_data(reason=message.text, voice_id=None)
    await generate_and_send_confirmation(message, state)

async def generate_and_send_confirmation(message: Message, state: FSMContext):
    data = await state.get_data()
    user = await db.get_user(message.from_user.id)
    
    caption = (f"📦 <b>YANGI BUYURTMA HOLATI</b>\n━━━━━━━━━━━━\n"
               f"🆔 <b>Mahsulot:</b> {data['product_id']}\n"
               f"📱 <b>Tel:</b> {data['client_phone']}\n"
               f"⚠️ <b>Holat/Sabab:</b> {data['reason']}\n━━━━━━━━━━━━\n"
               f"🚚 <b>Kuryer:</b> {user[1]}\n📍 <b>Hudud:</b> {user[2]}")
    await state.update_data(final_caption=caption)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Yuborish", callback_data="send_order_now")
    builder.button(text="❌ Bekor qilish", callback_data="cancel_order_now")
    builder.adjust(2)
    
    temp_msg = await message.answer("⏳ Ma'lumotlar tayyorlanmoqda...", reply_markup=ReplyKeyboardRemove())
    await temp_msg.delete()
    
    if data.get('photo_id'):
        await message.answer_photo(photo=data['photo_id'], caption=f"📝 <b>Tekshiring:</b>\n\n{caption}", parse_mode="HTML", reply_markup=builder.as_markup())
    else:
        await message.answer(f"📝 <b>Tekshiring:</b>\n\n{caption}", parse_mode="HTML", reply_markup=builder.as_markup())
    
    if data.get('voice_id'):
        await message.answer_voice(voice=data['voice_id'], caption="🎤 <i>Sizning ovozli sababingiz</i>", parse_mode="HTML")
        
    await state.set_state(CreateOrder.confirm)

@user_router.callback_query(F.data == "send_order_now", CreateOrder.confirm)
async def send_order(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    markup = InlineKeyboardBuilder()
    markup.button(text="💬 Javob berish", callback_data="reply_to_order")
    
    try:
        # 1. Asosiy rasm yoki matnni guruhga yuborish
        if data.get('photo_id'):
            msg = await call.bot.send_photo(chat_id=data['target_chat_id'], photo=data['photo_id'], caption=data['final_caption'], parse_mode="HTML", reply_markup=markup.as_markup())
        else:
            msg = await call.bot.send_message(chat_id=data['target_chat_id'], text=data['final_caption'], parse_mode="HTML", reply_markup=markup.as_markup())
            
        # 2. Agar kuryer ovozli xabar qoldirgan bo'lsa, xuddi shu xabarga 'Reply' qilib yuborish
        if data.get('voice_id'):
            await call.bot.send_voice(chat_id=data['target_chat_id'], voice=data['voice_id'], reply_to_message_id=msg.message_id)
            
        await call.bot.pin_chat_message(data['target_chat_id'], msg.message_id)
        await db.save_order_msg(msg.message_id, msg.chat.id, call.from_user.id)
        
        await call.message.delete()
        await call.message.answer("✅ Yuborildi va qadaldi!", reply_markup=get_user_main_menu())
    except Exception as e:
        await call.message.answer("❌ Guruhga yuborib bo'lmadi. Bot guruhda ADMIN ekanligini tekshiring!", reply_markup=get_user_main_menu())
    await state.clear()

@user_router.callback_query(F.data == "cancel_order_now", CreateOrder.confirm)
async def cancel_order(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer("🚫 Bekor qilindi.", reply_markup=get_user_main_menu())
    await state.clear()


# ==========================================
# 🔄 GURUHDA JAVOB BERISH TIZIMI (ADMIN -> KURYER)
# ==========================================
@user_router.callback_query(F.data == "reply_to_order")
async def btn_reply(call: CallbackQuery, state: FSMContext):
    orig_msg = call.message
    courier_id = await db.get_courier_by_msg(orig_msg.chat.id, orig_msg.message_id)
    if not courier_id: return await call.answer("❌ Kuryer topilmadi.", show_alert=True)
    
    orig_text = orig_msg.caption or orig_msg.text or ""
    photo_id = orig_msg.photo[-1].file_id if orig_msg.photo else None
    prod_id = "Noma'lum"
    if "🆔 Mahsulot:" in orig_text:
        try: prod_id = orig_text.split("🆔 Mahsulot:")[1].split("\n")[0].strip()
        except IndexError: pass 
        
    await state.update_data(target_courier_id=courier_id, product_id=prod_id, photo_id=photo_id)
    await state.set_state(GroupReply.reply_text)
    await call.message.reply(f"✍️ <b>{call.from_user.full_name}</b>, javobingizni yozing yoki 🎤 ovozli xabar yuboring:", parse_mode="HTML")
    await call.answer()

@user_router.message(GroupReply.reply_text, F.chat.type.in_(['group', 'supergroup']))
async def catch_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    await send_reply_to_courier(message, data.get('target_courier_id'), data.get('product_id', "Noma'lum"), data.get('photo_id'))
    await state.clear()

@user_router.message(F.chat.type.in_(['group', 'supergroup']), F.reply_to_message)
async def native_reply(message: Message):
    if message.pinned_message: return
    orig_msg = message.reply_to_message
    courier_id = await db.get_courier_by_msg(message.chat.id, orig_msg.message_id)
    
    if courier_id:
        orig_text = orig_msg.caption or orig_msg.text or ""
        photo_id = orig_msg.photo[-1].file_id if orig_msg.photo else None
        prod_id = "Noma'lum"
        if "🆔 Mahsulot:" in orig_text:
            try: prod_id = orig_text.split("🆔 Mahsulot:")[1].split("\n")[0].strip()
            except IndexError: pass
        await send_reply_to_courier(message, courier_id, prod_id, photo_id)

async def send_reply_to_courier(message: Message, courier_id: int, prod_id: str, photo_id: str = None):
    caption = (f"🔔 <b>Buyurtmangizga adminga javob keldi!</b>\n"
               f"━━━━━━━━━━━━\n"
               f"🆔 <b>Mahsulot:</b> {prod_id}\n"
               f"👤 <b>Javob berdi:</b> {message.from_user.full_name}\n"
               f"👇 <i>Javob quyida:</i>")
    
    markup = InlineKeyboardBuilder()
    markup.button(text="💬 Qayta javob berish", callback_data=f"creply_{message.chat.id}")
    
    try:
        # 1. Kuryerga mahsulot rasmi va xabarnomani yuboramiz
        if photo_id:
            info_msg = await message.bot.send_photo(chat_id=courier_id, photo=photo_id, caption=caption, parse_mode="HTML", reply_markup=markup.as_markup())
        else:
            info_msg = await message.bot.send_message(chat_id=courier_id, text=caption, parse_mode="HTML", reply_markup=markup.as_markup())
            
        # 2. Guruh a'zosining ASIL xabarini (matn, ovoz, rasm) nusxalab yuboramiz
        await message.bot.copy_message(chat_id=courier_id, from_chat_id=message.chat.id, message_id=message.message_id, reply_to_message_id=info_msg.message_id)
        await message.reply("✅ Kuryerga muvaffaqiyatli yetkazildi.")
    except Exception: pass


# ==========================================
# 🔄 KURYER QAYTA ALOQAGA CHIQISHI (KURYER -> ADMIN)
# ==========================================
@user_router.callback_query(F.data.startswith("creply_"))
async def courier_btn_reply(call: CallbackQuery, state: FSMContext):
    group_chat_id = call.data.split("_")[1]
    
    orig_text = call.message.caption or call.message.text or ""
    prod_id = "Noma'lum"
    if "🆔 Mahsulot:" in orig_text:
        try: prod_id = orig_text.split("🆔 Mahsulot:")[1].split("\n")[0].strip()
        except IndexError: pass 
        
    await state.update_data(target_group_id=group_chat_id, product_id=prod_id)
    await state.set_state(CourierReply.reply_text)
    
    await call.message.reply(f"✍️ <b>ID: {prod_id}</b> uchun javobingizni yozing yoki 🎤 ovozli xabar yuboring:", parse_mode="HTML", reply_markup=get_cancel_menu())
    await call.answer()

@user_router.message(CourierReply.reply_text, F.chat.type == "private")
async def catch_courier_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    prod_id = data.get('product_id', "Noma'lum")
    group_id = data.get('target_group_id')
    
    caption = (f"🔄 <b>Kuryerdan qayta javob keldi!</b>\n"
               f"━━━━━━━━━━━━\n"
               f"🆔 <b>Mahsulot:</b> {prod_id}\n"
               f"👤 <b>Kuryer:</b> {message.from_user.full_name}\n"
               f"👇 <i>Qayta javob quyida:</i>")
    
    try:
        # Guruhga ma'lumotni tashlaymiz
        info_msg = await message.bot.send_message(chat_id=group_id, text=caption, parse_mode="HTML")
        
        # Kuryerning o'zi yuborgan (ovoz, matn, video) xabarni guruhga Reply qilib uzatamiz
        await message.bot.copy_message(chat_id=group_id, from_chat_id=message.chat.id, message_id=message.message_id, reply_to_message_id=info_msg.message_id)
        
        await message.reply("✅ Javobingiz guruhga muvaffaqiyatli yuborildi.", reply_markup=get_user_main_menu())
    except Exception as e:
        await message.reply(f"❌ Xatolik yuz berdi. Iltimos adminga murojaat qiling.\nXato: {e}", reply_markup=get_user_main_menu())
    
    await state.clear()