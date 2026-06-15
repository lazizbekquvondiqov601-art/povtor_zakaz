from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    choosing_name = State()
    changing_name = State()
    filter_category = State()
    filter_subcategory = State()

class AdminStates(StatesGroup):
    waiting_block_id = State()
    waiting_unblock_id = State()
    waiting_allow_id = State()
    waiting_disallow_id = State()

class SettingsManagement(StatesGroup):
    waiting_for_new_value = State()
    choosing_setting = State()

class SupplierSearch(StatesGroup):
    waiting_query = State()
