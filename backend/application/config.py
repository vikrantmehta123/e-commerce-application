from datetime import timedelta
from celery.schedules import crontab

# Flask configurations
SQLALCHEMY_DATABASE_URI = r""
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = ''
SESSION_TYPE = 'filesystem'  
SESSION_PERMANENT = False

# Redis config for cache
CACHE_TYPE='RedisCache'
CACHE_DEFAULT_TIMEOUT = 300
CACHE_REDIS_URL = "redis://localhost:6379/1"

# SMTP Config
SMTP_SERVER_HOST = "smtp.gmail.com"
SMTP_SERVER_PORT = 465 # Change to 587
SENDER_ADDRESS = ""
SENDER_PASSWORD = ""

# JWT Config
from datetime import timedelta
JWT_SECRET_KEY = ''
JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=45)

# Celery configurations
CELERY_CONFIG = {
    'broker_url': 'redis://127.0.0.1:6379/2',
    'beat_schedule' : {
        'daily_mail_task':{
            'task' :'application.tasks.send_daily_purchase_reminder_mail', 
            'schedule': crontab(hour=22, minute=12,day_of_week='*', day_of_month='*'),
        }, 
        'monthly_activity_task':{
            'task' : 'application.tasks.monthly_activity_report_task', 
            'schedule' : crontab(day_of_month=17, hour=22, minute=12)
        }
    },
    'broker_connection_retry_on_startup':False,
    'timezone' : 'Asia/Kolkata', 
    'imports' : ('application.tasks',),
    'task_serializer' : 'json',
    'result_serializer' : 'json', 
    'accept_content' : ['json'],

}


