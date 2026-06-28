import os
import datetime
import razorpay
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import get_db_connection, init_db

app = Flask(__name__)
app.secret_key = 'super-secret-ca-portal-key-change-in-prod'
app.permanent_session_lifetime = datetime.timedelta(days=30)

# Configure Razorpay Keys (Default Test Keys - Replace with your live keys from Razorpay dashboard)
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', 'rzp_test_1234567890')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', 'sample_secret_key_123')
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Configure upload directory
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize DB on app startup
init_db()

def create_notification(user_id, message):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO notifications (user_id, message) VALUES (?, ?)", (user_id, message))
        conn.commit()
        conn.close()
    except Exception as e:
        print("Notification error:", e)

@app.context_processor
def inject_notifications():
    if 'user_id' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 5", (session['user_id'],))
        user_notifications = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0", (session['user_id'],))
        unread_count = cursor.fetchone()[0]

        cursor.execute("SELECT pan_number, gstin_number FROM users WHERE id = ?", (session['user_id'],))
        current_user_info = cursor.fetchone()
        conn.close()
        return dict(user_notifications=user_notifications, unread_count=unread_count, current_user_info=current_user_info, razorpay_key_id=RAZORPAY_KEY_ID)
    return dict(user_notifications=[], unread_count=0, current_user_info=None, razorpay_key_id=RAZORPAY_KEY_ID)

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'customer')
        phone = request.form.get('phone', '').strip()
        specialization = request.form.get('specialization', '').strip() if role == 'ca' else None
        pan_number = request.form.get('pan_number', '').strip().upper()
        gstin_number = request.form.get('gstin_number', '').strip().upper()

        if not name or not email or not password:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('register'))

        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            flash('Email address is already registered. Please login.', 'danger')
            return redirect(url_for('register'))

        password_hash = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role, phone, specialization, pan_number, gstin_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, email, password_hash, role, phone, specialization, pan_number, gstin_number))
        conn.commit()
        conn.close()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session.permanent = True
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/profile/update_tax_info', methods=['POST'])
def update_tax_info():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    pan_number = request.form.get('pan_number', '').strip().upper()
    gstin_number = request.form.get('gstin_number', '').strip().upper()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET pan_number = ?, gstin_number = ? WHERE id = ?", (pan_number, gstin_number, session['user_id']))
    conn.commit()
    conn.close()

    flash('Tax ID Profile (PAN & GSTIN) updated successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if session['user_role'] == 'customer':
        cursor.execute("SELECT id, name, email, phone, specialization FROM users WHERE role = 'ca'")
        cas = cursor.fetchall()

        cursor.execute("""
            SELECT a.*, u.name as ca_name, u.email as ca_email
            FROM appointments a
            JOIN users u ON a.ca_id = u.id
            WHERE a.customer_id = ?
            ORDER BY a.created_at DESC
        """, (session['user_id'],))
        appointments = [dict(row) for row in cursor.fetchall()]

        for appt in appointments:
            cursor.execute("SELECT * FROM appointment_documents WHERE appointment_id = ?", (appt['id'],))
            appt['documents'] = cursor.fetchall()
            cursor.execute("SELECT * FROM appointment_notes WHERE appointment_id = ? ORDER BY created_at ASC", (appt['id'],))
            appt['notes'] = cursor.fetchall()

        conn.close()
        return render_template('customer_dashboard.html', cas=cas, appointments=appointments)

    elif session['user_role'] == 'ca':
        cursor.execute("""
            SELECT a.*, u.name as customer_name, u.email as customer_email, u.phone as customer_phone, u.pan_number as customer_pan, u.gstin_number as customer_gstin
            FROM appointments a
            JOIN users u ON a.customer_id = u.id
            WHERE a.ca_id = ?
            ORDER BY a.created_at DESC
        """, (session['user_id'],))
        appointments = [dict(row) for row in cursor.fetchall()]

        for appt in appointments:
            cursor.execute("SELECT * FROM appointment_documents WHERE appointment_id = ?", (appt['id'],))
            appt['documents'] = cursor.fetchall()
            cursor.execute("SELECT * FROM appointment_notes WHERE appointment_id = ? ORDER BY created_at ASC", (appt['id'],))
            appt['notes'] = cursor.fetchall()

        conn.close()
        return render_template('ca_dashboard.html', appointments=appointments)

    conn.close()
    return redirect(url_for('login'))

@app.route('/customer/book', methods=['POST'])
def book_appointment():
    if 'user_id' not in session or session.get('user_role') != 'customer':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))

    ca_id = request.form.get('ca_id')
    service_type = request.form.get('service_type')
    appointment_date = request.form.get('appointment_date')
    appointment_time = request.form.get('appointment_time')
    work_details = request.form.get('work_details')

    if not all([ca_id, service_type, appointment_date, appointment_time, work_details]):
        flash('All fields are required to book an appointment.', 'danger')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO appointments (customer_id, ca_id, service_type, work_details, appointment_date, appointment_time, status)
        VALUES (?, ?, ?, ?, ?, ?, 'Pending')
    """, (session['user_id'], ca_id, service_type, work_details, appointment_date, appointment_time))
    appt_id = cursor.lastrowid
    conn.commit()

    create_notification(ca_id, f"📥 New consultation request from {session['user_name']} for {service_type}.")

    if 'document' in request.files:
        file = request.files['document']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            saved_filename = f"appt_{appt_id}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
            file.save(filepath)

            cursor.execute("""
                INSERT INTO appointment_documents (appointment_id, filename, filepath, uploaded_by)
                VALUES (?, ?, ?, ?)
            """, (appt_id, filename, saved_filename, session['user_id']))
            conn.commit()

    conn.close()
    flash('Appointment request submitted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/appointment/<int:appointment_id>/upload', methods=['POST'])
def upload_document(appointment_id):
    if 'user_id' not in session:
        flash('Please log in.', 'danger')
        return redirect(url_for('login'))

    if 'document' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('dashboard'))

    file = request.files['document']
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        saved_filename = f"appt_{appointment_id}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
        file.save(filepath)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO appointment_documents (appointment_id, filename, filepath, uploaded_by)
            VALUES (?, ?, ?, ?)
        """, (appointment_id, filename, saved_filename, session['user_id']))
        conn.commit()

        cursor.execute("SELECT customer_id, ca_id FROM appointments WHERE id = ?", (appointment_id,))
        appt = cursor.fetchone()
        if appt:
            target_user = appt['ca_id'] if session['user_id'] == appt['customer_id'] else appt['customer_id']
            create_notification(target_user, f"📎 New document '{filename}' uploaded for appointment #{appointment_id}.")

        conn.close()
        flash('Document uploaded successfully!', 'success')

    return redirect(url_for('dashboard'))

