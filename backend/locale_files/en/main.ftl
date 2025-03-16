start_menu = Start
started = I'm running🥳.
stopped = Bot stopped.
my_profile_menu = 👤 My profile
my_profile_text = My profile
bot_stopped = Bot stopped

# Web authorization
login-to-web = 🌐 Login to web version
web-auth-success = ✅ Authorization successful! Click the button below to enter the web version of the application:
login-to-web-mini-app = 📱 Open in browser
web-auth-mini-app = 🔄 Or use the built-in Telegram browser:
web-auth-error = ❌ Authorization error. Please try again.
welcome-message = 👋 Hello, {$name}! I am a task management bot.

# Common phrases
back = Back
next = Next
create = Create
error = ❌ Error
success = ✅ Success

# Settings
settings_menu = ⚙️ Settings
settings_header = ⚙️ Your settings:
settings_statuses = 📊 Task statuses
settings_priorities = 🔔 Task priorities
settings_durations = ⏱️ Task durations
settings_task_types = 📁 Task types
settings_not_found = Settings not found

# Settings commands
settings_command_help = /settings - View and edit settings
settings_statuses_command_help = /settings_statuses - Manage task statuses
settings_priorities_command_help = /settings_priorities - Manage task priorities
settings_durations_command_help = /settings_durations - Manage task durations
settings_task_types_command_help = /settings_types - Manage task types
create_settings_command_help = /create_settings - Force create settings

# Tasks
task-title = Enter task title:
task-description = Enter task description (or send '-' to skip):
task-type = Select task type:
task-status = Select task status:
task-priority = Select task priority:
task-duration = Select task duration:

# Task list
tasks-empty = You don't have any tasks yet. Create a new task with the /add_task command
tasks-header = 📋 Your tasks:
task-item = #{$id} {$title}
task-status-line = Status: {$status}
task-priority-line = Priority: {$priority}
task-description-line = 📝 {$description}
task-duration-line = ⏱️ Duration: {$duration}
task-deadline-line = ⏰ Deadline: {$deadline}
tasks-menu = 📋 Task list

# Task list dialog
task-list-title = Your tasks (page {$page}/{$total_pages}, total {$total_tasks}):
task-list-error = ❌ Error: {$error}
task-list-filter-description = {$filter_description}
task-list-search-query = Search: {$search_query}
task-list-sort-description = Sort: {$sort_description}
task-list-empty = You don't have any tasks. Create a new task with the /add_task command
task-list-item = 📌 {$title} (ID: {$id})
    Description: {$description}
    Type: {$type}
    Status: {$status}
    Priority: {$priority}
    Deadline: {$deadline}
    Completed: {$completed}

# Task list dialog buttons
task-list-filter-button = 🔍 Filter
task-list-search-button = 🔎 Search
task-list-sort-button = 📊 Sort
task-list-reset-filters-button = ❌ Reset filters
task-list-reset-sort-button = ❌ Reset sort
task-list-close-button = Close

# Filters
task-list-filter-menu-title = Select filter type:
task-list-filter-status-button = 🔄 Status
task-list-filter-priority-button = 🔥 Priority
task-list-filter-type-button = 📋 Task type
task-list-filter-deadline-button = 📅 Deadline
task-list-filter-completed-button = ✅ Show completed
task-list-back-button = ↩️ Back

# Status filter
task-list-filter-status-title = Select status for filtering:

# Priority filter
task-list-filter-priority-title = Select priority for filtering:

# Task type filter
task-list-filter-type-title = Select task type for filtering:

# Deadline filter
task-list-filter-deadline-title = Select deadline period for filtering:
task-list-filter-deadline-today = Today
task-list-filter-deadline-tomorrow = Tomorrow
task-list-filter-deadline-week = This week
task-list-filter-deadline-month = This month
task-list-filter-deadline-overdue = Overdue

# Completion filter
task-list-filter-completed-title = Select completion filter:
task-list-filter-completed-all = Show all tasks
task-list-filter-completed-only = Only completed
task-list-filter-uncompleted-only = Only uncompleted

# Sorting
task-list-sort-title = Select sorting parameter:
task-list-sort-by-title = By title
task-list-sort-by-deadline = By deadline
task-list-sort-by-priority = By priority
task-list-sort-by-created = By creation date
task-list-sort-asc = Ascending
task-list-sort-desc = Descending

# Sort field names
sort-field-title = Title
sort-field-created_at = Creation date
sort-field-deadline = Deadline
sort-field-priority = Priority
sort-field-status = Status
sort-field-type = Type

# Sort directions
sort-direction-asc = ascending
sort-direction-desc = descending

# Search
task-list-search-title = Enter search query:
task-list-search-cancel = ↩️ Cancel

