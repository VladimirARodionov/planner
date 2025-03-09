started = Я запущен🥳.
stopped = Бот остановлен.
my_profile_menu = 👤 Мой профиль
my_profile_text = Мой профиль
bot_stopped = Бот остановлен

# Общие фразы
back = Назад
next = Далее
create = Создать
error = ❌ Ошибка
success = ✅ Успешно

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
task-item = {$status_emoji} {$priority_emoji} {$title}
task-description-line = 📝 {$description}
task-deadline-line = ⏰ Дедлайн: {$deadline}

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

# Удаление задачи
task-deleted = ✅ Задача {$id} успешно удалена
task-delete-error = ❌ Задача {$id} не найдена или у вас нет прав на её удаление
task-delete-usage = ❌ Пожалуйста, укажите ID задачи: /delete_task id

# Справка
help-header = 📋 Доступные команды:
help-tasks = /tasks - Показать список задач
help-add-task = /add_task - Создать новую задачу
help-delete-task = /delete_task id - Удалить задачу по ID
help-help = /help - Показать эту справку

# Статусы и приоритеты
status-not-set = Не указан
priority-not-set = Не указан
duration-not-set = Не указана
deadline-not-set = Не указан
type-not-set = Не указан