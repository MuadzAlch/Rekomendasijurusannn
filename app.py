from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
import pandas as pd
import joblib
import mysql.connector
import hashlib
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import io
import smtplib
from email.mime.text import MIMEText
import re
import threading

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# ================= DATABASE MYSQL =================
def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("mysql.railway.internal"),
        user=os.environ.get("root"),
        password=os.environ.get("AyRpgYvjqhInWuJMcJpvxLJxHtKFzjpW"),
        database=os.environ.get("railway"),
        port=os.environ.get("3306")
    )

# ================= LOAD MODEL =================
model = joblib.load('model/model_rekomendasi_smk.pkl')

def format_tanggal_indo(tanggal):
    bulan = [
        "Januari","Februari","Maret","April","Mei","Juni",
        "Juli","Agustus","September","Oktober","November","Desember"
    ]
    return f"{tanggal.day} {bulan[tanggal.month-1]} {tanggal.year}"
# ================= HELPER =================
def konversi_nilai(nilai):
    if nilai >= 90: return 4
    elif nilai >= 80: return 3
    elif nilai >= 70: return 2
    else: return 1

def konversi_minat(total):
    if 13 <= total <= 15: return 4
    elif 10 <= total <= 12: return 3
    elif 8 <= total <= 9: return 2
    else: return 1

def is_valid_email(email):
    if not email:
        return False
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email)

import smtplib
import io
from email.message import EmailMessage
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors


def send_email(to_email, jurusan, username):

    if not is_valid_email(to_email):
        return

    try:
        sender_email = "brokenworld044@gmail.com"
        sender_password = "vsaqofbpqskgjmcq"

        subject = "Pemberitahuan Hasil Rekomendasi Jurusan"

        # =========================
        # EMAIL HTML
        # =========================

        html_body = f"""
        <html>
        <body style="font-family:Arial;">
        
        <h3>SMKN 8 GARUT</h3>

        <p>Yth. <b>{username}</b>,</p>

        <p>
        Berdasarkan hasil analisis nilai akademik yang telah dilakukan melalui
        <b>Sistem Rekomendasi Jurusan SMKN 8 Garut</b>, maka diperoleh hasil
        rekomendasi jurusan sebagai berikut:
        </p>

        <p style="font-size:18px;">
        <b>{jurusan}</b>
        </p>

        <p>
        Dokumen resmi hasil rekomendasi jurusan dapat dilihat pada
        lampiran PDF yang disertakan dalam email ini.
        </p>

        <p>
        Semoga hasil rekomendasi ini dapat membantu dalam menentukan
        jurusan yang sesuai dengan minat dan kemampuan Anda.
        </p>

        <br>

        Hormat kami,<br>
        <b>Sistem Rekomendasi Jurusan</b><br>
        SMKN 8 Garut
        
        </body>
        </html>
        """

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = to_email
        msg.set_content("Email ini memerlukan tampilan HTML.")
        msg.add_alternative(html_body, subtype='html')

        # =========================
        # BUAT PDF RESMI
        # =========================

        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=40,
            rightMargin=40,
            topMargin=30,
            bottomMargin=30
        )

        styles = getSampleStyleSheet()
        elements = []

        # LOGO
        logo = Image("static/img/logo.png", width=3*cm, height=3*cm)

        # KOP SURAT
        kop = Paragraph(
            "<para align=center>"
            "<font size=16><b>SMKN 8 GARUT</b></font><br/>"
            "<font size=11>"
            "JL RAYA LIMBANGAN SELAAWI KM.12<br/>"
            "Kec. Selaawi, Kab. Garut, Prov. Jawa Barat"
            "</font>"
            "</para>",
            styles['Normal']
        )

        header = Table([
            [logo, kop, ""]
        ], colWidths=[4*cm,10*cm,4*cm])

        elements.append(header)
        elements.append(Spacer(1,10))

        line = Table([[""]], colWidths=[17*cm])
        line.setStyle(TableStyle([
            ('LINEABOVE',(0,0),(-1,0),2,colors.black)
        ]))

        elements.append(line)
        elements.append(Spacer(1,30))

        # JUDUL
        title = Paragraph(
            "<para align=center><b>SURAT HASIL REKOMENDASI JURUSAN</b></para>",
            styles['Title']
        )

        elements.append(title)
        elements.append(Spacer(1,30))

        # ISI SURAT
        isi = Paragraph(
            f"""
            Berdasarkan hasil analisis nilai akademik yang telah dilakukan
            melalui Sistem Rekomendasi Jurusan SMKN 8 Garut, maka siswa dengan
            nama berikut:

            <br/><br/>

            <b>Nama Siswa :</b> {username}<br/>
            <b>Hasil Rekomendasi Jurusan :</b> {jurusan}

            <br/><br/>

            Demikian surat hasil rekomendasi jurusan ini dibuat agar dapat
            digunakan sebagaimana mestinya.
            """,
            styles['Normal']
        )

        elements.append(isi)
        elements.append(Spacer(1,50))

        # TANDA TANGAN
        ttd = Paragraph(
           f"""
    <para align=right>
    Garut, {format_tanggal_indo(datetime.now())}
    <br/><br/>
    Mengetahui,<br/>
    Kesiswaan
    <br/><br/>
    <img src="static/img/ttd.png" width="120" height="60"/>
    <br/>
    <b>Pendi Abdul Wahab, ST.</b>
    <br/>
    NIP. 123456789
    </para>
    """,
            styles['Normal']
        )

        elements.append(ttd)

        doc.build(elements)

        buffer.seek(0)

        msg.add_attachment(
            buffer.read(),
            maintype='application',
            subtype='pdf',
            filename='hasil_rekomendasi_jurusan.pdf'
        )

        # =========================
        # KIRIM EMAIL
        # =========================

        with smtplib.SMTP_SSL('smtp.gmail.com',465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)

    except Exception as e:
        print("Email gagal dikirim:", e)
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = to_email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

    except Exception as e:
        print("Gagal kirim email:", e)

