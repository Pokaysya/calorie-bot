from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.config import WEBAPP_URL

def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='📊 Мой профиль', callback_data='profile')
    builder.button(text='🍽 Добавить еду', callback_data='add_meal')
    builder.button(text='📈 Статистика', callback_data='stats')
    builder.button(text='⚙️ Настройки', callback_data='settings')
    if WEBAPP_URL:
        builder.button(text='🌐 Открыть приложение', web_app=WebAppInfo(url=WEBAPP_URL))
    builder.adjust(2, 2, 1)
    return builder.as_markup()

def gender_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='Мужской', callback_data='gender_male')
    builder.button(text='Женский', callback_data='gender_female')
    builder.adjust(2)
    return builder.as_markup()

def activity_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='🪑 Минимальная', callback_data='activity_sedentary')
    builder.button(text='🚶 Легкая', callback_data='activity_light')
    builder.button(text='🏃 Умеренная', callback_data='activity_moderate')
    builder.button(text='💪 Высокая', callback_data='activity_active')
    builder.button(text='🔥 Очень высокая', callback_data='activity_very_active')
    builder.adjust(1)
    return builder.as_markup()

def confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='✅ Верно', callback_data='confirm_yes')
    builder.button(text='🔄 Изменить', callback_data='confirm_no')
    builder.adjust(2)
    return builder.as_markup()

def meal_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='🌅 Завтрак', callback_data='meal_breakfast')
    builder.button(text='☀️ Обед', callback_data='meal_lunch')
    builder.button(text='🌙 Ужин', callback_data='meal_dinner')
    builder.button(text='🍿 Перекус', callback_data='meal_snack')
    builder.adjust(2, 2)
    return builder.as_markup()

def settings_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='⚖️ Изменить вес', callback_data='set_weight')
    builder.button(text='🎯 Изменить цель', callback_data='set_target_weight')
    builder.button(text='📏 Изменить рост', callback_data='set_height')
    builder.button(text='🎂 Изменить возраст', callback_data='set_age')
    builder.button(text='🏃 Изменить активность', callback_data='set_activity')
    builder.button(text='🔄 Сбросить дневной счет', callback_data='reset_today')
    builder.button(text='🔙 Назад', callback_data='back_menu')
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()

def back_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 В меню', callback_data='back_menu')
    return builder.as_markup()
