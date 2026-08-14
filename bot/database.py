import aiosqlite
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

DATABASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DATABASE_DIR, '..', 'data', 'calorie_bot.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                gender TEXT,
                age INTEGER,
                height REAL,
                weight REAL,
                target_weight REAL,
                activity_level TEXT,
                bmi REAL,
                bmr REAL,
                daily_calories REAL,
                target_calories REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                photo_file_id TEXT,
                description TEXT,
                calories REAL,
                protein REAL,
                fat REAL,
                carbs REAL,
                meal_type TEXT DEFAULT 'other',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS daily_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                total_calories REAL DEFAULT 0,
                total_protein REAL DEFAULT 0,
                total_fat REAL DEFAULT 0,
                total_carbs REAL DEFAULT 0,
                meals_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, date)
            )
        ''')
        await db.commit()

async def get_user(telegram_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def create_or_update_user(telegram_id: int, data: Dict[str, Any]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await db.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
        row = await existing.fetchone()
        if row:
            fields = []
            values = []
            for key, value in data.items():
                fields.append(f'{key} = ?')
                values.append(value)
            values.append(telegram_id)
            await db.execute(f'''
                UPDATE users SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            ''', values)
        else:
            fields = ['telegram_id'] + list(data.keys())
            values = [telegram_id] + list(data.values())
            placeholders = ', '.join(['?' for _ in values])
            await db.execute(f'''
                INSERT INTO users ({', '.join(fields)}) VALUES ({placeholders})
            ''', values)
        await db.commit()

async def add_meal(user_id: int, telegram_id: int, meal_data: Dict[str, Any]) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        user = await db.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
        user_row = await user.fetchone()
        if not user_row:
            return -1
        user_db_id = user_row[0]
        cursor = await db.execute('''
            INSERT INTO meals (user_id, photo_file_id, description, calories, protein, fat, carbs, meal_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_db_id, meal_data.get('photo_file_id', ''), meal_data.get('description', ''),
              meal_data.get('calories', 0), meal_data.get('protein', 0),
              meal_data.get('fat', 0), meal_data.get('carbs', 0), meal_data.get('meal_type', 'other')))
        meal_id = cursor.lastrowid
        today = datetime.now().strftime('%Y-%m-%d')
        await db.execute('''
            INSERT INTO daily_logs (user_id, date, total_calories, total_protein, total_fat, total_carbs, meals_count)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(user_id, date) DO UPDATE SET
                total_calories = total_calories + ?,
                total_protein = total_protein + ?,
                total_fat = total_fat + ?,
                total_carbs = total_carbs + ?,
                meals_count = meals_count + 1
        ''', (user_db_id, today, meal_data.get('calories', 0), meal_data.get('protein', 0),
              meal_data.get('fat', 0), meal_data.get('carbs', 0),
              meal_data.get('calories', 0), meal_data.get('protein', 0),
              meal_data.get('fat', 0), meal_data.get('carbs', 0)))
        await db.commit()
        return meal_id

async def get_today_meals(telegram_id: int) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        today = datetime.now().strftime('%Y-%m-%d')
        cursor = await db.execute('''
            SELECT m.* FROM meals m
            JOIN users u ON m.user_id = u.id
            WHERE u.telegram_id = ? AND date(m.created_at) = ?
            ORDER BY m.created_at DESC
        ''', (telegram_id, today))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_user_stats(telegram_id: int) -> Dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        user = await cursor.fetchone()
        if not user:
            return {}
        user_dict = dict(user)
        today = datetime.now().strftime('%Y-%m-%d')
        cursor = await db.execute('''
            SELECT * FROM daily_logs WHERE user_id = ? AND date = ?
        ''', (user_dict['id'], today))
        daily = await cursor.fetchone()
        if daily:
            daily_dict = dict(daily)
            user_dict['today_calories'] = daily_dict.get('total_calories', 0)
            user_dict['today_protein'] = daily_dict.get('total_protein', 0)
            user_dict['today_fat'] = daily_dict.get('total_fat', 0)
            user_dict['today_carbs'] = daily_dict.get('total_carbs', 0)
            user_dict['meals_count'] = daily_dict.get('meals_count', 0)
        else:
            user_dict['today_calories'] = 0
            user_dict['today_protein'] = 0
            user_dict['today_fat'] = 0
            user_dict['today_carbs'] = 0
            user_dict['meals_count'] = 0
        cursor = await db.execute('''
            SELECT COUNT(*) as total_meals, SUM(calories) as total_all_calories
            FROM meals WHERE user_id = ?
        ''', (user_dict['id'],))
        stats = await cursor.fetchone()
        if stats:
            stats_dict = dict(stats)
            user_dict['total_meals'] = stats_dict.get('total_meals', 0) or 0
            user_dict['total_all_calories'] = stats_dict.get('total_all_calories', 0) or 0
        return user_dict

async def get_weekly_stats(telegram_id: int) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT d.* FROM daily_logs d
            JOIN users u ON d.user_id = u.id
            WHERE u.telegram_id = ? AND d.date >= date('now', '-7 days')
            ORDER BY d.date DESC
        ''', (telegram_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
