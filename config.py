import os

class Config:

    SECRET_KEY = os.environ.get('SECRET_KEY', 'mysecretkey')

    MYSQL_HOST = 'localhost'

    MYSQL_USER = 'root'

    MYSQL_PASSWORD = ''

    MYSQL_DB = 'student_performance_db'