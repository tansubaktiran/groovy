import os
import pandas as pd
from sqlalchemy import create_engine, or_ , and_

from groovy1 import app, db, bcrypt
from groovy1.forms import myform, login_form, fileuploadform, employee_entry_form #11.05.2022


from flask import render_template, url_for, flash, redirect, request, send_file, jsonify

from flask_login import login_user, current_user, logout_user, login_required
from groovy1.forms import myform, login_form, str_import_entry_form, str_case_approval, delete_confirm, task_type_definition, task_step_addition, new_task_assignment_form, groovy_conversations, groovy_calendar
from groovy1.models import str_cases_db2, str_staff_db2, groovy_task_types_db, groovy_tasks_db, groovy_conversations_db, status_logs_db, groovy_calendar_db

from datetime import datetime, date, timedelta
from email.message import EmailMessage
import smtplib


#-- Calendar 08 05 24

#Calendar
@app.route('/calendar')
@login_required
def calendar():
    print("Calendar >------->")
    #print(events)
    return render_template('calendar.html')

#Events for current user eklenecek - 08_05_2024 - MY TASKS - TASKS I ASSIGNED CALENDAR üzerinde görünmüyor??
@app.route('/events')
def get_events():
    
    user_mail = current_user.email_db
    # Fetch events from the database
    #events_from_db = groovy_calendar_db.query.all()
    events_from_db = groovy_calendar_db.query.filter_by(assigned_user_email_db=user_mail).all() #Events for current user eklenecek - 08_05_2024

    
    # Serialize events into a JSON-compatible format
    events = []
    for event in events_from_db:
        events.append({
            'id': event.id,
            'start': str(event.date_time_db),  # Convert datetime to string
            'title': event.title_db,
            'user_email': event.user_email_db,
            'assigned_user_email': event.assigned_user_email_db
        })
    
    # Return events data as JSON
    return jsonify(events)

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

