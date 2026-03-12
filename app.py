import io
import os
from flask import Flask, render_template, request, redirect, session, flash, send_file, send_from_directory
from pymongo import MongoClient
from config import Config
from datetime import datetime
from reportlab.pdfgen import canvas
import urllib.parse
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "hr_secret_key"
app.config.from_object(Config)

UPLOAD_FOLDER = os.path.join("static", "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

client = MongoClient(app.config["MONGO_URI"])
db = client[app.config["DB_NAME"]]

users = db.users
ratings = db.ratings
projects=db.projects


# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        loginId = request.form["loginId"]
        password = request.form["password"]
        role = request.form["role"]

        user = users.find_one({
            "loginId": loginId,
            "password": password,
            "role": role
        })

        if user:
            session["user"] = user["name"]
            session["role"] = role

            if role == "admin":
                return redirect("/admin")
            else:
                return redirect("/employee")

        flash("Invalid Credentials")

    return render_template("login.html")


# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if session.get("role") != "admin":
        return redirect("/")
    return render_template("admin_dashboard.html")

#-----------------RATE PRODUCT----------------------
@app.route("/rate-product", methods=["GET","POST"])
def rate_product():

    if session.get("role") != "admin":
        return redirect("/")

    if request.method == "POST":

        ratings.insert_one({
            "employeeName": request.form["employee"],
            "projectName": request.form["project"],
            "rating": int(request.form["rating"]),
            "comment": request.form["comment"],
            "adminName": session["user"],
            "date": request.form["date"]
        })

        flash("Rating Submitted Successfully!")

    employees = users.find({"role":"employee"})
    project_list = list(projects.find())

    today = datetime.now().strftime("%Y-%m-%d")

    return render_template(
        "rating_product.html",
        employees=employees,
        projects=project_list,
        today=today
    )

# ---------------- ADD DATA PAGE ----------------
@app.route("/add-data")
def add_data():
    if session.get("role") != "admin":
        return redirect("/")
    return render_template("add_data.html")

# ---------------- ADD EMPLOYEE ----------------
@app.route("/add-employee", methods=["POST"])
def add_employee():
    if session.get("role") != "admin":
        return redirect("/")

    name = request.form["name"]
    loginId = request.form["loginId"]
    password = request.form["password"]
    position=request.form["position"]

    if not users.find_one({"loginId": loginId}):
        users.insert_one({
            "name": name,
            "loginId": loginId,
            "password": password,
            "role": "employee",
            "position": position
        })
        flash("Employee Added Successfully!")

    return redirect("/admin")

# ---------------- ADD PROJECT ----------------
@app.route("/add-project", methods=["POST"])
def add_project():
    if session.get("role") != "admin":
        return redirect("/")

    projectName = request.form["projectName"]

    if not projects.find_one({"projectName": projectName}):
        projects.insert_one({
            "projectName": projectName
        })
        flash("Project Added Successfully!")

    return redirect("/admin")

# ---------------- ASSIGN PROJECT PAGE ----------------
@app.route("/assign-project", methods=["GET","POST"])
def assign_project():

    if session.get("role") != "admin":
        return redirect("/")

    if request.method == "POST":

        product = request.form["product"]
        apm = request.form.getlist("apm")
        developer = request.form.getlist("developer")
        timeline = request.form["timeline"]
        task = request.form["task"]

        db.assignments.insert_one({
            "product": product,
            "apm": apm,
            "developer": developer,
            "timeline": timeline,
            "task": task,
            "createdBy": session["user"]
        })

        flash("Project Assigned Successfully!")

    products = list(projects.find())

    apms = users.find({"position":"apm"})
    developers = users.find({"position":"developer"})

    return render_template(
        "assign_project.html",
        products=products,
        apms=apms,
        developers=developers
    )

# ---------------- ADMIN CAPSTONE ----------------
@app.route("/capstone")
def capstone():

    if session.get("role") != "admin":
        return redirect("/")

    employees = users.find({"role":"employee"})

    return render_template(
        "admin_capstone.html",
        employees=employees
    )


# ---------------- PROJECT TIMELINE ----------------
@app.route("/project-timeline")
def project_timeline():

    if session.get("role") != "employee":
        return redirect("/")

    name = session["user"]

    records = db.assignments.find({
        "$or": [
            {"developer": {"$in": [name]}},
            {"apm": {"$in": [name]}}
        ]
    })

    return render_template(
        "view_project.html",
        records=records
    )

# ---------------- VIEW REPORTS ----------------
@app.route("/reports")
def reports():
    if session.get("role") != "admin":
        return redirect("/")
    employees = users.find({"role": "employee"})
    return render_template("view_reports.html", employees=employees)

# ---------------- VIEW EMPLOYEE CAPSTONE ----------------
@app.route("/capstone/<name>")
def view_capstone(name):

    if session.get("role") != "admin":
        return redirect("/")

    files = db.capstones.find({"employee": name})

    return render_template(
        "capstone_files.html",
        files=files,
        name=name
    )

#--------------------Capstone Download---------------------
@app.route("/capstone-download/<filename>")
def capstone_download(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename,
        as_attachment=True
    )

# ---------------- VIEW PDF ----------------
@app.route("/capstone-view/<filename>")
def capstone_view(filename):

    if session.get("role") != "admin":
        return redirect("/")

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )

# ---------------- EMPLOYEE REPORT ----------------
@app.route("/employee/<name>")
def employee_report(name):
    name = urllib.parse.unquote(name)
    records = ratings.find({"employeeName": name})
    return render_template("employee_report.html",
                           records=records,
                           name=name)


# ---------------- EMPLOYEE LOGIN VIEW ----------------
@app.route("/employee")
def employee_dashboard():
    if session.get("role") != "employee":
        return redirect("/")
    name = session["user"]
    return render_template("employee_dashboard.html",name=name)

# ---------------- EMPLOYEE CAPSTONE ----------------
@app.route("/employee-capstone", methods=["GET","POST"])
def employee_capstone():

    if session.get("role") != "employee":
        return redirect("/")

    if request.method == "POST":

        file = request.files["pdf"]

        if file:
            filename = secure_filename(file.filename)

            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(path)

            db.capstones.insert_one({
                "employee": session["user"],
                "filename": filename,
                "date": datetime.now()
            })

            flash("Capstone Uploaded Successfully")

    return render_template("employee_capstone.html")

# ---------------- DOWNLOAD PDF ----------------
@app.route("/download/<path:name>")
def download(name):
    name = urllib.parse.unquote(name)
    records = list(ratings.find({"employeeName": name}))

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=letter)

    elements = []

    styles = getSampleStyleSheet()

    title = Paragraph(f"<b>HR Appraisal Report - {name}</b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1,20))

    # Table Header
    data = [["Date", "Project", "Rating", "Comment"]]

    for r in records:
        data.append([
            r.get("date",""),
            r.get("projectName",""),
            f"{r.get('rating','')}/10",
            r.get("comment","")
        ])

    table = Table(data, colWidths=[100,120,80,260])

    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.grey),
        ("TEXTCOLOR",(0,0),(-1,0),colors.whitesmoke),

        ("GRID",(0,0),(-1,-1),1,colors.black),

        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),

        ("ALIGN",(2,1),(2,-1),"CENTER"),
    ]))

    elements.append(table)

    doc.build(elements)

    buffer.seek(0)

    return send_file(buffer,
                     as_attachment=True,
                     download_name="report.pdf",
                     mimetype="application/pdf")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)