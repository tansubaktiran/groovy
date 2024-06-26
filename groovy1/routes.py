import os
import pandas as pd
from sqlalchemy import create_engine, or_ , and_, desc

from groovy1 import app, db, bcrypt

from flask import render_template, url_for, flash, redirect, request, send_file, jsonify

from flask_login import login_user, current_user, logout_user, login_required
from groovy1.forms import  login_form, task_type_definition, task_step_addition, new_task_assignment_form, groovy_conversations, groovy_calendar
from groovy1.models import str_staff_db2, groovy_task_types_db, groovy_tasks_db, groovy_conversations_db, status_logs_db, groovy_calendar_db, groovy_routine_tasks_db

from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from email.message import EmailMessage
import smtplib

import locale

#Index2 Temizlendi. Son kontrolden geçecek.20_04_24
#Index and summary page of the active and upcoming tasks
@app.route('/')
@app.route('/index2') #Should be showing only relevant user's (current) tasks. Solved. Will be checked.
def index2():
    
    if current_user.is_authenticated:
    
        # Set the locale to Turkish
        locale.setlocale(locale.LC_TIME, 'tr_TR.UTF-8')
        today_to_be_displayed = datetime.now().strftime('%d %B %Y')

        #Should be showing only relevant user's (current) tasks. #Should be showing only relevant user's (current) tasks. Solved. Will be checked.
        active_tasks = groovy_tasks_db.query.filter(groovy_tasks_db.final_status_db != 1,groovy_tasks_db.subordinate_email_db == current_user.email_db).order_by(desc(groovy_tasks_db.date_added_db)).all()
        
        number_of_active_tasks = len(active_tasks)
        
        # Calculate one month time range
        today = datetime.now()
        one_month_later = today + timedelta(days=30)

        # Fetch records
        tasks_within_one_month = groovy_calendar_db.query.filter(
        groovy_calendar_db.date_time_db >= today,
        groovy_calendar_db.date_time_db <= one_month_later, groovy_calendar_db.assigned_user_email_db == current_user.email_db
        ).order_by(groovy_calendar_db.date_time_db.asc()).all()
        
        tasks_in_calendar = len(tasks_within_one_month)

        all_routine_tasks = groovy_routine_tasks_db.query.filter(
        and_(groovy_routine_tasks_db.task_status_db == 'uncompleted', groovy_routine_tasks_db.process_owner_email_db == current_user.email_db)).all()
        
        return render_template("index2.html", tasks_within_one_month=tasks_within_one_month, number_of_active_tasks=number_of_active_tasks, today=today_to_be_displayed, tasks_in_calendar=tasks_in_calendar, active_tasks=active_tasks,  all_routine_tasks=all_routine_tasks)
    
    return render_template("index2.html")

#Temizlendi.
#Index of previous version which is now functioning as advanced options page.
@app.route('/index') #Advanced options
@login_required
def index():
    return render_template("index.html")

