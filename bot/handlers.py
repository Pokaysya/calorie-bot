import base64, io, json, os
from aiogram import Router, F, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from PIL import Image
from bot.config import OPENAI_API_KEY, GEMINI_API_KEY
from bot.database import (
    create_or_update_user, get_user, add_meal,
    get_today_meals, get_user_stats
)
from bot.keyboards import (
    main_menu_keyboard, gender_keyboard, activity_keyboard,
    confirm_keyboard, meal_type_keyboard, settings_keyboard, back_menu_keyboard
)
from bot.states import UserProfile, MealAdd, Settings
from bot.utils import (
    calculate_bmi, calculate_bmr, calculate_daily_calories,
    calculate_target_calories, get_bmi_category, get_activity_description,
    get_progress_bar, get_remaining_calories, get_weight_progress
)
import aiohttp

router = Router()

def get_ai_provider():
    if OPENAI_API_KEY:
        return 'openai'
    if GEMINI_API_KEY:
        return 'gemini'
    return None

@router.message(Command('start'))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    if user and user.get('gender'):
        await message.answer(
            f'Привет, {message.from_user.first_name}! 👋<br><br>'
            f'Добро пожаловать обратно в <b>CalorieAI</b>.<br><br>'
            f'Используй меню ниже:',
            reply_markup=main_menu_keyboard(), parse_mode='HTML'
        )
    else:
        ai_status = ''
        provider = get_ai_provider()
        if provider == 'openai':
            ai_status = '<br><br>🤖 <b>AI-режим:</b> OpenAI (фото еды)'
        elif provider == 'gemini':
            ai_status = '<br><br>🤖 <b>AI-режим:</b> Gemini (фото еды)'
        else:
            ai_status = '<br><br>✏️ <b>Режим:</b> ручной ввод (без AI)'
        await message.answer(
            f'Привет, {message.from_user.first_name}! 👋<br><br>'
            f'Добро пожаловать в <b>CalorieAI</b> — умного бота для подсчета калорий.'
            f'{ai_status}<br><br>Давай настроим твой профиль. Выбери пол:',
            reply_markup=gender_keyboard(), parse_mode='HTML'
        )
        await state.set_state(UserProfile.gender)

@router.callback_query(UserProfile.gender, F.data.startswith('gender_'))
async def process_gender(callback: CallbackQuery, state: FSMContext):
    gender = callback.data.split('_')[1]
    await state.update_data(gender=gender)
    await callback.message.edit_text('Отлично! Теперь укажи свой возраст (число):')
    await state.set_state(UserProfile.age)
    await callback.answer()

@router.message(UserProfile.age)
async def process_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer('Пожалуйста, введи число (возраст):')
        return
    age = int(message.text)
    if age < 10 or age > 120:
        await message.answer('Введи реальный возраст (10-120):')
        return
    await state.update_data(age=age)
    await message.answer('Теперь укажи свой рост в см (например, 175):')
    await state.set_state(UserProfile.height)

@router.message(UserProfile.height)
async def process_height(message: Message, state: FSMContext):
    try:
        height = float(message.text.replace(',', '.'))
        if height < 50 or height > 300:
            raise ValueError
    except ValueError:
        await message.answer('Введи корректный рост в см (например, 175):')
        return
    await state.update_data(height=height)
    await message.answer('Теперь укажи свой текущий вес в кг (например, 70):')
    await state.set_state(UserProfile.weight)

@router.message(UserProfile.weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text.replace(',', '.'))
        if weight < 20 or weight > 300:
            raise ValueError
    except ValueError:
        await message.answer('Введи корректный вес в кг (например, 70):')
        return
    await state.update_data(weight=weight)
    await message.answer('Какой вес ты хочешь достичь? Укажи в кг (например, 65):')
    await state.set_state(UserProfile.target_weight)

