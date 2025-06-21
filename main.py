from flask import Flask, render_template, request, g, redirect, session, url_for, flash, jsonify, current_app
import sqlite3, os, json, random, string, smtplib, ssl, time
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask_login import LoginManager, current_user, login_required, login_user, logout_user

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

APP_NAME = "Yash Cyber Cafe"
EMAIL_ADDRESS = "yashcybercafeofficial@gmail.com"
EMAIL_PASSWORD = "jgwujcylyefeaefz"
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'users.db')

def generate_random_otp(length=6):
    import random
    return ''.join(random.choices('0123456789', k=length))

def send_otp_to_email(email, otp):
    import smtplib, ssl

    subject = f"{APP_NAME} - OTP Verification"
    body = f"""Hello,

Your OTP for {APP_NAME} is: {otp}

This code is valid for 5 minutes. Please do not share it with anyone.

Regards,  
{APP_NAME} Team
"""

    # Add custom From header (may be ignored by Gmail)
    message = f"From: {APP_NAME} <{EMAIL_ADDRESS}>\nSubject: {subject}\n\n{body}"

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, email, message)
        return True
    except Exception as e:
        print("OTP send error:", e)
        return False

def send_user_welcome_email(email, name):
    import smtplib, ssl

    subject = f"Welcome to {APP_NAME}!"
    body = f"""Hello {name},

🎉 Welcome to {APP_NAME}!

Your account has been created successfully. You can now log in using the following email:

📧 User ID: {email}

If you have any questions or need help, feel free to reach out to our support team.

We're excited to have you on board!

Warm regards,  
{APP_NAME} Team
"""

    message = f"Subject: {subject}\n\n{body}"

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, email, message)
        return True
    except Exception as e:
        print("Failed to send user welcome email:", e)
        return False

