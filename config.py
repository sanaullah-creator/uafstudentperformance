import os
from urllib.parse import quote_plus

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mysecretkey')
    
    # ==================== MongoDB Atlas Configuration ====================
    MONGO_USER = "uafstudent"
    MONGO_PASSWORD = "Sa805124@"
    
    MONGO_URI = (
        f"mongodb+srv://{quote_plus(MONGO_USER)}:{quote_plus(MONGO_PASSWORD)}"
        f"@uafstudentperformance.hegsh6s.mongodb.net/"
        f"student_performance_db?retryWrites=true&w=majority&appName=uafstudentperformance"
    )