#Aşağısı temizlendi -- zipped_data2 silinebilir mi? HTML üzerinde kontrol edilmeli. 20_06_24
#See all tasks - this new version is a simplified version of the older versions for easier use
@app.route("/see_my_tasks_briefly", methods=['GET', 'POST'])
@login_required
def see_my_tasks_briefly():
    user_email = current_user.email_db
    
    #Retrieving all task types with step names
    all_task_types = groovy_task_types_db.query.all()
    df_all_task_types = pd.DataFrame([r.__dict__ for r in all_task_types])
    
    #Below should be only showing non-archived 17_04_24
    #Tasks assigned to self
    my_tasks = groovy_tasks_db.query.filter(
    (groovy_tasks_db.subordinate_email_db == user_email) & (or_(groovy_tasks_db.archived_db != 1, groovy_tasks_db.archived_db == None))).order_by(groovy_tasks_db.date_added_db.desc()).all()
    
    #Tasks assigned to non-self users
    other_tasks = groovy_tasks_db.query.filter(
    and_(
        groovy_tasks_db.subordinate_email_db != user_email,
        or_(groovy_tasks_db.archived_db != 1, groovy_tasks_db.archived_db == None),
        groovy_tasks_db.process_owner_email_db == user_email
    )
    ).order_by(groovy_tasks_db.date_added_db.desc()).all()
    
    df_my_tasks = pd.DataFrame([r.__dict__ for r in my_tasks])
    
    if my_tasks:
        #Converting my specific task types into a list
        list_of_task_types = list(df_my_tasks["task_type_name_db"])
        
        # Creating an empty list of process steps to be rendered in each individual task's status update field
        list_of_ordered_task_process_steps = []
        
        #For each task type extracted; append the process step options to list of ordered task process steps
        for task_type in list_of_task_types:
            task_filter = df_all_task_types["task_type_name_db"] == task_type
            list_of_ordered_task_process_steps.append(list(df_all_task_types[task_filter]["task_step_names_db"]))
            
        if request.method == "GET":
            
            test_lists_of_options = list_of_ordered_task_process_steps
            #print("list_of_ordered_task_process_steps", list_of_ordered_task_process_steps)
            #print("test_lists_of_options", test_lists_of_options)
            zipped_data = zip(my_tasks,list_of_ordered_task_process_steps)
            zipped_data2 = zip(my_tasks,list_of_ordered_task_process_steps)

            #for item in zipped_data:
            #    print("item", item)
            
            #Below should be only showing non-archived 17_04_24
            my_tasks = groovy_tasks_db.query.filter(
            (groovy_tasks_db.subordinate_email_db == user_email) & (or_(groovy_tasks_db.archived_db != 1, groovy_tasks_db.archived_db == None))).order_by(groovy_tasks_db.date_added_db.desc()).all()
            
            return render_template("active_tasks_briefly.html", my_tasks=my_tasks, other_tasks=other_tasks,  zipped_data=zipped_data, zipped_data2=zipped_data2) #test_lists_of_options=list_of_ordered_task_process_steps,
    elif other_tasks:
        return render_template("active_tasks_briefly.html", other_tasks=other_tasks)
    else:
        return render_template("active_tasks_briefly.html")

    if request.method == "POST": #Burada kaldım.. devam edeceğim..
        
        #Get selected options from the form object on html.
        selected_options = request.form.getlist('selected_options[]')

        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        
        #Unpair the selected option for each task seen on the html (my or other tasks) in a for loop
        for task, option in zip(my_tasks, selected_options):
            
            #Get all relevant task types from database to extract their step_names for my or other tasks
            
            all_task_steps = groovy_task_types_db.query.filter(groovy_task_types_db.task_type_name_db==task.task_type_name_db).all()
            
            #Below is a mechanism for identifying whether the selected option for a particular task is the last option in the flow list.
            #This way, we save a final status (final_status_db) to the database about this task. We can filter tasks at their final status accordingly. For example an auto-archive option may be added to the app.
            
            #Keep in mind that, every task step is another row in the database. Therefore, we retrieve all rows for a specific task type.
            #Then we find the last one ([-1]) and get the step_name_db on that record/row.
            #Will print each task, its last step and the selected option below within the for loop above.
            #Did not delete these prints for clarity of the mechanism. 20_06_24
            print("End of steps list = ", all_task_steps[-1].task_step_names_db, "> - Selected option = ", option)
            print("----------------------------")
            if all_task_steps[-1].task_step_names_db==option:
                print("End of task steps list")
                task.final_status_db = 1
                db.session.commit()
            elif all_task_steps[-1].task_step_names_db!=task.task_status_db:
                print("Still going to go to go..")
                task.final_status_db = 0
                db.session.commit()
            
            #If there is a selected option for a particular task within the POST request; the status of the task will be saved.
            #Also its log will be saved to logs with the current date.
            if option!="":
                print("Status modified as: ",  option)
                task.task_status_db = option
                new_log = status_logs_db(
                    sender_db = user_email,
                    status_changed_to_db = option,
                    date_of_status_change_db = dt_string,
                    task_id_db = task.id
                )
                db.session.add(new_log)
                db.session.commit()
            else:
                print("No change in this task's status. Current status is : ", task.task_status_db)

        #Below should be only showing non-archived 17_04_24
        #Updating the information on the page after POST request.
        
        #One question here : check whether zipped_data2 is necessary here. 20_06_2024
        
        my_tasks = groovy_tasks_db.query.filter(
        (groovy_tasks_db.subordinate_email_db == user_email) & (or_(groovy_tasks_db.archived_db != 1, groovy_tasks_db.archived_db == None))).order_by(groovy_tasks_db.date_added_db.desc()).all()

        test_lists_of_options = list_of_ordered_task_process_steps
        zipped_data = zip(my_tasks,test_lists_of_options)
        zipped_data2 = zip(my_tasks,test_lists_of_options)
        
        return render_template("active_tasks_briefly.html", my_tasks=my_tasks, test_lists_of_options=test_lists_of_options, zipped_data=zipped_data, zipped_data2=zipped_data2, other_tasks=other_tasks)
    
    
    return render_template("active_tasks_briefly.html", my_tasks=my_tasks, other_tasks=other_tasks)

