from aiogram.fsm.state import State, StatesGroup

class UserProfile(StatesGroup):
    gender = State()
    age = State()
    height = State()
    weight = State()
    target_weight = State()
    activity = State()
    confirm = State()

class MealAdd(StatesGroup):
    photo = State()
    confirm = State()

class Settings(StatesGroup):
    field = State()
    value = State()
