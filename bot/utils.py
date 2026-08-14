def calculate_bmi(weight: float, height: float) -> float:
    height_m = height / 100
    return round(weight / (height_m ** 2), 1)

def get_bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return 'Недостаточный вес'
    elif bmi < 25:
        return 'Норма'
    elif bmi < 30:
        return 'Избыточный вес'
    else:
        return 'Ожирение'

def calculate_bmr(gender: str, weight: float, height: float, age: int) -> float:
    if gender.lower() == 'male':
        bmr = 88.36 + (13.4 * weight) + (4.8 * height) - (5.7 * age)
    else:
        bmr = 447.6 + (9.2 * weight) + (3.1 * height) - (4.3 * age)
    return round(bmr, 0)

def calculate_daily_calories(bmr: float, activity_level: str) -> float:
    activity_multipliers = {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'active': 1.725,
        'very_active': 1.9
    }
    multiplier = activity_multipliers.get(activity_level, 1.2)
    return round(bmr * multiplier, 0)

def calculate_target_calories(current_weight: float, target_weight: float, daily_calories: float, bmr: float) -> float:
    weight_diff = current_weight - target_weight
    min_calories = round(bmr * 1.2, 0)
    if weight_diff > 0:
        deficit = min(550 * (weight_diff / 5), 1000)
        target = daily_calories - deficit
        return max(round(target, 0), min_calories)
    elif weight_diff < 0:
        surplus = min(400 * (abs(weight_diff) / 5), 500)
        return round(daily_calories + surplus, 0)
    else:
        return daily_calories

def get_activity_description(level: str) -> str:
    descriptions = {
        'sedentary': 'Минимальная активность (сидячий образ жизни)',
        'light': 'Легкая активность (1-2 тренировки в неделю)',
        'moderate': 'Умеренная активность (3-4 тренировки в неделю)',
        'active': 'Высокая активность (5-6 тренировок в неделю)',
        'very_active': 'Очень высокая активность (ежедневные тренировки)'
    }
    return descriptions.get(level, 'Неизвестно')

def get_progress_bar(current: float, target: float, length: int = 20) -> str:
    if target <= 0:
        return '░' * length
    ratio = min(current / target, 1.0)
    filled = int(ratio * length)
    empty = length - filled
    bar = '█' * filled + '░' * empty
    percentage = round(ratio * 100, 1)
    return f'{bar} {percentage}%'

def get_remaining_calories(current: float, target: float) -> float:
    return max(target - current, 0)

def get_weight_progress(current: float, target: float, start: float = None) -> str:
    if start is None:
        start = current
    if start == target:
        return 'Цель достигнута!'
    diff = abs(start - target)
    progress = abs(start - current)
    if diff == 0:
        return 'Цель достигнута!'
    percentage = round((progress / diff) * 100, 1)
    direction = 'похудел' if start > target else 'набрал'
    return f'{percentage}% ({direction} {round(progress, 1)} кг)'
