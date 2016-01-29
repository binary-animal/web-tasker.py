# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, send_from_directory, request, make_response, session, redirect, url_for
from datetime import datetime

import logging

from web_tasker import app, db
from web_tasker.models import *

@app.route("/")
def index():
  # getting referer
  user_from='some-site.ru'

  if not logined_by_cookie():
    user=None
  else:
    user=get_user_id()

  return render_template('index.html', title='Hi', user_from=user_from, user=user) 

###########################
########## TASK ###########
###########################
@app.route("/task")
@app.route("/task/<action>", methods=['GET', 'POST'])
def task(action='list'):
  if not logined_by_cookie():
    app.logger.error('Not logined') # debug
    return redirect(url_for('do_login')) # if not logined go to login
  else:
    user_id = get_user_id()
  app.logger.info('Task viewing by user:\t'+str(user_id)) # debug

  ### Showing task list
  if action == 'list' or action == 'list_closed':
    # rewrite to sqlalchemy like User.query.all() or User.query.filter() like in edit section
    # http://flask.pocoo.org/docs/0.10/patterns/sqlalchemy/
    if action == 'list_closed':
      task_status = False # for taskmenu
      cur = db.session.execute("SELECT id, taskname, timestamp FROM task WHERE status='Disabled' AND user_id='{}'".format(user_id))
    else:
      task_status = True # for taskmenu
      cur = db.session.execute("SELECT id, taskname, timestamp FROM task WHERE status!='Disabled' AND user_id='{}'".format(user_id))

    tasks = cur.fetchall()  
    return render_template('task.html', tittle='Задачи', user=get_nick(), task_list=tasks, task_status=task_status)

  ### Creating task
  elif action=='create':
    if request.method == 'POST':
      # Getting user id
      cur = db.session.execute("SELECT id FROM user WHERE nickname='{}'".format(get_nick()))
      user_id = cur.fetchone()[0]
      # Example of sqlAlchemy usage
      task_row = Task(user_id=user_id, taskname=request.form['taskname'], body=request.form['taskbody'], timestamp=datetime.now(), status='Active')
      db.session.add(task_row)
      db.session.commit()
      return redirect(url_for('task'))
    return render_template('task_create.html', tittle='Задачи', user=get_nick())

  ### Explain task 
  elif action=='view':
    app.logger.debug('### Start viewing ###')
    task_id = request.args.get('id')
    nickname = get_nick()
    cur = db.session.execute("SELECT id FROM user WHERE nickname='{}'".format(nickname))
    try: # if logined
      user_id = cur.fetchone()[0]
      task_explained = db.session.execute("SELECT taskname,body,timestamp FROM task WHERE id='{}' AND user_id='{}'".format(task_id, user_id))
      all_comments = db.session.execute("SELECT c.id,c.user_id,c.timestamp,c.text,u.nickname FROM comment c, user u WHERE c.task_id='{}' and c.user_id=u.id".format(task_id))
      #all_comments = db.session.query(models.Comment).filter_by(task_id=task_id).all()
      app.logger.debug('### End viewing ###')
      # may be need redirect to internal func here
      return render_template('task_view.html', tittle='Задачи', user=nickname,
                              task_expl=task_explained.fetchone(), task_opened=task_id,
                              comments=all_comments.fetchall())
    except TypeError: # if not logined go to login
      return redirect(url_for('do_login'))
    else:
      return 'Unresolved error'

  ### Edit task
  elif action=='edit':
    nickname = get_nick()
    if request.method == 'GET':
      task_edited = request.args.get('id')
      # Getting user id
      cur = db.session.execute("SELECT id FROM user WHERE nickname='{}'".format(nickname))
      try:
        user_id = cur.fetchone()[0]
        cur = db.session.execute("SELECT taskname,body,timestamp,status FROM task WHERE id='{}' AND user_id='{}'".format(task_edited, user_id))
        return render_template('task_modify.html', tittle='Задачи', user=nickname, task_edited=task_edited, task_expl=cur.fetchone())
      except TypeError: pass
      return render_template('task_modify.html', tittle='Задачи', user=nickname, task_edited=task_edited)
    elif request.method == 'POST':
      try:
        cur = db.session.execute("SELECT id FROM user WHERE nickname='{}'".format(nickname))
        user_id = cur.fetchone()[0]
        db.session.query(Task).filter_by(id=request.form['taskid']).update({'taskname':request.form['taskname'], 'status':request.form['taskstatus'], 'body':request.form['taskbody']})
        db.session.commit()
        return redirect(url_for('task'))
      except TypeError: return redirect(url_for('do_login'))

  return 'Unresolved error 2'


