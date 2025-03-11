start_menu = Старт
started = Я запущен🥳.
stopped = Бот остановлен.
my_profile_menu = 👤 Мой профиль
my_profile_text = Мой профиль
bot_stopped = Бот остановлен

# Авторизация через веб
login-to-web = 🌐 Войти в веб-версию
web-auth-success = ✅ Авторизация успешна! Нажмите на кнопку ниже, чтобы войти в веб-версию приложения:
login-to-web-mini-app = 📱 Открыть в браузере
web-auth-mini-app = 🔄 Или используйте встроенный браузер Telegram:
web-auth-error = ❌ Ошибка авторизации. Пожалуйста, попробуйте снова.
welcome-message = 👋 Привет, {$name}! Я бот для управления задачами.

# Общие фразы
back = Назад
next = Далее
create = Создать
error = ❌ Ошибка
success = ✅ Успешно

# Настройки
settings_menu = ⚙️ Настройки
settings_header = ⚙️ Ваши настройки:
settings_statuses = 📊 Статусы задач
settings_priorities = 🔔 Приоритеты задач
settings_durations = ⏱️ Длительности задач
settings_task_types = 📁 Типы задач
settings_not_found = Настройки не найдены

# Команды настроек
settings_command_help = /settings - Просмотр и редактирование настроек
settings_statuses_command_help = /settings_statuses - Управление статусами задач
settings_priorities_command_help = /settings_priorities - Управление приоритетами задач
settings_durations_command_help = /settings_durations - Управление длительностями задач
settings_task_types_command_help = /settings_types - Управление типами задач
create_settings_command_help = /create_settings - Принудительное создание настроек

# Задачи
task-title = Введите название задачи:
task-description = Введите описание задачи (или отправьте '-' чтобы пропустить):
task-type = Выберите тип задачи:
task-status = Выберите статус задачи:
task-priority = Выберите приоритет задачи:
task-duration = Выберите длительность задачи:

# Список задач
tasks-empty = У вас пока нет задач. Создайте новую задачу командой /add_task
tasks-header = 📋 Ваши задачи:
task-item = {$status_emoji} {$priority_emoji} #{$id} {$title}
task-description-line = 📝 {$description}
task-duration-line = ⏱️ Длительность: {$duration}
task-deadline-line = ⏰ Дедлайн: {$deadline}
tasks-menu = 📋 Список задач

# Создание задачи
task-created = ✅ Задача успешно создана!
task-created-details =
    📝 {$title}
        Описание: {$description}
        Тип: {$type}
        Статус: {$status}
        Приоритет: {$priority}
        Длительность: {$duration}
        Дедлайн: {$deadline}

# Подтверждение создания задачи
task-confirm-header = 📋 Подтвердите создание задачи:
task-confirm-details = 
    📝 {$title}
        Описание: {$description}
        Тип: {$type}
        Статус: {$status}
        Приоритет: {$priority}
        Длительность: {$duration}

# Удаление задачи
task-deleted = ✅ Задача {$id} успешно удалена
task-delete-error = ❌ Задача {$id} не найдена или у вас нет прав на её удаление
task-delete-usage = ❌ Пожалуйста, укажите ID задачи: /delete_task id

# Справка
help-header = 📋 Доступные команды:
help-tasks = /tasks - Показать список задач
add-task-menu = Создать новую задачу
help-add-task = /add_task Создать новую задачу
help-delete-task = /delete_task id - Удалить задачу по ID
help-menu = Показать эту справку
help-help = /help Показать эту справку

# Статусы и приоритеты
status-not-set = Не указан
priority-not-set = Не указан
duration-not-set = Не указана
deadline-not-set = Не указан
type-not-set = Не указан

stop_menu = Остановить бота
