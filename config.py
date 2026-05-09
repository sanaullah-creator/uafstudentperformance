import os

class Config:

    SECRET_KEY = os.environ.get('SECRET_KEY', 'mysecretkey')

    MYSQL_HOST = 'sql312.infinityfree.com'

    MYSQL_USER = 'if0_41847455'

    MYSQL_PASSWORD = 'I9BB771jqjT'

    MYSQL_DB = 'if0_41847455_studentperformance'
    # SECRET_KEY = os.environ.get('SECRET_KEY', 'mysecretkey')

    # MYSQL_HOST = 'localhost'

    # MYSQL_USER = 'root'

    # MYSQL_PASSWORD = ''

    # MYSQL_DB = 'student_performance_db'