def send_admin_welcome_email(email, name, password):
    import smtplib, ssl

    subject = f"{APP_NAME} - Admin Account Created"
    body = f"""Hi {name},

Welcome to {APP_NAME}! Your admin account has been created successfully.

📧 Email: {email}
🔐 Default Password: {password}

👉 Please log in and change your password immediately from your account settings for security.

If you did not request this account, please contact the system owner.

Regards,  
{APP_NAME} Team
"""

    # Include 'From' properly in the message
    message = f"From: {APP_NAME} <{EMAIL_ADDRESS}>\nTo: {email}\nSubject: {subject}\n\n{body}"

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, email, message)
        print("✅ Admin welcome email sent.")
        return True
    except Exception as e:
        print("❌ Failed to send admin welcome email:", e)
        return False

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, timeout=10)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def get_user_db():
    conn = sqlite3.connect(DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def get_product_db():
    conn = sqlite3.connect('product.db', timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def get_services_db():
    conn = sqlite3.connect("services.db", timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_temp_password(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def utc_to_local(utc_str):
    utc_time = datetime.strptime(utc_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("UTC"))
    local_time = utc_time.astimezone(ZoneInfo("Asia/Kolkata"))
    return local_time.strftime("%d/%m/%y %I:%M %p")

@app.template_filter('datetimeformat')
def format_datetime(value):
    try:
        utc = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        ist = utc + timedelta(hours=5, minutes=30)
        return ist.strftime("%d/%m/%Y %I:%M %p")
    except Exception:
        return value

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

def get_user():
    user = session.get("user")
    if not user or not isinstance(user, dict):
        return None

    user_email = user.get("email")
    if not user_email:
        return None

    conn = get_db()
    row = conn.execute(
        """
        SELECT id, full_name, email, profile_image, role, contact, gender_id,
               security_question, security_answer
        FROM users
        WHERE email = ?
        """, (user_email,)
    ).fetchone()

    if row:
        return dict(row)

    return None

def handle_login(expected_role):
    email = request.form.get("email")
    password = request.form.get("password")

    conn = get_user_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if user and check_password_hash(user["password"], password):
        if user["role"] != expected_role:
            flash("Invalid login for this portal.", "error")
            return redirect(request.path)

        session["user_id"] = user["id"]
        flash("Logged in successfully!", "success")
        return redirect(url_for("dashboard"))

    flash("Invalid credentials", "error")
    return redirect(request.path)

@app.route('/')
def login_user():
    conn = get_product_db()
    product_items = conn.execute("SELECT * FROM product").fetchall()
    conn.close()

    # Convert to list of dicts and parse image
    parsed_products = []
    for item in product_items:
        product_dict = dict(item)
        try:
            images = json.loads(product_dict['images'])
            product_dict['image_url'] = images[0] if images else None
        except Exception:
            product_dict['image_url'] = None
        parsed_products.append(product_dict)

    return render_template('login_user.html', product_items=parsed_products)

@app.route("/quick-links")
def quick_links():
    return render_template("quick_links.html")

@app.route("/home")
def home():
    user = get_user()
    if not user:
        return redirect(url_for("login_user"))

    conn = get_product_db()

    # Fetch product items
    cursor = conn.execute("SELECT id, name, description, price, discount_price, images FROM product")
    product_items = []
    for row in cursor.fetchall():
        try:
            images = json.loads(row["images"]) if row["images"] else []
        except Exception:
            images = []
        product_items.append({
            'id': row['id'],
            'name': row['name'],
            'description': row['description'],
            'price': row['price'],
            'discount_price': row['discount_price'],
            'images': images
        })

    # Fetch last used address
    last_order = conn.execute("""
        SELECT address1, address2, city, pincode 
        FROM orders 
        WHERE user_email = ? 
        ORDER BY id DESC LIMIT 1
    """, (user['email'],)).fetchone()

    conn.close()

    return render_template(
        "home.html",
        user=user,
        full_name=user["full_name"],
        product_items=product_items,
        last_order=last_order
    )

@app.route("/my_orders")
def my_orders():
    user = get_user()
    if not user:
        return redirect(url_for("login_user"))

    conn = get_product_db()
    cursor = conn.execute(
        """
        SELECT id, item_name, quantity, status, address1, address2, city, pincode, 
               order_date, is_paid, amount 
        FROM orders 
        WHERE user_email = ?
        ORDER BY order_date DESC
        """,
        (user['email'],)
    )
    my_orders = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return render_template(
        "my_orders.html",
        user=user,
        full_name=user.get("full_name", ""),
        my_orders=my_orders
    )

@app.route('/submit_order/<int:item_id>', methods=['POST'])
def submit_order(item_id):
    user = get_user()
    if not user:
        flash("Login required to submit an order", "error")
        return redirect(url_for("login_user"))

    # Get form data
    name = request.form.get('name')
    contact = request.form.get('contact')
    email = request.form.get('email')
    address1 = request.form.get('address1')
    address2 = request.form.get('address2')
    city = request.form.get('city')
    pincode = request.form.get('pincode')
    quantity = request.form.get('quantity')
    amount = request.form.get('amount')

    # Validate required fields
    if not quantity or not amount:
        flash("Quantity and amount are required.", "error")
        return redirect(request.referrer or url_for('home'))

    conn = get_product_db()
    item = conn.execute("SELECT id, name FROM product WHERE id = ?", (item_id,)).fetchone()
    if not item:
        flash("Item not found.", "error")
        conn.close()
        return redirect(url_for("home"))

    order_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    user_id = user.get('id', None)

    conn.execute("""
        INSERT INTO orders 
        (item_name, quantity, amount, status, address1, address2, city, pincode, order_date, user_id, user_name, user_contact, user_email) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item['name'], 
        int(quantity), 
        float(amount), 
        'pending', 
        address1, 
        address2, 
        city, 
        pincode, 
        order_date, 
        user_id,
        name,
        contact,
        email
    ))
    conn.commit()
    conn.close()

    flash('Order submitted successfully!', 'success')
    return redirect(url_for('my_orders'))

@app.route("/orders")
def orders():
    user = get_user()
    if not user:
        flash("Please log in to view orders.", "error")
        return redirect(url_for("login_user"))  # or your login page

    status_filter = request.args.get("status")
    date_filter = request.args.get("date")

    conn = get_product_db()
    query = "SELECT * FROM orders WHERE 1=1"
    params = []

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)

    if date_filter:
        query += " AND DATE(order_date) = ?"
        params.append(date_filter)

    query += " ORDER BY order_date DESC"
    cursor = conn.execute(query, params)

    orders = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return render_template("orders.html",
        user=user,
        full_name=user.get("full_name", ""),
        orders=orders,
        selected_status=status_filter or "",
        selected_date=date_filter or ""
    )

@app.route('/accept_order/<int:order_id>', methods=['POST'])
def accept_order(order_id):
    user = get_user()
    if not user or user.get('role') not in ('admin', 'owner'):
        flash("Unauthorized", "error")
        return redirect(url_for('home'))

    conn = get_product_db()
    conn.execute("UPDATE orders SET status = 'accepted' WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()

    flash("Order accepted.", "success")
    return redirect(url_for('orders'))

@app.route('/cancel_order/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    user = get_user()
    if not user:
        flash("Unauthorized", "error")
        return redirect(url_for("login_user"))

    conn = get_product_db()
    order = conn.execute("SELECT user_email FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        flash("Order not found.", "error")
        conn.close()
        return redirect(url_for('home'))

    # Allow if user is owner of the order or role is admin or owner
    if user['email'] != order['user_email'] and user.get('role') not in ('admin', 'owner'):
        flash("Unauthorized to cancel this order.", "error")
        conn.close()
        return redirect(url_for('home'))

    conn.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()

    flash("Order cancelled.", "success")
    # Redirect admins/owners to all orders, others to their orders
    return redirect(url_for('orders') if user.get('role') in ('admin', 'owner') else url_for('my_orders'))

@app.route('/deliver_order/<int:order_id>', methods=['POST'])
def deliver_order(order_id):
    user = get_user()
    if not user or user.get('role') not in ('admin', 'owner'):
        flash("Unauthorized access.", "error")
        return redirect(url_for("home"))

    conn = get_product_db()
    order = conn.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()

    if not order:
        flash("Order not found.", "error")
        conn.close()
        return redirect(url_for("orders"))

    if order['status'] == 'accepted':
        conn.execute("UPDATE orders SET status = 'delivered' WHERE id = ?", (order_id,))
        conn.commit()
        flash("Order marked as delivered.", "success")
    else:
        flash("Only accepted orders can be marked as delivered.", "error")

    conn.close()
    return redirect(url_for("orders"))

@app.route('/mark_paid/<int:order_id>', methods=['POST'])
def mark_paid(order_id):
    user = get_user()
    if not user:
        flash("Unauthorized access.", "error")
        return redirect(url_for("login_user"))

    conn = get_product_db()
    order = conn.execute("SELECT id, user_email FROM orders WHERE id = ?", (order_id,)).fetchone()

    if not order:
        flash("Order not found.", "error")
        conn.close()
        return redirect(url_for("home"))

    # Allow if user role is admin or owner, or user is the order owner
    if user.get('role') not in ('admin', 'owner') and user['email'] != order['user_email']:
        flash("Unauthorized access.", "error")
        conn.close()
        return redirect(url_for("home"))

    conn.execute("UPDATE orders SET is_paid = 1 WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()

    flash("Order marked as paid.", "success")

    # Redirect admins and owners to all orders, others to their own orders
    if user.get('role') in ('admin', 'owner'):
        return redirect(url_for("orders"))
    else:
        return redirect(url_for("my_orders"))

@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    user = get_user()
    if not user or user.get('role') not in ('admin', 'owner'):
        flash("Unauthorized", "error")
        return redirect(url_for('home'))

    conn = get_product_db()
    conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()

    flash("Order deleted.", "success")
    return redirect(url_for('orders'))

@app.route("/sales")
def sales():
    user = get_user()
    if not user:
        return redirect(url_for("login_user"))

    # ---- Online Orders (your original logic) ----
    conn = get_product_db()
    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    delivered_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE status = 'delivered'").fetchone()[0]
    pending_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'").fetchone()[0]
    total_revenue = conn.execute("SELECT SUM(amount) FROM orders WHERE status = 'delivered'").fetchone()[0] or 0
    orders = conn.execute("SELECT * FROM orders ORDER BY order_date DESC").fetchall()
    conn.close()

    # ---- Offline Bills ----
    import sqlite3
    conn2 = sqlite3.connect("bill.db")
    conn2.row_factory = sqlite3.Row
    cur2 = conn2.cursor()

    offline_bills = cur2.execute("SELECT * FROM bills ORDER BY created_at DESC").fetchall()
    offline_revenue = sum(b["total"] for b in offline_bills if b["total"])

    bills = [{
        "name": b["name"],
        "contact": b["contact"],
        "amount": b["total"],
        "date": b["created_at"]
    } for b in offline_bills]

    conn2.close()

    # ---- Grand Total ----
    grand_revenue = int(total_revenue) + round(offline_revenue or 0, 2)

    return render_template("sales.html",
        user=user,
        full_name=user["full_name"],
        total_orders=total_orders,
        delivered_orders=delivered_orders,
        pending_orders=pending_orders,
        total_revenue=int(total_revenue),
        offline_revenue=round(offline_revenue, 2),
        grand_revenue=round(grand_revenue, 2),
        orders=orders,
        bills=bills
    )

@app.route('/product', methods=['GET', 'POST'])
def product():
    user = get_user()
    if not user:
        return redirect(url_for("login_user"))

    full_name = user.get("full_name", "Guest")

    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        price = request.form['price']
        discount_price = request.form['discount_price']
        images = request.files.getlist('images')

        if not (1 <= len(images) <= 5):
            flash("Upload between 1 to 5 images.", "error")
            return redirect(url_for('product'))

        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
        os.makedirs(upload_folder, exist_ok=True)
        saved_filenames = []

        for img in images:
            if img and allowed_file(img.filename):
                filename = secure_filename(img.filename)
                img_path = os.path.join(upload_folder, filename)
                img.save(img_path)
                saved_filenames.append(filename)

        conn = get_product_db()
        conn.execute(
            "INSERT INTO product (name, description, price, discount_price, images) VALUES (?, ?, ?, ?, ?)",
            (name, description, price, discount_price, json.dumps(saved_filenames))
        )
        conn.commit()
        conn.close()

        flash("product item added successfully!", "success")
        return redirect(url_for('product'))

    # GET: Fetch and prepare product items for display
    conn = get_product_db()
    rows = conn.execute("SELECT * FROM product ORDER BY id DESC").fetchall()
    product_items = []
    for row in rows:
        try:
            images = json.loads(row["images"]) if row["images"] else []
        except Exception:
            images = []

        product_items.append({
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "price": row["price"],
            "discount_price": row["discount_price"],
            "images": images
        })
    conn.close()

    return render_template(
        'product.html',
        user=user,
        full_name=full_name,
        product_items=product_items
    )

@app.route('/edit_product/<int:item_id>', methods=['POST'])
def edit_product(item_id):
    user = get_user()
    if not user or user.get("role") not in ["admin", "owner"]:
        flash("Unauthorized", "error")
        return redirect(url_for("home"))

    conn = get_product_db()

    # Get existing images from DB for this item
    cur = conn.execute("SELECT images FROM product WHERE id = ?", (item_id,))
    row = cur.fetchone()
    old_images = []

    if row and row[0]:
        try:
            old_images = json.loads(row[0])
            if not isinstance(old_images, list):
                old_images = []
        except json.JSONDecodeError:
            raw = row[0]
            if ',' in raw:
                old_images = [img.strip() for img in raw.split(',')]
            else:
                old_images = [raw.strip()]

    name = request.form['name']
    description = request.form['description']
    price = request.form['price']
    discount_price = request.form['discount_price']

    uploaded_files = request.files.getlist('images')
    new_images = []

    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')

    if uploaded_files and any(f.filename for f in uploaded_files):
        # Delete old image files
        for img in old_images:
            try:
                os.remove(os.path.join(upload_folder, img))
            except Exception as e:
                print(f"Error deleting old image {img}: {e}")

        # Save new images
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                new_images.append(filename)

        if len(new_images) > 5:
            flash("You can upload maximum 5 images", "error")
            conn.close()
            return redirect(url_for('product'))
    else:
        # No new images uploaded, keep old ones
        new_images = old_images

    conn.execute("""
        UPDATE product
        SET name = ?, description = ?, price = ?, discount_price = ?, images = ?
        WHERE id = ?
    """, (name, description, price, discount_price, json.dumps(new_images), item_id))

    conn.commit()
    conn.close()

    flash("product item updated successfully.", "success")
    return redirect(url_for('product'))

@app.route('/delete_product/<int:item_id>', methods=['POST'])
def delete_product(item_id):
    user = get_user()
    if not user or user.get("role") not in ["admin", "owner"]:
        flash("Unauthorized action.", "error")
        return redirect(url_for("home"))

    conn = get_product_db()
    cur = conn.cursor()

    images_row = cur.execute("SELECT images FROM product WHERE id = ?", (item_id,)).fetchone()
    if images_row and images_row[0]:
        # images stored as JSON string, safer to load as JSON if possible
        try:
            image_list = json.loads(images_row[0])
        except Exception:
            # fallback if not JSON, assume comma-separated string
            image_list = images_row[0].split(',')

        for img_filename in image_list:
            img_filename = img_filename.strip()
            if img_filename:
                img_path = os.path.join(app.root_path, 'static/uploads', img_filename)
                if os.path.exists(img_path):
                    os.remove(img_path)

    cur.execute("DELETE FROM product WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    flash("product item deleted successfully.", "success")
    return redirect(url_for("product"))

@app.route("/services", methods=["GET", "POST"])
def services():
    user = get_user()
    if not user:
        return redirect(url_for("login_user"))

    conn = get_services_db()

    if request.method == "POST":
        name = request.form.get("name")
        price = request.form.get("price")
        discount_price = request.form.get("discount_price")
        description = request.form.get("description")

        conn.execute(
            "INSERT INTO services (name, price, discount_price, description) VALUES (?, ?, ?, ?)",
            (name, price, discount_price, description)
        )
        conn.commit()

    services = conn.execute("SELECT * FROM services ORDER BY id DESC").fetchall()
    conn.close()

    return render_template("services.html", user=user, full_name=user["full_name"], services=services)

@app.route('/edit_service/<int:service_id>', methods=['POST'])
def edit_service(service_id):
    user = get_user()
    if not user or user.get("role") not in ["admin", "owner"]:
        flash("Unauthorized", "error")
        return redirect(url_for("services"))

    name = request.form.get("name")
    price = request.form.get("price")
    discount_price = request.form.get("discount_price")
    description = request.form.get("description")

    conn = get_services_db()
    conn.execute(
        "UPDATE services SET name = ?, price = ?, discount_price = ?, description = ? WHERE id = ?",
        (name, price, discount_price, description, service_id)
    )
    conn.commit()
    conn.close()

    flash("Service updated successfully.", "success")
    return redirect(url_for("services"))

@app.route('/delete_service/<int:service_id>', methods=['POST'])
def delete_service(service_id):
    user = get_user()
    if not user or user.get("role") not in ["admin", "owner"]:
        flash("Unauthorized", "error")
        return redirect(url_for("services"))

    conn = get_services_db()
    conn.execute("DELETE FROM services WHERE id = ?", (service_id,))
    conn.commit()
    conn.close()

    flash("Service deleted successfully.", "success")
    return redirect(url_for("services"))

@app.route("/inbox")
def inbox():
    user = get_user()
    if not user:
        return redirect(url_for("login_admin"))

    conn = get_product_db()

    if user['role'] in ('admin', 'owner'):
        # Get distinct user emails they've messaged or received messages from
        users_sent = conn.execute(
            "SELECT DISTINCT receiver_email FROM messages WHERE sender_email = ?", (user['email'],)
        ).fetchall()
        users_received = conn.execute(
            "SELECT DISTINCT sender_email FROM messages WHERE receiver_email = ?", (user['email'],)
        ).fetchall()

        user_emails = set(row['receiver_email'] for row in users_sent) | set(row['sender_email'] for row in users_received)
        user_emails.discard(user['email'])

        user_info_list = []
        user_db = sqlite3.connect(DATABASE)
        user_db.row_factory = sqlite3.Row

        for email in user_emails:
            user_info = user_db.execute(
                "SELECT full_name FROM users WHERE email = ?", (email,)
            ).fetchone()
            if user_info:
                user_info_list.append({
                    "name": user_info['full_name'],
                    "email": email
                })

        user_db.close()
        conn.close()
        return render_template("inbox.html", user=user, full_name=user.get("full_name"), user_list=user_info_list)

    else:
        # Regular users: no chat, no messages, just simple info page
        conn.close()
        flash("Chat system is disabled for regular users.", "info")
        return render_template("empty_inbox.html", user=user, full_name=user.get("full_name"))

from flask import render_template

@app.route("/bill", methods=["GET", "POST"])
def bill():
    user = get_user()
    if not user:
        return redirect(url_for("login_admin"))

    # Load product dropdown
    conn1 = sqlite3.connect("product.db")
    conn1.row_factory = sqlite3.Row
    products = conn1.execute("SELECT name, price, discount_price FROM product").fetchall()
    conn1.close()

    # Load service dropdown
    conn2 = sqlite3.connect("services.db")
    conn2.row_factory = sqlite3.Row
    services = conn2.execute("SELECT name, price, discount_price FROM services").fetchall()
    conn2.close()

    if request.method == "POST":
        data = request.form
        cust_name = data.get("name")
        contact = data.get("contact")
        address1 = data.get("address1")
        address2 = data.get("address2")
        city = data.get("city")
        pincode = data.get("pincode")

        conn = sqlite3.connect("bill.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cur.execute("""
            INSERT INTO bills (name, contact, address1, address2, city, pincode, total, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (cust_name, contact, address1, address2, city, pincode, 0, created_at))
        bill_id = cur.lastrowid

        items = []
        for key in data:
            if key.startswith("product_name_"):
                idx = key.split("_")[-1]
                item_name = data.get(key)
                qty = int(data.get(f"product_qty_{idx}") or 1)
                if item_name:
                    items.append(("product", item_name, qty))
            if key.startswith("service_name_"):
                idx = key.split("_")[-1]
                item_name = data.get(key)
                qty = int(data.get(f"service_qty_{idx}") or 1)
                if item_name:
                    items.append(("service", item_name, qty))

        total = 0
        for item_type, item_name, qty in items:
            db_file = "product.db" if item_type == "product" else "services.db"
            table = "product" if item_type == "product" else "services"

            lookup_conn = sqlite3.connect(db_file)
            lookup_conn.row_factory = sqlite3.Row
            row = lookup_conn.execute(f"SELECT price, discount_price FROM {table} WHERE name = ?", (item_name,)).fetchone()
            lookup_conn.close()

            if row:
                price = float(row["discount_price"] or row["price"] or 0)
                total += price * qty
                cur.execute("""
                    INSERT INTO bill_items (bill_id, item_type, item_name, quantity, price)
                    VALUES (?, ?, ?, ?, ?)
                """, (bill_id, item_type, item_name, qty, price))

        cur.execute("UPDATE bills SET total = ? WHERE id = ?", (round(total, 2), bill_id))
        conn.commit()
        conn.close()

        return redirect(url_for("bill"))

    # Show all bills
    conn3 = sqlite3.connect("bill.db")
    conn3.row_factory = sqlite3.Row
    cur3 = conn3.cursor()

    bills_raw = cur3.execute("SELECT * FROM bills ORDER BY created_at DESC").fetchall()
    bills = []

    for b in bills_raw:
        items = cur3.execute("SELECT * FROM bill_items WHERE bill_id = ?", (b["id"],)).fetchall()
        item_summary = ", ".join([f"{i['item_name']} x{i['quantity']}" for i in items])
        bills.append({
            "id": b["id"],
            "name": b["name"],
            "contact": b["contact"],
            "address": f"{b['address1']} {b['address2']}, {b['city']} - {b['pincode']}",
            "total": b["total"],
            "date": b["created_at"],
            "items": item_summary
        })

    conn3.close()

    return render_template("bill.html",
        user=user,
        full_name=user.get("full_name", "Yash Cyber Cafe"),
        products=products,
        services=services,
        bills=bills
    )

@app.route("/bill/delete/<int:bill_id>", methods=["POST"])
def delete_bill(bill_id):
    conn = sqlite3.connect("bill.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM bill_items WHERE bill_id = ?", (bill_id,))
    cur.execute("DELETE FROM bills WHERE id = ?", (bill_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("bill"))

@app.route("/bill/print/<int:bill_id>")
def print_bill(bill_id):
    user = get_user()
    if not user:
        return redirect(url_for("login_user"))

    import sqlite3

    conn = sqlite3.connect("bill.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get main bill
    cur.execute("SELECT * FROM bills WHERE id = ?", (bill_id,))
    bill = cur.fetchone()

    # Get bill items
    items_raw = cur.execute("SELECT * FROM bill_items WHERE bill_id = ?", (bill_id,)).fetchall()
    conn.close()

    final_items = []
    for item in items_raw:
        item_name = item["item_name"]
        item_type = item["item_type"]
        quantity = int(item["quantity"])

        # Connect to the appropriate DB
        if item_type == "product":
            db = sqlite3.connect("product.db")
            table = "product"
        else:
            db = sqlite3.connect("services.db")
            table = "services"

        db.row_factory = sqlite3.Row
        cur = db.cursor()
        cur.execute(f"SELECT price, discount_price FROM {table} WHERE name = ?", (item_name,))
        row = cur.fetchone()
        db.close()

        # Convert prices safely
        try:
            price = float(row["price"]) if row and row["price"] else 0.0
        except:
            price = 0.0

        try:
            discount_price = float(row["discount_price"]) if row and row["discount_price"] else price
        except:
            discount_price = price

        final_items.append({
            "item_type": item_type,
            "item_name": item_name,
            "quantity": quantity,
            "price": price,
            "discount_price": discount_price,
            "total": round(discount_price * quantity, 2)
        })

    return render_template("print_receipt.html", bill=bill, items=final_items, user=user)

@app.route('/contact', methods=["GET", "POST"])
def contact():
    user = get_user()
    if not user:
        return redirect(url_for("login_user"))

    if request.method == "POST":
        # You can either disable sending completely:
        flash("Messaging system is disabled.", "info")
        # Or handle other contact logic (like sending email) if you want here.

    return render_template("contact.html", full_name=user["full_name"], user=user)

@app.route("/settings")
def settings():
    user = get_user()
    if not user:
        return redirect(url_for("login_user"))

    conn = sqlite3.connect("security.db")
    conn.row_factory = sqlite3.Row
    questions = conn.execute("SELECT * FROM security_questions").fetchall()
    conn.close()

    return render_template("settings.html", user=user, full_name=user.get("full_name"), questions=questions)

@app.route("/delete-account", methods=["POST"])
def delete_account():
    user = get_user()
    if not user:
        return redirect(url_for("login_user"))

    email = user["email"]
    role = user.get("role", "")

    # Block deletion differently for admin and owner
    if role == "admin":
        return redirect(url_for("settings", admin_delete_blocked=1))
    elif role == "owner":
        return redirect(url_for("settings", owner_delete_blocked=1))

    conn = sqlite3.connect("users.db")
    conn.execute("DELETE FROM users WHERE email = ?", (email,))
    conn.commit()
    conn.close()

    session.pop("user", None)
    flash("Your account has been deleted.", "success")
    return redirect(url_for("register"))

@app.route("/account", methods=["GET", "POST"])
def account():
    user = get_user()
    if not user:
        flash("Please log in to access your account.", "error")
        return redirect(url_for("login_user"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        gender_id = request.form.get("gender_id", 1)

        conn = sqlite3.connect("users.db")
        cur = conn.cursor()

        # Handle image removal
        if 'remove_image' in request.form:
            cur.execute("UPDATE users SET profile_image = NULL WHERE id = ?", (user["id"],))

        # Handle image upload
        image = request.files.get("image")
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cur.execute("UPDATE users SET profile_image = ? WHERE id = ?", (filename, user["id"]))

        # Update full name and gender
        cur.execute("UPDATE users SET full_name = ?, gender_id = ? WHERE id = ?", 
                    (full_name, gender_id, user["id"]))
        conn.commit()
        conn.close()

        flash("Account updated successfully.", "success")
        return redirect(url_for("account"))

    # Load security questions for display
    conn = sqlite3.connect("security.db")
    questions = conn.execute("SELECT * FROM questions").fetchall()
    conn.close()

    return render_template("account.html", user=user, questions=questions)

@app.route("/change-password", methods=["POST"])
def change_password():
    user = get_user()
    if not user:
        return redirect(url_for("account"))

    old_pw = request.form.get("old_password")
    new_pw = request.form.get("new_password")
    confirm_pw = request.form.get("confirm_password")

    if new_pw != confirm_pw:
        flash("New password and confirmation do not match.", "error")
        return redirect(url_for("account"))

    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    row = cur.execute("SELECT password, temp_password, temp_password_uses FROM users WHERE email = ?", (user["email"],)).fetchone()

    if not row:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("account"))

    db_password = row["password"]
    temp_password = row["temp_password"]
    temp_uses = row["temp_password_uses"] or 0

    # Check if old_pw matches real OR valid temp password
    is_real = check_password_hash(db_password, old_pw)
    is_temp = temp_password == old_pw and temp_uses < 2

    if is_real or is_temp:
        cur.execute("""
            UPDATE users 
            SET password = ?, temp_password = NULL, temp_password_uses = 0 
            WHERE email = ?
        """, (generate_password_hash(new_pw), user["email"]))
        conn.commit()
        flash("Password updated successfully.", "success")
    else:
        flash("Current password is incorrect.", "error")

    conn.close()
    return redirect(url_for("account"))

@app.route("/change-info", methods=["POST"])
def change_info():
    user = get_user()
    if not user:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("account"))

    email = request.form.get("email", "").strip()
    contact = request.form.get("contact", "").strip()

    if not email and not contact:
        flash("Please provide at least one field to update.", "error")
        return redirect(url_for("account"))

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()

    # ✅ If email is changed, require OTP
    if email and email != user["email"]:
        if not session.get("otp_verified"):
            flash("Please verify OTP before changing your email.", "error")
            conn.close()
            return redirect(url_for("account"))
        cur.execute("UPDATE users SET email = ? WHERE id = ?", (email, user["id"]))
        session["user"]["email"] = email  # Update session email
        # Clear OTP session after success
        session.pop("otp_verified", None)
        session.pop("register_otp", None)
        session.pop("otp_expiry", None)

    if contact and contact != user["contact"]:
        cur.execute("UPDATE users SET contact = ? WHERE id = ?", (contact, user["id"]))
        session["user"]["contact"] = contact

    conn.commit()
    conn.close()

    flash("Information updated successfully.", "success")
    return redirect(url_for("account"))

@app.route("/set-security", methods=["POST"])
def set_security():
    user_id = session.get("user_id")
    if not user_id:
        user = session.get("user")
        if not user:
            flash("Session expired. Please login again.", "error")
            return redirect(url_for("account"))

        # Get user id from DB if not in session
        conn = sqlite3.connect("users.db")
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT id FROM users WHERE email = ?", (user["email"],)).fetchone()
        conn.close()

        if not row:
            flash("User not found.", "error")
            return redirect(url_for("account"))

        user_id = row["id"]
        session["user_id"] = user_id  # Save it for next time

    question = request.form.get("question")
    answer = request.form.get("answer")

    if not question or not answer:
        flash("Please select a question and provide an answer.", "error")
        return redirect(url_for("account"))

    conn = sqlite3.connect("users.db")
    conn.execute("""
        UPDATE users 
        SET security_question = ?, security_answer = ? 
        WHERE id = ?
    """, (question, answer, user_id))
    conn.commit()
    conn.close()

    flash("Security question and answer updated successfully.", "success")
    return redirect(url_for("account"))

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    if not email or not password:
        flash("Email and password are required.", "login_error")
        return redirect(url_for("login_user"))

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if not user:
        conn.close()
        flash("Invalid email or password", "login_error")
        return redirect(url_for("login_user"))

    # Check real password (hashed)
    is_correct_password = check_password_hash(user["password"], password)

    # Check temp password (plain + max 2 uses)
    temp_pass = user["temp_password"]
    usage = user["temp_password_uses"] if "temp_password_uses" in user.keys() else 0
    is_temp_password = temp_pass == password and usage < 2

    if not is_correct_password and not is_temp_password:
        conn.close()
        flash("Invalid email or password", "login_error")
        return redirect(url_for("login_user"))

    # Prevent admin/owner login from here
    db_role = user["role"] if "role" in user.keys() else "user"
    if db_role in ("admin", "owner"):
        conn.close()
        flash("Please login from admin panel.", "login_error")
        return redirect(url_for("login_user"))

    # If temp password is used, increment usage or clear if limit reached
    if is_temp_password:
        usage += 1
        if usage >= 2:
            conn.execute("UPDATE users SET temp_password = NULL, temp_password_uses = 0 WHERE id = ?", (user["id"],))
        else:
            conn.execute("UPDATE users SET temp_password_uses = ? WHERE id = ?", (usage, user["id"]))
        conn.commit()

    conn.close()

    # Set session
    session["user_id"] = user["id"]
    session["user"] = {
        "email": user["email"],
        "role": db_role,
        "name": user["full_name"]
    }
    # Redirect logic
    if is_temp_password:
        flash("🔐 Temporary password used. Please change your password now.", "login_info")
        return redirect(url_for("account", show_change_password="true"))

    return redirect(url_for("home"))

@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    temp_password = None

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        contact = request.form.get("contact", "").strip()
        question = request.form.get("question", "").strip()
        answer = request.form.get("answer", "").strip()

        if not (email or contact):
            flash("Please fill at least Email or Mobile Number.", "error")
        elif not question or not answer:
            flash("Security question and answer are required.", "error")
        else:
            conn = sqlite3.connect("users.db")
            conn.row_factory = sqlite3.Row

            user = conn.execute("""
                SELECT * FROM users
                WHERE (email = ? OR contact = ?) AND security_question = ? AND security_answer = ?
            """, (email, contact, question, answer)).fetchone()

            if user:
                # Example temp password logic
                temp_password = "Temp@123"  # or generate randomly
                conn.execute("UPDATE users SET temp_password = ? WHERE id = ?", (temp_password, user["id"]))
                conn.commit()
                flash("Temporary password generated. It can be used only 2 times. Please change your password after login.", "success")
            else:
                flash("User not found or incorrect security answer.", "error")

            conn.close()

    # Fetch questions from security.db
    conn2 = sqlite3.connect("security.db")
    questions = conn2.execute("SELECT * FROM questions").fetchall()
    conn2.close()

    return render_template("forgot.html", questions=questions, temp_password=temp_password)

@app.route("/recover_otp", methods=["POST"])
def recover_otp():
    email = request.form.get("otp_email", "").strip().lower()
    otp = request.form.get("otp_code", "").strip()
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not email or not otp or not new_password or not confirm_password:
        flash("All fields are required.", "error")
        return redirect(url_for("forgot"))

    if new_password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for("forgot"))

    # OTP validation (assuming stored in session)
    stored_otp = session.get("register_otp")
    expiry = session.get("otp_expiry", 0)

    if not stored_otp or otp != stored_otp:
        flash("Invalid OTP.", "error")
        return redirect(url_for("forgot"))

    if time.time() > expiry:
        flash("OTP has expired. Please request a new one.", "error")
        return redirect(url_for("forgot"))

    conn = sqlite3.connect(DATABASE)
    hashed_pw = generate_password_hash(new_password)
    try:
        conn.execute("UPDATE users SET password = ? WHERE email = ?", (hashed_pw, email))
        conn.commit()
        flash("✅ Password reset successful. Please login.", "success")
    except Exception as e:
        print("Error resetting password:", e)
        flash("Something went wrong.", "error")
    finally:
        conn.close()

    return redirect(url_for("login_user"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        contact = request.form.get("contact", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        otp = request.form.get("otp", "").strip()

        # Validate required fields
        if not full_name or not contact or not email or not password or not confirm_password:
            flash("All fields are required.", "register_error")
            return redirect(url_for("login_user"))

        if password != confirm_password:
            flash("Passwords do not match.", "register_error")
            return redirect(url_for("login_user"))

        hashed_pw = generate_password_hash(password)

        try:
            conn = sqlite3.connect(DATABASE)
            conn.execute(
                "INSERT INTO users (full_name, contact, email, password, role) VALUES (?, ?, ?, ?, ?)",
                (full_name, contact, email, hashed_pw, 'user')
            )
            conn.commit()

            # ✅ Send welcome email after successful registration
            send_user_welcome_email(email, full_name)

            flash("Registration successful. Please login.", "register_success")

        except sqlite3.IntegrityError:
            flash("Email already registered.", "register_error")
        except Exception as e:
            flash("Something went wrong. Please try again.", "register_error")
            print("Registration error:", str(e))
        finally:
            conn.close()

        return redirect(url_for("login_user"))

    return redirect(url_for("login_user"))

@app.route("/send-otp", methods=["POST"])
def send_otp():
    email = request.json.get("email")
    if not email:
        return jsonify(success=False, message="Email is required.")

    now = time.time()
    expiry = session.get("otp_expiry", 0)

    if expiry and now < expiry:
        remaining = int((expiry - now) // 60)
        return jsonify(success=False, message=f"OTP already sent. Try again after {remaining} min.")

    otp = generate_random_otp()
    session["register_otp"] = otp
    session["register_email"] = email
    session["otp_expiry"] = now + 300  # 5 mins
    session["otp_verified"] = False

    if send_otp_to_email(email, otp):
        return jsonify(success=True)
    return jsonify(success=False, message="Failed to send OTP.")

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    user_otp = request.json.get("otp", "").strip()
    actual_otp = session.get("register_otp", "").strip()
    expiry = session.get("otp_expiry", 0)

    if datetime.now().timestamp() > expiry:
        return jsonify(verified=False, message="OTP expired. Please request a new one.")

    if user_otp == actual_otp:
        session["otp_verified"] = True
        return jsonify(verified=True)

    return jsonify(verified=False, message="Incorrect OTP.")

@app.route('/create_admin', methods=['GET', 'POST'])
def create_admin():
    user = get_user()
    if not user or user.get('role') not in ['admin', 'owner']:
        flash("Unauthorized access.", "error")
        return redirect(url_for('login_user'))

    conn = get_user_db()

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        contact = request.form.get('contact')

        if not full_name or not email or not contact:
            flash("All fields are required.", "error")
            conn.close()
            return redirect(url_for('create_admin'))

        existing_user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if existing_user:
            flash("Email already exists.", "error")
            conn.close()
            return redirect(url_for('create_admin'))

        default_password = '1234'
        password_hash = generate_password_hash(default_password)

        try:
            conn.execute(
                "INSERT INTO users (full_name, email, contact, password, role) VALUES (?, ?, ?, ?, ?)",
                (full_name, email, contact, password_hash, 'admin')
            )
            conn.commit()

            # Send welcome email with plain password used
            subject = "Your Admin Account Credentials"
            body = f"""Hi {full_name},

Your admin account has been created successfully.

📧 Email: {email}
🔐 Default Password: {default_password}

Please log in and change your password immediately from your account settings.

Best regards,  
Yash Cyber Cafe Team
"""
            message = f"Subject: {subject}\n\n{body}"

            import smtplib, ssl
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.sendmail(EMAIL_ADDRESS, email, message)

            flash("Admin user created and email sent with default credentials.", "success")
        except Exception as e:
            print("Admin creation or email error:", e)
            flash("Admin created, but email sending failed.", "error")

    admins = conn.execute("SELECT id, full_name as name, email, contact FROM users WHERE role = 'admin'").fetchall()
    conn.close()

    return render_template('create_admin.html', user=user, admins=admins)

@app.route('/delete_admin/<int:admin_id>', methods=['POST'])
def delete_admin(admin_id):
    user = get_user()
    if not user or user.get('role') not in ['admin', 'owner']:
        flash("Unauthorized access.", "error")
        return redirect(url_for('login_user'))

    conn = get_user_db()
    conn.execute("DELETE FROM users WHERE id = ? AND role = 'admin'", (admin_id,))
    conn.commit()
    conn.close()

    flash("Admin deleted successfully.", "success")
    return redirect(url_for('create_admin'))

@app.route("/login_admin", methods=["GET", "POST"])
def login_admin():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Email and password are required.", "error")
            return redirect(url_for("login_admin"))

        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        user = conn.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email,)).fetchone()
        conn.close()

        if not user or not user["password"]:
            flash("Invalid email or password", "error")
            return redirect(url_for("login_admin"))

        if not check_password_hash(user["password"], password):
            flash("Invalid email or password", "error")
            return redirect(url_for("login_admin"))

        db_role = user["role"] if "role" in user.keys() else "user"
        if db_role not in ("admin", "owner"):
            flash("You are not authorized to log in as Admin/Owner.", "error")
            return redirect(url_for("login_admin"))

        session["user_id"] = user["id"]
        session["user"] = {
    "email": user["email"],
    "role": db_role,
    "name": user["full_name"]
        }

        return redirect(url_for("home"))

    return render_template("login_admin.html")

@app.route("/logout")
def logout():
    user = session.get("user")
    role = user.get("role") if user else None  

    session.pop("user", None)

    if role in ("admin", "owner"):
        return redirect(url_for("login_admin"))
    else:
        return redirect(url_for("login_user"))

if __name__ == "__main__":
    app.run(debug=True)