@app.route("/comment_to_task", methods=['POST'])
def post_comment_to_task():
  app.logger.info('### Post Comment to db ###') # debug
  new_comment = Comment(user_id=check_user(), task_id=request.form['taskid'], timestamp=datetime.now(), text=request.form.get('commenttext'))
  db.session.add(new_comment)
  db.session.commit()
  return redirect(url_for('task', action='view', id=int(request.form['taskid'])))

###########################
######### PROJECT #########
###########################
@app.route("/project")
@app.route("/project/<action>", methods=['GET', 'POST'])
def project(action='list'):
  if not logined_by_cookie():
    app.logger.error('Not logined') # debug
    return redirect(url_for('do_login')) # if not logined go to login
  else:
    user_id = get_user_id()

  app.logger.info(' ### Project logined user ID:\t'+str(user_id)) # debug

  ### Show Project List ###
  if action == 'list' or action == 'list_closed':
    if action == 'list_closed':
      project_status = False
      cur = db.session.execute("SELECT id FROM project WHERE option='user' and value='{}'".format(user_id))
      project_ids = cur.fetchall()[0]
    else:
      project_status = True
      project_ids = db.session.query(models.Project_association.project_id).filter_by(user_id=user_id)

    app.logger.debug('project_ids: '+str(project_ids)) # debug
    if project_ids:
      projects = []
      for project_id in project_ids:
        project_name = db.session.query(models.Project.name).filter_by(id=project_id[0]).all()[0]
        projects.append([project_id[0], project_name[0]])
        # app.logger.debug('project_id is: '+str(project_id[0])+' name is '+str(project_name)) # debug
    return render_template('project.html', tittle='Проекты', user=get_nick(), project_list=projects, project_status=project_status)

  ### Create new Project ###
  elif action == 'create':
    user_id = get_user_id()
    if request.method == 'POST':
      # Need:
      #       User ID (upper)
      #       Project Name
      #       Project ID
      project_name = request.form.get('projectname')

      db.session.add(models.Project(name=project_name))
      db.session.commit()
      project_id = db.session.query(models.Project.id).filter_by(name=project_name)
      db.session.add(models.Project_association(user_id=user_id, project_id=project_id[0][0]))
      db.session.commit()
      return redirect(url_for('project')) # got to project list

    else: # if GET request
      return render_template('project_create.html', tittle='Проекты', user=get_nick(), user_id=user_id)

  ### Edit Project ###
  elif action == 'edit':
    if request.method == 'POST':
      pass
    else: # if GET request
      # Need:
      #       Project ID
      #       Project Name
      #       Project Users
      project_id = request.args.get('id')
      project_name = db.session.query(models.Project.name).filter_by(id=project_id).all()[0]
      project_user_ids = db.session.query(models.Project_association.user_id).filter_by(project_id=project_id).all()
      project_user_names = []
      for user_id in project_user_ids:
        name = db.session.query(models.User.nickname).filter_by(id=user_id[0]).all()[0]
        project_user_names.append(name[0])

      app.logger.debug('### Project # Edit ### id from form: '+str(project_id[0])+'\n'+ \
                        'Name: '+str(project_name)+'\n'+ \
                        'User IDs: '+str(project_user_ids)+'\n'+ \
                        'Users in project: '+str(project_user_names) ) # debug
      project_full_data = [project_id, project_name[0], project_user_ids, project_user_names]
      return render_template('project_edit.html', tittle='Проекты', user=get_nick(), project=project_full_data)


@app.route("/profile")
def profile():
  if not logined_by_cookie():
    return redirect(url_for('do_login')) # if not logined go to login
  else:
    return render_template('profile.html', user=get_nick())
    

@app.route("/about")
def about():
    return render_template('about.html', tittle='О сайте')