@router.message(UserProfile.target_weight)
async def process_target_weight(message: Message, state: FSMContext):
    try:
        target_weight = float(message.text.replace(',', '.'))
        if target_weight < 20 or target_weight > 300:
            raise ValueError
    except ValueError:
        await message.answer('Введи корректный целевой вес в кг (например, 65):')
        return
    data = await state.get_data()
    current_weight = data['weight']
    if target_weight == current_weight:
        await message.answer('Целевой вес равен текущему. Значит, цель — поддержание веса.')
    elif target_weight < current_weight:
        diff = round(current_weight - target_weight, 1)
        await message.answer(f'Цель — похудеть на {diff} кг. Отлично!')
    else:
        diff = round(target_weight - current_weight, 1)
        await message.answer(f'Цель — набрать {diff} кг. Хорошо!')
    await state.update_data(target_weight=target_weight)
    await message.answer(
        'Выбери свой уровень физической активности:',
        reply_markup=activity_keyboard()
    )
    await state.set_state(UserProfile.activity)

@router.callback_query(UserProfile.activity, F.data.startswith('activity_'))
async def process_activity(callback: CallbackQuery, state: FSMContext):
    activity = callback.data.split('_')[1]
    data = await state.get_data()
    data['activity'] = activity
    bmi = calculate_bmi(data['weight'], data['height'])
    bmr = calculate_bmr(data['gender'], data['weight'], data['height'], data['age'])
    daily = calculate_daily_calories(bmr, activity)
    target = calculate_target_calories(data['weight'], data['target_weight'], daily, bmr)
    weight_diff = data['weight'] - data['target_weight']
    goal_text = ''
    if weight_diff > 0:
        goal_text = f'Похудение: {round(weight_diff, 1)} кг'
    elif weight_diff < 0:
        goal_text = f'Набор: {round(abs(weight_diff), 1)} кг'
    else:
        goal_text = 'Поддержание веса'
    summary = (
        f'<b>Проверь данные:</b><br><br>'
        f"Пол: {'Мужской' if data['gender'] == 'male' else 'Женский'}<br>"
        f"Возраст: {data['age']} лет<br>"
        f"Рост: {data['height']} см<br>"
        f"Текущий вес: {data['weight']} кг<br>"
        f"Целевой вес: {data['target_weight']} кг<br>"
        f'Цель: {goal_text}<br>'
        f'Активность: {get_activity_description(activity)}<br><br>'
        f'<b>Расчеты:</b><br>'
        f'ИМТ: {bmi} ({get_bmi_category(bmi)})<br>'
        f'Базовый обмен: {bmr} ккал<br>'
        f'Норма калорий: {daily} ккал<br>'
        f'Цель калорий: {target} ккал'
    )
    await state.update_data(bmi=bmi, bmr=bmr, daily_calories=daily, target_calories=target)
    await callback.message.edit_text(summary, reply_markup=confirm_keyboard(), parse_mode='HTML')
    await state.set_state(UserProfile.confirm)
    await callback.answer()

@router.callback_query(UserProfile.confirm, F.data == 'confirm_yes')
async def process_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await create_or_update_user(callback.from_user.id, {
        'username': callback.from_user.username,
        'first_name': callback.from_user.first_name,
        'last_name': callback.from_user.last_name,
        'gender': data['gender'],
        'age': data['age'],
        'height': data['height'],
        'weight': data['weight'],
        'target_weight': data['target_weight'],
        'activity_level': data['activity'],
        'bmi': data['bmi'],
        'bmr': data['bmr'],
        'daily_calories': data['daily_calories'],
        'target_calories': data['target_calories']
    })
    provider = get_ai_provider()
    ai_hint = ''
    if provider:
        ai_hint = '<br><br>📸 Отправь фото еды — я определю калорийность автоматически!'
    else:
        ai_hint = '<br><br>✏️ Нажми <b>Добавить еду</b> и введи название с калориями.'
    await callback.message.edit_text(
        f'✅ Профиль создан!{ai_hint}<br><br>Используй меню:',
        reply_markup=main_menu_keyboard(), parse_mode='HTML'
    )
    await state.clear()
    await callback.answer()

