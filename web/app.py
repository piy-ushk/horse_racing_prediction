"""
Flask demo web server.

Routes:
  /                       — today's races dashboard
  /race/<race_id>         — race detail (requires ?auth=line_only)
  /preview/<slug>         — serve static HTML written by the publisher
  /run                    — trigger the pipeline manually (POST)
  /logs                   — today's log file
  /admin                  — operator admin panel (schedule time, config)
  /admin/schedule         — update schedule time (POST)
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template, request, redirect, url_for, abort, send_file
from datetime import date
import config
from database import db

app = Flask(__name__)


@app.route("/")
def index():
    today = date.today().strftime("%Y-%m-%d")
    races = db.get_races_for_date(today)
    race_data = []
    for race in races:
        preds = db.get_predictions_for_race(race["race_id"])
        marked = [p for p in preds if p["mark"]]
        race_data.append({"race": race, "predictions": preds, "marked": marked})
    h, m = config.get_schedule()
    return render_template("index.html", race_data=race_data, today=today,
                           auth_param=config.AUTH_PARAM, auth_value=config.AUTH_VALUE,
                           demo_mode=config.DEMO_MODE,
                           scheduled_time=f"{h:02d}:{m:02d}")


@app.route("/race/<race_id>")
def race_detail(race_id):
    auth = request.args.get(config.AUTH_PARAM)
    if auth != config.AUTH_VALUE:
        return render_template("access_denied.html"), 403

    preds = db.get_predictions_for_race(race_id)
    if not preds:
        abort(404)

    races = db.get_races_for_date(date.today().strftime("%Y-%m-%d"))
    race = next((r for r in races if r["race_id"] == race_id), None)
    if not race:
        abort(404)

    h, m = config.get_schedule()
    return render_template("race.html", race=race, predictions=preds,
                           auth_param=config.AUTH_PARAM, auth_value=config.AUTH_VALUE,
                           demo_mode=config.DEMO_MODE,
                           scheduled_time=f"{h:02d}:{m:02d}")


@app.route("/preview/<slug>")
def preview(slug):
    html_path = config.DATA_DIR / "html" / f"{slug}.html"
    if not html_path.exists():
        abort(404)
    return send_file(str(html_path))


@app.route("/run", methods=["POST"])
def run_pipeline():
    import main as pipeline
    pipeline.run()
    return redirect(url_for("index"))


@app.route("/logs")
def show_logs():
    log_file = config.LOG_DIR / f"{date.today().strftime('%Y-%m-%d')}.log"
    content = log_file.read_text(encoding="utf-8") if log_file.exists() else "No log yet."
    return render_template("logs.html", content=content, date=date.today().strftime("%Y-%m-%d"))


@app.route("/admin")
def admin():
    h, m = config.get_schedule()
    task_status = None
    try:
        from scheduler.setup_windows_task import get_task_status
        task_status = get_task_status()
    except Exception:
        pass
    updated = request.args.get("updated") == "1"
    error = request.args.get("error") == "1"
    return render_template(
        "admin.html",
        scheduled_hour=h,
        scheduled_minute=m,
        task_status=task_status,
        demo_mode=config.DEMO_MODE,
        wp_url=config.WP_BASE_URL,
        jravan_key_set=bool(config.JRAVAN_LICENSE_KEY),
        umaconn_key_set=bool(config.UMACONN_API_KEY),
        wp_configured=bool(config.WP_USERNAME and config.WP_APP_PASSWORD),
        updated=updated,
        error=error,
    )


@app.route("/admin/schedule", methods=["POST"])
def update_schedule():
    try:
        hour = int(request.form.get("hour", 9))
        minute = int(request.form.get("minute", 30))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("out of range")
        config.save_schedule(hour, minute)
        try:
            from scheduler.setup_windows_task import create_task
            create_task(hour, minute)
        except Exception:
            pass
        return redirect(url_for("admin") + "?updated=1")
    except ValueError:
        return redirect(url_for("admin") + "?error=1")


if __name__ == "__main__":
    db.init_db()
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG)
