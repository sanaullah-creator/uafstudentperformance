import os

class Config:

    SECRET_KEY = os.environ.get('SECRET_KEY', 'mysecretkey')

    MYSQL_HOST = 'mysql-2cda301d-uafstudentsperformance.k.aivencloud.com'

    MYSQL_USER = 'avnadmin'

    MYSQL_PASSWORD = 'avnadmin'

    MYSQL_DB = 'defaultdb'
    MYSQL_PORT = 12138
    # SECRET_KEY = os.environ.get('SECRET_KEY', 'mysecretkey')

    # MYSQL_HOST = 'localhost'

    # MYSQL_USER = 'root'

    # MYSQL_PASSWORD = ''

    # MYSQL_DB = 'student_performance_db'