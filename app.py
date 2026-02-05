from flask import Flask, render_template, request, redirect, session, flash, send_file
from pymongo import MongoClient
from config import Config
from datetime import datetime
from reportlab.pdfgen import canvas
import io
import urllib.parse

app = Flask(__name__)
app.secret_key = "hr_secret_key"
app.config.from_object(Config)

client = MongoClient(app.config["MONGO_URI"])
db = client[app.config["DB_NAME"]]

users = db.users
ratings = db.ratings   # 🔥 using ratings collection


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

    if request.method == "POST":
        employee = request.form["employee"]
        project = request.form["project"]
        rating_value = int(request.form["rating"])
        date = request.form["date"]

        ratings.insert_one({
            "employeeName": employee,
            "projectName": project,
            "rating": rating_value,
            "adminName": session["user"],
            "date": date
        })

        flash("Rating Submitted Successfully!")

    employees = users.find({"role": "employee"})
    today = datetime.now().strftime("%Y-%m-%d")

    return render_template("admin_dashboard.html",
                           employees=employees,
                           today=today)


# ---------------- VIEW REPORTS ----------------
@app.route("/reports")
def reports():
    if session.get("role") != "admin":
        return redirect("/")
    employees = users.find({"role": "employee"})
    return render_template("view_reports.html", employees=employees)


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
    records = ratings.find({"employeeName": name})
    return render_template("employee_report.html",
                           records=records,
                           name=name)


# ---------------- DOWNLOAD PDF ----------------
@app.route("/download/<path:name>")
def download(name):
    name = urllib.parse.unquote(name)
    records = ratings.find({"employeeName": name})

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    y = 800

    p.drawString(200, y, f"HR Appraisal Report - {name}")
    y -= 40

    for r in records:
        p.drawString(100, y, f"Date: {r['date']}")
        y -= 20
        p.drawString(100, y, f"Project: {r['projectName']}")
        y -= 20
        p.drawString(100, y, f"Rating: {r['rating']}/10")
        y -= 40

    p.save()
    buffer.seek(0)

    return send_file(buffer,
                     as_attachment=True,
                     download_name="report.pdf",
                     mimetype='application/pdf')


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
