from y_data import get_connection  # ✅ use your existing DB connector
from psycopg2.extras import execute_values
from datetime import datetime

# ============================================
# INSERT INTO delivery_instruction
# ============================================
def insert_delivery_instructions(db_rows, version):
    """
    Inserts multiple delivery instruction rows into the database.

    Each item in db_rows should contain:
        {
            "PurchaseSchedule": 410026130,
            "Date": "2025-10-01",
            "CustomerName": "Hong Leong Yamaha Motor Sdn Bhd",
            "CustomerCode": "46829-P",
            "PartDesc": "CAM, SHAFT 1",
            "PartNum": "10C-F5351-00",
            "Qty": 200
        }
    """
    if not db_rows:
        print("⚠️ No rows to insert.")
        return

    conn = None
    try:
        conn = get_connection()
        print("🧩 Connected to DB successfully.")
        cursor = conn.cursor()

         # Get PO number (all rows share same one)
        purchase_schedule_no = db_rows[0].get("PurchaseSchedule")

        # 1️⃣ Delete existing rows with same PurchaseSchedule + version
        cursor.execute("""
            DELETE FROM delivery_instruction
            WHERE purchase_schedule = %s AND version = %s
        """, (purchase_schedule_no, version))
        print(f"🧹 Deleted old version {version} for PO {purchase_schedule_no}")

        query = """
        INSERT INTO delivery_instruction
        (purchase_schedule, date_commit, customer_name, customer_code,
         customer_part_desc, customer_part_num, quantity, created_at, version)
        VALUES %s;
        """

        values = [
            (
                row.get("PurchaseSchedule"),
                row.get("Date"),
                row.get("CustomerName"),
                row.get("CustomerCode"),
                row.get("PartDesc"),
                row.get("PartNum"),
                row.get("Qty"),
                datetime.now(),
                version
            )
            for row in db_rows
        ]
        print("🧠 Prepared to insert rows:", len(values))
        print(values[:3])  # show first few rows

        try:
            execute_values(cursor, query, values)
            print("✅ execute_values ran successfully.")
        except Exception as inner_e:
            print("🚨 execute_values failed:", inner_e)

        conn.commit()
        print("🧾 Commit done at", datetime.now())

        print(f"✅ Successfully inserted {len(values)} delivery rows.")

    except Exception as e:
        print(f"❌ Error inserting delivery data: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            cursor.close()
            conn.close()
