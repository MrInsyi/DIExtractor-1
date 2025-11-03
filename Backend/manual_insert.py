from y_data import get_connection

def manual_data_insert(version, header_data, quantities):
    """
    Replace (delete + insert) rows for the same purchase_schedule, part_num, and version.
    """
    conn = get_connection()
    cur = conn.cursor()
    count = 0

    purchase_schedule = header_data.get("purchaseSchedule")
    part_number = header_data.get("partNumber")

    # 🧱 Step 2: insert new rows
    for q in quantities:
        if not q.get("date") or not q.get("qty"):
            continue

        
        # delete existing for this date
        cur.execute("""
            DELETE FROM delivery_instruction
            WHERE purchase_schedule = %s
            AND customer_part_num = %s
            AND version = %s
            AND date_commit = %s
        """, (purchase_schedule, part_number, version, q["date"]))

        cur.execute("""
            INSERT INTO delivery_instruction (
                purchase_schedule, customer_name, customer_code,
                customer_part_desc, customer_part_num,
                date_commit, quantity, version, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            purchase_schedule,
            header_data.get("customerName"),
            header_data.get("customerCode"),
            header_data.get("partDesc"),
            part_number,
            q["date"],
            q["qty"],
            version
        ))
        count += 1

    conn.commit()
    cur.close()
    conn.close()
    return count
