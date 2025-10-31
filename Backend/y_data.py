import psycopg2

def get_connection():
    try:
        conn = psycopg2.connect(
            host="10.0.100.14",          # your PostgreSQL server IP
            database="purchase_schedule",
            user="postgres",
            password="yollinkvc@2020",
            port=5432
        )
        print("✅ Database connected successfully!")
        return conn
    except psycopg2.Error as e:
        print("❌ Database connection failed:", e)
        return None


# Optional: quick test
if __name__ == "__main__":
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print("🧠 PostgreSQL version:", version[0])
        cursor.close()
        conn.close()
