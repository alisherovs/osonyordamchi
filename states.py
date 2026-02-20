from aiogram.fsm.state import State, StatesGroup

class CourierReg(StatesGroup):
    full_name = State()
    phone = State()
    region = State()

class AdminAddGroup(StatesGroup):
    name = State()
    chat_id = State()

class CreateOrder(StatesGroup):
    photo = State()
    product_id = State()
    client_phone = State()
    reason = State()          
    custom_reason = State()  
    confirm = State()  

class GroupReply(StatesGroup):
    reply_text = State()


class CourierReply(StatesGroup):
    reply_text = State()