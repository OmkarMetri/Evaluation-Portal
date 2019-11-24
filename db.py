import sqlite3
def main(database_path):
	student_create_table = """ CREATE TABLE IF NOT EXISTS Students (
				student_id TEXT NOT NULL,
				name TEXT NOT NULL,
				email TEXT NOT NULL,
				psw TEXT NOT NULL,
				tc_id TEXT NOT NULL
				); """

	teacher_create_table = """CREATE TABLE IF NOT EXISTS Teachers (
				teacher_id TEXT NOT NULL,
				name TEXT NOT NULL,
				email TEXT NOT NULL,
				psw TEXT NOT NULL
				);"""

	submissions_create_table = """ CREATE TABLE IF NOT EXISTS Submissions (
				submission_id TEXT NOT NULL,
				student_id TEXT NOT NULL,
				description TEXT NOT NULL,
				files TEXT NOT NULL,
				type TEXT NOT NULL,
				assignment_id TEXT NOT NULL,
				submitted_on TEXT NOT NULL,
				assigned_marks INTEGER NOT NULL
				);"""

	tc_create_table = """CREATE TABLE IF NOT EXISTS TC (
				tc_id TEXT NOT NULL,
				course_id TEXT NOT NULL,
				teacher_id TEXT NOT NULL
				);"""

	assignments_create_table = """CREATE TABLE IF NOT EXISTS Assignments (
				assignment_id TEXT NOT NULL,
				posted_by TEXT NOT NULL, 
				posted_to TEXT NOT NULL, 
				posted_on TEXT NOT NULL,
				heading TEXT NOT NULL,
				deadline TEXT NOT NULL,
				max_marks INTEGER NOT NULL,
				online INTEGER NOT NULL,
				description TEXT NOT NULL,
				files TEXT NOT NULL,
				submission_files TEXT NOT NULL
				);"""

	courses_create_table = """CREATE TABLE IF NOT EXISTS Courses (
				course_id TEXT NOT NULL,
				name TEXT NOT NULL
				);"""

	#create a database connection
	conn = sqlite3.connect(database_path)
	
	if conn is not None:
		c = conn.cursor()
		c.execute(student_create_table)
		c.execute(teacher_create_table)
		c.execute(courses_create_table)
		c.execute(assignments_create_table)
		c.execute(tc_create_table)
		c.execute(submissions_create_table)
		c.execute('INSERT INTO Teachers VALUES ("1", "prof1", "prof1@gmail.com", "1234");')
		c.execute('INSERT INTO Teachers VALUES ("2", "prof2", "prof2@gmail.com", "1234");')
		c.execute('INSERT INTO Students VALUES ("1", "stud1", "stud1@gmail.com", "12345", "T1;;;T2");')
		c.execute('INSERT INTO Students VALUES ("2", "stud2", "stud2@gmail.com", "12345", "T1;;;T2");')
		c.execute('INSERT INTO Courses VALUES ("CS401", "OOMD");')
		c.execute('INSERT INTO Courses VALUES ("CS402", "SE");')
		c.execute('INSERT INTO TC VALUES ("T1", "CS401", "1");')
		c.execute('INSERT INTO TC VALUES ("T2", "CS402", "1");')
		conn.commit()
		conn.close()
		
	else:
		print("Error! cannot create the database connection.")
		
if __name__ == '__main__':
	db_path = "database.db"
	main(db_path)