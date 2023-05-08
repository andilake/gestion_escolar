# Web based student management system

### Video Demo:  <https://youtu.be/lunJ4meE8v4>

### Default admin login:
Username: admin@colegionuevo.com
Password: 123456

### Description:
This application is going to be used as management system of students information. It includes the folowwing sections:
- Login: Login page. You have to enter a valid admin email and password in order to be able to use the application.
- Index: Dashboard of the website. It has two charts created with Chart.js, one is the students per section and the other is the students per date.
- Student list: Lists all the active students in a sortable and searchable table. It can be filtered by section, grade and group and suspended users can be shown or hidden.
- New student: Creates a new student. After submitting the student info, the email address is created automatically, if another student already owns the email address, the system adds a numbre to the new one so there won't be duplicates.
- Edit student: Student information can be edited and from this page students can also be deleted or suspended/activated.
- Suspend/Delete users: Users can be suspended and deleted one by one or by selecting multiple of them.
- Deleted users: Deleted users can be restored or permanently deleted from the database.
- Group list: Lists all the exitent groups.
- New group: Creates a new group.
- Logout: Closes the current session.
- Responsive design: The application is responsive so it will work in small and big screens.

### Technologies used:
HTML, CSS, Javascript, Python, Flask, Bootstrap, Chart.js, SQLite,SQLAlchemy and Jinja.