from flask import Flask,request, session, render_template, jsonify, make_response,redirect,url_for,send_file
import json
import hashlib
import uuid 
import os
from datetime import datetime
import shutil
import sqlite3
import multiprocessing
import notify

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super secret key'
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

url="http://localhost:5000"

def getstudents(aid,tid): 
	dictionary={}
	dictionary['students']=[]
	
	conn = sqlite3.connect('database.db')
	c = conn.cursor()
	c.execute('SELECT posted_to FROM Assignments WHERE assignment_id = ?', (aid, ))
	cid = c.fetchone()[0]
	
	c.execute('SELECT name FROM Courses WHERE course_id = ?', (cid,))
	dictionary['course'] = c.fetchone()[0]
	
	c.execute('SELECT name FROM Teachers WHERE teacher_id = ?', (tid,))
	dictionary['teacher'] = c.fetchone()[0]

	c.execute('SELECT tc_id FROM TC WHERE teacher_id = ? AND course_id = ?', (tid, cid))
	tc_took = c.fetchone()[0]
	
	c.execute('SELECT name, email, tc_id, student_id FROM Students')
	allstuds = c.fetchall()

	for i in allstuds:
		if(tc_took in i[2]):
			dictionary['students'].append([i[0],i[1],i[3]])

	conn.close()
	return dictionary


@app.route('/')
def home():
	return render_template('login.html')

@app.route('/login', methods=['GET','POST'])
def login():
	if request.method=='POST':
		user = request.form.get("username")
		password = request.form.get("password")
		#password =  hashlib.sha256(password.encode()).hexdigest()

		#teacher verification
		conn = sqlite3.connect('database.db')
		c = conn.cursor()
		c.execute('SELECT teacher_id FROM Teachers WHERE email = ? AND psw = ?', (user, password))
		temp = c.fetchone()

		if (temp is not None) and (len(temp)>0):
			session['user']='teacher'
			session['id'] = temp[0]
			conn.close()
			return redirect('/PES/teacher/'+temp[0]+'/assignments')

		#Student verification
		c.execute('SELECT student_id FROM students WHERE email = ? AND psw = ?', (user, password))
		temp = c.fetchone()
		conn.close()

		if (temp is not None) and (len(temp)>0):
			session['user']='student'
			session['id'] = temp[0]
			return redirect('/PES/student/'+temp[0]+'/assignments')
		else:
			return render_template('login.html')
	else:
		return render_template('login.html')

@app.route("/logout")
def logout():
	session.pop('user', None)
	session.pop('id', None)
	return render_template('login.html')


@app.route('/PES/teacher/<tid>/assignments')
def list_assignments_teachers(tid):
	#compulsory login
	if 'id' not in session:
		return render_template('login.html')

	#invalid user
	if tid != session['id'] or session['user']!='teacher':
		return "Please Check your URL"

	#database
	conn = sqlite3.connect('database.db')
	c = conn.cursor()

	#name of the teacher
	c.execute('SELECT name FROM Teachers WHERE teacher_id = ?', (tid,))
	name = c.fetchone()[0]
	#print(name)

	#all the assignments submitted by the teacher
	c.execute('SELECT * FROM Assignments WHERE posted_by = ?', (tid,))
	list_ass = c.fetchall()
	#print(list_ass)

	#prepare data to send
	passer=[]
	for item in list_ass:
		c.execute('SELECT name FROM Courses WHERE course_id = ?', (item[2],) )
		cname = c.fetchone()[0]
		cname = item[2] + ' (' + cname + ')' 
		#print(cname)

		passer.append({
			'assignment_id' : item[0],
			'heading' : item[4],
			'deadline' :item[5],
			'max_marks' : item[6],
			'posted_on' : item[3],
			'professor' : name,
			'course' : cname
		})

	#print(passer)
	conn.close()
	return render_template('teachers/list.html',arg=passer,id=tid)



