import MAPS_CONN2 as Maps
import y_data as Yollink
import pandas as pd
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS
from tabulate import tabulate
import traceback

# ===========================================
# STEP 1: Extract Data from MAPS
# ===========================================
def extract_maps_data():
    try:
        sql = """
        SELECT 
            j.id AS job_id,
            j.OrderNumber,
            j.DesireDate,
            j.Quantity,
            prod.PartNumber AS In_PartNumber,
            prod.Name AS In_PartDescription,
            prod.Field1 AS CustomerPartNumber,
            CO.PONumber AS CustomerPONumber
        FROM job AS j
        LEFT JOIN Product AS prod ON prod.id = j.ProductId
        LEFT JOIN CustomerOrderItem AS COI ON COI.id = j.COItemId
        LEFT JOIN CustomerOrder AS CO ON CO.Id = COI.CustomerOrderId
        WHERE prod.IsFinal = 1 
        AND j.COItemId IS NOT NULL 
        AND CO.Field1 = 'Confirm Order';
        """
        conn = Maps.get_connection()
        df_maps = pd.read_sql(sql, conn)
        conn.close()

        print(f"✅ MAPS data extracted: {len(df_maps)} rows")
        return df_maps
    
    except Exception as e:
        print("❌ Failed to extract MAPS data:", e)
        traceback.print_exc()
        return pd.DataFrame()

# ===========================================
# STEP 2: Extract Data from Yollink (MES)
# ===========================================
def extract_yollink_data():
    try:
        sql = """
        SELECT 
            job_id,
            job_ordernumber,
            job_desiredate,
            job_quantity,
            in_partnumber,
            in_partdesc,
            custpartnumber,
            custponumber
        FROM yollink_orders
        """
        conn = Yollink.get_connection()
        df_yollink = pd.read_sql(sql, conn)
        conn.close()
        print(f"✅ Yollink data extracted: {len(df_yollink)} rows")
        return df_yollink
    except Exception as e:
        print("❌ Failed to extract Yollink data:", e)
        traceback.print_exc()
        return pd.DataFrame()

# ===========================================
# STEP 3: Compare Both Data Sources
# ===========================================
def compare_data(df_maps, df_yollink):
    try:
        # Standardize date and quantity formats
        df_maps["DesireDate"] = pd.to_datetime(df_maps["DesireDate"]).dt.date
        df_yollink["job_desiredate"] = pd.to_datetime(df_yollink["job_desiredate"]).dt.date

        df_maps["Quantity"] = df_maps["Quantity"].astype(int)
        df_yollink["job_quantity"] = df_yollink["job_quantity"].astype(int)


        merged = df_maps.merge(df_yollink, on="job_id", how="outer", suffixes=("_maps", "_yollink"), indicator=True)

        new_rows = merged[merged["_merge"] == "left_only"]
        missing_rows = merged[merged["_merge"] == "right_only"]
        modified_rows = merged[
            (merged["_merge"] == "both") &
            (
                (merged["Quantity"] != merged["job_quantity"]) |
                (merged["DesireDate"] != merged["job_desiredate"])
            )
        ]

        print(f"🆕 New rows to insert: {len(new_rows)}")
        print(f"🧾 Rows to update: {len(modified_rows)}")

        return new_rows, modified_rows
    except Exception as e:
        print("❌ Comparison failed:", e)
        traceback.print_exc()
        return pd.DataFrame(), pd.DataFrame()

# ===========================================
# STEP 4: Insert & Update to Yollink
# ===========================================
def update_yollink(new_rows, modified_rows):
    try:
        conn = Yollink.get_connection()
        cursor = conn.cursor()

        # Insert new rows
        for _, row in new_rows.iterrows():
            cursor.execute("""
                INSERT INTO yollink_orders (
                    job_id, job_ordernumber, job_desiredate, job_quantity,
                    in_partnumber, in_partdesc, custpartnumber, custponumber, updated_at
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                row["job_id"], row["OrderNumber"], row["DesireDate"], row["Quantity"],
                row["In_PartNumber"], row["In_PartDescription"],
                row["CustomerPartNumber"], row["CustomerPONumber"], datetime.now()
            ))

        # Update modified rows
        for _, row in modified_rows.iterrows():
            cursor.execute("""
                UPDATE yollink_orders
                SET job_quantity = %s,
                    job_desiredate = %s,
                    updated_at = %s
                WHERE job_id = %s
            """, (row["Quantity"], row["DesireDate"], datetime.now(), row["job_id"]))

        conn.commit()
        conn.close()
        print("✅ Yollink database successfully updated.")

    except Exception as e:
        print("❌ Failed to update Yollink:", e)
        traceback.print_exc()

# ===========================================
# STEP 5: Full Transfer if Empty
# ===========================================
def full_transfer_if_empty():
    try:
        df_yollink = extract_yollink_data()
        if df_yollink.empty:
            print("⚠️ Yollink is empty. Performing full transfer.")
            df_maps = extract_maps_data()
            full_transfer(df_maps)
        else:
            print("✅ Yollink has data. Proceeding with comparison.")
    except Exception as e:
        print("❌ Full transfer failed:", e)
        traceback.print_exc()

def full_transfer(df_maps):
    try:
        conn = Yollink.get_connection()
        cursor = conn.cursor()

        for _, row in df_maps.iterrows():
            cursor.execute("""
                INSERT INTO yollink_orders (
                    job_id, job_ordernumber, job_desiredate, job_quantity,
                    in_partnumber, in_partdesc, custpartnumber, custponumber, updated_at
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                row["job_id"], row["OrderNumber"], row["DesireDate"], row["Quantity"],
                row["In_PartNumber"], row["In_PartDescription"],
                row["CustomerPartNumber"], row["CustomerPONumber"], datetime.now()
            ))
        conn.commit()
        conn.close()
        print("✅ Full data transferred successfully.")
    except Exception as e:
        print("❌ Full transfer failed:", e)
        traceback.print_exc()

# ===========================================
# STEP 6: Main
# ===========================================
def main():
    try:
        print("🚀 Starting daily data synchronization...")
        full_transfer_if_empty()

        df_maps = extract_maps_data()
        df_yollink = extract_yollink_data()
        new_rows, modified_rows = compare_data(df_maps, df_yollink)

        update_yollink(new_rows, modified_rows)
        print("🎯 Daily update complete.")
    except Exception as e:
        print("❌ Main function failed:", e)
        traceback.print_exc()

# ===========================================
# RUN
# ===========================================
if __name__ == "__main__":
    main()