@router.callback_query(UserProfile.confirm, F.data == 'confirm_no')
async def process_reject(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text('Выбери пол:', reply_markup=gender_keyboard())
    await state.set_state(UserProfile.gender)
    await callback.answer()

@router.callback_query(F.data == 'profile')
async def show_profile(callback: CallbackQuery):
    user = await get_user_stats(callback.from_user.id)
    if not user or not user.get('gender'):
        await callback.message.edit_text('Сначала настрой профиль: /start')
        return
    bmi = user.get('bmi', 0)
    target = user.get('target_calories', 0)
    current = user.get('today_calories', 0)
    remaining = get_remaining_calories(current, target)
    progress = get_progress_bar(current, target)
    weight_progress = get_weight_progress(user.get('weight', 0), user.get('target_weight', 0))
    text = (
        f'<b>👤 Мой профиль</b><br><br>'
        f"Имя: {user.get('first_name', 'Неизвестно')}<br>"
        f"Пол: {'Мужской' if user.get('gender') == 'male' else 'Женский'}<br>"
        f"Возраст: {user.get('age')} лет<br>"
        f"Рост: {user.get('height')} см<br>"
        f"Текущий вес: {user.get('weight')} кг<br>"
        f"Целевой вес: {user.get('target_weight')} кг<br>"
        f'Прогресс: {weight_progress}<br>'
        f'Активность: {get_activity_description(user.get('activity_level', ''))}<br><br>'
        f'<b>📊 Показатели:</b><br>'
        f'ИМТ: {bmi} ({get_bmi_category(bmi)})<br>'
        f'Базовый обмен: {user.get('bmr')} ккал<br>'
        f'Норма: {user.get('daily_calories')} ккал<br>'
        f'Цель: {target} ккал<br><br>'
        f'<b>📈 Сегодня:</b><br>'
        f'Съедено: {current} ккал<br>'
        f'Осталось: {remaining} ккал<br>'
        f'{progress}<br>'
        f'Приемов пищи: {user.get('meals_count', 0)}'
    )
    await callback.message.edit_text(text, reply_markup=back_menu_keyboard(), parse_mode='HTML')
    await callback.answer()

@router.callback_query(F.data == 'add_meal')
async def add_meal_start(callback: CallbackQuery, state: FSMContext):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.message.edit_text('Сначала настрой профиль: /start')
        return
    provider = get_ai_provider()
    if provider:
        await callback.message.edit_text('Отправь фото еды, и я определю калорийность:')
        await state.set_state(MealAdd.photo)
    else:
        await callback.message.edit_text(
            'Введи название блюда и калории.<br>Формат: <b>название - калории</b><br>'
            'Пример: <code>Гречка с курицей - 450</code>',
            parse_mode='HTML'
        )
        await state.set_state(MealAdd.confirm)
    await callback.answer()

@router.message(MealAdd.photo, F.photo)
async def process_meal_photo(message: Message, state: FSMContext, bot: Bot):
    provider = get_ai_provider()
    if not provider:
        await message.answer('AI-режим недоступен. Введи вручную: название - калории')
        await state.clear()
        return
    processing_msg = await message.answer('🔍 Анализирую фото...')
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_path = file.file_path
    image_bytes = await bot.download_file(file_path)
    image = Image.open(io.BytesIO(image_bytes.read()))
    if image.mode in ('RGBA', 'P'):
        image = image.convert('RGB')
    buffered = io.BytesIO()
    image.save(buffered, format='JPEG')
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    try:
        if provider == 'openai':
            meal_data = await analyze_with_openai(img_base64)
        else:
            meal_data = await analyze_with_gemini(img_base64)
        if not meal_data:
            raise ValueError('Empty response')
        await state.update_data(meal_data=meal_data, photo_file_id=photo.file_id)
        text = (
            f'<b>🍽 Результат анализа:</b><br><br>'
            f"<b>{meal_data['dish']}</b><br>"
            f"{meal_data.get('description', '')}<br><br>"
            f"🔥 Калории: {meal_data['calories']} ккал<br>"
            f"🥩 Белки: {meal_data['protein']} г<br>"
            f"🥑 Жиры: {meal_data['fat']} г<br>"
            f"🍞 Углеводы: {meal_data['carbs']} г<br><br>"
            f'Выбери тип приема пищи:'
        )
        await processing_msg.edit_text(text, reply_markup=meal_type_keyboard(), parse_mode='HTML')
        await state.set_state(MealAdd.confirm)
    except Exception as e:
        print(f'Error analyzing photo: {e}')
        await processing_msg.edit_text(
            '❌ Не удалось распознать блюдо. Попробуй другое фото или опиши текстом.<br><br>'
            'Формат: <b>название - калории</b>',
            reply_markup=back_menu_keyboard(), parse_mode='HTML'
        )
        await state.clear()

async def analyze_with_openai(img_base64: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            'https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {OPENAI_API_KEY}', 'Content-Type': 'application/json'},
            json={
                'model': 'gpt-4o-mini',
                'messages': [
                    {
                        'role': 'system',
                        'content': "Ты — эксперт по питанию. Определи блюдо на фото и оцени его калорийность. Ответь СТРОГО в JSON формате: {'dish': 'название', 'calories': число, 'protein': число_г, 'fat': число_г, 'carbs': число_г, 'description': 'краткое описание'}"
                    },
                    {
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': 'Что за блюдо на фото? Оцени калорийность и БЖУ на 100г или за порцию, если видно размер.'},
                            {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{img_base64}', 'detail': 'low'}}
                        ]
                    }
                ],
                'max_tokens': 500,
                'temperature': 0.3
            }
        ) as resp:
            result = await resp.json()
            content = result['choices'][0]['message']['content']
            return parse_ai_response(content)

