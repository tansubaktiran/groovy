from flask import Flask, render_template, request, flash

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, SelectField, TextAreaField, ValidationError, DateTimeField, DateField
from wtforms.fields.simple import PasswordField
from wtforms.validators import DataRequired, Email, InputRequired, Optional
from flask_wtf.file import FileField

#from wtforms.fields.core import #RadioField #DateField,
#from appfolder.models import lesson4_users_db

class login_form(FlaskForm):
    email = StringField("E-mailinizi giriniz...", validators=[Email()] )
    password = PasswordField("Şifrenizi giriniz...", validators=[DataRequired()]) 
    submit = SubmitField("Giriş")

class task_type_definition(FlaskForm):
    task_type_name = StringField("Yeni görev akış ismini giriniz...") #  ,validators=[InputRequired()] #, validators=[DataRequired()]
    task_first_step_name = StringField("Görevin ilk adımını giriniz...")
    task_second_final_step_name = StringField("Enter second (or final if only 2 steps)task step name please..")
    submit = SubmitField("Yeni görev akış tipini kaydet...")

class task_step_addition(FlaskForm):
    new_task_process_step = StringField("Görev akışının sonraki adımını giriniz...", validators=[DataRequired()]) #  ,validators=[InputRequired()]
    submit = SubmitField("Yeni adımı kaydet")

class new_task_assignment_form(FlaskForm):
    task_name = StringField("Yeni yapılacak görev konusunu giriniz ")
    task_type_name = SelectField('Görev türünü seçiniz...', choices=[])
    subordinate_email = StringField("Atanacak kişiyi giriniz...")
    urgent_or_not = reply_result = SelectField(label='Aciliyet türünü seçiniz', choices=[("Not Urgent", "Not Urgent"), ("Urgent", "Urgent")])
    acceptance_required_or_not = SelectField(label='Kabul onayı gerekiyor mu?', choices=[("Acceptance Required", "Acceptance Required"), ("Direct Order", "Direct Order")])
    
    submit = SubmitField("Kaydet")

class groovy_conversations(FlaskForm):
            
    message = TextAreaField("Bu görev hakkında yeni mesaj gönderin...")
    submit = SubmitField("Gönder")

#This is not used for saving the datetime to calendar 09.05.2024
class groovy_calendar(FlaskForm):
    # Define a DateTimeField with optional validators
    #datetime_field = DateTimeField('Please choose Date and Time', validators=[DataRequired()])
    datetime_field = DateField('Please choose Date and Time', validators=[DataRequired()], format='%Y-%m-%d %H:%M:%S')