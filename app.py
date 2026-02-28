from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import joblib
import sqlite3
import hashlib
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from flask import make_response
import io
from flask import flash
import smtplib
from email.mime.text import MIMEText
import re



app = Flask(__name__)
app.secret_key = 'supersecretkey'  # wajib untuk session

# Load model
model = joblib.load('model/model_rekomendasi_smk.pkl')

# Fungsi konversi nilai akademik ke label 1-4
def konversi_nilai(nilai):
    if nilai >= 90:
        return 4
    elif nilai >= 80:
        return 3
    elif nilai >= 70:
        return 2
    else:
        return 1

# Fungsi konversi total skor minat ke label 1-4
def konversi_minat(total):
    if 13 <= total <= 15:
        return 4
    elif 10 <= total <= 12:
        return 3
    elif 8 <= total <= 9:
        return 2
    else:
        return 1

# Koneksi database SQLite
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def is_valid_email(email):
    if not email:
        return False
    
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email)

def send_email(to_email, jurusan, username):

    if not is_valid_email(to_email):
        print("Email tidak valid, skip kirim.")
        return

    try:
        sender_email = "brokenworld044@gmail.com"
        sender_password = "vsaqofbpqskgjmcq"  # pakai app password!

        subject = "Hasil Rekomendasi Jurusan"
        body = f"""
        Halo,

        Hasil rekomendasi jurusan untuk Anda adalah:
        {jurusan}

        Semoga membantu menentukan masa depan Anda 😊
        """

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = to_email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        print("Email berhasil dikirim!")

    except Exception as e:
        print("Gagal kirim email:", e)

def is_admin():
    return 'role' in session and session['role'] == 'admin'

def is_admin_or_kesiswaan():
    return 'role' in session and session['role'] in ['admin', 'kesiswaan']
# Route utama diarahkan ke login
@app.route('/')
def home():
    return redirect(url_for('login'))

