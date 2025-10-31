import MAPS_CONN2 as Maps
import y_data as Yollink
import pandas as pd
from datetime import datetime
import traceback

# ===========================================
# STEP 1: Extract Data from MAPS (Stock)
# ===========================================
def extract_maps_stock():
    try:
        sql = """
        SELECT 
            st.id AS stockid,
            CAST(st.DateCreated AS DATE) AS DateTransaction,
            prod.PartNumber AS PartNumber,
            prod.Name AS PartDesc,
            prod.Field1 AS CustPartNumber,
            st.Quantity AS StockIn,
            j.OrderNumber AS Job_orderNum,
            co.OrderNumber AS CO_orderNum,
            co.PONumber AS CustomerPONum
        FROM stock AS st
        LEFT JOIN Product AS prod ON prod.Id = st.ProductId
        LEFT JOIN LotCompletion AS lc ON lc.Id = st.LotCompletionId
        LEFT JOIN task AS ts ON ts.Id = lc.TaskId
        LEFT JOIN job AS j ON j.Id = ts.JobId
        LEFT JOIN CustomerOrderItem AS coi ON coi.Id = j.COItemId
        LEFT JOIN CustomerOrder AS co ON coi.CustomerOrderId = co.Id
        WHERE 
            st.Type = 0 
            AND st.LotCompletionId IS NOT NULL 
            AND prod.IsFinal = 1 
            AND co.PONumber IS NOT NULL;
        """
        conn = Maps.get_connection()
        df = pd.read_sql(sql, conn)
        conn.close()
        print(f"✅ MAPS stock data extracted: {len(df)} rows")
        return df
    except Exception as e:
        print("❌ Failed to extract MAPS stock data:", e)
        traceback.print_exc()
        return pd.DataFrame()

# ===========================================
# STEP 2: Extract Data from Yollink
# ===========================================
def extract_yollink_stock():
    try:
        sql = """
        SELECT 
            stockid,
            datetransaction,
            partnumber,
            partdesc,
            custpartnumber,
            stockin,
            job_ordernum,
            co_ordernum,
            customerponum
        FROM yollink_output
        """
        conn = Yollink.get_connection()
        df = pd.read_sql(sql, conn)
        conn.close()
        print(f"✅ Yollink stock data extracted: {len(df)} rows")
        return df
    except Exception as e:
        print("❌ Failed to extract Yollink stock data:", e)
        traceback.print_exc()
        return pd.DataFrame()

# ===========================================
# STEP 3: Compare Both Data Sources
# ===========================================
def compare_stock_data(df_maps, df_yollink):
    try:
        if df_maps.empty or df_yollink.empty:
            print("⚠️ One of the datasets is empty — performing full transfer.")
            return df_maps, pd.DataFrame()

        merged = df_maps.merge(df_yollink, on="stockid", how="outer", suffixes=("_maps", "_yollink"), indicator=True)

        new_rows = merged[merged["_merge"] == "left_only"]
        modified_rows = merged[
            (merged["_merge"] == "both") &
            (
                (merged["stockin_maps"] != merged["stockin_yollink"]) |
                (merged["datetransaction_maps"] != merged["datetransaction_yollink"])
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
# STEP 4: Insert & Update
# ===========================================
def update_yollink_stock(new_rows, modified_rows):
    try:
        conn = Yollink.get_connection()
        cursor = conn.cursor()

        for _, row in new_rows.iterrows():
            cursor.execute("""
                INSERT INTO yollink_output (
                    stockid, datetransaction, partnumber, partdesc, custpartnumber,
                    stockin, job_ordernum, co_ordernum, customerponum, updated_at
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (stockid) DO NOTHING;
            """, (
                row["stockid"], row["DateTransaction"], row["PartNumber"], row["PartDesc"],
                row["CustPartNumber"], row["StockIn"], row["Job_orderNum"], 
                row["CO_orderNum"], row["CustomerPONum"], datetime.now()
            ))

        for _, row in modified_rows.iterrows():
            cursor.execute("""
                UPDATE yollink_stockin
                SET stockin = %s,
                    datetransaction = %s,
                    updated_at = %s
                WHERE stockid = %s;
            """, (row["StockIn"], row["DateTransaction"], datetime.now(), row["stockid"]))

        conn.commit()
        conn.close()
        print("✅ Yollink stock table successfully updated.")
    except Exception as e:
        print("❌ Failed to update Yollink stock table:", e)
        traceback.print_exc()

# ===========================================
# STEP 5: Full Transfer if Empty
# ===========================================
def full_transfer_stock(df_maps):
    try:
        conn = Yollink.get_connection()
        cursor = conn.cursor()

        for _, row in df_maps.iterrows():
            cursor.execute("""
                INSERT INTO yollink_output (
                    stockid, datetransaction, partnumber, partdesc, custpartnumber,
                    stockin, job_ordernum, co_ordernum, customerponum, updated_at
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (stockid) DO NOTHING;
            """, (
                row["stockid"], row["DateTransaction"], row["PartNumber"], row["PartDesc"],
                row["CustPartNumber"], row["StockIn"], row["Job_orderNum"],
                row["CO_orderNum"], row["CustomerPONum"], datetime.now()
            ))

        conn.commit()
        conn.close()
        print("✅ Full stock data transferred successfully.")
    except Exception as e:
        print("❌ Full stock transfer failed:", e)
        traceback.print_exc()

# ===========================================
# STEP 6: Main
# ===========================================
def main():
    try:
        print("🚀 Starting stock synchronization...")

        df_maps = extract_maps_stock()
        df_yollink = extract_yollink_stock()

        if df_yollink.empty:
            full_transfer_stock(df_maps)
        else:
            new_rows, modified_rows = compare_stock_data(df_maps, df_yollink)
            update_yollink_stock(new_rows, modified_rows)

        print("🎯 Stock sync complete.")
    except Exception as e:
        print("❌ Main function failed:", e)
        traceback.print_exc()

# ===========================================
# RUN
# ===========================================
if __name__ == "__main__":
    main()