#Aşağısı temizlendi -- 1 yerdeki commented out kısım silinebilir!!
#Adds a new task to general tasks database table - task can be assigned to user herself or someone else
@app.route("/new_task_assignment", methods=['GET', 'POST'])
@login_required
def new_task_assignment():
    
    user_email = current_user.email_db
    form = new_task_assignment_form()
    
    #Identifying the unique task flow types for the task type dropdown menu from the database
    task_types_data = groovy_task_types_db.query.all()
    data_dict_list = [item.__dict__ for item in task_types_data]
    df = pd.DataFrame(data_dict_list)
    
    task_types_list = df["task_type_name_db"].unique()
    
    #Passing the extracted choices_lists to front-end to be displayed in each 
    if request.method == "GET":
        #Assigning extracted task types to form class' choices arrtibute
        form.task_type_name.choices = [(column, column) for column in task_types_list]
        print("Choices list:", task_types_list)
        
        return render_template("new_task_assignment.html", form=form)
    
    elif request.method == "POST":

        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        user_country = current_user.country_db

        #Identifying the unique process steps
        process_step_data = groovy_task_types_db.query.filter(groovy_task_types_db.task_type_name_db==form.task_type_name.data).all()

        #Consider cleaning as it seems not used! 20 06 24
        #data_dict_list = [item.__dict__ for item in process_step_data]
        #df_process_steps = pd.DataFrame(data_dict_list)
                
        #Setting acceptance required mechanism
        if form.acceptance_required_or_not.data == "Acceptance Required":
            status_to_be_updated = "Acceptance Waited"
        else :
            status_to_be_updated = "New"
        
        #Saving the new task on database
        new_task = groovy_tasks_db(
                task_name_db = form.task_name.data,
                task_type_name_db = form.task_type_name.data,
                task_status_db = status_to_be_updated, #list(process_steps_list)[0]
                final_status_db = 0,
                process_owner_email_db = user_email,
                subordinate_email_db = form.subordinate_email.data,
                urgent_or_not_db = form.urgent_or_not.data,
                acceptance_required_or_not_db = form.acceptance_required_or_not.data,
                country_db = user_country,
                date_added_db = dt_string
                )
        
        db.session.add(new_task)
        db.session.commit()
        
        #Handled separately, as previous version created some id mis-calculations after deletions.
        #Below adds a new log to logs table for the newly created task. This may be used later for duration calculations.
        latest_id = db.session.query(db.func.max(groovy_tasks_db.id)).scalar()
        print(">>>>>>ID of the latest task is: ", latest_id)
        new_log = status_logs_db(
                    sender_db = user_email,
                    status_changed_to_db = "Newly Assigned",
                    date_of_status_change_db = dt_string,
                    task_id_db = latest_id)
        db.session.add(new_log)
        db.session.commit()
        flash("Yeni görev oluşturuldu...", "success")
                
        #Comment out will be removed on Ubuntu - 20_06_24
        #return redirect("http://38.242.143.89:84/see_my_tasks_briefly")
        #return  render_template("active_tasks_briefly.html", my_tasks=my_tasks, test_lists_of_options=test_lists_of_options, zipped_data=zipped_data, zipped_data2=zipped_data2)
        return redirect(url_for("see_my_tasks_briefly"))

    return render_template("new_task_assignment.html", form=form)