@app.route('/PES/teacher/<tid>/upload', methods=['GET','POST'])
def upload_assignment_teachers(tid):
	if('id' not in session):
		return render_template('login.html')
	
	if tid != session['id'] or session['user']!='teacher':
		return "Please Check your URL"

	conn = sqlite3.connect('database.db')
	c = conn.cursor()
	
	if request.method=='GET':
		c.execute('SELECT course_id FROM TC WHERE teacher_id = ?', (session['id'],))
		temp = c.fetchall()
		temp = [tup[0] for tup in temp]

		if len(temp)>0:
			stri="('"
			for i in range(len(temp)):
				if(i<len(temp)-1):
					stri=stri+temp[i]+"','"
				else:
					stri=stri+temp[i]+"')"

			c.execute('SELECT course_id, name from Courses WHERE course_id IN ' + stri)
			course = c.fetchall()
		return render_template('teachers/upload_assignment.html',course=course,id=tid)
	
	if request.method=='POST':
		#deadline
		dead = request.form.get("datetime")
		deadline = datetime.strptime(dead, '%Y-%m-%dT%H:%M').strftime("%Y-%m-%d %H:%M:%S")
		#print(deadline)

		#required files
		sub_files = request.form.getlist("name[]")
		#print(sub_files)

		guid = uuid.uuid1()
		target = os.path.join(APP_ROOT,'attachments/',str(guid))
		#print(target)
		if not os.path.isdir(target):
			os.mkdir(target)
		fname = []
		for file in request.files.getlist("file"):
			#print(file)
			filename = file.filename
			fname.append(filename)
			destination = "/".join([target,filename])
			#print(destination)
			file.save(destination) 

		ass_id = str(guid) 	
		posted_by = session['id']
		online = int(request.form.get("type"))
		heading = request.form.get("name")
		description = request.form.get("message")
		max_marks = int(request.form.get("number"))
		deadline = str(deadline)
		posted_on = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		posted_to = request.form.get("select-form1-k")
		c.execute('SELECT course_id FROM Courses WHERE name = ?', (posted_to,))
		posted_to = c.fetchone()[0]
		files = ";;;".join(fname)
		submission_files = ";;;".join(sub_files)

		temp = (ass_id, posted_by, posted_to, posted_on, heading, deadline, max_marks, online, description, files, submission_files)
		c.execute("INSERT INTO Assignments VALUES(?,?,?,?,?,?,?,?,?,?,?)", temp)
		conn.commit()
		conn.close()

		dictionary=getstudents(str(guid),session['id'])
		#print(dictionary['students'])
		note1 = multiprocessing.Process(target=notify.NewAssignment,name="new_"+str(guid), args=(dictionary['students'],dictionary["teacher"],dictionary["course"],
				[url+"/PES/student/"+j[2]+"/assignments/"+str(guid) for j in dictionary['students']],
				request.form.get("name"))) 
		note2 = multiprocessing.Process(target=notify.Deadline,name=str(guid),args=(dictionary['students'],dictionary["teacher"],dictionary["course"],
				[url+"/PES/student/"+j[2]+"/assignments/"+str(guid) for j in dictionary['students']],
				request.form.get("name"),str(deadline)))
		note1.start()
		note2.start()
		
	return redirect(url_for('list_assignments_teachers',tid = tid))

@app.route('/PES/teacher/<tid>/assignment/<aid>')
def particular_assignment_teachers(tid,aid):
	if('id' not in session):
		return render_template('login.html')
	if tid != session['id'] or session['user']!='teacher':
		return "Please Check your URL"

	conn = sqlite3.connect('database.db')
	c = conn.cursor()
	
	c.execute('SELECT * FROM Assignments WHERE assignment_id = ?', (aid,))
	list_ass = c.fetchall()

	c.execute('SELECT name FROM Teachers WHERE teacher_id = ?', (tid,))
	name = c.fetchone()[0]

	for item in list_ass:
		c.execute('SELECT * FROM Courses WHERE course_id = ?', (item[2],))
		cname = c.fetchone()
		cname = cname[0] + ' (' + cname[1] + ')'
		conn.close()

		passer={}
		passer['assignment_id']=item[0]
		passer['heading'] = item[4]
		passer['deadline'] =item[5]
		passer['max_marks'] = item[6]
		passer['posted_on'] = item[3]
		passer['professor'] = name
		passer['course'] = cname
		passer['description'] = item[8]
		passer['online'] = item[7]
		passer['files']=item[9].split(';;;')
		return render_template('teachers/view_assignment.html',arg=passer,id=tid)

	conn.close()
	return "No such assignment"


@app.route('/PES/teacher/<tid>/updatemarks/<aid>',methods=["POST"])
def update_marks_teachers(tid,aid):
	if('id' not in session):
		return render_template('login.html')
	if tid != session['id'] or session['user']!='teacher':
		return "Please Check your URL"
	students_now=getstudents(aid,tid)
	dictionary=json.loads(request.data.decode("utf-8"))
	print(dictionary)
	conn = sqlite3.connect('database.db')
	c = conn.cursor()
	c.execute('UPDATE Submissions SET assigned_marks = ? WHERE student_id = ? AND submission_id = ? AND assignment_id = ?', (dictionary['marks'], dictionary['student_id'], dictionary['submission_id'], dictionary['assignment_id']))
	conn.commit()
	conn.close()
	
	return json.dumps(dictionary)