@app.route('/delete_event/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    # Retrieve the event from the database
    event_to_delete = groovy_calendar_db.query.get_or_404(event_id)
    
    # Delete the event from the database
    db.session.delete(event_to_delete)
    db.session.commit()



#-- Calendar 08 05 24

#Task management test -1 25.08.2023 12:31
@app.route('/new_task_definition', methods=["GET",'POST'])
@login_required
def new_task_definition():
    form = task_type_definition()
    form2 = task_step_addition()
    print("New task definition function")
    
    if request.method == "POST":
        

        print("------------")
        print(form2.new_task_process_step.data)
        print("------------")
        
        user_email = current_user.email_db
        user_country = current_user.country_db
        
        if form.task_type_name.data:
            print("There is a new task type------------")
            print(form.task_type_name.data)
            print("------------")
            new_task_type = groovy_task_types_db(
                task_type_name_db = form.task_type_name.data,
                task_step_names_db = form.task_first_step_name.data,
                process_owner_email_db = user_email,
                country_db = user_country)
            db.session.add(new_task_type)
            db.session.commit()
            flash("New task type has been added...", "success")
        if form2.new_task_process_step.data:
            print("There is a new process step------------")
            print(form2.new_task_process_step.data)
            print("------------")
            
            current_task_edited = groovy_task_types_db.query.order_by(groovy_task_types_db.id.desc()).first() 
            print("Current task id:", current_task_edited.id)
            
            print("Current task type name id:", current_task_edited.task_type_name_db)
            
            new_task_step = groovy_task_types_db(
                task_type_name_db = current_task_edited.task_type_name_db,
                task_step_names_db = form2.new_task_process_step.data,
                process_owner_email_db = user_email,
                country_db = user_country)
            db.session.add(new_task_step)
            db.session.commit()
            flash("New process step has been added...", "success")

        return render_template("new_task_definition.html", form=form, form2=form2, task_type_name=form.task_type_name.data, new_task_step=form2.new_task_process_step.data)
    
    return render_template("new_task_definition.html", form=form, form2=form2)

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
    print(df[["task_type_name_db", "task_step_names_db"]])

    return render_template("see_task_types.html", task_types_process_steps=[df.to_html(index=True)])


@app.route("/new_task_assignment", methods=['GET', 'POST'])
@login_required
def new_task_assignment():
    print("new_task_assignment ----")

    form = new_task_assignment_form()
    
    #Identifying the unique task types for dropdown menu
    data = groovy_task_types_db.query.all()
    data_dict_list = [item.__dict__ for item in data]
    df = pd.DataFrame(data_dict_list)
    #choices_list = ["Yes", "No"]
    choices_list = df["task_type_name_db"].unique()
    
        
    if request.method == "GET":
        form.task_type_name.choices = [(column, column) for column in choices_list]
        return render_template("new_task_assignment.html", form=form)
    elif request.method == "POST":
        print("Selected task type : ", form.task_type_name.data)

        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        print("<<<<<<<>>>>>>>>> type and value of dt_string", type(dt_string), dt_string)
        user_email = current_user.email_db
        user_country = current_user.country_db

        #
        #Identifying the unique process steps
        #process_step_data = groovy_task_types_db.query.all()
        process_step_data = groovy_task_types_db.query.filter(groovy_task_types_db.task_type_name_db==form.task_type_name.data).all() #.order_by(groovy_task_types_db.date_added_db.desc())

        data_dict_list = [item.__dict__ for item in process_step_data]
        df_process_steps = pd.DataFrame(data_dict_list)
        #choices_list = ["Yes", "No"]
        
        #IS THIS USED IN SOMEWHERE?
        #process_steps_list = df_process_steps["task_step_names_db"].unique()
        
        #Setting acceptance required mechanism
        if form.acceptance_required_or_not.data == "Acceptance Required":
            status_to_be_updated = "Acceptance Waited"
        else :
            status_to_be_updated = "New"
        
        new_task = groovy_tasks_db(
                task_name_db = form.task_name.data,
                task_type_name_db = form.task_type_name.data,
                task_status_db = status_to_be_updated, #list(process_steps_list)[0]
                process_owner_email_db = user_email,
                subordinate_email_db = form.subordinate_email.data,
                urgent_or_not_db = form.urgent_or_not.data,
                acceptance_required_or_not_db = form.acceptance_required_or_not.data,
                country_db = user_country,
                date_added_db = dt_string
                )
        #Get the latest id on the tasks database

        #07 09 23 - Look at the foreign key mechanism in tasks and logs tables.
        #Ensure a new task assignment works correctly. 07 09 23
        db.session.add(new_task)
        db.session.commit()
        #Handled separately, as previous version created some id mis-calculations after deletions.
        
        #try:
        latest_id = db.session.query(db.func.max(groovy_tasks_db.id)).scalar()
        print(">>>>>>Latest id is: ", latest_id)
        #except:
        #latest_id = 1
        print("<<<<>>>>>>> LATEST id", latest_id)
        new_log = status_logs_db(
                    sender_db = user_email,
                    status_changed_to_db = "Newly Assigned",
                    date_of_status_change_db = dt_string,
                    task_id_db = latest_id
                )
        db.session.add(new_log)
        
        
        db.session.commit()
        flash("New task has been assigned...", "success")
        
        return render_template("new_task_assignment.html", form=form)

    return render_template("new_task_assignment.html", form=form)


@app.route("/see_my_tasks", methods=['GET', 'POST'])
@login_required
def see_my_tasks():
    user_email = current_user.email_db
    user_country = current_user.country_db
    
    #Retrieving all tasks
    all_task_types = groovy_task_types_db.query.all()
    df_all_task_types = pd.DataFrame([r.__dict__ for r in all_task_types])
    #print("-----------------------------------------")

    #print("-----------------------------------------")
    #print(df_all_task_types[["task_type_name_db", "task_step_names_db"]])
    #print("All task types : ", all_task_types)
    
    #Retrieving my tasks
    #my_tasks = groovy_tasks_db.query.filter(groovy_tasks_db.subordinate_email_db==user_email).order_by(groovy_tasks_db.date_added_db.desc()).all()
    
    #Below should be only showing non-archived 17_04_24
    my_tasks = groovy_tasks_db.query.filter(
    (groovy_tasks_db.subordinate_email_db == user_email) & (or_(groovy_tasks_db.archived_db != 1, groovy_tasks_db.archived_db == None))).order_by(groovy_tasks_db.date_added_db.desc()).all()
    
    df_my_tasks = pd.DataFrame([r.__dict__ for r in my_tasks])
    
    #print("-------------my tasks", my_tasks)
    #for task in my_tasks:
    #    print("------------->>>>>", task.id, task.task_name_db, task.task_type_name_db)


    #print(df_my_tasks["task_type_name_db"])
    #Converting my specific tasks types into a list
    list_of_task_types = list(df_my_tasks["task_type_name_db"])
    #print(list_of_task_types)
    list_of_ordered_task_process_steps = []
    
    #Getting an ordered list of task types with their sub-steps (steps) and writing them to a list named list_of_ordered_task_process_steps as a list of lists to be used later on in the dynamic selec fields. 29.08.2023 (Done)
    # 29.08.2023 Burada kaldık. Hepsini bir tabloya koyacağız.. yani taskler ayrı ayrı rowlarda olacak ve sağdaki sütunda da drop down menu olacak. (Done) 
    # Sonra da elimizdeki son status listesini sırasıyla karıştırmadan database'e yazacağız. (Statü güncellemesi)
    
    for task_type in list_of_task_types:
        task_filter = df_all_task_types["task_type_name_db"] == task_type
        #print(df_all_task_types[task_filter]["task_step_names_db"])
        list_of_ordered_task_process_steps.append(list(df_all_task_types[task_filter]["task_step_names_db"]))
    #print("+++++++++++++++")
    #print(list_of_ordered_task_process_steps)
    
    
    if request.method == "GET":
        
        #test_lists_of_options = [["Trial1","Test2","Mest3"], ["Janu","Febr","Marc"], ["Bajaj","Triumph","BMW"]]
        test_lists_of_options = list_of_ordered_task_process_steps
        zipped_data = zip(my_tasks,test_lists_of_options)
        zipped_data2 = zip(my_tasks,test_lists_of_options)

        #my_tasks = groovy_tasks_db.query.filter(groovy_tasks_db.subordinate_email_db==user_email).order_by(groovy_tasks_db.date_added_db.desc()).all()
        #Below should be only showing non-archived 17_04_24
        my_tasks = groovy_tasks_db.query.filter(
        (groovy_tasks_db.subordinate_email_db == user_email) & (or_(groovy_tasks_db.archived_db != 1, groovy_tasks_db.archived_db == None))).order_by(groovy_tasks_db.date_added_db.desc()).all()

        return render_template("active_tasks.html", my_tasks=my_tasks, test_lists_of_options=test_lists_of_options, zipped_data=zipped_data, zipped_data2=zipped_data2)
    
    elif request.method == "POST":
        #selected_option = request.form.get('selected_option') #If there is only one selection option. If multiple, see below.29.08.2023
        selected_options = request.form.getlist('selected_options[]')
        print("Type of selected options", selected_options)
        
        # List of options per task to find out whether updated status is the last one. 23.09.2023
        

        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        
        for task, option in zip(my_tasks, selected_options):
            
            all_task_steps = groovy_task_types_db.query.filter(groovy_task_types_db.task_type_name_db==task.task_type_name_db).all()
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
            #print("One of the selected option :", option)
            #print("Task name :", task)
            #Updating the status records in the database
            
            if option!="": 
                print("Option",  option)
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
                print("Hello from else...")

        #For showing the updated statuses in the new table
        

        #user_to_be_updated = str_staff_db2.query.filter_by(id=current_user.id).first()
    
        #For recording last logout time
        #now = datetime.now()
        #dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        #user_to_be_updated.last_logout_db = dt_string
        #db.session.commit()

        #test_lists_of_options = [["Trial1","Test2","Mest3"], ["Janu","Febr","Marc"], ["Bajaj","Triumph","BMW"]]
        #my_tasks = groovy_tasks_db.query.filter(groovy_tasks_db.subordinate_email_db==user_email).order_by(groovy_tasks_db.date_added_db.desc()).all()
        #Below should be only showing non-archived 17_04_24
        my_tasks = groovy_tasks_db.query.filter(
        (groovy_tasks_db.subordinate_email_db == user_email) & (or_(groovy_tasks_db.archived_db != 1, groovy_tasks_db.archived_db == None))).order_by(groovy_tasks_db.date_added_db.desc()).all()

        test_lists_of_options = list_of_ordered_task_process_steps
        zipped_data = zip(my_tasks,test_lists_of_options)
        zipped_data2 = zip(my_tasks,test_lists_of_options)
        
        return render_template("active_tasks.html", my_tasks=my_tasks, test_lists_of_options=test_lists_of_options, zipped_data=zipped_data, zipped_data2=zipped_data2)
    
    
    return render_template("active_tasks.html", my_tasks=my_tasks)

@app.route("/see_tasks_I_assigned", methods=['GET', 'POST'])
@login_required
def see_tasks_I_assigned():

    user_email = current_user.email_db
    user_country = current_user.country_db
    
    #Retrieving all tasks
    all_task_types = groovy_task_types_db.query.all()
    df_all_task_types = pd.DataFrame([r.__dict__ for r in all_task_types])

    my_tasks = groovy_tasks_db.query.filter(groovy_tasks_db.process_owner_email_db==user_email).order_by(groovy_tasks_db.date_added_db.desc()).all()
    df_my_tasks = pd.DataFrame([r.__dict__ for r in my_tasks])
    
    
    #Converting my specific tasks types into a list
    list_of_task_types = list(df_my_tasks["task_type_name_db"])
    
    list_of_ordered_task_process_steps = []
    
    for task_type in list_of_task_types:
        task_filter = df_all_task_types["task_type_name_db"] == task_type
        list_of_ordered_task_process_steps.append(list(df_all_task_types[task_filter]["task_step_names_db"]))

    if request.method == "GET":
        
        test_lists_of_options = list_of_ordered_task_process_steps
        zipped_data = zip(my_tasks,test_lists_of_options)
        zipped_data2 = zip(my_tasks,test_lists_of_options)

        my_tasks = groovy_tasks_db.query.filter(groovy_tasks_db.process_owner_email_db==user_email).order_by(groovy_tasks_db.date_added_db.desc()).all()

        return render_template("tasks_i_assigned.html", my_tasks=my_tasks,  test_lists_of_options=test_lists_of_options, zipped_data=zipped_data, zipped_data2=zipped_data2)
    
    elif request.method == "POST":
        #selected_option = request.form.get('selected_option') #If there is only one selection option. If multiple, see below.29.08.2023
        selected_options = request.form.getlist('selected_options[]')
        print("Type of selected options", selected_options)
        
        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        
        for task, option in zip(my_tasks, selected_options):
            print("One of the selected option :", option)
            #Updating the status records in the database
            
            if option!="": 
                print("Option",  option)
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
                print("Hello from else...")

        
        my_tasks = groovy_tasks_db.query.filter(groovy_tasks_db.process_owner_email_db==user_email).order_by(groovy_tasks_db.date_added_db.desc()).all()
        test_lists_of_options = list_of_ordered_task_process_steps
        zipped_data = zip(my_tasks,test_lists_of_options)
        
        return render_template("tasks_i_assigned.html", my_tasks=my_tasks,  test_lists_of_options=test_lists_of_options, zipped_data=zipped_data)
    
    return render_template("tasks_i_assigned.html", my_tasks=my_tasks)

@app.route("/one_task_to_calendar/<int:id>", methods=['GET', 'POST'])
@login_required
def one_task_to_calendar(id):
    form = groovy_calendar()
    task_to_be_sent_to_calendar = groovy_tasks_db.query.get_or_404(id)


    if request.method == "GET":
        print("This is Get")

        return render_template("one_task_to_calendar.html", form=form, task_to_be_sent_to_calendar=task_to_be_sent_to_calendar)
    return render_template("one_task_to_calendar.html", form=form)


@app.route('/submit_datetime', methods=['POST'])
def submit_datetime():
    datetime_value = request.form['datetimeInput']
    task_id = request.form['taskId']
    task_to_be_sent_to_calendar = groovy_tasks_db.query.get_or_404(task_id)
    
    print("This is Post and datetime value is:", datetime_value)
    
    # Process the datetime value here
    # Parse the datetime string
    parsed_datetime = datetime.fromisoformat(datetime_value)

    # Format the datetime as required for MySQL DateTime field
    formatted_datetime = parsed_datetime.strftime('%Y-%m-%d %H:%M:%S')
    print("-------------")
    print("This is Post and FOrmATteD datetime value is:", formatted_datetime)
    print("Current user email:", current_user.email_db)
    print("Subordinate Email", task_to_be_sent_to_calendar.subordinate_email_db)
    print("Task name", task_to_be_sent_to_calendar.task_name_db)
    print("-------------")
    
    #Database saving part
    new_calendar_item = groovy_calendar_db(
            date_time_db = formatted_datetime,
            task_id = task_id,
            title_db = task_to_be_sent_to_calendar.task_name_db,
            user_email_db = current_user.email_db,
            assigned_user_email_db = task_to_be_sent_to_calendar.subordinate_email_db 
        )
    
    db.session.add(new_calendar_item)
    db.session.commit()
    #Database saving part
    
    flash("Calendar event has been saved...", "success")
    return redirect(url_for('see_my_tasks'))
    #return render_template("active_tasks.html")
    #return 'Datetime submitted successfully'



@app.route("/see_one_task/<int:id>", methods=['GET', 'POST'])
@login_required
def see_one_task(id):
    user_email = current_user.email_db
    user_country = current_user.country_db
    
    form = groovy_conversations()
    task_to_show = groovy_tasks_db.query.get_or_404(id)
    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
    conversation_about_this_task = groovy_conversations_db.query.filter(groovy_conversations_db.task_id_db==task_to_show.id).order_by(groovy_conversations_db.date_of_sending_db.desc()).all()
    
    if task_to_show:
        print("there is a task to show, task type name :",task_to_show.task_type_name_db)
        print("there is a task to show, task name :",task_to_show.task_name_db)

    if request.method == "POST":
        #Logs - hem mesajlar hem de statü değişimleri için. Sonra da raporlama ekranı olacak. Toplam task başına kaç mesajlaşma olmuş. Statü değişimleri ne kadar süre almış? 31.08.2023
        #Buraya var ise takvim kayıtları da alınabilir.. 09.05.2024
        
        conversation_to_be_recorded = groovy_conversations_db(

                    sender_db = user_email,
                    date_of_sending_db = dt_string,
                    text_db = form.message.data,
                    task_id_db = task_to_show.id)
        
        if form.message.data:
            db.session.add(conversation_to_be_recorded)
            db.session.commit()
            flash("Message has been sent...", "success")
            conversation_about_this_task = groovy_conversations_db.query.filter(groovy_conversations_db.task_id_db==task_to_show.id).order_by(groovy_conversations_db.date_of_sending_db.desc()).all()

        return render_template("see_one_task.html", task_to_show=task_to_show, form=form, conversation_about_this_task=conversation_about_this_task)


    return render_template("see_one_task.html", task_to_show=task_to_show, form=form, conversation_about_this_task=conversation_about_this_task)
    
# &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
#----17_04_24 archiving work to be copied to remote

@app.route('/archive_one_case/<int:id>', methods=["GET", "POST"])
@login_required
def archive_one_case(id):#Sadece non-archived görünecek şekilde modifiye edelim..

    user_name = current_user.name_db
    user_role = current_user.role_db
    user_email = current_user.email_db
    
    #all_cases = str_cases_db.query.filter(str_cases_db.operation_type_db=="Import to Turkey").order_by(str_cases_db.id.desc()).all()
    #We put a filter here as we do not want to havev a large all_cases object while we pass to Jinja1. 05_12_2022
    all_cases = groovy_tasks_db.query.order_by(groovy_tasks_db.id.desc()).all()
    
    task_to_modify = groovy_tasks_db.query.get_or_404(id)
    task_to_modify.archived_db = 1
    #task_to_modify.acceptance_required_or_not_db = "Accepted"

    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
    print("ID of task to be accepted :", id)
    new_log = status_logs_db(
                    sender_db = user_email,
                    status_changed_to_db = "Archived",
                    date_of_status_change_db = dt_string,
                    task_id_db = id
                )
    db.session.add(new_log)
    db.session.commit()

    #------------- Re-calculating the remaining tasks, their statuses and so on.. 20.09.23 (We do this with render_template rather than with redirect because, on remote vps; redirect created problems such as freezing etc.) 20.09.23
    #-------------
    #-------------
    
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

    #-------------
    #-------------
    #-------------
    
    return  render_template("active_tasks.html", my_tasks=my_tasks, test_lists_of_options=test_lists_of_options, zipped_data=zipped_data, zipped_data2=zipped_data2)


#----17_04_24 archiving work to be copied to remote
# &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&

#Easy status change -Accept task
@app.route('/accept_one_case/<int:id>', methods=["GET", "POST"])
@login_required
def accept_one_case(id):

    user_name = current_user.name_db
    user_role = current_user.role_db
    user_email = current_user.email_db
    
    #all_cases = str_cases_db.query.filter(str_cases_db.operation_type_db=="Import to Turkey").order_by(str_cases_db.id.desc()).all()
    #We put a filter here as we do not want to havev a large all_cases object while we pass to Jinja1. 05_12_2022
    all_cases = groovy_tasks_db.query.order_by(groovy_tasks_db.id.desc()).all()
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

    #------------- Re-calculating the remaining tasks, their statuses and so on.. 20.09.23 (We do this with render_template rather than with redirect because, on remote vps; redirect created problems such as freezing etc.) 20.09.23
    #-------------
    #-------------
    
    #Retrieving all tasks
    all_task_types = groovy_task_types_db.query.all()
    df_all_task_types = pd.DataFrame([r.__dict__ for r in all_task_types])
    
    #Retrieving my tasks
    #my_tasks = groovy_tasks_db.query.filter(groovy_tasks_db.subordinate_email_db==user_email).order_by(groovy_tasks_db.date_added_db.desc()).all()
    
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
    #-------------
    
    return  render_template("active_tasks.html", my_tasks=my_tasks, test_lists_of_options=test_lists_of_options, zipped_data=zipped_data, zipped_data2=zipped_data2)
    



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


@app.route('/see_logs', methods=["GET", "POST"])
@login_required
def show_logs():
    # Fetch data from the MySQL table using SQLAlchemy
    data = status_logs_db.query.all()

    # Convert the SQLAlchemy query result to a list of dictionaries
    data_dict_list = [item.__dict__ for item in data]

    # Create a pandas DataFrame from the list of dictionaries
    df = pd.DataFrame(data_dict_list)
    #print(df[["task_type_name_db", "task_step_names_db"]])

    return render_template("see_logs.html", task_logs=[df.to_html(index=True)])

@app.route('/delete_task/<int:id>', methods=["GET", "POST"])
@login_required
def delete_task(id):
    user_email = current_user.email_db
    task_to_delete = groovy_tasks_db.query.get_or_404(id)
    
    try:
        #Will we need to delete all related rows in conversations and logs tables? (20.09.2023)    
        #------Deleting the conversations and logs for this task_id first
        # Delete all matching records from groovy_conversations_db
        conversation_records = groovy_conversations_db.query.filter(groovy_conversations_db.task_id_db == id).all()
    
        for conversation_record in conversation_records:
            db.session.delete(conversation_record)
    
        # Delete all matching records from status_logs_db
        status_log_records = status_logs_db.query.filter(status_logs_db.task_id_db == id).all()
    
        for status_log_record in status_log_records:
            db.session.delete(status_log_record)
    
        #db.session.commit()
        
        db.session.delete(task_to_delete)
        db.session.commit()
        flash("Task deleted, thank you.", "success")
        
        #------------- Re-calculating the remaining tasks, their statuses and so on.. 20.09.23 (We do this with render_template rather than with redirect because, on remote vps; redirect created problems such as freezing etc.) 20.09.23
        #-------------
        #-------------
        
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
        #-------------
        
        
        
        #my_tasks = groovy_tasks_db.query.filter(groovy_tasks_db.subordinate_email_db==user_email).order_by(groovy_tasks_db.date_added_db.desc()).all()
        #print("Type my tasks", type(my_tasks), "Length my tasks", len(my_tasks))
        #return redirect(url_for("see_my_tasks"))  #, my_tasks=my_tasks
        return  render_template("active_tasks.html", my_tasks=my_tasks, test_lists_of_options=test_lists_of_options, zipped_data=zipped_data, zipped_data2=zipped_data2)
    except:
        #my_tasks = groovy_tasks_db.query.filter(groovy_tasks_db.subordinate_email_db==user_email).order_by(groovy_tasks_db.date_added_db.desc()).all()

        #Below should be only showing non-archived 17_04_24
        my_tasks = groovy_tasks_db.query.filter(
        (groovy_tasks_db.subordinate_email_db == user_email) & (or_(groovy_tasks_db.archived_db != 1, groovy_tasks_db.archived_db == None))).order_by(groovy_tasks_db.date_added_db.desc()).all()
        flash("There is a problem in deletion of the record. Please inform your administrator.", 'error')
        return  render_template("active_tasks.html", my_tasks=my_tasks)


#To be added as password generator code. 
# Idea, admin or supervisor enters a subordinates contact details, password goes to subordinates' email.
# See password_generator.py 


#Task management test -1 25.08.2023 12:31


@app.route('/admin_panel', methods=["GET",'POST'])
def admin_panel():
    form = employee_entry_form()
    if request.method == "GET":

        engine = create_engine("mysql+pymysql://tansubaktiran:Avz9p9&9Dgsu_099@193.111.73.99/tansubaktiran")
        #engine = create_engine("mariadb://admin:Cimcime762104@localhost/storbridge")
        #app.config["SQLALCHEMY_DATABASE_URI"] = "mariadb://admin:Cimcime762104@localhost/storbridge"
        dbConnection    = engine.connect()
        df = pd.read_sql("SELECT * FROM str_cases_db2", engine)
        dbConnection.close()
        df = df[['id', 'country_db', 'str_ref_db', 'invoice_no_db', 'date_added_db', 'date_initial_response_db', 'date_customs_clearance_response_db', 'date_waiting_enduser_db', 'date_delivered_to_customer_db', 'date_last_status_change_db']]
        print(df)
    
        return render_template("admin_panel.html", form=form) 
    elif request.method == "POST":
        print ("Form -name", form.name.data)

        return render_template("admin_panel.html", form=form) 

#NEW NEW NEW NEW NEW NEW NEW NEW 

@app.route('/')
@app.route('/index')
def index():
    if current_user.is_authenticated:
        user_name = current_user.name_db
        user_role = current_user.role_db
        user_country = current_user.country_db
        user_email = current_user.email_db

        active_tasks_filter = groovy_tasks_db.query.filter(groovy_tasks_db.subordinate_email_db==user_email).all()
        print("Length of tasks assigned to me:", len(active_tasks_filter))
            #-----------------------
        engine = create_engine("mysql+pymysql://tansubaktiran:Avz9p9&9Dgsu_099@193.111.73.99/tansubaktiran")
        #engine = create_engine("mariadb://admin:Cimcime762104@localhost/storbridge")
        #app.config["SQLALCHEMY_DATABASE_URI"] = "mariadb://admin:Cimcime762104@localhost/storbridge"
        dbConnection    = engine.connect()
        df = pd.read_sql("SELECT * FROM str_cases_db2", engine)
        dbConnection.close()
        df = df.rename(columns={"id":"Counts", "country_db":"Country", "status_db":"Status"})
        df = df[["Counts", "Country", "Status"]]
        mydict = {'Pending':1, 'Approved':2, 'Documents Requested':3, 'In Transit':4, 'In Cus Wait Docs (e.g. ATR)':5, 'Customs Clearance Continue':6,'Cus Clear Finished':7,'Delivered To Customer':8}
        df["Status Order"] = df["Status"].map(mydict)
        
        df = df.sort_values(by='Status Order', ascending=True)# Sort according to status order
        #print("------------------")
        #print(df)
        #Below calculating Turkey table.
        turkey_country_filter = df["Country"]== "Turkey"
        turkey_df = df[turkey_country_filter]
        turkey_df = turkey_df.groupby(["Status"]).count()
        turkey_df = turkey_df[['Counts']]
        turkey_df["Status Order"] = turkey_df.index
        turkey_df["Status Order"] = turkey_df["Status Order"].map(mydict)
        turkey_df = turkey_df.sort_values(by="Status Order", ascending=True)
        turkey_df = pd.DataFrame(turkey_df["Counts"]) #Leave only one column for display
        
        #Below calculating Turkey table.
        other_country_filter = df["Country"]== "Other"
        other_df = df[other_country_filter]
        other_df = other_df.groupby(["Status"]).count()
        other_df = other_df[['Counts']]
        other_df["Status Order"] = other_df.index
        other_df["Status Order"] = other_df["Status Order"].map(mydict)
        other_df = other_df.sort_values(by="Status Order", ascending=True)
        other_df = pd.DataFrame(other_df["Counts"]) #Leave only one column for display
        
        #Below working properly.
        df_groupby_general_pre = df.groupby(["Status"]).count()
        df_groupby_general = df_groupby_general_pre[['Counts']]
        df_groupby_general["Status Order"] = df_groupby_general.index
        df_groupby_general["Status Order"] = df_groupby_general["Status Order"].map(mydict)
        df_groupby_general = df_groupby_general.sort_values(by='Status Order', ascending=True)# Sort according to status order
        df_groupby_general = pd.DataFrame(df_groupby_general["Counts"]) #Leave only one column for display
        
        if user_role=="user0":
                        
            return  render_template("index.html", user_name = user_name, user_role = user_role, user_country=user_country,  tables_info=[turkey_df.to_html(index=True)],tables_info_other=[other_df.to_html(index=True)], tables_info2=[df_groupby_general.to_html(index=True)], number_of_my_tasks=len(active_tasks_filter)) 

        if user_role=="user1":
            
            
            df_groupby_country_pre = df.groupby(["Country", "Status"]).count()
            df_groupby_general_pre = df.groupby(["Status"]).count()
            
            country_filter = df["Country"]==user_country
            df_filter_country = df[country_filter].groupby(["Status"])

            df_groupby_country = df_groupby_country_pre[['Counts']]
            df_groupby_general = df_groupby_general_pre[['Counts']]
            print(df_groupby_country)
            
            return  render_template("index.html", user_name = user_name, user_role = user_role, user_country=user_country, tables_info=[df_groupby_country.to_html(index=True)], tables_info2=[df_groupby_general.to_html(index=True)])
        
        if user_role=="user3":
            
            if current_user.is_authenticated:
                if current_user.country_db=="Turkey":
                    df_filter_country = turkey_df
                elif current_user.country_db=="Other":
                    df_filter_country = other_df
            
            #df_groupby_country_pre = df.groupby(["Country", "Status"]).count()
            #df_groupby_general_pre = df.groupby(["Status"]).count()
            
            #country_filter = df["Country"]==user_country
            #df_filter_country = df[country_filter].groupby(["Status"]).count()
            #df_groupby_country = df_filter_country[['Counts']]
            
            #print(df_groupby_country.index)
            
            return  render_template("index.html", user_name = user_name, user_role = user_role, user_country=user_country, tables_info=[df_filter_country.to_html(index=True)])

    return render_template("index.html")

#This is kept as a reference for Ubuntu deployment to give an idea. Not a functional active function.
@app.route('/upload_file', methods=["GET",'POST'])
def upload_file():
    form = fileuploadform()

    if request.method=="POST":
        uploaded_file = request.files['file']
        if uploaded_file.filename != '':
            uploaded_file.save(os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename))
    return  render_template("upload_file.html", form=form)