def is_admin():
    return 'role' in session and session['role'] == 'admin'

def is_admin_or_kesiswaan():
    return 'role' in session and session['role'] in ['admin', 'kesiswaan']

# ================= ROUTES =================
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/index', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        mat = int(request.form['mat'])
        tik = int(request.form['tik'])
        seni = int(request.form['seni'])
        bindo = int(request.form['bindo'])

        session['mat_asli'] = mat
        session['tik_asli'] = tik
        session['seni_asli'] = seni
        session['bindo_asli'] = bindo

        session['mat'] = konversi_nilai(mat)
        session['tik'] = konversi_nilai(tik)
        session['seni'] = konversi_nilai(seni)
        session['bindo'] = konversi_nilai(bindo)

        return redirect(url_for('tes_minat'))

    return render_template('index.html')

@app.route('/tes_minat', methods=['GET', 'POST'])
def tes_minat():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':

        tkr_score = sum(int(request.form[f'tkr{i}']) for i in range(1, 6))
        tkj_score = sum(int(request.form[f'tkj{i}']) for i in range(1, 6))
        mm_score  = sum(int(request.form[f'mm{i}']) for i in range(1, 6))
        ap_score  = sum(int(request.form[f'ap{i}']) for i in range(1, 6))

        tkr_label = konversi_minat(tkr_score)
        tkj_label = konversi_minat(tkj_score)
        mm_label  = konversi_minat(mm_score)
        ap_label  = konversi_minat(ap_score)

        score = pd.DataFrame({
            'Score_TKR': [tkr_label + session.get('mat')],
            'Score_TKJ': [tkj_label + session.get('tik')],
            'Score_MM':  [mm_label + session.get('seni')],
            'Score_AP':  [ap_label + session.get('bindo')]
        })

        pred = model.predict(score)[0]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            INSERT INTO requests 
            (user_id, username, mat, tik, seni, bindo, hasil)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            session['user_id'],
            session['username'],
            session['mat_asli'],
            session['tik_asli'],
            session['seni_asli'],
            session['bindo_asli'],
            pred
        ))

        conn.commit()
        request_id = cursor.lastrowid

        cursor.execute(
            "SELECT email FROM users WHERE id=%s",
            (session['user_id'],)
        )

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        # kirim email di background
        if user and is_valid_email(user['email']):
            threading.Thread(
                target=send_email,
                args=(user['email'], pred, session['username'])
            ).start()

        return render_template(
            'hasil.html',
            jurusan=pred,
            request_id=request_id
        )

    return render_template('tes_minat.html')

# ================= REGISTER =================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        hashed = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
                (username, email, hashed, 'user')
            )
            conn.commit()
            flash("Registrasi berhasil! Silakan login.")
        except mysql.connector.IntegrityError:
            flash("Username atau email sudah dipakai!")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')

# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_input = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()

        cursor.close()
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