# Task creation
task-created = ✅ Task successfully created!
task-created-details =
    📝 {$title}
    Description: {$description}
    Type: {$type}
    Status: {$status}
    Priority: {$priority}
    Duration: {$duration}
    Deadline: {$deadline}

# Task creation confirmation
task-confirm-header = 📋 Confirm task creation:
task-confirm-details =
    📝 {$title}
    Description: {$description}
    Type: {$type}
    Status: {$status}
    Priority: {$priority}
    Duration: {$duration}
    Deadline: {$deadline}

# Task deadline selection
task-deadline = Select task deadline:

# Task deletion
task-deleted = ✅ Task {$id} successfully deleted
task-delete-error = ❌ Task {$id} not found or you don't have permission to delete it
task-delete-usage = ❌ Please specify task ID: /delete_task id

# Help
help-header = 📋 Available commands:
help-tasks = /tasks - Show task list
add-task-menu = Create new task
help-add-task = /add_task Create new task
help-delete-task = /delete_task id - Delete task by ID
help-menu = Show this help
help-help = /help Show this help

# Statuses and priorities
status-not-set = Not specified
priority-not-set = Not specified
duration-not-set = Not specified
deadline-not-set = Not specified
type-not-set = Not specified

stop_menu = Stop bot

# Task editing dialog
task-edit-title = 🔄 Task editing
task-edit-error = Error: {$error}
task-edit-details = 
    <b>Task:</b> {$title}
    <b>Description:</b> {$description}
    <b>Type:</b> {$type_name}
    <b>Status:</b> {$status_name}
    <b>Priority:</b> {$priority_name}
    <b>Duration:</b> {$duration_name}
    <b>Deadline:</b> {$deadline_display}
    <b>Completed:</b> {$completed}
    {$completed_at ->
        [null] {}
        *[other] <b>Completion date:</b> {$completed_at}
    }

task-edit-button-title = ✏️ Title
task-edit-button-description = 📝 Description
task-edit-button-type = 🏷️ Type
task-edit-button-status = 📊 Status
task-edit-button-priority = ⚡ Priority
task-edit-button-duration = ⏱️ Duration
task-edit-button-deadline = 📅 Deadline
task-edit-button-mark-completed = ✅ Mark as completed
task-edit-button-mark-uncompleted = ❌ Mark as uncompleted
task-edit-button-save = 💾 Save changes
task-edit-button-cancel = 🔙 Cancel
task-edit-button-back = 🔙 Back
task-edit-button-clear = ❌ Don't select
task-edit-button-clear-deadline = ❌ Remove deadline

task-edit-title-prompt = ✏️ Enter new task title:
task-edit-description-prompt = 📝 Enter new task description:
task-edit-description-hint = (Enter '-' to remove description)
task-edit-type-prompt = 🏷️ Select task type:
task-edit-status-prompt = 📊 Select task status:
task-edit-priority-prompt = ⚡ Select task priority:
task-edit-duration-prompt = ⏱️ Select task duration:
task-edit-deadline-prompt = 📅 Select task deadline:

task-edit-success = Task successfully updated!
task-edit-error-update = Failed to update task
task-edit-error-generic = Error: {$error}

# Edit button in task list
task-list-edit-button = ✏️ #{$id}
task-list-delete-button = 🗑️ #{$id}

# Task deletion confirmation
task-delete-confirm-title = Delete confirmation
task-delete-confirm-text = Do you really want to delete task #{$id}?
task-delete-confirm-yes = ✅ Yes, delete
task-delete-confirm-no = ❌ No, cancel
task-delete-success = ✅ Task #{$id} successfully deleted
task-delete-error = ❌ Failed to delete task #{$id}
task-delete-error-no-id = ❌ No task ID specified for deletion

# Language settings
language-settings-menu = 🌐 Language selection
language-current = Current language: {$language}
language-select = Select language:
language-ru = 🇷🇺 Русский
language-en = 🇬🇧 English
language-changed = ✅ Language changed to English

# Language notifications
language-not-supported = ❌ Selected language is not supported
language-change-error = ❌ Error changing language. Please try again later

# Add language to settings menu
settings_language = 🌐 Change language
settings_language_help = Change language

# Common messages for command outputs
common-default = Default
common-description = Description
common-color = Color
common-type = Type
common-value = Value
common-error-user-not-found = User not found. Please run the /start command first

# Additional settings strings
settings-is-final = Final status
settings-color = Color
settings-value = Value
settings-position = Position

# Task list messages
task-list-loading = Loading task list...
task-list-error-loading = Error loading task list: {$error}

# Language selection strings
language_selection_header = 🌐 Choose interface language:
language_changed = ✅ Language successfully changed to English.
language_change_error = ❌ Failed to change language. Please try again.
language_not_supported = ❌ Selected language is not supported.

# Add language to settings menu
settings_language = 🌐 Change language 