@app.route("/login", methods=['GET', 'POST'])
def do_login():
  if request.method == 'POST':
    user = str(request.form['username'])
    password = str(request.form['password'])
    
    #app.logger.info('Check password:\t'+str(check_passwd(user, password))) # debug
    if check_passwd(user, password):
      # Set Cookies for knowing about user on other pages
      auth_hash = str(id_generator())
      user_id = int(get_user_id_from_db(user))
      app.logger.debug('Set cookies '+str(user)+' '+str(user_id)+' '+auth_hash) # debug
      
      response = app.make_response(redirect(url_for('task')))
      response.set_cookie('id', value=str(user_id))
      response.set_cookie('hash', value=auth_hash)
      response.set_cookie('logged_at', value=str(datetime.now()))
      db.session.query(User).filter_by(id=user_id).update({'cookie':auth_hash})
      db.session.commit()
      #sql = "UPDATE user SET cookie='{}' WHERE id='{}'".format(auth_hash, user_id)
      #app.logger.info('SQL:\t'+str(sql)) # debug
      #db.session.execute(sql)
      return response # need for set cookies finaly
    else:
      return 'login wrong'

  # if request.method == GET
  return render_template('login.html', user=None)


@app.route("/logout")
def logout():
  response = app.make_response(redirect(url_for('index')))
  response.set_cookie('id', value=' ', expires=1)
  response.set_cookie('pass', value=' ', expires=1)
  return response


@app.route("/register", methods=['GET', 'POST'])
def register_user():
  if request.method == 'POST':
    if mail_exist(request.form.get('email')):
      return 'mail exist'
    else:
      # Prepare empty project for user
      new_project = models.Project(name=u'Привет проект')
      db.session.add(new_project)
      db.session.commit()
      # Prepare user data to insert in db
      import crypt;
      salt = '$6$FIXEDS'
      pass_hash = crypt.crypt(request.form.get('password'), salt)
      app.logger.info('Generated hash:\t'+pass_hash) # debug
      user_row = User(nickname=request.form.get('username'),
  			                     email=request.form.get('email'), 
                             password=request.form.get('password'),
                             p_hash=pass_hash,
                             role=models.ROLE_USER,
                             register_date=datetime.now())
      db.session.add(user_row)
      db.session.commit()
      return redirect(url_for('index'))

  if request.method == 'GET':
    return render_template('register.html', user=None)


@app.route("/users")
def users_list():
  if not logined_by_cookie():
    return redirect(url_for('do_login')) # if not logined go to login
  else:
    user_id = get_user_id()

  cur = db.session.execute("select id,nickname,email from user")
  user_list = cur.fetchall()
  return render_template('user_list.html', user=get_nick(), user_list=user_list)

#############################################

def get_user_id():
  if logined_by_cookie():
    # refactoring
    user_id = request.cookies.get('id')
    app.logger.info('Logined by cookies:\t'+str(user_id)) # debug
    return int(user_id)
  else:
    return None


def mail_exist(email):
  cur = db.session.execute("SELECT email FROM user")
  all_emails = cur.fetchall()
  if email in all_emails:
    app.logger.info('### Email exist in database ###') # debug
    return True
  else:
    app.logger.info('### Email doesn\'t exist in database ###') # debug
    return False


def get_user_id_from_db(username):
    cur = db.session.execute("SELECT id FROM user WHERE nickname='{0}'".format(str(username)))
    return cur.fetchone()[0]


def check_passwd(login, password):
  db_hash = get_hash_from_db(login)[0]
  if db_hash: # exist
    salt_end = db_hash.rindex('$')
    salt = db_hash[:salt_end]
    import crypt;
    crypted_pass_hash = crypt.crypt(password, salt)
    if crypted_pass_hash == db_hash:
      return 1 # Passwords equal
    else:
      return 0 # Not equal
  else:
    return 0 # p_hash doesn't exist


def logined_by_cookie():
  user_id = str(request.cookies.get('id'))
  user_hash = request.cookies.get('hash')
  if user_hash:
    app.logger.debug('UserID from cookie:\t'+user_id+' '+user_hash) # debug

    if not user_id == str('None'): # if user_id exist
      cur = db.session.execute("SELECT cookie FROM user WHERE id='{0}'".format(user_id))
      cookie = cur.fetchone()[0] # getting hash
      app.logger.debug('Cookie from db:\t\t'+str(cookie)) # debug

      if str(cookie) == str(user_hash):
        return True # yeah LOGINED
    
  return False


def get_nick():
  user_id = request.cookies.get('id')
  if user_id:
    cur = db.session.execute("SELECT nickname FROM user WHERE id='{0}'".format(int(user_id)))
    return cur.fetchone()[0]

  return None


def get_hash_from_db(username):
  cur = db.session.execute("SELECT p_hash FROM user WHERE nickname='{0}'".format(username))
  return cur.fetchone()


import string
def id_generator(size=8, chars=string.ascii_uppercase + string.digits):
    import random
    return ''.join(random.choice(chars) for _ in range(size))