@app.route('/PES/teacher/<tid>/finalize')
def finalize_marks_teachers(tid):
	if('id' not in session):
		return render_template('login.html')
	if tid != session['id'] or session['user']!='teacher':
		return "Please Check your URL"

	conn = sqlite3.connect('database.db')
	c = conn.cursor()
	c.execute('SELECT course_id FROM TC WHERE teacher_id = ?', (tid, ))
	list_courses = c.fetchall()
	list_courses = [tup[0] for tup in list_courses]

	cnames=[]
	passer={}

	for cid in list_courses:
		c.execute('SELECT heading, max_marks, assignment_id FROM Assignments WHERE posted_to = ? AND posted_by=?', (cid, tid))
		list_ass = c.fetchall()

		c.execute('SELECT * FROM Courses WHERE course_id = ?', (cid,))
		cnames.append(c.fetchone()[0])

		passer[cid]=[]
		for item in list_ass:
			passer[cid].append({
					"heading" : item[0],
					"marks" : item[1],
					"assignment_id" : item[2],
					"url" : '/PES/teacher/'+tid+'/assignment/'+item[2]
			})
	return render_template('teachers/finalize_assignment_marks.html',passer=passer,id=tid,courses=cnames)


@app.route('/PES/teacher/<tid>/submissions/<aid>')
def view_submissions_teachers(tid,aid):
	if('id' not in session):
		return render_template('login.html')
	if tid != session['id'] or session['user']!='teacher':
		return "Please Check your URL"
	students_now=getstudents(aid,tid)
	conn = sqlite3.connect('database.db')
	c = conn.cursor()
	
	c.execute('SELECT max_marks, heading FROM Assignments WHERE assignment_id = ?', (aid,))
	temp = c.fetchone()
	max_marks,heading = temp[0], temp[1]
	print(temp)
	passer=[]
	print("students:",students_now)


	for student in students_now['students']:
		marks=0
		c.execute('SELECT student_id, description, files, submission_id FROM Submissions WHERE type = "submission" AND assignment_id = ? AND student_id = ?',(aid, student[2]))
		submissions_now = c.fetchall()
		print(submissions_now)

		if(len(submissions_now)!=0):
			c.execute('SELECT assigned_marks FROM Submissions WHERE assignment_id = ? AND student_id = ?', (aid, student[2]))
			marks = c.fetchone()
			if(len(marks)>0):
				marks=marks[0]
		else:
			submissions_now=[[student[2],"---","---","---"]]
		print(submissions_now)
		urls=[]
		temp = submissions_now[0][2].split(";;;")

		files = {}

		if len(temp)>1:
			for item in temp:
				t1 = item.split(":::")
				files[t1[0]] = t1[1]

		print("files:\n",files)
		for n,v in files.items():
			files[n]="/getfile/"+aid+"/"+student[2]+"/"+v
		
		dictionary={}
		dictionary["student_name"]=student[0]
		dictionary["student_id"]=submissions_now[0][0]
		dictionary["description"]=submissions_now[0][1]
		dictionary["files"]=files
		dictionary["submission_id"]=submissions_now[0][3]
		dictionary["marks"]=marks
		if(submissions_now[0][3]=='---'):
			dictionary["submitted"]=0
		else:
			dictionary["submitted"]=1
		passer.append(dictionary)

	print(passer)
	conn.close()
	return render_template('teachers/view_submissions.html',max_marks=max_marks,passer=passer,heading=heading,aid=aid,id=tid)

@app.route('/getfile/<aid>/<sid>/<file>')
def get_file_student(aid,sid,file):
	if('id' not in session):
		return render_template('login.html')
	try:
		return send_file('attachments/'+aid+'/'+sid+'/'+file, attachment_filename=file)
	except FileNotFoundError:
		return "File not found"