# ================= ADMIN DASHBOARD =================
@app.route('/admin/dashboard')
def admin_dashboard():
    if not is_admin_or_kesiswaan():
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    cursor.execute("SELECT * FROM requests")
    requests = cursor.fetchall()

    cursor.execute("""
        SELECT hasil, COUNT(*) as jumlah
        FROM requests
        GROUP BY hasil
    """)
    jurusan_data = cursor.fetchall()

    cursor.close()
    conn.close()

    total_users = len(users)
    total_requests = len(requests)

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
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT username, mat, tik, seni, bindo, hasil FROM requests")
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=30,
        bottomMargin=30
    )

    elements = []
    styles = getSampleStyleSheet()

    from reportlab.platypus import Image, Spacer
    from reportlab.lib.units import cm
    from datetime import datetime

    # =========================
    # KOP SURAT
    # =========================

    logo = Image("static/img/logo.png", width=3*cm, height=3*cm)

    kop = Paragraph(
    "<para align=center>"
    "<font size=16><b>SMKN 8 GARUT</b></font><br/>"
    "<font size=11>"
    "JL RAYA LIMBANGAN SELAAWI KM.12<br/>"
    "Kec. Selaawi, Kab. Garut, Prov. Jawa Barat"
    "</font>"
    "</para>",
    styles['Normal']
)

    header = Table([
    [logo, kop, ""]
    ], colWidths=[4*cm, 10*cm, 4*cm])

    header.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
    ]))

    elements.append(header)
    elements.append(Spacer(1,10))

    # =========================
    # GARIS PEMBATAS
    # =========================

    line = Table([[""]], colWidths=[17*cm])
    line.setStyle(TableStyle([
        ('LINEABOVE',(0,0),(-1,0),2,'black')
    ]))

    elements.append(line)
    elements.append(Spacer(1,25))

    # =========================
    # JUDUL LAPORAN
    # =========================

    judul = Paragraph(
        "<para align=center><b>LAPORAN HASIL REKOMENDASI JURUSAN SISWA</b></para>",
        styles['Title']
    )

    elements.append(judul)
    elements.append(Spacer(1,20))

    # =========================
    # TANGGAL CETAK
    # =========================

    tanggal = Paragraph(
        "Tanggal Cetak: " + format_tanggal_indo(datetime.now()),
        styles['Normal']
    )

    elements.append(tanggal)
    elements.append(Spacer(1,25))

    # =========================
    # TABEL DATA
    # =========================

    table_data = [[
        "Nama",
        "Matematika",
        "TIK",
        "Seni",
        "B. Indonesia",
        "Hasil Rekomendasi"
    ]]

    for row in data:
        table_data.append([
            row['username'],
            row['mat'],
            row['tik'],
            row['seni'],
            row['bindo'],
            row['hasil']
        ])

    table = Table(
        table_data,
        colWidths=[3*cm,2.5*cm,2*cm,2*cm,3*cm,4*cm]
    )

    table.setStyle(TableStyle([

        ('BACKGROUND',(0,0),(-1,0),'#6c757d'),
        ('TEXTCOLOR',(0,0),(-1,0),'white'),

        ('ALIGN',(0,0),(-1,-1),'CENTER'),

        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),

        ('GRID',(0,0),(-1,-1),1,'black'),

        ('BOTTOMPADDING',(0,0),(-1,0),8)

    ]))

    elements.append(table)
    elements.append(Spacer(1,60))

    # =========================
    # TANDA TANGAN
    # =========================

    ttd = Paragraph(
        "<para align=right>"
        "Garut, " + format_tanggal_indo(datetime.now()) +
        "<br/><br/>Mengetahui,<br/>Kepala Sekolah"
        "<br/><br/><br/><br/>"
        "(........................................)"
        "</para>",
        styles['Normal']
    )

    elements.append(ttd)

    # =========================
    # BUILD PDF
    # =========================

    doc.build(elements)

    buffer.seek(0)

    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=laporan_rekomendasi.pdf'

    return response


@app.route('/admin/users')
def admin_users():
    if not is_admin_or_kesiswaan():
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin_users.html', users=users, username=session['username'])


@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():

    request_id = request.form.get('request_id')
    rating = request.form.get('rating')
    feedback = request.form.get('feedback')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE requests
        SET rating=%s, feedback=%s
        WHERE id=%s
    ''', (rating, feedback, request_id))

    conn.commit()
    cursor.close()
    conn.close()

    flash("✅ Terima kasih! Feedback berhasil dikirim.")
    return redirect(url_for('index'))


@app.route('/admin/clear_requests', methods=['POST'])
def clear_requests():

    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM requests")

    conn.commit()
    cursor.close()
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
    cursor = conn.cursor()

    cursor.execute("DELETE FROM requests WHERE user_id=%s", (user_id,))
    cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))

    conn.commit()
    cursor.close()
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
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
            (username, email, hashed, role)
        )
        conn.commit()
        flash("User berhasil ditambahkan!")
    except mysql.connector.IntegrityError:
        flash("Username sudah dipakai!")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_users'))


@app.route('/admin/requests')
def admin_requests():
    if not is_admin_or_kesiswaan():
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM requests")
    requests = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin_requests.html', requests=requests, username=session['username'])
# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