#Accept task in those cases where an assignee's approval is requested
@app.route('/accept_one_case/<int:id>', methods=["GET", "POST"])
@login_required
def accept_one_case(id):

    user_email = current_user.email_db
    task_to_modify = groovy_tasks_db.query.get_or_404(id)
    task_to_modify.task_status_db = "New"
    task_to_modify.acceptance_required_or_not_db = "Accepted"

    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
    print("ID of task to be accepted :", id)
    new_log = status_logs_db(
                    sender_db = user_email,
                    status_changed_to_db = "Accepted",
                    date_of_status_change_db = dt_string,
                    task_id_db = id
                )
    db.session.add(new_log)
    db.session.commit()

    #Keeping the commented out section on purpose in case of a malfunction in redirect("http//:ip_address") scenario
    #------------- Re-calculating the remaining tasks, their statuses and so on.. 20.09.23 (We do this with render_template rather than with redirect because, on remote vps; redirect created problems such as freezing etc.) 20.09.23
    #-------------
    #-------------
    """
    #Retrieving all tasks
    all_task_types = groovy_task_types_db.query.all()
    df_all_task_types = pd.DataFrame([r.__dict__ for r in all_task_types])
    
    #Below should be only showing non-archived 17_04_24
    my_tasks = groovy_tasks_db.query.filter(
    (groovy_tasks_db.subordinate_email_db == user_email) & (or_(groovy_tasks_db.archived_db != 1, groovy_tasks_db.archived_db == None))).order_by(groovy_tasks_db.date_added_db.desc()).all()
    
    df_my_tasks = pd.DataFrame([r.__dict__ for r in my_tasks])
    
    #Converting my specific tasks types into a list
    list_of_task_types = list(df_my_tasks["task_type_name_db"])
    list_of_ordered_task_process_steps = []
    
    for task_type in list_of_task_types:
        task_filter = df_all_task_types["task_type_name_db"] == task_type
        list_of_ordered_task_process_steps.append(list(df_all_task_types[task_filter]["task_step_names_db"]))
    test_lists_of_options = list_of_ordered_task_process_steps
    zipped_data = zip(my_tasks,test_lists_of_options)
    zipped_data2 = zip(my_tasks,test_lists_of_options)

    """
        
    #Comment out will be removed on Ubuntu - 20_06_24
    #return redirect("http://38.242.143.89:84/see_my_tasks_briefly")
    #return  render_template("active_tasks_briefly.html", my_tasks=my_tasks, test_lists_of_options=test_lists_of_options, zipped_data=zipped_data, zipped_data2=zipped_data2)
    return redirect(url_for("see_my_tasks_briefly"))
    
    #Check the above mechanism on remote. We had issues with redirect function on remote. 31-05-24
    """try:
        db.session.commit()
        flash("Case has been succesfully accepted.", "success")
        #return render_template("see_all_cases.html", all_cases=all_cases, id=id)
        return redirect(url_for('see_my_tasks', all_cases=all_cases, id=id))
            
    except:
        db.session.commit()
        flash("There has been a problem during updating process. Please inform your IT Administrator.", "success")
        #return render_template("see_all_cases.html", all_cases=all_cases,id=id)
        return redirect(url_for('see_my_tasks', all_cases=all_cases, id=id))"""

#For viewing the details of a general task including the calendar events and messages about this task
@app.route("/see_one_task/<int:id>", methods=['GET', 'POST'])
@login_required
def see_one_task(id):
    user_email = current_user.email_db
        
    form = groovy_conversations()
    task_to_show = groovy_tasks_db.query.get_or_404(id)
    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
    
    #For passing conversation messages of the task
    conversation_about_this_task = groovy_conversations_db.query.filter(groovy_conversations_db.task_id_db==task_to_show.id).order_by(groovy_conversations_db.date_of_sending_db.desc()).all()
    
    #For passing calendar events of the task
    calendar_events_for_this_task = groovy_calendar_db.query.filter(groovy_calendar_db.task_id==id).order_by(groovy_calendar_db.date_time_db.desc()).all()

    if task_to_show:
        print("there is a task to show, task type name :",task_to_show.task_type_name_db)
        print("there is a task to show, task name :",task_to_show.task_name_db)

    if request.method == "POST":
        conversation_to_be_recorded = groovy_conversations_db(
                    sender_db = user_email,
                    date_of_sending_db = dt_string,
                    text_db = form.message.data,
                    task_id_db = task_to_show.id)
        
        if form.message.data:
            db.session.add(conversation_to_be_recorded)
            db.session.commit()
            flash("Mesaj kaydedildi...", "success")
            conversation_about_this_task = groovy_conversations_db.query.filter(groovy_conversations_db.task_id_db==task_to_show.id).order_by(groovy_conversations_db.date_of_sending_db.desc()).all()

        return render_template("see_one_task.html", task_to_show=task_to_show, form=form, conversation_about_this_task=conversation_about_this_task, calendar_events_for_this_task=calendar_events_for_this_task)

    return render_template("see_one_task.html", task_to_show=task_to_show, form=form, conversation_about_this_task=conversation_about_this_task, calendar_events_for_this_task=calendar_events_for_this_task)
    