"""@app.route('/show_file_names')
def show_file_names():
    my_file_list = os.listdir('flasknew/uploaded_files/')
    print("Here are files available : ", my_file_list)
    return  render_template("index.html")"""

#This is kept as a reference for Ubuntu deployment to give an idea. Not a functional active function.
@app.route('/download_one_file')
def download_one_file():
    file_and_path = 'uploaded_files/cat1.jpeg'
    my_file_list = os.listdir('flasknew/uploaded_files/')
    print("Here are files available : ", my_file_list)
    return  send_file(file_and_path, as_attachment=True)

@app.route("/new_entry", methods=['GET', 'POST'])
@login_required
def new_entry():
    form = str_import_entry_form()

    user_name = current_user.name_db
    user_role = current_user.role_db
    user_country = current_user.country_db

    if user_role == "user0":
            
        if request.method == "POST":
            now = datetime.now()
            dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
            if form.validate_on_submit():
                print("Case entry work validation step check")
                
                new_case = str_cases_db2(  
                    
                    country_db = form.country.data,
                    operation_type_db = form.type.data,
                    str_ref_db = form.str_ref.data,
                    tur_ref_db = form.tur_ref.data,
                    invoice_no_db = form.invoice_no.data,
                    hawb_no_db = form.hawb_no.data,
                    date_added_db = dt_string,
                    date_last_status_change_db = dt_string,
                    status_db = "Pending",
                    cancellation_status_db = form.cancellation_status.data,
                     
                    notes_db = form.note.data,
                    enduser_name_surname_db = form.enduser_name.data,
                    enduser_company_name_db = form.enduser_company.data,
                    enduser_address_db = form.enduser_address.data,
                    enduser_tel_db = form.enduser_telephone.data,
                    enduser_email_db = form.enduser_email.data)
                
                db.session.add(new_case)
                db.session.commit()

                #FOR E-MAIL SENDING AS A NOTIFICATION  07.03.2022
                EMAIL_ADDRESS = "tansubaktiran3@gmail.com"
                EMAIL_PASSWORD = "uowjakmibfngtwqy"
                
                #E-mail recipient will be defined here for multiple countries. 27th June 2023
                #If loop will be designed for multiple recipients. 27th June 2023
                
                msg = EmailMessage()
                msg['Subject'] = 'You have a new approval request. Storbridge reference is ' + (form.str_ref.data)
                msg['From'] = EMAIL_ADDRESS
                msg['To'] = "ebru.sesiz@mentorgumruk.com.tr"
                msg[""]

                msg.set_content('You have a new approval request. Storbridge reference is ' + (form.str_ref.data))
                
                msg.add_alternative("""<!DOCTYPE html>
                <html>
                    <body>
                        <h1 style="color:SlateGray;">You have a new approval request</h1>
                        
                        <p style="color:orangered;">Please visit your Storbridge Global online system account. </p>
                    </body>
                </html>
                """, subtype="html")

                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                    
                    smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

                    smtp.send_message(msg)
                #FOR E-MAIL SENDING AS A NOTIFICATION 07.03.2022

                #Create directory for saving the files
                path_to_be_created = 'storbridge/uploaded_files/' + form.str_ref.data
                #print("<<<>>>", path_to_be_created)
                try:
                    os.mkdir(path_to_be_created)
                except OSError as error:
                    print(error)
                
                #Saving all selected files to folder
                list_of_potential_files_to_be_uploaded = ["file1", "file2", "file3", "file4", "file5", "file6", "file7", "file8", "file9", "file10", ]
                for file_name in list_of_potential_files_to_be_uploaded:
                    file_to_be_uploaded = request.files[file_name]
                    if file_to_be_uploaded.filename != '':
                        #file_to_be_uploaded.save(os.path.join(app.config['UPLOAD_FOLDER'], file_to_be_uploaded.filename))
                        file_to_be_uploaded.save(os.path.join(path_to_be_created, file_to_be_uploaded.filename))

                flash("New case has been recorded successfully. Thank you!", "success")
                return render_template("index.html", user_name = user_name, user_role = user_role, user_country=user_country) 
            else:
                flash("There has been a problem during saving the new case. Please inform your administrator.", 'error')
    else:   
        flash("New case entry screen is only available for authorized staff. Please inform your administrator in case of a mistake.", 'error')
        return render_template("index.html")
    
    return render_template("new_entry.html", form=form, user_name = user_name, user_role = user_role, user_country=user_country)

