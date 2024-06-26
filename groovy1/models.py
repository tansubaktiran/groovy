from groovy1 import db, login_manager
from datetime import datetime
from flask_login import UserMixin

#User database name to be updated both here and on remote! 30-05-24
class str_staff_db2(db.Model, UserMixin): 
    id = db.Column(db.Integer, primary_key=True)
    country_db = db.Column(db.String(50))
    name_db = db.Column(db.String(200))
    email_db = db.Column(db.String(200))
    password_db = db.Column(db.String(120))
    role_db = db.Column(db.String(120))
    last_login_db = db.Column(db.DateTime, default=datetime.utcnow)
    last_logout_db = db.Column(db.DateTime, default=datetime.utcnow)
        
    def __repr__(self):
        #Aşağıdaki gibi (global active_user_id gerek olmadan bir current_user üzerinden loggedin kullanıcıyı takip edebilir miyiz? 21.12.2021 - Buna bir bakalım. 11.02.2022
        #return self.id
        #return '<Id %r>' % self.id
        return '<Name %r>' % self.name_db

class groovy_task_types_db(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_type_name_db = db.Column(db.String(100))
    task_step_names_db = db.Column(db.String(100))
    process_owner_email_db = db.Column(db.String(100))
    country_db = db.Column(db.String(50))

class groovy_tasks_db(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_name_db = db.Column(db.String(100))
    task_type_name_db = db.Column(db.String(100))
    task_status_db = db.Column(db.String(100)) 
    final_status_db = db.Column(db.Integer)
    process_owner_email_db = db.Column(db.String(100))
    subordinate_email_db = db.Column(db.String(100))
    urgent_or_not_db = db.Column(db.String(20))
    acceptance_required_or_not_db = db.Column(db.String(30))
    country_db = db.Column(db.String(50))
    date_added_db = db.Column(db.DateTime, default=datetime.utcnow)
    conversations = db.relationship('groovy_conversations_db', backref='case')
    status_logs = db.relationship('status_logs_db', backref='case')
    archived_db = db.Column(db.Integer, nullable=True)

#archived_db = db.Column(db.Integer) #

class groovy_routine_tasks_db(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_name_db = db.Column(db.String(100))
    period_db = db.Column(db.String(100))
    task_status_db = db.Column(db.String(100))
    final_status_db = db.Column(db.Integer)
    archived_db = db.Column(db.Integer)
    process_owner_email_db = db.Column(db.String(100))
    date_added_db = db.Column(db.DateTime, default=datetime.utcnow)
    date_completed_db = db.Column(db.DateTime, nullable=True)
    date_due_db = db.Column(db.DateTime, nullable=True)
    
class groovy_conversations_db(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_db = db.Column(db.String(100))
    date_of_sending_db = db.Column(db.DateTime, default=datetime.utcnow)
    text_db = db.Column(db.String(2500))
    task_id_db = db.Column(db.Integer, db.ForeignKey('groovy_tasks_db.id'))
    
class status_logs_db(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_db = db.Column(db.String(100))
    status_changed_to_db = db.Column(db.String(100))
    date_of_status_change_db = db.Column(db.DateTime, default=datetime.utcnow)
    task_id_db = db.Column(db.Integer, db.ForeignKey('groovy_tasks_db.id'))

class groovy_calendar_db(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer)
    date_time_db = db.Column(db.DateTime)
    title_db = db.Column(db.String(500), nullable=True)
    user_email_db = db.Column(db.String(120), nullable=True)
    assigned_user_email_db = db.Column(db.String(120), nullable=True)
    
#USER LOGIN FUNCTION FOR LOADING ACTIVE USER?
@login_manager.user_loader
def load_user(id):
    return str_staff_db2.query.get(int(id)) #DB table name to be updated!!!! ////////////