from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

BASE_URL = "https://www.osmania.ac.in/res07/20260188.jsp"

history = []


def get_result(htno):
    session = requests.Session()

    # GET request
    page = session.get(BASE_URL, verify=False)
    soup = BeautifulSoup(page.text, "html.parser")

    # Hidden fields
    form_data = {
        hidden.get("name"): hidden.get("value", "")
        for hidden in soup.find_all("input", type="hidden")
    }

    # Add data
    form_data["htno"] = htno
    form_data["submit"] = "Submit"

    # POST request
    response = session.post(BASE_URL, data=form_data, verify=False)

    return response.text


def parse_result(html):
    soup = BeautifulSoup(html, "html.parser")

    result = {
        "name": "",
        "status": "",
        "subjects": [],
        "sgpa": 0
    }

    # ✅ Extract Name
    name_label = soup.find(string="Name")
    if name_label:
        td = name_label.find_parent("td").find_next_sibling("td")
        if td:
            result["name"] = td.get_text(strip=True)

    # ✅ Extract Status
    text = soup.get_text()
    if "PASSED" in text:
        result["status"] = "PASSED"
    elif "PROMOTED" in text:
        result["status"] = "PROMOTED"
    elif "ALREADY PROMOTED" in text:
        result["status"] = "ALREADY PROMOTED"
    else:
        result["status"] = "UNKNOWN"

    # ✅ Grade points
    grade_points = {
        "S": 10,
        "A": 9,
        "B": 8,
        "C": 7,
        "D": 6,
        "E": 5,
        "F": 0,
        "FAIL": 0
    }

    total_points = 0
    total_credits = 0

    # ✅ Extract Subjects (robust logic)
    subjects_set = set()   # to avoid duplicates

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cols = [td.get_text(strip=True) for td in row.find_all("td")]

            if len(cols) == 4 and (
                cols[0].startswith("PC")
                or cols[0].startswith("LAB")
                or cols[0].startswith("SINT")
            ):
                key = tuple(cols)  # unique row

                if key not in subjects_set:
                    subjects_set.add(key)

                    grade = cols[3].upper()
                    credits = float(cols[2])

                    point = grade_points.get(grade, 0)

                    total_points += point * credits
                    total_credits += credits

                    result["subjects"].append({
                        "code": cols[0],
                        "name": cols[1],
                        "credits": credits,
                        "grade": grade,
                        "point": point
                    })

        # ✅ STOP after first valid table found
        if result["subjects"]:
            break
    
    # ✅ SGPA Calculation — only if no failed subjects
    failed = any(s["grade"] in ("F", "FAIL") for s in result["subjects"])
    if total_credits > 0 and not failed:
        result["sgpa"] = round(total_points / total_credits, 2)
    else:
        result["sgpa"] = None
    
    return result

@app.route("/", methods=["GET", "POST"])
def index():
    result = None

    if request.method == "POST":
        htno = request.form.get("htno")

        html = get_result(htno)
        result = parse_result(html)

        history.append({
            "htno": htno,
            "name": result["name"],
            "status": result["status"]
        })

    return render_template("index.html", result=result, history=history)


if __name__ == "__main__":
    app.run(debug=True)