@app.route("/show_all_cases", methods=['GET', 'POST'])
@login_required
def show_all_cases():
    if request.method == "GET":
        user_name = current_user.name_db
        user_role = current_user.role_db
        user_country = current_user.country_db
        now = datetime.now()
        if (user_role == "user1") or (user_role == "user3"):
            #all_cases = str_cases_db.query.order_by(str_cases_db.date_added_db.desc()).all()
            all_cases = str_cases_db2.query.filter(str_cases_db2.status_db!="Delivered To Customer", str_cases_db2.country_db==user_country).order_by(str_cases_db2.date_added_db.desc()).all()
            return render_template("show_all_cases.html", all_cases=all_cases, user_name = user_name, user_role = user_role, now=now, user_country=user_country)#,number_of_pending_cases=number_of_pending_cases, number_of_approved_cases=number_of_approved_cases, number_of_intransit_cases=number_of_intransit_cases, number_of_customsclearancecont_cases=number_of_customsclearancecont_cases, number_of_docreq_cases=number_of_docreq_cases, number_of_atrreq_cases=number_of_atrreq_cases, number_of_waitenduser_cases=number_of_waitenduser_cases, number_of_delivered_cases=number_of_delivered_cases
        elif (user_role == "user0"):
            
            all_cases = str_cases_db2.query.filter(str_cases_db2.status_db!="Delivered To Customer").order_by(str_cases_db2.date_added_db.desc()).all()
            return render_template("show_all_cases.html", all_cases=all_cases, user_name = user_name, user_role = user_role, now=now, user_country=user_country)
        else:
            flash("This screen is only available for authorized staff. Please inform your administrator in case of a mistake.", 'error')
            return render_template("index.html")

