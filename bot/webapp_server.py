from aiohttp import web
from bot.database import get_user_stats, get_today_meals, get_weekly_stats
import json

async def get_user_data(request):
    telegram_id = request.match_info.get('telegram_id')
    try:
        telegram_id = int(telegram_id)
    except ValueError:
        return web.json_response({'error': 'Invalid telegram_id'}, status=400)
    user = await get_user_stats(telegram_id)
    if not user:
        return web.json_response({'error': 'User not found'}, status=404)
    meals = await get_today_meals(telegram_id)
    weekly = await get_weekly_stats(telegram_id)
    return web.json_response({
        'user': {
            'first_name': user.get('first_name', ''),
            'gender': user.get('gender', ''),
            'age': user.get('age', 0),
            'height': user.get('height', 0),
            'weight': user.get('weight', 0),
            'target_weight': user.get('target_weight', 0),
            'activity_level': user.get('activity_level', ''),
            'bmi': user.get('bmi', 0),
            'bmr': user.get('bmr', 0),
            'daily_calories': user.get('daily_calories', 0),
            'target_calories': user.get('target_calories', 0),
        },
        'today': {
            'calories': user.get('today_calories', 0),
            'protein': user.get('today_protein', 0),
            'fat': user.get('today_fat', 0),
            'carbs': user.get('today_carbs', 0),
            'meals_count': user.get('meals_count', 0),
            'target': user.get('target_calories', 0)
        },
        'meals': [{
            'description': m.get('description', ''),
            'calories': m.get('calories', 0),
            'protein': m.get('protein', 0),
            'fat': m.get('fat', 0),
            'carbs': m.get('carbs', 0),
            'meal_type': m.get('meal_type', ''),
            'created_at': m.get('created_at', '')
        } for m in meals],
        'weekly': [{
            'date': w.get('date', ''),
            'calories': w.get('total_calories', 0),
            'protein': w.get('total_protein', 0),
            'fat': w.get('total_fat', 0),
            'carbs': w.get('total_carbs', 0),
            'meals_count': w.get('meals_count', 0)
        } for w in weekly]
    })

def setup_webapp(app):
    app.router.add_get('/api/user/{telegram_id}', get_user_data)
