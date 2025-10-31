from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
from datetime import datetime
from DIExtract07 import process_pdf          # ✅ your main extraction
from insert_data import insert_delivery_instructions  # ✅ your DB insertion
import os

# ==============================
# CONFIGURATION
# ==============================
app = Flask(__name__)
CORS(app)  # allow access from your React app

BASE_FOLDER = Path(r"C:\Users\abang\Documents\ReactPython\DIExtractor\PDFs")

# ==============================
# API ROUTE — UPLOAD & PROCESS PDF
# ==============================
@app.route("/upload", methods=["POST"])
def upload_pdf():
    """
    Receives PDF from React, saves it in structured folder:
    PDFs/F1/102025/bucket_01/F1_102025_01.pdf
    Then calls DIExtract.process_pdf() to extract and insert data.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    factory = request.form.get("factory", "F1")
    month_year = request.form.get("month_year", "102025")
    bucket = request.form.get("bucket", "01")
    version = int(request.form.get("version", 1))  # ✅ capture version from React

    # -------------------------------
    # Create personalized folder path
    # -------------------------------
    folder_path = BASE_FOLDER / factory / month_year / f"bucket_{bucket}"
    folder_path.mkdir(parents=True, exist_ok=True)

    # Save the uploaded PDF
    file_path = folder_path / file.filename
    file.save(file_path)
    print(f"📥 Saved file: {file_path}")

    try:
        # -------------------------------
        # Run the full extraction pipeline
        # -------------------------------
        result = process_pdf(str(file_path), out_dir=str(folder_path / "rows_out"))

        # ❌ FIX: result.get().get(...) is invalid
        # ✅ Correct:
        db_rows = result.get("db_rows", [])
        insert_delivery_instructions(db_rows, version)

        header = result.get("header", {})
        total_parts = len(result.get("parts", []))
        total_rows = len(db_rows)

        print(f"✅ Extraction complete for {file.filename}")
        print(f"📊 Found {total_parts} part lines, {total_rows} DB rows ready")

        # -------------------------------
        # Prepare response for React
        # -------------------------------
        return jsonify({
            "status": "success",
            "message": "File processed successfully",
            "saved_to": str(file_path),
            "header": header,
            "total_parts": total_parts,
            "total_db_rows": total_rows,
            "version": version,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    except Exception as e:
        print(f"❌ Error processing file: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/delivery-calendar", methods=["GET"])
def get_delivery_calendar():
    """
    Returns aggregated delivery data grouped by date for calendar display.
    Optional query parameters:
        ?month=10&year=2025&version=1
    """
    import psycopg2
    from y_data import get_connection

    month = request.args.get("month", None)
    year = request.args.get("year", None)
    version = request.args.get("version", None)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
        SELECT 
            date_commit,
            SUM(quantity) AS total_qty,
            COUNT(DISTINCT customer_part_num) AS total_parts
        FROM delivery_instruction
        WHERE TRUE
        """

        params = []
        if month and year:
            query += " AND EXTRACT(MONTH FROM date_commit) = %s AND EXTRACT(YEAR FROM date_commit) = %s"
            params.extend([month, year])
        if version:
            query += " AND version = %s"
            params.append(version)

        query += " GROUP BY date_commit ORDER BY date_commit"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        result = [
            {
                "date": str(r[0]),
                "total_qty": int(r[1]),
                "total_parts": int(r[2])
            }
            for r in rows
        ]

        return jsonify({"status": "success", "data": result})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route("/api/matrixtable", methods=["GET"])
def get_matrix_table():
    """
    Returns structured DI data grouped by part_number and date
    for a given month, year, and version.
    Example: /api/matrixtable?month=10&year=2025&version=1
    """
    import psycopg2
    from y_data import get_connection

    month = request.args.get("month", None)
    year = request.args.get("year", None)
    version = request.args.get("version", None)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Step 1. Filter base condition
        base_query = """
            SELECT customer_part_num,
                customer_part_desc,
                date_commit,
                SUM(quantity) AS qty
            FROM delivery_instruction
            WHERE TRUE
        """
        params = []

        if month and year:
            base_query += " AND EXTRACT(MONTH FROM date_commit) = %s AND EXTRACT(YEAR FROM date_commit) = %s"
            params.extend([month, year])
        if version:
            base_query += " AND version = %s"
            params.append(version)

        base_query += " GROUP BY customer_part_num, customer_part_desc, date_commit ORDER BY customer_part_num, date_commit"

        cursor.execute(base_query, params)
        rows = cursor.fetchall()

        # Step 2. Build matrix
        data_by_part = {}

        for part_num, part_desc, date_commit, qty in rows:
            part_num = part_num.strip() if part_num else "UNKNOWN"
            part_desc = part_desc.strip() if part_desc else "UNKNOWN"
            day = int(date_commit.day)

            if part_num not in data_by_part:
                data_by_part[part_num] = {
                    "part_desc": part_desc,
                    "days": {}
                }

            data_by_part[part_num]["days"][str(day)] = int(qty)

        # Step 3. Format result
        result = []
        for part_num, info in data_by_part.items():
            result.append({
                "part_number": part_num,
                "part_desc": info["part_desc"],
                "days": info["days"]
            })

        return jsonify({"status": "success", "data": result})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

# ==============================
# SERVER ENTRY POINT
# ==============================
if __name__ == "__main__":
    # Flask runs on port 8000 to match your React app
    app.run(host="0.0.0.0", port=8000, debug=True)