async def analyze_with_gemini(img_base64: str) -> dict:
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}'
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            headers={'Content-Type': 'application/json'},
            json={
                'contents': [{
                    'parts': [
                        {'text': "Ты — эксперт по питанию. Определи блюдо на фото и оцени его калорийность. Ответь СТРОГО в JSON формате: {'dish': 'название', 'calories': число, 'protein': число_г, 'fat': число_г, 'carbs': число_г, 'description': 'краткое описание'}"},
                        {'inline_data': {'mime_type': 'image/jpeg', 'data': img_base64}}
                    ]
                }]
            }
        ) as resp:
            result = await resp.json()
            content = result['candidates'][0]['content']['parts'][0]['text']
            return parse_ai_response(content)

def parse_ai_response(content: str) -> dict:
    if '```json' in content:
        content = content.split('```json')[1].split('```')[0].strip()
    elif '```' in content:
        content = content.split('```')[1].split('```')[0].strip()
    return json.loads(content)

@router.message(MealAdd.confirm)
async def process_manual_meal(message: Message, state: FSMContext):
    try:
        parts = message.text.split('-')
        if len(parts) < 2:
            await message.answer(
                'Формат: <b>название - калории</b><br>Пример: <code>Гречка с курицей - 450</code>',
                parse_mode='HTML'
            )
            return
        name = parts[0].strip()
        calories = float(parts[1].strip().split()[0])
        meal_data = {
            'dish': name,
            'calories': calories,
            'protein': 0,
            'fat': 0,
            'carbs': 0,
            'description': name
        }
        await state.update_data(meal_data=meal_data)
        await message.answer(
            f'<b>{name}</b><br>Калории: {calories}<br><br>Выбери тип приема пищи:',
            reply_markup=meal_type_keyboard(), parse_mode='HTML'
        )
    except ValueError:
        await message.answer(
            'Ошибка. Формат: <b>название - калории</b><br>Пример: <code>Гречка с курицей - 450</code>',
            parse_mode='HTML'
        )