#Archiving the task for cleaning the active tasks screens
@app.route('/archive_one_case/<int:id>', methods=["GET", "POST"])
@login_required
def archive_one_case(id):#Sadece non-archived görünecek şekilde modifiye edelim..
    
    user_email = current_user.email_db
    
    task_to_modify = groovy_tasks_db.query.get_or_404(id)
    task_to_modify.archived_db = 1
    task_to_modify.acceptance_required_or_not_db = "Accepted"

    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
    print("ID of task to be accepted :", id)
    new_log = status_logs_db(
                    sender_db = user_email,
                    status_changed_to_db = "Archived",
                    date_of_status_change_db = dt_string,
                    task_id_db = id)
    db.session.add(new_log)
    db.session.commit()

    #Keeping the commented out section on purpose in case of a malfunction in redirect("http//:ip_address") scenario
    #------------- Re-calculating the remaining tasks, their statuses and so on.. 20.09.23 (We do this with render_template rather than with redirect because, on remote vps; redirect created problems such as freezing etc.) 20.09.23
    """#-------------
    
    #Retrieving all tasks
    all_task_types = groovy_task_types_db.query.all()
    df_all_task_types = pd.DataFrame([r.__dict__ for r in all_task_types])
    
    #Retrieving my tasks
    #my_tasks = groovy_tasks_db.query.filter(groovy_tasks_db.subordinate_email_db==user_email).order_by(groovy_tasks_db.date_added_db.desc()).all()
    #my_tasks = groovy_tasks_db.query.filter((groovy_tasks_db.subordinate_email_db == user_email) & (groovy_tasks_db.archived_db != 1)).order_by(groovy_tasks_db.date_added_db.desc()).all()
    
    #Only those non-archived tasks
    my_tasks = groovy_tasks_db.query.filter(
    (groovy_tasks_db.subordinate_email_db == user_email) & (or_(groovy_tasks_db.archived_db != 1, groovy_tasks_db.archived_db == None))).order_by(groovy_tasks_db.date_added_db.desc()).all()
    
    df_my_tasks = pd.DataFrame([r.__dict__ for r in my_tasks])
    
    #Converting my specific tasks types into a list
    list_of_task_types = list(df_my_tasks["task_type_name_db"])
    list_of_ordered_task_process_steps = []
    
    for task_type in list_of_task_types:
        task_filter = df_all_task_types["task_type_name_db"] == task_type
        list_of_ordered_task_process_steps.append(list(df_all_task_types[task_filter]["task_step_names_db"]))
    test_lists_of_options = list_of_ordered_task_process_steps
    zipped_data = zip(my_tasks,test_lists_of_options)
    zipped_data2 = zip(my_tasks,test_lists_of_options)

    """
    
    #return  render_template("active_tasks_briefly.html", my_tasks=my_tasks, test_lists_of_options=test_lists_of_options, zipped_data=zipped_data, zipped_data2=zipped_data2)
    #Comment out will be removed on Ubuntu - 20_06_24
    #return redirect("http://38.242.143.89:84/see_my_tasks_briefly")
    return redirect(url_for("see_my_tasks_briefly"))
    
#Deleting a task from general tasks database table.
@app.route('/delete_task/<int:id>', methods=["GET", "POST"])
@login_required
def delete_task(id):
    user_email = current_user.email_db
    task_to_delete = groovy_tasks_db.query.get_or_404(id)
    
    try:
                
        #------Deleting the conversations logs for this task_id first
        
        # Delete all matching records from groovy_conversations_db
        conversation_records = groovy_conversations_db.query.filter(groovy_conversations_db.task_id_db == id).all()
    
        for conversation_record in conversation_records:
            db.session.delete(conversation_record)
    
        # Delete all matching records from status_logs_db
        status_log_records = status_logs_db.query.filter(status_logs_db.task_id_db == id).all()
    
        for status_log_record in status_log_records:
            db.session.delete(status_log_record)
        
        db.session.delete(task_to_delete)
        db.session.commit()
        flash("Görev silindi.", "success")
        
        #Keeping the commented out section on purpose in case of a malfunction in redirect("http//:ip_address") scenario
        #------------- 
        # Re-calculating the remaining tasks, their statuses and so on.. 20.09.23 
        # (We do this with render_template rather than with redirect because, 
        # on remote vps; redirect created problems such as freezing etc.) 20.09.23
        #-------------
        
        """
        #Retrieving all tasks
        all_task_types = groovy_task_types_db.query.all()
        df_all_task_types = pd.DataFrame([r.__dict__ for r in all_task_types])
        
        #Retrieving my tasks
        my_tasks = groovy_tasks_db.query.filter(groovy_tasks_db.subordinate_email_db==user_email).order_by(groovy_tasks_db.date_added_db.desc()).all()
        #Below should be only showing non-archived 17_04_24
        my_tasks = groovy_tasks_db.query.filter(
        (groovy_tasks_db.subordinate_email_db == user_email) & (or_(groovy_tasks_db.archived_db != 1, groovy_tasks_db.archived_db == None))).order_by(groovy_tasks_db.date_added_db.desc()).all()


        df_my_tasks = pd.DataFrame([r.__dict__ for r in my_tasks])
        
        #Converting my specific tasks types into a list
        list_of_task_types = list(df_my_tasks["task_type_name_db"])
        list_of_ordered_task_process_steps = []
        
        for task_type in list_of_task_types:
            task_filter = df_all_task_types["task_type_name_db"] == task_type
            list_of_ordered_task_process_steps.append(list(df_all_task_types[task_filter]["task_step_names_db"]))
        test_lists_of_options = list_of_ordered_task_process_steps
        zipped_data = zip(my_tasks,test_lists_of_options)
        zipped_data2 = zip(my_tasks,test_lists_of_options)
        #-------------
        #-------------
        """
        #return  render_template("active_tasks_briefly.html", my_tasks=my_tasks, test_lists_of_options=test_lists_of_options, zipped_data=zipped_data, zipped_data2=zipped_data2)
        return redirect(url_for("see_my_tasks_briefly"))
        
        #Comment out will be removed on Ubuntu - 20_06_24
        #return redirect("http://38.242.143.89:84/see_my_tasks_briefly")

        
    except:

        #Below should be only showing non-archived records 17_04_24
        my_tasks = groovy_tasks_db.query.filter(
        (groovy_tasks_db.subordinate_email_db == user_email) & (or_(groovy_tasks_db.archived_db != 1, groovy_tasks_db.archived_db == None))).order_by(groovy_tasks_db.date_added_db.desc()).all()
        flash("There is a problem in deletion of the record. Please inform your administrator.", 'error')
        return  render_template("active_tasks_briefly.html", my_tasks=my_tasks)