##########################################################################################################
@app.route('/PES/student/<sid>/assignments')
def list_assignments_students(sid):
	if('id' not in session):
		return render_template('login.html')
	if sid != session['id'] or session['user']!='student':
		return "Please Check your URL"
	
	conn = sqlite3.connect('database.db')
	c = conn.cursor()

	c.execute('SELECT tc_id FROM Students WHERE student_id = ?', (sid,))
	list_tc = c.fetchone()[0].split(';;;')
	#print(list_tc)

	passer=[]
	for tcid in list_tc:
		c.execute('SELECT course_id, teacher_id FROM TC WHERE tc_id = ?', (tcid,))
		temp = c.fetchone()
		cid = temp[0]
		tid = temp[1]

		c.execute('SELECT name FROM Courses WHERE course_id = ?', (cid,))
		cname = c.fetchone()[0]

		c.execute('SELECT name FROM Teachers WHERE teacher_id = ?', (tid,))
		name = c.fetchone()[0]
		
		c.execute('SELECT * FROM Assignments WHERE posted_by = ? AND posted_to = ?', (tid, cid))
		list_ass = c.fetchall()

		for item in list_ass:
			dead=datetime.strptime(item[5], '%Y-%m-%d %H:%M:%S')
			colour="#838587" 
			#838587 - grey #cc1b1b - red #edc928 - yellow #179c13 - green
			if(datetime.now()>dead):
				colour="#cc1b1b"
			elif((dead - datetime.now()).days<=1):
				colour = "#edc928"

			#Needs unit testing
			c.execute('SELECT student_id FROM Submissions WHERE assignment_id = ? AND type = "submission"', (item[0],))
			list_sid = c.fetchall()
			list_sid = [tup[0] for tup in list_sid]

			if sid in list_sid:
				colour="#179c13"
			passer.append({
				'assignment_id' : item[0],
				'heading' : item[4],
				'deadline' :item[5],
				'max_marks' : item[6],
				'posted_on' : item[3],
				'professor' : name,
				'course' : cname,
				'colour' : colour
			})
	conn.close()
	return render_template('students/assignment_list.html',arg=passer,id=sid)

@app.route('/PES/student/<sid>/assignment/<aid>')
def particular_assignment_students(sid,aid):
	if('id' not in session):
		return render_template('login.html')
	if sid != session['id'] or session['user']!='student':
		return "Please Check your URL"

	conn = sqlite3.connect('database.db')
	c = conn.cursor()

	c.execute('SELECT * FROM Assignments WHERE assignment_id = ?', (aid,))
	list_ass = c.fetchall()

	for item in list_ass:
		c.execute('SELECT course_id, name FROM Courses WHERE course_id = ?', (item[2],))
		cname = c.fetchone()
		cname = cname[0] + ' (' + cname[1] + ')'

		c.execute('SELECT name FROM Teachers WHERE teacher_id = ?', (item[1],))
		name = c.fetchone()[0]

		passer={}
		passer['assignment_id']=item[0]
		passer['heading'] = item[4]
		passer['deadline'] =item[5]
		passer['max_marks'] = item[6]
		passer['posted_on'] = item[3]
		passer['professor'] = name
		passer['course'] = cname
		passer['description'] = item[8]
		passer['online'] = item[7]
		passer['files']=item[9].split(';;;')

		conn.close()
		return render_template('students/assignment_details.html',arg=passer,id=sid)
	
	conn.close()
	return "No such assignment"

@app.route('/PES/teacher/<tid>/delete-assignment/<aid>')
def delete_assignment_teachers(tid,aid):
	if('id' not in session):
		return render_template('login.html')
	if tid != session['id'] or session['user']!='teacher':
		return "Please Check your URL"
	try:
		target = os.path.join(APP_ROOT,'attachments/',aid)
		if os.path.isdir(target):
		 	shutil.rmtree(target)

		print("here")
		list1 = multiprocessing.active_children()
		for thread in list1:
			if(thread.name == aid):
				thread.terminate()
		
		conn = sqlite3.connect('database.db')
		c = conn.cursor()
		c.execute('DELETE FROM Assignments WHERE posted_by = ? AND assignment_id = ? ', (tid,aid))
		conn.commit()
		conn.close()
		print("Done")
	except:
		return redirect(url_for('list_assignments_teachers',tid = tid))

	return redirect(url_for('list_assignments_teachers',tid = tid))