@app.route("/show_one_case/<int:id>", methods=['GET', 'POST'])
@login_required
def show_one_case(id):
    print(id) #19.05.2022
    
    #Bunu düzeltelim
    user_name = current_user.name_db
    user_role = current_user.role_db
    case_to_show = str_cases_db2.query.get_or_404(id)
    id = case_to_show.id
    if case_to_show:
        print("there is a case to show")
        print("Case id", case_to_show)

        #Get the list of attachments
        path = 'storbridge/uploaded_files/' + case_to_show.str_ref_db
        print("Path - ", path)
        list_of_attachments = os.listdir(path)
        print("List of attachments : ", list_of_attachments)
        #DOSYALARI İSİMLERİNİ DOĞRUDAN REMOTE SERVER ÜZERİNDEKİ DIRECTORY ÜZERİNDEN ALMAK.
        list_of_attachments.reverse()
        len_of_files_list = len(list_of_attachments)
        
        list_of_file_name_numbers = [] #23.03.2022 -start
        for file_number in range(len_of_files_list):
            list_of_file_name_numbers.append(file_number)
        #print("List of file name numbers : ", list_of_file_name_numbers) #23.03.2022 -end
        
        #print("Len of files list", len_of_files_list)
        #print("List of file names : ", list_of_attachments)
        


        download_text="download_attachment"
        #List of download links
        list_of_links = []
        for num_of_file in range(len_of_files_list):
            list_of_links.append(download_text + str(num_of_file+1))
        #print("Download Links of attachments : ", list_of_links)

        #IMPORTANT - FOR ZIPPING TWO LISTS IN JINJA2 - IN THIS CASE FOR ZIPPING 
        app.jinja_env.filters['zip'] = zip
        # Sadece dosya sayısı kadar download link yazdırma imkanımız var mı? File list muhtemelen 6 len ile geliyor. Bir adımı bu olabilir. 15.02.2022
        # Bunu yaptık. Fonksiyon içinde (hemen yukarıda) zipleyerek html/jinja2 içinde url_for fonksiyonunun içinde hem bağlı olduğu flask fonksiyonunu hem de dosyanın adını ayrı ayrı listeden çekerek indirilebilecek bir mekanizma yazdık. 16.02.2022

    
    return render_template("show_one_case.html", case_to_show=case_to_show, len_of_files_list=len_of_files_list, list_of_file_name_numbers=list_of_file_name_numbers, list_of_attachments=list_of_attachments, user_name=user_name, user_role=user_role, id=id)

