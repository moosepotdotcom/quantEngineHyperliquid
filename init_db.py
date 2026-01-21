import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'WILLIAMS_ML_STRATEGY_V1'))
from auth import engine, Base, SessionLocal, create_user, get_user

def init_db():
    print("🔒 Initializing Secure Database...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Check if admin exists
    if get_user(db, "admin"):
        print("✅ Admin user already exists.")
    else:
        print("👤 Creating Default Admin User...")
        create_user(db, "admin", "admin@moosepot.com", "admin123", role="admin")
        print("✅ Admin created: admin / admin123")
        print("⚠️  PLEASE CHANGE THIS PASSWORD IMMEDIATELY AFTER LOGIN")
        
    db.close()

if __name__ == "__main__":
    init_db()
