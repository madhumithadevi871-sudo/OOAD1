"""Check XAMPP MySQL connectivity without exposing credentials."""
import os
import mysql.connector
from dotenv import load_dotenv
load_dotenv()
try:
    cn=mysql.connector.connect(host=os.getenv("DB_HOST","127.0.0.1"),port=int(os.getenv("DB_PORT","3306")),user=os.getenv("DB_USER","root"),password=os.getenv("DB_PASSWORD",""),database=os.getenv("DB_NAME","tour_travel_booking"))
    cur=cn.cursor(); cur.execute("SELECT DATABASE(), VERSION()"); db,version=cur.fetchone(); print(f"Connected to {db} (MySQL {version})."); cn.close()
except mysql.connector.Error as exc: raise SystemExit(f"MySQL connection failed ({exc.__class__.__name__}). Check XAMPP and .env.")
