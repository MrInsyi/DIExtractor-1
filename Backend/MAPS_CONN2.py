import pyodbc


def get_connection():
    # Establishing the connection
    connection = pyodbc.connect(
            'DRIVER={SQL Server};'
            'SERVER=10.0.100.15\\SQLEXPRESS;'
            'DATABASE=avelon-yollink;'
            'UID=sa;'
            'PWD=sa@123;'
        )
    return connection