@app.route('/download_attachment/<int:id>/<int:file_no>', methods=["GET", "POST"])
@login_required
def download_attachment(id, file_no):
    #Have a second look for cleaning - 13.06.2023
    user_name = current_user.name_db
    user_role = current_user.role_db
    case_to_show = str_cases_db2.query.get_or_404(id)
    
    #Get the list of attachments from relevant directory
    path = 'storbridge/uploaded_files/' + case_to_show.str_ref_db
    
    list_of_attachments = os.listdir(path)
    list_of_attachments.reverse()
    file_name_to_download = list_of_attachments[file_no]
    
    storbridge_directory_to_download = case_to_show.str_ref_db
    file_path_to_download_on_remote =  "uploaded_files/" + storbridge_directory_to_download + "/" + file_name_to_download #"uploaded_files/" + storbridge_directory_to_download +
    
    if request.method == "GET":        
        file_and_path = file_path_to_download_on_remote
        return  send_file(file_path_to_download_on_remote, as_attachment=True)

    return render_template("see_one_case.html", case_to_show=case_to_show, user_name = user_name, user_role = user_role)


@app.route('/update_one_case/<int:id>/', methods=["GET", "POST"])
@login_required
def update_one_case(id):

    form = str_import_entry_form()
    case_to_update = str_cases_db2.query.get_or_404(id)

    
    if request.method == "GET":

        #if case_to_update.operation_type_db=="Import":
        form = str_import_entry_form()
        form.str_ref.data = case_to_update.str_ref_db
        form.tur_ref.data = case_to_update.tur_ref_db
        
        form.invoice_no.data = case_to_update.invoice_no_db
        form.hawb_no.data = case_to_update.hawb_no_db
        
        form.note.data = case_to_update.notes_db
        form.enduser_name.data = case_to_update.enduser_name_surname_db
        form.enduser_company.data = case_to_update.enduser_company_name_db
        form.enduser_address.data = case_to_update.enduser_address_db
        form.enduser_telephone.data = case_to_update.enduser_tel_db
        form.enduser_email.data = case_to_update.enduser_email_db
        form.cancellation_status.data = case_to_update.cancellation_status_db
        return render_template("update_one_case.html", form=form, case_to_update=case_to_update, id=id)
   
        
    
    
    #HERE WE WILL ADD IMPORT OR EXPORT IF -TO BE ABLE TO FORWARD RELEVANT INFORMATION TO IMPORT/EXPORT  // RECORDING IS REMAINING 18.03.2022
    #ALSO DISABLE OTHER USERS FROM REACHING TO THIS END POINT!!! 18.03.2022
    
    if request.method == "POST":
        #UPDATE FONKSİYONUNDA BURADA KALDIK...05.03.2022 - SONRA BU YORUM SİLİNECEK -aşağıda----------------------------------------------------------------------------

        #----------------------------------------------------------------------------------------
        
        #Update one case dosya yükleme 500MB üzerinde çalışmıyor.. bunun sebebi ne olabilir?
        #Alttaki kod yerine başka bir sorun olabilir mi? Örneğin template sorunu?
        #Create directory for saving the files
            path_to_be_created = 'storbridge/uploaded_files/' + form.str_ref.data
            print("<<<>>>", path_to_be_created)
            """try:
                os.mkdir(path_to_be_created)
            except OSError as error:
                print(error)"""
            
            #Saving all selected files to folder
            list_of_potential_files_to_be_uploaded = ["file1", "file2", "file3", "file4", "file5", "file6", "file7", "file8", "file9", "file10"]
            for file_name in list_of_potential_files_to_be_uploaded:
                
                file_to_be_uploaded = request.files[file_name]
                print("Abbr of file to be used :", file_name, "Name of file : ", file_to_be_uploaded.filename)
            
                if file_to_be_uploaded.filename != '':
                    #file_to_be_uploaded.save(os.path.join(app.config['UPLOAD_FOLDER'], file_to_be_uploaded.filename))
                    file_to_be_uploaded.save(os.path.join(path_to_be_created, file_to_be_uploaded.filename))
            
            
            #UPDATE FONKSİYONUNDA BURADA KALDIK...05.03.2022 - SONRA BU YORUM SİLİNECEK -yukarıda----------------------------------------------------------------------------
            case_to_update.str_ref_db = form.str_ref.data
            case_to_update.tur_ref_db = form.tur_ref.data
            case_to_update.invoice_no_db = form.invoice_no.data,
            case_to_update.hawb_no_db = form.hawb_no.data,
            case_to_update.notes_db = form.note.data
            case_to_update.enduser_name_surname_db = form.enduser_name.data
            case_to_update.enduser_company_name_db = form.enduser_company.data
            case_to_update.enduser_address_db = form.enduser_address.data
            case_to_update.enduser_tel_db = form.enduser_telephone.data
            case_to_update.enduser_email_db = form.enduser_email.data
            case_to_update.cancellation_status_db = form.cancellation_status.data

            try:
                db.session.commit()
                flash("Case has been succesfully updated.", "success")
                return render_template("update_one_case.html", form=form, case_to_update=case_to_update, id=id) 
                
            except:
                db.session.commit()
                flash("There has been a problem during updating process. Please inform your IT Administrator.", "success")
                return render_template("update_one_case.html", form=form, case_to_update=case_to_update, id=id) 



