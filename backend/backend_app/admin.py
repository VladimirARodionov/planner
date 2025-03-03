from django.contrib import admin
from .models import TaskType, TaskPriority, TaskDuration, Task, Reminder

@admin.register(TaskType)
class TaskTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(TaskPriority)
class TaskPriorityAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(TaskDuration)
class TaskDurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'days')
    search_fields = ('name',)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'task_type', 'priority', 'duration', 'deadline', 'completed')
    list_filter = ('completed', 'task_type', 'priority', 'duration')
    search_fields = ('title', 'description')
    date_hierarchy = 'created_at'

@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ('task', 'remind_at', 'sent')
    list_filter = ('sent',)
    date_hierarchy = 'remind_at'
