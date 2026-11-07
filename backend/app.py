from flask import Flask, render_template


def create_app():
    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template("index.html")

    # HTMX test: returns a small HTML snippet that gets swapped into the page
    @app.route("/health")
    def health():
        return '<span class="text-emerald-600 font-semibold">Flask is connected ✓</span>'

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)