@app.route('/PES/student/<sid>/assignment/<aid>/submitpage')
def submit_page_assignment_students(sid,aid):
	if('id' not in session):
		return render_template('login.html')
	if sid != session['id'] or session['user']!='student':
		return "Please Check your URL"

	conn = sqlite3.connect('database.db')
	c = conn.cursor()

	c.execute('SELECT student_id from Submissions WHERE assignment_id = ? AND type = "submission"', (aid,))
	list_sid = c.fetchall()
	list_sid = [tup[0] for tup in list_sid]
	passer={}
	if sid in list_sid:
		c.execute('SELECT * FROM Assignments WHERE assignment_id = ?', (aid,))
		list_ass = c.fetchall()

		for item in list_ass:
			c.execute('SELECT name FROM Courses WHERE course_id = ?', (item[2],))
			cname = c.fetchone()[0]
			
			c.execute('SELECT name FROM Teachers WHERE teacher_id = ?', (item[1],))
			name = c.fetchone()[0]

			passer={}
			passer['assignment_id']=item[0]
			passer['heading'] = item[4]
			passer['deadline'] =item[5]
			passer['max_marks'] = item[6]
			passer['professor'] = name
			passer['course'] = cname

			c.execute('SELECT description, files, submitted_on FROM Submissions WHERE assignment_id = ? AND student_id = ? AND type ="submission"', (aid, sid))
			sub = c.fetchone()
			
			passer['description'] = sub[0]
			passer['files'] = []
			passer['filenames'] = []

			temp_list = sub[1].split(';;;')
			print(temp_list)
			for k in temp_list:
				temp = k.split(':::')
				passer['files'].append(temp[0])
				passer['filenames'].append(temp[1])
			
			passer['submitted_on'] = sub[2]
			
			conn.close()
			return render_template('students/view_submitted.html',arg=passer,id=sid)
		conn.close()
		return "No Such assignment"
	else:
		c.execute('SELECT assignment_id, submission_files FROM Assignments WHERE assignment_id = ?', (aid,))
		list_ass = c.fetchall()

		for item in list_ass:
			passer['assignment_id']=item[0]
			passer['submission_files']=item[1].split(';;;')
			conn.close()
			return render_template('students/submit.html',arg=passer,id=sid)
		conn.close()
		return "No Such Assignment"


@app.route('/PES/student/<sid>/assignment/<aid>/submit',methods=["POST"])
def submit_assignment_students(sid,aid):
	if('id' not in session):
		return render_template('login.html')
	if sid != session['id'] or session['user']!='student':
		return "Please Check your URL"

	conn = sqlite3.connect('database.db')
	c = conn.cursor()

	c.execute('SELECT student_id FROM Submissions WHERE assignment_id = ? AND type = "submission"', (aid,))
	list_sid = c.fetchall()
	list_sid = [tup[0] for tup in list_sid]

	if sid in list_sid:
		return redirect(url_for('submit_page_assignment_students',sid = sid,aid=aid))
	else:
		target = os.path.join(APP_ROOT,'attachments/', aid, sid)
		#print(target)
		if not os.path.isdir(target):
			os.mkdir(target)
		files = []
		for file,value in request.files.items():
			#print(file,value)
			filename = value.filename
			files.append(file + ":::" + filename)
			destination = "/".join([target,filename])
			#print(destination)
			value.save(destination) 

		files = ";;;".join(files)
		sub_id = str(uuid.uuid1())
		mks = int(0)

		temp_tup = (sub_id, sid, request.form.get("description"), files, 'submission', aid, datetime.now().strftime("%d-%m-%Y %H:%M:%S"), mks)
		print(temp_tup)
		c.execute('INSERT INTO Submissions VALUES (?,?,?,?,?,?,?,?)', temp_tup)
		conn.commit()
		conn.close()

		return redirect(url_for('submit_page_assignment_students',sid = sid, aid = aid))


@app.route('/PES/student/<sid>/assignment/<aid>/delete-submission')
def delete_submission_students(sid,aid):
	if('id' not in session):
		return render_template('login.html')
	if sid != session['id'] or session['user']!='student':
		return "Please Check your URL"
	try:
		target = os.path.join(APP_ROOT,'attachments/', aid, sid)
		if os.path.isdir(target):
			shutil.rmtree(target)

		conn = sqlite3.connect('database.db')
		c = conn.cursor()
		
		c.execute('SELECT submission_id FROM Submissions WHERE student_id = ? AND assignment_id = ? and type = "submission"', (sid, aid))
		sub_id = c.fetchone()[0]

		c.execute('DELETE FROM Submissions WHERE submission_id = ?', (sub_id,))
		conn.commit()
		conn.close()

	except:
		print("error")
		return redirect(url_for('list_assignments_students',sid = sid))
	
	return redirect(url_for('list_assignments_students',sid = sid))
	
if __name__ == '__main__':
   app.run(debug = True)




