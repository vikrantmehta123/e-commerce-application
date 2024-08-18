from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from celery import Celery
from flask_cors import CORS
import bcrypt
from flask_caching import Cache

app = Flask(__name__)
app.config.from_object('application.config')

db = SQLAlchemy(app)
jwt = JWTManager(app)
cache = Cache(app)

def init_db():
    from application.models import User, Role
    with app.app_context():
        db.create_all()
        
        # Create roles
        roles = ['admin', 'manager', 'user']
        for role_name in roles:
            role = Role.query.filter_by(name=role_name).first()
            if role is None:
                role = Role(name=role_name)
                db.session.add(role)
        
        # Create a default admin user
        admin = User.query.filter_by(username='admin').first()
        if admin is None:
            admin = User(username='admin', password=bcrypt.hashpw('password'.encode('utf-8'), bcrypt.gensalt())
                         , name="vikrant mehta", contact="9405119506", email="vikrantmehta123@gmail.com", 
                         address="home")
        admin.roles = Role.query.all()
        db.session.add(admin)

        db.session.commit()

        from application.fts import setup_fts
        #setup_fts()

def make_celery(app:Flask):
    celery = Celery(app.import_name, backend='redis://localhost:6379/0', broker='redis://127.0.0.1:6379/2')
    celery.conf.update(app.config["CELERY_CONFIG"])

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

celery = make_celery(app)

from application import api

cors = CORS(app, resources={r"*": {"origins": ["http://localhost:8080"]} })
app.register_blueprint(api.api)