#Create a new routine task - separate from other general tasks, these are completed regularly
@app.route('/create_task', methods=['GET', 'POST'])
@login_required
def create_task():
    if request.method == 'POST':
        task_name = request.form['task_name']
        period = request.form['period']
        deadline_date = request.form.get('deadline_date')
        today = datetime.now()
        
        # Create a new routine task
        new_task = groovy_routine_tasks_db(
            task_name_db = task_name,
            period_db = period,
            date_due_db = datetime.strptime(deadline_date, '%Y-%m-%d') if deadline_date else None,
            task_status_db = "uncompleted",
            archived_db = 0,
            process_owner_email_db = current_user.email_db,
            date_added_db = today)
        
        # Add the new task to the database
        db.session.add(new_task)
        db.session.commit()
        
        return redirect(url_for('see_and_modify_routine_tasks'))
    
    return render_template('new_routine_task.html')

#For viewing and modifying routine tasks - once completed a new task is automatically created for the next month
@app.route("/see_and_modify_routine_tasks", methods=['GET', 'POST'])
@login_required
def see_and_modify_routine_tasks():
    
    #all_routine_tasks = groovy_routine_tasks_db.query.filter_by(task_status_db='uncompleted').all()
    #Sorting for date_due_db
    all_routine_tasks = groovy_routine_tasks_db.query.filter_by(task_status_db='uncompleted').order_by(groovy_routine_tasks_db.date_due_db).all()
    
    return render_template("routine_tasks.html", all_routine_tasks=all_routine_tasks)

#For marking a routine task as completed and creating a new task for the next period
@app.route('/complete-task/<int:task_id>', methods=['POST'])
def complete_task(task_id):
    task = groovy_routine_tasks_db.query.get(task_id)
    print("Task ID to be completed:", task.id)
    
    if task:
        
        # Get the current date
        today = datetime.now()
        
        # Calculate the exact same day of the next month
        one_month_later = task.date_due_db + relativedelta(months=1)
        
        #Updating the routine task as completed
        task.task_status_db = 'completed'
        task.final_status_db = 1
        task.archived_db = 0
        task.date_completed_db = today

        #Commit changes
        db.session.commit()

        # Creating a new task for the next month same day
        new_task = groovy_routine_tasks_db(
        task_name_db = task.task_name_db,
        period_db = task.period_db,
        task_status_db = 'uncompleted',
        final_status_db = 0,
        archived_db = 0,
        process_owner_email_db=current_user.email_db,
        date_added_db=one_month_later,
        date_due_db=one_month_later)

        # Add the new task to the database session and commit
        db.session.add(new_task)
        db.session.commit()

        # Fetch the updated tasks list
        #all_routine_tasks = groovy_routine_tasks_db.query.filter_by(task_status_db='uncompleted').all()
        #Sorting for date_due_db
        all_routine_tasks = groovy_routine_tasks_db.query.filter_by(task_status_db='uncompleted').order_by(groovy_routine_tasks_db.date_due_db).all()


        tasks = [{  'id': t.id, 
                    'task_name_db': t.task_name_db, 
                    'task_status_db': t.task_status_db, 
                    'date_due_db': t.date_due_db.isoformat()} for t in all_routine_tasks]

        return jsonify({'message': 'Task completed successfully', 'tasks': tasks}), 200
        #return redirect("/see_and_modify_routine_tasks")
        #all_routine_tasks = groovy_routine_tasks_db.query.filter_by(task_status_db='uncompleted').all()
        #return render_template("routine_tasks.html",  all_routine_tasks=all_routine_tasks)
    else:
        return jsonify({'message': 'Task not found'}), 404

