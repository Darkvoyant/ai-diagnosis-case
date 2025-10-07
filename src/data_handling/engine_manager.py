# src/data/engine_manager.py
import random
import pandas as pd
import os
from src.utils import config

class EngineManager:
    """
    Класс управляющий состоянием двигателей и логикой пользователей.
    """
    def __init__(self):
        self.engines = self._initialize_engines()

    def _initialize_engines(self):
        """
        Инициализирует список двигателей из CSV файла для детерминированного состояния.
        """
        engine_list = []
        
        # --- НОВАЯ ЛОГИКА ---
        try:
            df = pd.read_csv(config.ENGINE_STATES_CSV_PATH)
        except FileNotFoundError:
            # Обработка ошибки, если файл не найден
            print(f"ОШИБКА: Файл конфигурации не найден по пути: {config.ENGINE_STATES_CSV_PATH}")
            # Можно вернуть пустой список или создать аварийный мок
            return []

        for index, row in df.iterrows():
            status = row['status']
            # Обрабатываем NaN для пустых ячеек дефектов
            defect = row['defect'] if pd.notna(row['defect']) else None
            rul = 0

            if status == "Работает":
                rul = random.randint(*config.RUL_RANGES["ok"])
            elif status == "Предупреждение":
                rul = random.randint(*config.RUL_RANGES["warning"])
            elif status == "Не работает":
                rul = config.RUL_RANGES["error"]

            engine_list.append({
                "id": row['id'],
                "status": status,
                "serial": f"SN-{random.randint(100000, 999999)}", # Серийник оставим случайным
                "defect": defect,
                "rul": rul
            })
            
        return engine_list

    def get_all_engines(self):
        return self.engines

    def get_faulty_engines(self):
        """Возвращает список двигателей не в статусе 'Работает'."""
        return [e for e in self.engines if e['status'] != 'Работает']

    def get_system_summary(self):
        """Возвращает статистику по системе."""
        working = sum(1 for e in self.engines if e['status'] == 'Работает')
        warning = sum(1 for e in self.engines if e['status'] == 'Предупреждение')
        error = sum(1 for e in self.engines if e['status'] == 'Не работает')
        return working, warning, error

    def fix_engine(self, engine_id):
        """Сбрасывает статус двигателя на 'Работает'."""
        for engine in self.engines:
            if engine['id'] == engine_id:
                engine["status"] = "Работает"
                engine["defect"] = None
                engine["rul"] = random.randint(*config.RUL_RANGES["ok"])
                return True
        return False

    # --- Логика пользователей (можно вынести в отдельный класс AuthManager, но пока оставим тут) ---
    @staticmethod
    def check_login(username, password):
        users = config.USERS
        if username in users and users[username]["password"] == password:
            return True, users[username]
        return False, None