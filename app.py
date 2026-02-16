"""Flask web app for the AI DDR Report Generator."""

import logging
import tempfile
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

from src.pipeline import run_pipeline

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload
logging.basicConfig(level=logging.INFO)
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt", "md"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    inspection_file = request.files.get("inspection")
    thermal_file = request.files.get("thermal")
    output_format = request.form.get("format", "markdown")

    has_inspection = inspection_file and inspection_file.filename
    has_thermal = thermal_file and thermal_file.filename
    if not has_inspection and not has_thermal:
        return jsonify({"error": "At least one document (inspection or thermal) is required."}), 400

    inspection_path = None
    thermal_path = None

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            if has_inspection and allowed_file(inspection_file.filename):
                inspection_path = tmp / secure_filename(inspection_file.filename)
                inspection_file.save(inspection_path)

            if has_thermal and allowed_file(thermal_file.filename):
                thermal_path = tmp / secure_filename(thermal_file.filename)
                thermal_file.save(thermal_path)

            if not inspection_path and not thermal_path:
                return jsonify({"error": "No valid files uploaded. Use PDF, DOCX, or TXT."}), 400

            app.logger.info("Running pipeline...")
            report = run_pipeline(
                inspection_path=inspection_path,
                thermal_path=thermal_path,
                output_format=output_format,
            )
            app.logger.info("Pipeline complete.")
            return jsonify({"success": True, "report": report, "format": output_format})

    except ValueError as e:
        app.logger.warning("ValueError: %s", e)
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.exception("Generation failed")
        return jsonify({"error": f"Generation failed: {str(e)}"}), 500


@app.route("/download", methods=["POST"])
def download():
    import io

    report = request.form.get("report", "")
    format_type = request.form.get("format", "markdown")

    if not report:
        return jsonify({"error": "No report to download."}), 400

    extensions = {"markdown": "md", "json": "json", "html": "html"}
    ext = extensions.get(format_type, "md")

    buffer = io.BytesIO(report.encode("utf-8"))
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"ddr_report.{ext}",
        mimetype="text/plain; charset=utf-8",
    )


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent / ".env")
    except ImportError:
        pass
    app.run(host="127.0.0.1", port=5000, debug=True)