#Calendar route for assigning and viewing tasks on calendar (JS FullCalendar is used)
@app.route('/calendar')
@login_required
def calendar():
        
    return render_template('calendar.html')

#For fetching events from database table to display on the HTML calendar (FullCalendar)
@app.route('/events')
def get_events():
    
    user_email = current_user.email_db
    
    #Fetching only relevant events from calendar - either assigned to current user or assigned by current user 31-05-2024
    my_events_from_db = groovy_calendar_db.query.filter_by(assigned_user_email_db=user_email).all()
    other_events_from_db = db.session.query(groovy_calendar_db).filter(and_(groovy_calendar_db.user_email_db == user_email,
            groovy_calendar_db.assigned_user_email_db != user_email)).all()
    
    # Serialize events into a JSON-compatible format
    events = []
    for event in my_events_from_db:
        events.append({
            'id': event.id,
            'start': str(event.date_time_db),  # Convert datetime to string
            'title': event.title_db,
            'user_email': event.user_email_db,
            'assigned_user_email': event.assigned_user_email_db
        })
    for event in other_events_from_db:
        events.append({
            'id': event.id,
            'start': str(event.date_time_db),  # Convert datetime to string
            'title': event.title_db,
            'user_email': event.user_email_db,
            'assigned_user_email': event.assigned_user_email_db
        })
    
    # Return events data as JSON
    return jsonify(events)

#Adding an event to calendar. Database table is groovy_calendar_db
@app.route('/add_event', methods=['POST'])
def add_event():
    
    user_email = current_user.email_db
    # Extract event data from JSON request
    event_data = request.json
    start = event_data['start']
    title = event_data['title']
    assigned_user_email = event_data['assigned_user_email']
    #telephone = event_data['telephone']

    # Create a new event instance
    new_event = groovy_calendar_db(
        date_time_db=start,
        title_db=title,
        user_email_db=user_email,
        assigned_user_email_db=assigned_user_email
    )

    # Add the new event to the database session
    db.session.add(new_event)
    # Commit changes to the database
    db.session.commit()

    return jsonify({'message': 'Event added successfully'})