@app.route('/import_approval_step/<int:id>', methods=["GET", "POST"])
@login_required
def import_approval_step(id): #Approving a new import request or not (mainly by Mentor staff or automatic)
    
    form = str_case_approval()
    user_name = current_user.name_db
    user_role = current_user.role_db
    test_for_current_user = current_user.name_db
    print("Test for current user : ", test_for_current_user)
    
    
    case_to_approve = str_cases_db2.query.get_or_404(id)

    if request.method== "POST":
        
        print("check point for POST")
        if current_user.role_db=="user3":
            print("check point for user3 POST")
            now = datetime.now()
            dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
            
            if form.validate_on_submit():
                
                print("check point for user3 POST and validate")
                #str_cases_db.initial_status_db = form.reply_result.data  yazarsak hangi DBrow'a yazacağını bilemez. :))) 16.02.2022
                case_to_approve.status_db = form.reply_result.data
                case_to_approve.date_initial_response_db = dt_string
                case_to_approve.date_last_status_change_db = dt_string
                                             
                db.session.commit() #Unutma
                                                               
                user_name = current_user.name_db
                user_role = current_user.role_db                   
                flash("Your reply is recorded successfully.", 'error')
                return render_template("approval_entry.html", form=form, case_to_approve=case_to_approve, user_name = user_name, user_role = user_role)
                
            else:
                flash("There was an error during recording your reply. Please inform your administrator.", 'error')
                return render_template("index.html", form=form, case_to_approve=case_to_approve, user_name = user_name, user_role = user_role)
        else:
            flash("This screen is only available for staff authorized to approve import requests. Please inform your administrator if you think there is a mistake.", 'error')
            return render_template("index.html", user_name = user_name, user_role = user_role)

    if request.method == "GET":
        work_to_show = str_cases_db2.query.get_or_404(id)
        
        if user_role=="user3":
            print("check point GET user3")
            form = str_case_approval()
            return render_template("approval_entry.html", form=form, case_to_approve=case_to_approve, user_role = user_role, user_name = user_name)
        else:
            flash("This screen is only available for staff authorized to approve import requests. Please inform your administrator if you think there is a mistake.", 'error')
            return render_template("index.html", form=form, user_role = user_role, user_name = user_name)

    return render_template("index.html", form=form, case_to_approve=case_to_approve, user_name = user_name, user_role = user_role)



