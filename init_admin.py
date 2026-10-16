"""Create an administrator interactively; no default password is shipped."""
import getpass
import os
import mysql.connector
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()
email=input("Admin email: ").strip().lower(); name=input("Admin full name: ").strip(); password=getpass.getpass("Admin password (12+ chars): ")
if len(password)<12: raise SystemExit("Use at least 12 characters.")
cn=mysql.connector.connect(host=os.getenv("DB_HOST","127.0.0.1"),port=int(os.getenv("DB_PORT","3306")),user=os.getenv("DB_USER","root"),password=os.getenv("DB_PASSWORD",""),database=os.getenv("DB_NAME","tour_travel_booking"))
try:
    cur=cn.cursor(); cur.execute("INSERT INTO users(full_name,email,phone,password_hash,role) VALUES(%s,%s,%s,%s,'admin')",(name,email,input("Phone: ").strip(),generate_password_hash(password))); cn.commit(); print("Administrator created.")
finally: cn.close()
