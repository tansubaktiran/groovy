#from flask import Flask
from flask import Flask, render_template

from flask_sqlalchemy import SQLAlchemy #pip install flask-sqlalchemy

from flask_login import LoginManager #27.05.2022
#Login password encryption için #27.05.2022
from flask_bcrypt import Bcrypt

from dotenv import load_dotenv, find_dotenv
import os

app = Flask(__name__)

# Loading environment variables from .env file for security reasons
load_dotenv()


# Access the environment variable
secret_key = os.getenv('SECRET_KEY')
app.config['SECRET_KEY'] = secret_key

database_uri = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_DATABASE_URI'] = database_uri

db = SQLAlchemy(app)

app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 100000

#Setting up user login parts #27.05.2022 - Login için
login_manager = LoginManager(app)
login_manager.login_view = 'login' #For directing to a please log in page. Otherwise throws >
login_manager.login_message_category = 'info'

bcrypt = Bcrypt(app) #27.05.2022 Şifre encryption için gerekli.

from groovy1 import routes