@router.callback_query(MealAdd.confirm, F.data.startswith('meal_'))
async def process_meal_type(callback: CallbackQuery, state: FSMContext):
    meal_type = callback.data.split('_')[1]
    data = await state.get_data()
    meal_data = data.get('meal_data', {})
    meal_data['meal_type'] = meal_type
    meal_data['photo_file_id'] = data.get('photo_file_id', '')
    if not meal_data.get('dish'):
        meal_data['dish'] = 'Неизвестно'
    if not meal_data.get('calories'):
        meal_data['calories'] = 0
    await add_meal(callback.from_user.id, callback.from_user.id, meal_data)
    user = await get_user_stats(callback.from_user.id)
    target = user.get('target_calories', 2000)
    current = user.get('today_calories', 0)
    remaining = get_remaining_calories(current, target)
    progress = get_progress_bar(current, target)
    text = (
        f"✅ <b>{meal_data['dish']}</b> добавлено!<br><br>"
        f"🔥 +{meal_data['calories']} ккал<br>"
        f"📊 Осталось на сегодня: {remaining} ккал<br><br>"
        f'<b>Прогресс:</b> {current} / {target} ккал<br>'
        f'{progress}'
    )
    await callback.message.edit_text(text, reply_markup=back_menu_keyboard(), parse_mode='HTML')
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == 'stats')
async def show_stats(callback: CallbackQuery):
    user = await get_user_stats(callback.from_user.id)
    if not user:
        await callback.message.edit_text('Сначала настрой профиль: /start')
        return
    target = user.get('target_calories', 2000)
    current = user.get('today_calories', 0)
    remaining = get_remaining_calories(current, target)
    progress = get_progress_bar(current, target)
    weight_progress = get_weight_progress(user.get('weight', 0), user.get('target_weight', 0))
    meals = await get_today_meals(callback.from_user.id)
    meals_text = ''
    for i, meal in enumerate(meals[:5], 1):
        desc = meal.get('description', 'Неизвестно')[:30]
        meals_text += f"{i}. {desc}... — {meal['calories']} ккал<br>"
    if not meals_text:
        meals_text = 'Сегодня еще не было приемов пищи.<br>'
    text = (
        f'<b>📈 Статистика</b><br><br>'
        f'<b>Цель веса:</b> {weight_progress}<br><br>'
        f'<b>Сегодня:</b><br>'
        f'Съедено: {current} ккал<br>'
        f'Осталось: {remaining} ккал<br>'
        f'{progress}<br>'
        f"Белки: {user.get('today_protein', 0)} г<br>"
        f"Жиры: {user.get('today_fat', 0)} г<br>"
        f"Углеводы: {user.get('today_carbs', 0)} г<br><br>"
        f'<b>🍽 Последние приемы пищи:</b><br>'
        f'{meals_text}<br>'
        f'<b>Всего за все время:</b><br>'
        f"Приемов пищи: {user.get('total_meals', 0)}<br>"
        f"Калорий: {user.get('total_all_calories', 0)}"
    )
    await callback.message.edit_text(text, reply_markup=back_menu_keyboard(), parse_mode='HTML')
    await callback.answer()

@router.callback_query(F.data == 'settings')
async def show_settings(callback: CallbackQuery):
    await callback.message.edit_text(
        '⚙️ <b>Настройки</b><br><br>Выбери, что изменить:',
        reply_markup=settings_keyboard(), parse_mode='HTML'
    )
    await callback.answer()

