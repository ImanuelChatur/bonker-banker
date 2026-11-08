from flask import Flask, render_template


def create_app():
    app = Flask(__name__)

    @app.route("/")
    def index():
        from routes.home import home_stat
        return render_template("index.html", stat=home_stat())

    # HTMX test: returns a small HTML snippet that gets swapped into the page
    @app.route("/health")
    def health():
        return '<span class="status-ok">Flask is connected ✓</span>'

    from routes import register_routes
    register_routes(app)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)