#Deleting an event from calendar. Database table is groovy_calendar_db
@app.route('/delete_event/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    # Retrieve the event from the database
    event_to_delete = groovy_calendar_db.query.get_or_404(event_id)
    
    # Delete the event from the database
    db.session.delete(event_to_delete)
    db.session.commit()
    return jsonify({'message': 'Event deleted successfully'})

#For assigning a date for a task on the general tasks. Calendar items are kept in a separate Mysql table.
@app.route("/one_task_to_calendar/<int:id>", methods=['GET', 'POST'])
@login_required
def one_task_to_calendar(id):
    form = groovy_calendar()
    task_to_be_sent_to_calendar = groovy_tasks_db.query.get_or_404(id)

    if request.method == "GET":       

        return render_template("one_task_to_calendar.html", form=form, task_to_be_sent_to_calendar=task_to_be_sent_to_calendar)
    return render_template("one_task_to_calendar.html", form=form)

#For assigning a date for a task on the general tasks. Calendar items are kept in a separate Mysql table.
@app.route('/submit_datetime', methods=['POST'])
@login_required
def submit_datetime():
    datetime_value = request.form['datetimeInput']
    task_id = request.form['taskId']
    task_to_be_sent_to_calendar = groovy_tasks_db.query.get_or_404(task_id)
       
    # Parse the datetime string for MYSQL
    parsed_datetime = datetime.fromisoformat(datetime_value)

    # Format the datetime as required for MySQL DateTime field
    formatted_datetime = parsed_datetime.strftime('%Y-%m-%d %H:%M:%S')
        
    #Saving to database
    new_calendar_item = groovy_calendar_db(
            date_time_db = formatted_datetime,
            task_id = task_id,
            title_db = task_to_be_sent_to_calendar.task_name_db,
            user_email_db = current_user.email_db,
            assigned_user_email_db = task_to_be_sent_to_calendar.subordinate_email_db 
        )
    db.session.add(new_calendar_item)
    db.session.commit()
    
    flash("Görev takvime eklendi...", "success")
    return redirect(url_for('see_my_tasks_briefly'))
    #Comment out will be removed on Ubuntu - 20_06_24
    #return redirect("http://38.242.143.89:84/see_my_tasks_briefly")

#Creating a new process flow for tasks - e.g. Not only Completed - Not Completed - For example as : 0% 25% 50% 75% 100%
#Main idea here was to enable users to define custom steps for a task
@app.route('/new_task_definition', methods=["GET",'POST'])
@login_required
def new_task_definition():
    form = task_type_definition()
    form2 = task_step_addition()
    
    if request.method == "POST":
        
        user_email = current_user.email_db
        user_country = current_user.country_db
        
        if form.task_type_name.data:
            
            #New task flow type
            new_task_type = groovy_task_types_db(
                task_type_name_db = form.task_type_name.data,
                task_step_names_db = form.task_first_step_name.data,
                process_owner_email_db = user_email,
                country_db = user_country)
            db.session.add(new_task_type)
            db.session.commit()
            flash("Yeni görev türü eklendi", "success")
        if form2.new_task_process_step.data:
            print("Yeni eklenecek görev akış adımı mevcut.. %75 % 90 gibi... -------------")
            print(form2.new_task_process_step.data)
            
            current_task_edited = groovy_task_types_db.query.order_by(groovy_task_types_db.id.desc()).first() 
            
            #For tracking the new process step on the terminal easily
            print("Current task id:", current_task_edited.id)           
            print("Current task type name id:", current_task_edited.task_type_name_db)
            
            #New task step
            new_task_step = groovy_task_types_db(
                task_type_name_db = current_task_edited.task_type_name_db,
                task_step_names_db = form2.new_task_process_step.data,
                process_owner_email_db = user_email,
                country_db = user_country)
            db.session.add(new_task_step)
            db.session.commit()
            flash("Yeni görev adımı başarıyla eklendi...", "success")

        return render_template("new_task_definition.html", form=form, form2=form2, task_type_name=form.task_type_name.data, new_task_step=form2.new_task_process_step.data)
    
    return render_template("new_task_definition.html", form=form, form2=form2)

#Displaying available task flow types - this is under advanced options menu
@app.route("/see_task_types", methods=['GET', 'POST'])
@login_required
def see_task_types():
    print("see task types ----")

    # Fetch data from the MySQL table using SQLAlchemy
    data = groovy_task_types_db.query.all()

    # Convert the SQLAlchemy query result to a list of dictionaries
    data_dict_list = [item.__dict__ for item in data]

    # Create a pandas DataFrame from the list of dictionaries
    df = pd.DataFrame(data_dict_list)

    return render_template("see_task_types.html", task_types_process_steps=[df.to_html(index=True)])

#Displaying activity logs - this is created for especially if we will need to report time between status changes
@app.route('/see_logs', methods=["GET", "POST"])
@login_required
def show_logs():
    # Fetch data from the MySQL table using SQLAlchemy
    data = status_logs_db.query.all()

    # Convert the SQLAlchemy query result to a list of dictionaries
    data_dict_list = [item.__dict__ for item in data]

    # Create a pandas DataFrame from the list of dictionaries
    df = pd.DataFrame(data_dict_list)

    return render_template("see_logs.html", task_logs=[df.to_html(index=True)])

#Login function
@app.route("/login", methods=['GET', 'POST'])
def login():
    
    if current_user.is_authenticated:
        print("User is ALREADY LOGGED IN")
        return redirect(url_for('index2'))
        #Comment out will be removed on Ubuntu - 20_06_24
        #return redirect("http://38.242.143.89:84/index2")
    form = login_form()
    if form.validate_on_submit():
        user = str_staff_db2.query.filter_by(email_db=form.email.data).first()
        if user:
            password = user.password_db
            password_check = bcrypt.check_password_hash(password, form.password.data)
            
        if user and password_check:
            login_user(user)
            
            #For recording last login time
            now = datetime.now()
            dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
            user.last_login_db = dt_string
            db.session.commit()
            
            print("New user login. User name: ", current_user.name_db, "User Role :", current_user.role_db)
            flash('Sisteme hoş geldin... İşlerinde kolaylıklar dilerim...', 'success')

            return redirect('/index2')
            #Comment out will be removed on Ubuntu - 20_06_24
            #return redirect("http://38.242.143.89:84/index2")
            
            
        else:
            flash('There has been a problem during logging in. Please check your username and password', 'error')
    return render_template('login.html', title='Login', form=form)
    
#Logout function
@app.route("/logout")
def logout():
    if current_user.is_authenticated:
        
        logout_user()
        print("Current user logged out")
        flash('Güzel bir gün dilerim...', 'success')
    
    return render_template('index2.html')
    