@router.callback_query(F.data.startswith('set_'))
async def process_setting(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split('_')[1]
    field_names = {
        'weight': 'вес',
        'height': 'рост',
        'age': 'возраст',
        'activity': 'активность',
        'target_weight': 'целевой вес'
    }
    if field == 'activity':
        await callback.message.edit_text(
            'Выбери новый уровень активности:',
            reply_markup=activity_keyboard()
        )
        await state.set_state(Settings.value)
        await state.update_data(field='activity')
    else:
        await callback.message.edit_text(f'Введи новый {field_names[field]}:')
        await state.set_state(Settings.value)
        await state.update_data(field=field)
    await callback.answer()

@router.message(Settings.value)
async def process_setting_value(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data['field']
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer('Ошибка. Начни с /start')
        await state.clear()
        return
    update_data = {}
    if field == 'activity':
        activity = message.text if message.text.startswith('activity_') else 'sedentary'
        update_data['activity_level'] = activity
        bmr = calculate_bmr(user['gender'], user['weight'], user['height'], user['age'])
        daily = calculate_daily_calories(bmr, activity)
        target = calculate_target_calories(user['weight'], user.get('target_weight', user['weight']), daily, bmr)
        update_data['bmr'] = bmr
        update_data['daily_calories'] = daily
        update_data['target_calories'] = target
    elif field == 'weight':
        try:
            weight = float(message.text.replace(',', '.'))
            update_data['weight'] = weight
            bmi = calculate_bmi(weight, user['height'])
            bmr = calculate_bmr(user['gender'], weight, user['height'], user['age'])
            daily = calculate_daily_calories(bmr, user['activity_level'])
            target = calculate_target_calories(weight, user.get('target_weight', weight), daily, bmr)
            update_data['bmi'] = bmi
            update_data['bmr'] = bmr
            update_data['daily_calories'] = daily
            update_data['target_calories'] = target
        except ValueError:
            await message.answer('Введи число:')
            return
    elif field == 'height':
        try:
            height = float(message.text.replace(',', '.'))
            update_data['height'] = height
            bmi = calculate_bmi(user['weight'], height)
            update_data['bmi'] = bmi
        except ValueError:
            await message.answer('Введи число:')
            return
    elif field == 'age':
        try:
            age = int(message.text)
            update_data['age'] = age
            bmr = calculate_bmr(user['gender'], user['weight'], user['height'], age)
            daily = calculate_daily_calories(bmr, user['activity_level'])
            target = calculate_target_calories(user['weight'], user.get('target_weight', user['weight']), daily, bmr)
            update_data['bmr'] = bmr
            update_data['daily_calories'] = daily
            update_data['target_calories'] = target
        except ValueError:
            await message.answer('Введи число:')
            return
    elif field == 'target_weight':
        try:
            target_weight = float(message.text.replace(',', '.'))
            update_data['target_weight'] = target_weight
            bmr = calculate_bmr(user['gender'], user['weight'], user['height'], user['age'])
            daily = calculate_daily_calories(bmr, user['activity_level'])
            target = calculate_target_calories(user['weight'], target_weight, daily, bmr)
            update_data['target_calories'] = target
        except ValueError:
            await message.answer('Введи число:')
            return
    await create_or_update_user(message.from_user.id, update_data)
    await message.answer('✅ Обновлено!', reply_markup=back_menu_keyboard())
    await state.clear()

@router.callback_query(F.data == 'reset_today')
async def reset_today(callback: CallbackQuery):
    await callback.answer('Функция в разработке', show_alert=True)

@router.callback_query(F.data == 'back_menu')
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text('Главное меню:', reply_markup=main_menu_keyboard())
    await callback.answer()

@router.message(F.photo)
async def quick_meal_photo(message: Message, state: FSMContext, bot: Bot):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer('Сначала настрой профиль: /start')
        return
    provider = get_ai_provider()
    if provider:
        await process_meal_photo(message, state, bot)
    else:
        await message.answer(
            'Я вижу фото, но у меня нет доступа к AI-анализу.<br>'
            'Напиши в формате: <b>название - калории</b>',
            parse_mode='HTML'
        )