@app.route('/document/<int:doc_id>/approve', methods=['POST'])
def approve_document(doc_id):
    if 'user_id' not in session or session.get('user_role') != 'customer':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.id, a.ca_id, d.filename 
        FROM appointment_documents d
        JOIN appointments a ON d.appointment_id = a.id
        WHERE d.id = ? AND a.customer_id = ?
    """, (doc_id, session['user_id']))
    doc = cursor.fetchone()
    if not doc:
        conn.close()
        return jsonify({'success': False, 'error': 'Document not found'}), 404

    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("UPDATE appointment_documents SET is_approved = 1, approved_at = ? WHERE id = ?", (now_str, doc_id))
    conn.commit()

    create_notification(doc['ca_id'], f"✍️ e-Sign Approved! Client verified document '{doc['filename']}'.")
    conn.close()

    return jsonify({'success': True, 'approved_at': now_str})

@app.route('/download/<int:doc_id>')
def download_document(doc_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appointment_documents WHERE id = ?", (doc_id,))
    doc = cursor.fetchone()
    conn.close()

    if doc:
        return send_from_directory(app.config['UPLOAD_FOLDER'], doc['filepath'], download_name=doc['filename'], as_attachment=True)
    
    flash('File not found.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/appointment/<int:appointment_id>/note', methods=['POST'])
def add_note(appointment_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    data = request.get_json()
    note_text = data.get('note', '').strip()
    if not note_text:
        return jsonify({'success': False, 'error': 'Note text empty'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT customer_id, ca_id FROM appointments WHERE id = ?", (appointment_id,))
    appt = cursor.fetchone()
    if not appt or (session['user_id'] not in [appt['customer_id'], appt['ca_id']]):
        conn.close()
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    cursor.execute("""
        INSERT INTO appointment_notes (appointment_id, sender_id, sender_name, note)
        VALUES (?, ?, ?, ?)
    """, (appointment_id, session['user_id'], session['user_name'], note_text))
    conn.commit()

    target_user = appt['ca_id'] if session['user_id'] == appt['customer_id'] else appt['customer_id']
    create_notification(target_user, f"💬 New note from {session['user_name']} on appointment #{appointment_id}.")

    conn.close()
    return jsonify({'success': True})

@app.route('/ca/appointment/<int:appointment_id>/status', methods=['POST'])
def update_status(appointment_id):
    if 'user_id' not in session or session.get('user_role') != 'ca':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    data = request.get_json()
    new_status = data.get('status')

    if new_status not in ['Confirmed', 'Rejected', 'Completed']:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT customer_id FROM appointments WHERE id = ? AND ca_id = ?", (appointment_id, session['user_id']))
    appt = cursor.fetchone()
    if not appt:
        conn.close()
        return jsonify({'success': False, 'error': 'Appointment not found'}), 404

    cursor.execute("UPDATE appointments SET status = ? WHERE id = ?", (new_status, appointment_id))
    conn.commit()
    conn.close()

    status_emoji = '✅' if new_status == 'Confirmed' else ('🎉' if new_status == 'Completed' else '❌')
    create_notification(appt['customer_id'], f"{status_emoji} Your appointment #{appointment_id} status was updated to '{new_status}'.")

    return jsonify({'success': True})

@app.route('/ca/appointment/<int:appointment_id>/fee', methods=['POST'])
def set_fee(appointment_id):
    if 'user_id' not in session or session.get('user_role') != 'ca':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    data = request.get_json()
    try:
        fee_amount = float(data.get('fee_amount', 0))
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid amount'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT customer_id FROM appointments WHERE id = ? AND ca_id = ?", (appointment_id, session['user_id']))
    appt = cursor.fetchone()
    if not appt:
        conn.close()
        return jsonify({'success': False, 'error': 'Appointment not found'}), 404

    cursor.execute("UPDATE appointments SET fee_amount = ? WHERE id = ?", (fee_amount, appointment_id))
    conn.commit()
    conn.close()

    create_notification(appt['customer_id'], f"💳 Invoice updated! CA set consultation fee to ₹{fee_amount:,.2f} for appointment #{appointment_id}.")

    return jsonify({'success': True})

@app.route('/customer/appointment/<int:appointment_id>/create_razorpay_order', methods=['POST'])
def create_razorpay_order(appointment_id):
    if 'user_id' not in session or session.get('user_role') != 'customer':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ca_id, fee_amount, service_type FROM appointments WHERE id = ? AND customer_id = ?", (appointment_id, session['user_id']))
    appt = cursor.fetchone()
    conn.close()

    if not appt or appt['fee_amount'] <= 0:
        return jsonify({'success': False, 'error': 'Invalid appointment fee'}), 400

    amount_in_paise = int(appt['fee_amount'] * 100)
    try:
        order_data = {
            'amount': amount_in_paise,
            'currency': 'INR',
            'receipt': f'receipt_appt_{appointment_id}',
            'payment_capture': 1
        }
        order = razorpay_client.order.create(data=order_data)
        return jsonify({'success': True, 'order_id': order['id'], 'amount': amount_in_paise, 'service_name': appt['service_type']})
    except Exception as e:
        # Fallback for demo mode if API keys are simulated
        return jsonify({'success': True, 'order_id': f'order_demo_{appointment_id}', 'amount': amount_in_paise, 'service_name': appt['service_type']})

@app.route('/customer/appointment/<int:appointment_id>/pay', methods=['POST'])
def process_payment(appointment_id):
    if 'user_id' not in session or session.get('user_role') != 'customer':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ca_id, fee_amount FROM appointments WHERE id = ? AND customer_id = ?", (appointment_id, session['user_id']))
    appt = cursor.fetchone()
    if not appt:
        conn.close()
        return jsonify({'success': False, 'error': 'Appointment not found'}), 404

    cursor.execute("UPDATE appointments SET payment_status = 'Paid' WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()

    create_notification(appt['ca_id'], f"💰 Payment Received via Razorpay Gateway! Client paid ₹{appt['fee_amount']:,.2f} for appointment #{appointment_id}.")

    return jsonify({'success': True})

@app.route('/api/tax_assistant', methods=['POST'])
def tax_assistant():
    data = request.get_json()
    query = data.get('query', '').lower()

    if 'regime' in query or 'old vs new' in query or 'difference' in query:
        reply = "💡 **Old vs New Tax Regime Guide**:\n- **New Regime**: Lower tax slabs, default regime, standard deduction of ₹75,000 applicable. No 80C deductions.\n- **Old Regime**: Allows deductions up to ₹1.5L under 80C, HRA, Health Insurance (80D), and Home Loan interest. Ideal if you have major investments!"
    elif '80c' in query or 'deduction' in query or 'save tax' in query:
        reply = "🔍 **Section 80C Deductions (Max ₹1,500,000)**:\nKey eligible investments under Old Regime:\n1. PPF & EPF Contributions\n2. ELSS Mutual Funds (3-yr lock-in)\n3. National Savings Certificate (NSC)\n4. Life Insurance Premiums\n5. Children's School Tuition Fees"
    elif 'gst' in query or 'rate' in query or 'return' in query:
        reply = "📊 **GST Compliance Quick Reference**:\n- **GSTR-1**: Monthly/Quarterly Outward Supplies (Due 11th/13th)\n- **GSTR-3B**: Monthly Summary Return & Tax Payment (Due 20th of following month)\n- Standard GST Slabs: 5%, 12%, 18%, 28%."
    elif 'itr' in query or 'deadline' in query or 'last date' in query:
        reply = "📅 **Key Tax Filing Deadlines**:\n- **Non-Audit ITR (Individual/Salaried)**: 31st July\n- **Tax Audit Cases**: 31st October\n- **GSTR-3B Monthly**: 20th of every month"
    else:
        reply = "🤖 **CA Assistant**: Hello! You can ask me about:\n- Old vs New Tax Regime comparison\n- Section 80C tax-saving deductions\n- GST return due dates and slabs\n- Income Tax filing deadlines\nOr book a custom consultation with one of our verified CAs above!"

    return jsonify({'reply': reply})

@app.route('/notifications/mark_read', methods=['POST'])
def mark_notifications_read():
    if 'user_id' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (session['user_id'],))
        conn.commit()
        conn.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
