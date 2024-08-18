# Celery configurations
broker_url = 'redis://localhost:6379/0'
result_backend = 'redis://localhost:6379/0'
include = ['application.tasks']

from datetime import timedelta

beat_schedule = {
    'daily_task': {
        'task': 'tasks.daily_task',
        'schedule': timedelta(days=1),
    },
    'monthly_task': {
        'task': 'tasks.monthly_task',
        'schedule': timedelta(days=30),
    }
}
