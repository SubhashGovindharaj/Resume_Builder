from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    resume = ""
    if request.method == "POST":
        name = request.form["name"]
        skills = request.form["skills"]
        experience = request.form["experience"]

        # Dummy resume output
        resume = f"""
        Name: {name}

        Skills:
        {skills}

        Experience:
        {experience}

        Summary:
        Enthusiastic professional with a passion for data and software development.
        """

    return render_template("index.html", resume=resume)

if __name__ == "__main__":
    app.run(debug=True)
