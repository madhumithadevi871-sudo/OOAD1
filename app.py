"""Tour and Travel Booking Management System — Flask entry point."""
import os
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps
from uuid import uuid4

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
app = Flask(__name__)
app.config.update(SECRET_KEY=os.getenv("SECRET_KEY", "local-demo-change-me"), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

def connect():
    return mysql.connector.connect(host=os.getenv("DB_HOST", "127.0.0.1"), port=int(os.getenv("DB_PORT", "3306")), user=os.getenv("DB_USER", "root"), password=os.getenv("DB_PASSWORD", ""), database=os.getenv("DB_NAME", "tour_travel_booking"))

def query(sql, params=(), one=False, commit=False):
    cn = connect()
    try:
        cur = cn.cursor(dictionary=True); cur.execute(sql, params)
        # INSERT/UPDATE/DELETE statements have no result set. Fetching from
        # those cursors raises an InterfaceError before the requested commit.
        result = (cur.fetchone() if one else cur.fetchall()) if cur.with_rows else None
        if commit: cn.commit()
        return result
    finally: cn.close()

def transaction(fn):
    cn=connect()
    try:
        cur=cn.cursor(dictionary=True); result=fn(cn,cur); cn.commit(); return result
    except Exception: cn.rollback(); raise
    finally: cn.close()

def login_required(fn):
    @wraps(fn)
    def wrapped(*a,**kw):
        if not session.get("user_id"):
            flash("Please sign in to continue.","warning"); return redirect(url_for("login"))
        return fn(*a,**kw)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    def wrapped(*a,**kw):
        if session.get("role")!="admin": abort(403)
        return fn(*a,**kw)
    return wrapped

@app.context_processor
def common(): return {"current_user":session.get("user_name"),"role":session.get("role")}

@app.route("/")
def home():
    try: rows=query("SELECT * FROM destinations WHERE is_active=1 ORDER BY name LIMIT 6")
    except mysql.connector.Error: rows=[]
    return render_template("index.html",destinations=rows)

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form.get("full_name","").strip(); email=request.form.get("email","").strip().lower(); phone=request.form.get("phone","").strip(); password=request.form.get("password","")
        if not name or "@" not in email or len(password)<8 or password!=request.form.get("confirm_password") or not phone: flash("Enter valid details and matching passwords (8+ characters).","danger")
        else:
            try:
                query("INSERT INTO users(full_name,email,phone,password_hash,role) VALUES(%s,%s,%s,%s,'customer')",(name,email,phone,generate_password_hash(password)),commit=True)
                flash("Account created. Please sign in.","success"); return redirect(url_for("login"))
            except mysql.connector.IntegrityError: flash("That email is already registered.","danger")
    return render_template("register.html")

def _login_flow(admin_page):
    if request.method=="POST":
        email=request.form.get("email","").strip().lower()
        user=query("SELECT * FROM users WHERE email=%s AND is_active=1",(email,),one=True)
        required_role="admin" if admin_page else "customer"
        if user and user["role"]==required_role and check_password_hash(user["password_hash"],request.form.get("password","")):
            session.clear(); session.update(user_id=user["id"],user_name=user["full_name"],role=user["role"])
            return redirect(url_for("admin_dashboard" if user["role"]=="admin" else "dashboard"))
        flash("Email or password is incorrect.","danger")
    return render_template("login.html",admin_page=admin_page)

@app.route("/login",methods=["GET","POST"])
def login():
    return _login_flow(False)

@app.route("/admin/login",methods=["GET","POST"])
def admin_login():
    return _login_flow(True)

@app.route("/logout",methods=["POST"])
def logout(): session.clear(); flash("You have signed out.","success"); return redirect(url_for("home"))

@app.route("/profile",methods=["GET","POST"])
@login_required
def profile():
    if request.method=="POST":
        name=request.form.get("full_name","").strip(); phone=request.form.get("phone","").strip()
        if not name or not phone: flash("Name and phone are required.","danger")
        else:
            query("UPDATE users SET full_name=%s,phone=%s WHERE id=%s",(name,phone,session["user_id"]),commit=True); session["user_name"]=name; flash("Profile updated.","success")
    return render_template("profile.html",user=query("SELECT full_name,email,phone FROM users WHERE id=%s",(session["user_id"],),one=True))

@app.route("/destinations")
def destinations(): return render_template("destinations.html",destinations=query("SELECT * FROM destinations WHERE is_active=1 ORDER BY name"))

@app.route("/packages")
def packages():
    clauses=["p.status='active'"]; args=[]
    if request.args.get("q"): clauses.append("(p.title LIKE %s OR d.name LIKE %s)"); args.extend([f"%{request.args['q']}%"]*2)
    if request.args.get("max_price"):
        try: clauses.append("p.price_per_person<=%s"); args.append(Decimal(request.args["max_price"]))
        except InvalidOperation: pass
    order={"price_asc":"p.price_per_person ASC","price_desc":"p.price_per_person DESC"}.get(request.args.get("sort"),"p.created_at DESC")
    rows=query(f"SELECT p.*,d.name destination_name FROM tour_packages p JOIN destinations d ON d.id=p.destination_id WHERE {' AND '.join(clauses)} ORDER BY {order}",tuple(args))
    return render_template("packages.html",packages=rows)

@app.route("/packages/<int:package_id>")
def package_detail(package_id):
    p=query("SELECT p.*,d.name destination_name FROM tour_packages p JOIN destinations d ON d.id=p.destination_id WHERE p.id=%s AND p.status='active'",(package_id,),one=True)
    if not p: abort(404)
    return render_template("package_detail.html",package=p)

@app.route("/bookings",methods=["GET","POST"])
@login_required
def bookings():
    if request.method=="POST":
        try:
            pid=int(request.form["package_id"]); count=int(request.form["traveller_count"]); start=date.fromisoformat(request.form["travel_start_date"])
            if start<date.today() or not 1<=count<=20: raise ValueError("Choose a future date and 1–20 travellers.")
            ref="TRV-"+uuid4().hex[:10].upper()
            def create(cn,cur):
                cur.execute("SELECT * FROM tour_packages WHERE id=%s AND status='active' FOR UPDATE",(pid,)); p=cur.fetchone()
                if not p or p["available_seats"]<count: raise ValueError("Not enough seats remain.")
                total=Decimal(p["price_per_person"])*count
                cur.execute("UPDATE tour_packages SET available_seats=available_seats-%s WHERE id=%s",(count,pid))
                cur.execute("INSERT INTO bookings(booking_reference,customer_id,package_id,travel_start_date,travel_end_date,traveller_count,amount_before_adjustments,discount_amount,tax_amount,final_amount,booking_status,payment_status) VALUES(%s,%s,%s,%s,%s,%s,%s,0,0,%s,'awaiting_payment','unpaid')",(ref,session["user_id"],pid,start,start+timedelta(days=p["duration_days"]-1),count,total,total))
                return cur.lastrowid
            bid=transaction(create); return redirect(url_for("payment",booking_id=bid))
        except (ValueError,KeyError,mysql.connector.Error) as exc: flash(str(exc) or "Could not create booking.","danger")
    rows=query("SELECT b.*,p.title package_title FROM bookings b LEFT JOIN tour_packages p ON p.id=b.package_id WHERE b.customer_id=%s ORDER BY b.created_at DESC",(session["user_id"],))
    return render_template("bookings.html",bookings=rows,packages=query("SELECT id,title,price_per_person,duration_days,available_seats FROM tour_packages WHERE status='active' AND available_seats>0"),today=date.today().isoformat())

@app.route("/payments/<int:booking_id>",methods=["GET","POST"])
@login_required
def payment(booking_id):
    b=query("SELECT b.*,COALESCE(p.title,c.unique_reference) package_title,u.full_name FROM bookings b JOIN users u ON u.id=b.customer_id LEFT JOIN tour_packages p ON p.id=b.package_id LEFT JOIN custom_tours c ON c.id=b.custom_tour_id WHERE b.id=%s AND b.customer_id=%s",(booking_id,session["user_id"]),one=True)
    if not b: abort(404)
    if request.method=="POST":
        tx="DEMO-"+uuid4().hex[:12].upper()
        def pay(cn,cur):
            cur.execute("SELECT * FROM bookings WHERE id=%s AND customer_id=%s FOR UPDATE",(booking_id,session["user_id"])); locked=cur.fetchone()
            if not locked: raise LookupError()
            if locked["payment_status"]=="paid": return
            cur.execute("INSERT INTO payments(booking_id,transaction_reference,payment_method,amount,payment_status,payment_mode,paid_at) VALUES(%s,%s,'demo',%s,'success','simulated',NOW())",(booking_id,tx,locked["final_amount"]))
            cur.execute("UPDATE bookings SET payment_status='paid',booking_status='confirmed' WHERE id=%s",(booking_id,))
            if locked["custom_tour_id"]:
                cur.execute("UPDATE custom_tours SET status='confirmed',updated_at=NOW() WHERE id=%s AND status='approved_for_booking'",(locked["custom_tour_id"],))
                cur.execute("UPDATE itineraries SET confirmation_status='confirmed' WHERE custom_tour_id=%s",(locked["custom_tour_id"],))
        try: transaction(pay)
        except LookupError: abort(404)
        return redirect(url_for("receipt",booking_id=booking_id))
    return render_template("payment.html",booking=b)

@app.route("/payments/<int:booking_id>/receipt")
@login_required
def receipt(booking_id):
    b=query("SELECT b.*,COALESCE(p.title,c.unique_reference) package_title,u.full_name,pay.transaction_reference,pay.payment_mode,pay.payment_status FROM bookings b JOIN users u ON u.id=b.customer_id LEFT JOIN tour_packages p ON p.id=b.package_id LEFT JOIN custom_tours c ON c.id=b.custom_tour_id LEFT JOIN payments pay ON pay.booking_id=b.id WHERE b.id=%s AND b.customer_id=%s ORDER BY pay.id DESC LIMIT 1",(booking_id,session["user_id"]),one=True)
    if not b: abort(404)
    return render_template("receipt.html",booking=b)

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html",bookings=query("SELECT b.*,p.title package_title FROM bookings b LEFT JOIN tour_packages p ON p.id=b.package_id WHERE b.customer_id=%s ORDER BY b.created_at DESC LIMIT 8",(session["user_id"],)),tours=query("SELECT * FROM custom_tours WHERE customer_id=%s ORDER BY updated_at DESC",(session["user_id"],)))

@app.route("/custom-tours",methods=["GET","POST"])
@login_required
def custom_tours():
    if request.method=="POST":
        f=request.form
        try:
            start=date.fromisoformat(f["start_date"]); end=date.fromisoformat(f["end_date"]); count=int(f["traveller_count"]); budget=Decimal(f.get("budget") or "0")
            if end<start or start<date.today() or not 1<=count<=30 or budget<0: raise ValueError()
            ref="CT-"+uuid4().hex[:10].upper()
            def save(cn,cur):
                cur.execute("INSERT INTO custom_tours(unique_reference,customer_id,departure_city,start_date,end_date,traveller_count,budget,accommodation_preference,room_count,transport_preference,travel_style,dietary_preferences,special_requests,estimated_total,status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'draft')",(ref,session["user_id"],f.get("departure_city"),start,end,count,budget,f.get("accommodation"),int(f.get("room_count") or 1),f.get("transport"),f.get("travel_style"),f.get("dietary"),f.get("special_requests"),budget))
                tid=cur.lastrowid
                for i,did in enumerate(f.getlist("destination_ids"),1): cur.execute("INSERT INTO custom_tour_destinations(custom_tour_id,destination_id,sequence_number) VALUES(%s,%s,%s)",(tid,int(did),i))
                for i,act in enumerate(f.getlist("activities"),1):
                    if act.strip(): cur.execute("INSERT INTO custom_tour_activities(custom_tour_id,activity_name,sequence_number) VALUES(%s,%s,%s)",(tid,act.strip(),i))
                return tid
            transaction(save); flash(f"Draft {ref} saved. Review and submit it for a quote.","success"); return redirect(url_for("dashboard"))
        except (ValueError,KeyError,mysql.connector.Error): flash("Please check the tour details and selected destinations.","danger")
    return render_template("custom_tours.html",destinations=query("SELECT * FROM destinations WHERE is_active=1 ORDER BY name"))

@app.route("/custom-tours/<int:tour_id>")
@login_required
def custom_tour_detail(tour_id):
    t=query("SELECT * FROM custom_tours WHERE id=%s AND customer_id=%s",(tour_id,session["user_id"]),one=True)
    if not t: abort(404)
    t["destinations"]=query("SELECT d.name FROM custom_tour_destinations x JOIN destinations d ON d.id=x.destination_id WHERE x.custom_tour_id=%s ORDER BY x.sequence_number",(tour_id,))
    t["quotations"]=query("SELECT * FROM custom_tour_quotations WHERE custom_tour_id=%s ORDER BY created_at DESC",(tour_id,))
    t["itinerary"]=query("SELECT i.*,d.name destination_name FROM itineraries i LEFT JOIN destinations d ON d.id=i.destination_id WHERE i.custom_tour_id=%s ORDER BY i.day_number,i.sequence_number",(tour_id,))
    t["booking"]=query("SELECT id,booking_reference,payment_status FROM bookings WHERE custom_tour_id=%s",(tour_id,),one=True)
    return render_template("custom_tour_detail.html",tour=t)

@app.route("/custom-tours/<int:tour_id>/submit",methods=["POST"])
@login_required
def submit_tour(tour_id):
    t=query("SELECT id FROM custom_tours WHERE id=%s AND customer_id=%s AND status='draft'",(tour_id,session["user_id"]),one=True)
    if not t: abort(404)
    query("UPDATE custom_tours SET status='submitted',updated_at=NOW() WHERE id=%s",(tour_id,),commit=True); flash("Request submitted for admin review.","success"); return redirect(url_for("custom_tour_detail",tour_id=tour_id))

@app.route("/custom-tours/<int:tour_id>/respond",methods=["POST"])
@login_required
def respond_quote(tour_id):
    choice=request.form.get("response"); status={"accept":"approved_for_booking","reject":"rejected","modify":"modification_requested"}.get(choice)
    if not status: abort(400)
    t=query("SELECT id FROM custom_tours WHERE id=%s AND customer_id=%s AND status='awaiting_customer_approval'",(tour_id,session["user_id"]),one=True)
    if not t: abort(404)
    def respond(cn,cur):
        cur.execute("SELECT id FROM custom_tour_quotations WHERE custom_tour_id=%s AND quotation_status='sent' AND customer_response IS NULL ORDER BY created_at DESC LIMIT 1",(tour_id,)); q=cur.fetchone()
        if not q: raise ValueError("No unanswered quotation is available.")
        cur.execute("UPDATE custom_tour_quotations SET customer_response=%s,responded_at=NOW() WHERE id=%s",(choice,q["id"]))
        cur.execute("UPDATE custom_tours SET status=%s,updated_at=NOW() WHERE id=%s",(status,tour_id))
        cur.execute("INSERT INTO custom_tour_status_history(custom_tour_id,previous_status,new_status,changed_by,change_reason) VALUES(%s,'awaiting_customer_approval',%s,%s,%s)",(tour_id,status,session["user_id"],choice))
    try: transaction(respond); flash("Your response was saved.","success")
    except ValueError: flash("No unanswered quotation is available.","warning")
    return redirect(url_for("custom_tour_detail",tour_id=tour_id))

@app.route("/custom-tours/<int:tour_id>/generate-itinerary",methods=["POST"])
@login_required
def generate_custom_itinerary(tour_id):
    t=query("SELECT * FROM custom_tours WHERE id=%s AND customer_id=%s AND status IN ('draft','submitted','under_review','awaiting_customer_approval','approved_for_booking')",(tour_id,session["user_id"]),one=True)
    if not t: abort(404)
    destinations=query("SELECT d.id,d.name FROM custom_tour_destinations x JOIN destinations d ON d.id=x.destination_id WHERE x.custom_tour_id=%s ORDER BY x.sequence_number",(tour_id,))
    activities=query("SELECT activity_name,description FROM custom_tour_activities WHERE custom_tour_id=%s ORDER BY sequence_number",(tour_id,))
    if not destinations: flash("Choose at least one destination before generating an itinerary.","warning"); return redirect(url_for("custom_tour_detail",tour_id=tour_id))
    days=(t["end_date"]-t["start_date"]).days+1
    def generate(cn,cur):
        cur.execute("DELETE FROM itineraries WHERE custom_tour_id=%s AND confirmation_status='suggested'",(tour_id,))
        for day in range(days):
            destination=destinations[min(len(destinations)-1,day*len(destinations)//days)]
            activity=activities[day%len(activities)]["activity_name"] if activities else f"Explore {destination['name']} at your own pace"
            description=next((a["description"] for a in activities if a["activity_name"]==activity),None) or "Suggested activity; confirm details and availability with the travel team."
            cur.execute("INSERT INTO itineraries(custom_tour_id,day_number,destination_id,activity_name,description,activity_date,start_time,end_time,sequence_number,confirmation_status) VALUES(%s,%s,%s,%s,%s,%s,'10:00:00','13:00:00',1,'suggested')",(tour_id,day+1,destination["id"],activity,description,t["start_date"]+timedelta(days=day)))
    transaction(generate); flash("Suggested itinerary generated. Confirm details and availability with the travel team.","success")
    return redirect(url_for("custom_tour_detail",tour_id=tour_id))

@app.route("/custom-tours/<int:tour_id>/book",methods=["POST"])
@login_required
def convert_custom_tour(tour_id):
    ref="TRV-"+uuid4().hex[:10].upper()
    def convert(cn,cur):
        cur.execute("SELECT * FROM custom_tours WHERE id=%s AND customer_id=%s FOR UPDATE",(tour_id,session["user_id"])); t=cur.fetchone()
        if not t or t["status"]!="approved_for_booking" or not t["quoted_total"]: raise ValueError()
        cur.execute("SELECT id FROM bookings WHERE custom_tour_id=%s",(tour_id,)); existing=cur.fetchone()
        if existing: return existing["id"]
        total=t["quoted_total"]
        cur.execute("INSERT INTO bookings(booking_reference,customer_id,custom_tour_id,travel_start_date,travel_end_date,traveller_count,amount_before_adjustments,discount_amount,tax_amount,final_amount,booking_status,payment_status) VALUES(%s,%s,%s,%s,%s,%s,%s,0,0,%s,'awaiting_payment','unpaid')",(ref,session["user_id"],tour_id,t["start_date"],t["end_date"],t["traveller_count"],total,total))
        return cur.lastrowid
    try: bid=transaction(convert)
    except ValueError: abort(409)
    return redirect(url_for("payment",booking_id=bid))

@app.route("/admin")
@admin_required
def admin_dashboard():
    stats={"customers":query("SELECT COUNT(*) n FROM users WHERE role='customer'",one=True)["n"],"packages":query("SELECT COUNT(*) n FROM tour_packages WHERE status='active'",one=True)["n"],"bookings":query("SELECT COUNT(*) n FROM bookings",one=True)["n"],"pending":query("SELECT COUNT(*) n FROM custom_tours WHERE status IN ('submitted','under_review','modification_requested')",one=True)["n"]}
    tours=query("SELECT t.*,u.full_name FROM custom_tours t JOIN users u ON u.id=t.customer_id WHERE t.status IN ('submitted','modification_requested','under_review') ORDER BY t.created_at")
    bookings=query("SELECT b.*,u.full_name,p.title package_title FROM bookings b JOIN users u ON u.id=b.customer_id LEFT JOIN tour_packages p ON p.id=b.package_id ORDER BY b.created_at DESC LIMIT 50")
    customers=query("SELECT id,full_name,email,phone,created_at,is_active FROM users WHERE role='customer' ORDER BY created_at DESC LIMIT 8")
    return render_template("admin_dashboard.html",stats=stats,tours=tours,bookings=bookings,customers=customers)

@app.route("/admin/customers")
@admin_required
def admin_customers():
    search=request.args.get("q","").strip()
    if search:
        term=f"%{search}%"
        customers=query("SELECT id,full_name,email,phone,created_at,is_active FROM users WHERE role='customer' AND (full_name LIKE %s OR email LIKE %s OR phone LIKE %s) ORDER BY created_at DESC LIMIT 200",(term,term,term))
    else:
        customers=query("SELECT id,full_name,email,phone,created_at,is_active FROM users WHERE role='customer' ORDER BY created_at DESC LIMIT 200")
    return render_template("admin_customers.html",customers=customers,search=search)

@app.route("/admin/custom-tours/<int:tour_id>/quotation",methods=["POST"])
@admin_required
def admin_quote(tour_id):
    try: amount=Decimal(request.form.get("amount","0"))
    except InvalidOperation: amount=Decimal(0)
    note=request.form.get("notes","").strip()
    if amount<=0: flash("Quotation must be greater than zero.","danger"); return redirect(url_for("admin_dashboard"))
    t=query("SELECT id,status FROM custom_tours WHERE id=%s AND status IN ('submitted','under_review','modification_requested')",(tour_id,),one=True)
    if not t: abort(404)
    def quote(cn,cur):
        cur.execute("INSERT INTO custom_tour_quotations(custom_tour_id,admin_id,quotation_amount,quotation_notes,quotation_status) VALUES(%s,%s,%s,%s,'sent')",(tour_id,session["user_id"],amount,note))
        cur.execute("UPDATE custom_tours SET quoted_total=%s,status='awaiting_customer_approval',updated_at=NOW() WHERE id=%s",(amount,tour_id))
        cur.execute("INSERT INTO custom_tour_status_history(custom_tour_id,previous_status,new_status,changed_by,change_reason) VALUES(%s,%s,'awaiting_customer_approval',%s,%s)",(tour_id,t["status"],session["user_id"],note))
    transaction(quote); flash("Quotation sent to customer.","success"); return redirect(url_for("admin_dashboard"))

@app.route("/admin/packages",methods=["GET","POST"])
@admin_required
def admin_packages():
    if request.method=="POST":
        f=request.form
        try:
            days=int(f["days"]); seats=int(f["seats"]); price=Decimal(f["price"])
            if days<1 or seats<1 or price<0: raise ValueError()
            query("INSERT INTO tour_packages(destination_id,title,description,duration_days,duration_nights,price_per_person,maximum_capacity,available_seats,inclusions,exclusions,accommodation_details,transport_details,status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'active')",(int(f["destination_id"]),f["title"],f["description"],days,days-1,price,seats,seats,f.get("inclusions"),f.get("exclusions"),f.get("accommodation"),f.get("transport")),commit=True); flash("Package added.","success")
        except Exception: flash("Package details were invalid.","danger")
    return render_template("admin_packages.html",packages=query("SELECT p.*,d.name destination_name FROM tour_packages p JOIN destinations d ON d.id=p.destination_id ORDER BY p.created_at DESC"),destinations=query("SELECT id,name FROM destinations WHERE is_active=1"))

@app.route("/admin/packages/<int:pid>/deactivate",methods=["POST"])
@admin_required
def deactivate_package(pid):
    query("UPDATE tour_packages SET status='inactive' WHERE id=%s",(pid,),commit=True); flash("Package deactivated.","success"); return redirect(url_for("admin_packages"))

@app.errorhandler(mysql.connector.Error)
def db_error(error):
    app.logger.error("Database failure (%s)",error.__class__.__name__)
    return render_template("error.html",message="The database is unavailable. Start XAMPP MySQL and check your .env settings."),503

if __name__=="__main__": app.run(debug=os.getenv("FLASK_DEBUG","0")=="1")
