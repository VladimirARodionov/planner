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
task-item = #{$id} {$title}
task-status-line = Статус: {$status}
task-priority-line = Приоритет: {$priority}
task-description-line = 📝 {$description}
task-duration-line = ⏱️ Длительность: {$duration}
task-deadline-line = ⏰ Дедлайн: {$deadline}
tasks-menu = 📋 Список задач

# Диалог списка задач
task-list-title = Ваши задачи (страница {$page}/{$total_pages}, всего {$total_tasks}):
task-list-error = ❌ Ошибка: {$error}
task-list-filter-description = {$filter_description}
task-list-search-query = Поиск: '{$search_query}'
task-list-sort-description = Сортировка: {$sort_description}
task-list-empty = У вас нет задач\n\nСоздайте новую задачу с помощью команды /add_task
task-list-item = 📌 {$title} (ID: {$id})
    Описание: {$description}
    Тип: {$type}
    Статус: {$status}
    Приоритет: {$priority}
    Дедлайн: {$deadline}
    Завершена: {$completed}

# Кнопки диалога списка задач
task-list-filter-button = 🔍 Фильтр
task-list-search-button = 🔎 Поиск
task-list-sort-button = 📊 Сортировка
task-list-reset-filters-button = ❌ Сбросить фильтры
task-list-reset-sort-button = ❌ Сбросить сортировку
task-list-close-button = Закрыть

# Фильтры
task-list-filter-menu-title = Выберите тип фильтра:
task-list-filter-status-button = 🔄 Статус
task-list-filter-priority-button = 🔥 Приоритет
task-list-filter-type-button = 📋 Тип задачи
task-list-filter-deadline-button = 📅 Дедлайн
task-list-filter-completed-button = ✅ Показать завершенные
task-list-back-button = ↩️ Назад

# Фильтр по статусу
task-list-filter-status-title = Выберите статус для фильтрации:

# Фильтр по приоритету
task-list-filter-priority-title = Выберите приоритет для фильтрации:

# Фильтр по типу задачи
task-list-filter-type-title = Выберите тип задачи для фильтрации:

# Фильтр по дедлайну
task-list-filter-deadline-title = Выберите период дедлайна для фильтрации:
task-list-filter-deadline-today = Сегодня
task-list-filter-deadline-tomorrow = Завтра
task-list-filter-deadline-week = Эта неделя
task-list-filter-deadline-month = Этот месяц
task-list-filter-deadline-overdue = Просроченные

# Фильтр по завершенности
task-list-filter-completed-title = Выберите фильтр по завершенности:
task-list-filter-completed-all = Показать все задачи
task-list-filter-completed-only = Только завершенные
task-list-filter-uncompleted-only = Только незавершенные

# Сортировка
task-list-sort-title = Выберите параметр сортировки:
task-list-sort-by-title = По названию
task-list-sort-by-deadline = По дедлайну
task-list-sort-by-priority = По приоритету
task-list-sort-by-created = По дате создания
task-list-sort-asc = По возрастанию
task-list-sort-desc = По убыванию

# Названия полей сортировки
sort-field-title = Название
sort-field-created_at = Дата создания
sort-field-deadline = Дедлайн
sort-field-priority = Приоритет
sort-field-status = Статус
sort-field-type = Тип

# Направления сортировки
sort-direction-asc = по возрастанию
sort-direction-desc = по убыванию

# Поиск
task-list-search-title = Введите поисковый запрос:
task-list-search-cancel = ↩️ Отмена

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