@app.route('/delete_one_case/<int:id>', methods=["GET", "POST"])
@login_required
def delete_one_case(id):

    #Birini POST birini GET içinde nasıl yönetebiliriz? 17_06_2023
    form = delete_confirm()
    user_name = current_user.name_db
    user_role = current_user.role_db
    user_country = current_user.country_db
    case_to_delete = str_cases_db2.query.get_or_404(id)
    all_cases = str_cases_db2.query.order_by(str_cases_db2.date_added_db.desc()).all()
    now = datetime.now()

    if request.method == "GET":
    
        return  render_template("delete_one_case_confirm.html", all_cases=all_cases, case_to_delete=case_to_delete, form=form, user_name=user_name, user_role=user_role, user_country=user_country, now=now)


    if request.method == "POST":
        path_to_be_deleted = 'storbridge/uploaded_files/' + case_to_delete.str_ref_db
    
        #import os
        #os.rmdir(path_to_be_deleted)
        dir_list = os.listdir(path_to_be_deleted)
        print("Case/reference/path to delete : ", path_to_be_deleted)
        print("Files in directory : ", dir_list)
        for file_ in dir_list:
            os.remove(path_to_be_deleted + "/" + file_)
            print("File to be deleted", file_)
        os.rmdir(path_to_be_deleted) 
        try:
            db.session.delete(case_to_delete)
            db.session.commit()
            flash("Record deleted, thank you.", "success")
            print("Entry deleted.. now should be re-routing to form2??")
            all_cases = str_cases_db2.query.order_by(str_cases_db2.date_added_db.desc()).all()
            #all_cases = str_cases_db.query.order_by(str_cases_db.date_added_db).all()
            #return redirect(url_for("show_all_cases.html")) #Orjinal codemy videsounda bu satır yok. 
            return render_template("show_all_cases.html", all_cases=all_cases, form=form, user_name=user_name, user_role=user_role, user_country=user_country, now=now)
            # Bunun yerine aşağıdaki satır yazılmış ama delete/n urlinde kalıyordu. 
            # Dolayısı ile sildikten sonra yeni giriş hata veriyordu.
            #return  render_template("form2.html", form=form, name=name, our_users=our_users)
        except:
            flash("There is a problem in deletion of the record. Please inform your administrator.", 'error')
            return  render_template("show_all_cases.html", all_cases=all_cases, form=form,user_name=user_name, user_role=user_role, user_country=user_country, now=now)

@app.route('/see_pending', methods=["GET", "POST"])
@login_required
def see_pending(): #Adding a new work to database by sales team

    user_name = current_user.name_db
    user_role = current_user.role_db
    user_country = current_user.country_db
    now = datetime.now()
    #all_cases = str_cases_db.query.order_by(str_cases_db.date_added_db).all()
    if request.method == "GET":
        if (user_role == "user0"):
            #Filtering for In Transit only.
            all_cases = str_cases_db2.query.filter(str_cases_db2.status_db=="Pending").order_by(str_cases_db2.date_added_db.desc()).all()
            #all_cases = str_cases_db.query.order_by(str_cases_db.date_added_db.desc()).all() #Previous filter
            return render_template("show_all_cases.html", all_cases=all_cases, user_name = user_name, user_role = user_role, user_country = user_country , now=now)
        
        elif (user_role == "user1"):
            #Filtering for In Transit only.
            all_cases = str_cases_db2.query.filter(str_cases_db2.status_db=="Pending").order_by(str_cases_db2.date_added_db.desc()).all()
            #all_cases = str_cases_db.query.order_by(str_cases_db.date_added_db.desc()).all() #Previous filter
            return render_template("show_all_cases.html", all_cases=all_cases, user_name = user_name, user_role = user_role, user_country = user_country, now=now)
        
        elif user_role == "user3":
            #all_cases = str_cases_db.query.filter(str_cases_db.operation_type_db=="Import to Turkey").order_by(str_cases_db.id.desc()).all()
            #all_cases = str_cases_db2.query.filter(str_cases_db2.status_db!="Delivered To Customer" and str_cases_db2.country_db==user_country).order_by(str_cases_db2.date_added_db.desc()).all()
            all_cases = str_cases_db2.query.filter(str_cases_db2.status_db=="Pending" ,str_cases_db2.country_db==user_country).order_by(str_cases_db2.date_added_db.desc()).all()
            #all_cases = str_cases_db2.query.filter(str_cases_db2.status_db=="Pending", str_cases_db2.country_db==user_country).order_by(str_cases_db2.date_added_db.desc()).all()
            return render_template("show_all_cases.html", all_cases=all_cases, user_name = user_name, user_role = user_role , user_country = user_country, now=now)
        
        elif user_role == "user4":
            all_cases = str_cases_db2.query.filter(str_cases_db2.operation_type_db=="Export from Turkey").order_by(str_cases_db2.id.desc()).all()
            print("Printing from Esra Hn's account... exports")
            return render_template("show_all_cases.html", all_cases=all_cases, user_name = user_name, user_role = user_role, user_country = user_country, now=now)

        else:
            flash("This screen is only available for authorized staff. Please inform your administrator in case of a mistake.", 'error')
            return render_template("index.html")




@app.route("/login", methods=['GET', 'POST'])
def login():
    
    if current_user.is_authenticated:
        print("User is ALREADY LOGGED IN")
        return redirect(url_for('index'))
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
            flash('You have successfully logged in. Have a nice day.', 'success')
            
            return render_template('index.html', user_name=current_user.name_db)
            return redirect(url_for('index'))
            
            
        else:
            flash('There has been a problem during logging in. Please check your username and password', 'error')
    return render_template('login.html', title='Login', form=form)
    
@app.route("/logout")
def logout():
    if current_user.is_authenticated:
        
        user_to_be_updated = str_staff_db2.query.filter_by(id=current_user.id).first()
    
        #For recording last logout time
        #now = datetime.now()
        #dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        #user_to_be_updated.last_logout_db = dt_string
        #db.session.commit()

    logout_user()
    print("The user should have been LOGGED OUT NOW!!!")
    flash('You have successfully logged out. Have a nice day.', 'success')
    #return redirect(url_for('index'))
    return render_template('index.html')