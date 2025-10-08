Event Planner — простое приложение на FastAPI

Файлы:
- app.py — основное приложение FastAPI, использует SQLite `events.db` в той же папке.
- requirements.txt — зависимости.

Как запустить (PowerShell, Windows):

1) Убедитесь, что Python установлен. В PowerShell выполните:

```powershell
py --version
# или
python --version
```

2) Рекомендуется создать виртуальное окружение и активировать его:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1

```

3) Установите зависимости:

```powershell
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

4) Запустите приложение:

```powershell
python app.py

uvicorn app:app --reload
```

5) Откройте в браузере: http://127.0.0.1:8000/docs — Swagger UI для тестирования API.

Примечания и возможные улучшения:
- Сейчас «отправка» напоминаний реализована как запись в лог. Для продакшена можно подключить SMTP, Twilio или push-уведомления.
- Добавить аутентификацию, права доступа и проверку владельца события.
- Добавить тесты и миграции (alembic) для базы данных.