# Halaman input nilai akademik
@app.route('/index', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        mat = int(request.form['mat'])
        tik = int(request.form['tik'])
        seni = int(request.form['seni'])
        bindo = int(request.form['bindo'])

        # Simpan nilai asli di session untuk dashboard admin
        session['mat_asli'] = mat
        session['tik_asli'] = tik
        session['seni_asli'] = seni
        session['bindo_asli'] = bindo

        # Simpan nilai konversi untuk prediksi
        session['mat'] = konversi_nilai(mat)
        session['tik'] = konversi_nilai(tik)
        session['seni'] = konversi_nilai(seni)
        session['bindo'] = konversi_nilai(bindo)

        return redirect(url_for('tes_minat'))
    return render_template('index.html')

# Halaman tes minat
@app.route('/tes_minat', methods=['GET', 'POST'])
def tes_minat():
    if request.method == 'POST':

        # Ambil jawaban tes minat
        tkr_score = sum(int(request.form[f'tkr{i}']) for i in range(1, 6))
        tkj_score = sum(int(request.form[f'tkj{i}']) for i in range(1, 6))
        mm_score  = sum(int(request.form[f'mm{i}'])  for i in range(1, 6))
        ap_score  = sum(int(request.form[f'ap{i}'])  for i in range(1, 6))

        # Konversi skor
        tkr_label = konversi_minat(tkr_score)
        tkj_label = konversi_minat(tkj_score)
        mm_label  = konversi_minat(mm_score)
        ap_label  = konversi_minat(ap_score)

        # Nilai akademik
        mat_label = session.get('mat')
        tik_label = session.get('tik')
        seni_label = session.get('seni')
        bindo_label = session.get('bindo')

        score = pd.DataFrame({
            'Score_TKR': [tkr_label + mat_label],
            'Score_TKJ': [tkj_label + tik_label],
            'Score_MM':  [mm_label + seni_label],
            'Score_AP':  [ap_label + bindo_label]
        })

        # Prediksi
        pred = model.predict(score)[0]

        # Nilai asli
        mat_asli = session.get('mat_asli')
        tik_asli = session.get('tik_asli')
        seni_asli = session.get('seni_asli')
        bindo_asli = session.get('bindo_asli')

        user_id = session.get('user_id')
        username = session.get('username')

        conn = get_db_connection()
        cursor = conn.cursor()

        # Simpan request
        cursor.execute('''
            INSERT INTO requests 
            (user_id, username, mat, tik, seni, bindo, hasil)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, mat_asli, tik_asli, seni_asli, bindo_asli, pred))

        conn.commit()
        request_id = cursor.lastrowid

        # 🔥 Ambil email user
        user = cursor.execute(
            "SELECT email FROM users WHERE id=?",
            (user_id,)
        ).fetchone()

        conn.close()

        # 🔥 Kirim email jika valid
        if user and is_valid_email(user['email']):
            send_email(user['email'], pred, username)

        return render_template(
            'hasil.html',
            jurusan=pred,
            request_id=request_id
        )

    return render_template('tes_minat.html')


# Register user
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        hashed = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                         (username, email, hashed, 'user'))
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Username atau email sudah dipakai!")
        finally:
            flash("Registrasi berhasil! Silakan login.")

        return redirect(url_for('login'))

    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_input = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and hashed_input == user['password']:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']

            if user['role'] in ['admin', 'kesiswaan']:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash("Password salah atau user tidak ditemukan!")

    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Halaman dashboard admin
@app.route('/admin/dashboard')
def admin_dashboard():
    if not is_admin_or_kesiswaan():
        return redirect(url_for('login'))

    conn = get_db_connection()

    users = conn.execute("SELECT * FROM users").fetchall()
    requests = conn.execute("SELECT * FROM requests").fetchall()

    # Hitung jumlah per jurusan
    jurusan_data = conn.execute("""
        SELECT hasil, COUNT(*) as jumlah
        FROM requests
        GROUP BY hasil
    """).fetchall()

    conn.close()

    total_users = len(users)
    total_requests = len(requests)

    # Default 0
    tkj = tkr = mm = ap = 0

    for row in jurusan_data:
        if row['hasil'] == 'TKJ':
            tkj = row['jumlah']
        elif row['hasil'] == 'TKR':
            tkr = row['jumlah']
        elif row['hasil'] == 'Multimedia':
            mm = row['jumlah']
        elif row['hasil'] == 'AP':
            ap = row['jumlah']

    return render_template(
        'admin_dashboard.html',
        username=session['username'],
        total_users=total_users,
        total_requests=total_requests,
        tkj=tkj,
        tkr=tkr,
        mm=mm,
        ap=ap
    )


@app.route('/admin/report/pdf')
def download_pdf():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    data = conn.execute("SELECT username, mat, tik, seni, bindo, hasil FROM requests").fetchall()
    conn.close()

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    title = Paragraph("Laporan Hasil Rekomendasi Jurusan", styles['Title'])
    elements.append(title)

    # Header tabel
    table_data = [[
        "Username",
        "Mat",
        "TIK",
        "Seni",
        "B.Indo",
        "Hasil"
    ]]

    # Isi tabel
    for row in data:
        table_data.append([
            row['username'],
            row['mat'],
            row['tik'],
            row['seni'],
            row['bindo'],
            row['hasil']
        ])

    table = Table(table_data)

    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('GRID',(0,0),(-1,-1),1,colors.black),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('PADDING', (0,0), (-1,0), 8),
    ]))

    elements.append(table)
    doc.build(elements)

    buffer.seek(0)

    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=laporan_rekomendasi.pdf'

    return response

# Halaman detail data siswa
@app.route('/admin/users')
def admin_users():
    if not is_admin_or_kesiswaan():
        return redirect(url_for('login'))

    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return render_template('admin_users.html', users=users, username=session['username'])


@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():

    request_id = request.form.get('request_id')
    rating = request.form.get('rating')
    feedback = request.form.get('feedback')

    conn = get_db_connection()
    conn.execute('''
        UPDATE requests
        SET rating=?, feedback=?
        WHERE id=?
    ''', (rating, feedback, request_id))

    conn.commit()
    conn.close()

    flash("✅ Terima kasih! Feedback berhasil dikirim.")
    
    return redirect(url_for('index'))  # atau ke halaman lain

@app.route('/admin/clear_requests', methods=['POST'])
def clear_requests():

    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute("DELETE FROM requests")
    conn.commit()
    conn.close()

    flash("Semua data request berhasil dihapus!")
    return redirect(url_for('admin_requests'))


@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):

    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    if user_id == session.get('user_id'):
        flash("Tidak bisa menghapus akun sendiri!")
        return redirect(url_for('admin_users'))

    conn = get_db_connection()

    # optional: hapus juga request milik user
    conn.execute("DELETE FROM requests WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))

    conn.commit()
    conn.close()

    flash("User berhasil dihapus!")
    return redirect(url_for('admin_users'))

@app.route('/admin/add_user', methods=['POST'])
def add_user():

    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    username = request.form.get('username')
    password = request.form.get('password')
    email = request.form.get('email')
    role = request.form.get('role')

    if not username or not password:
        flash("Username dan password wajib diisi!")
        return redirect(url_for('admin_users'))

    hashed = hashlib.sha256(password.encode()).hexdigest()

    conn = get_db_connection()

    try:
        conn.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
            (username, email, hashed, role)
        )
        conn.commit()
        flash("User berhasil ditambahkan!")
    except sqlite3.IntegrityError:
        flash("Username sudah dipakai!")
    finally:
        conn.close()

    return redirect(url_for('admin_users'))

@app.route('/admin/requests')
def admin_requests():
    if not is_admin_or_kesiswaan():
        return redirect(url_for('login'))

    conn = get_db_connection()
    requests = conn.execute("SELECT * FROM requests").fetchall()
    conn.close()
    return render_template('admin_requests.html', requests=requests, username=session['username'])


if __name__ == '__main__':
    app.run(debug=True)



