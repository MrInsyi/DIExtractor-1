import pdfplumber
import re
from datetime import datetime

# ==============================
# TEMP CUSTOMER LIBRARY
# ==============================
customer = {
    "Hong Leong Yamaha Motor Sdn Bhd": "46829-P",
    # Add more customers if needed
}

# ==============================
# HELPERS
# ==============================
def parse_date(date_str: str, year=2025):
    """Convert '16/10' to datetime with default year."""
    return datetime.strptime(f"{date_str}/{year}", "%d/%m/%Y")

def is_valid_part_number(value: str) -> bool:
    """Check if string looks like a part number (e.g. B17-E461A-10-C)."""
    if not value:
        return False
    return bool(re.match(r"^[A-Z0-9\-]+$", value.strip()))

def clean_cell(value: str):
    """Clean cell values (handle stacked text like '200\\n800')."""
    if not value:
        return None
    parts = value.split("\n")
    try:
        return sum(int(p) for p in parts if p.isdigit())
    except:
        return value.strip()

# ==============================
# HEADER EXTRACTION
# ==============================
def extract_header(pdf_path: str, customer_lib: dict) -> dict:
    header_data = {
        "Purchase Schedule No": None,
        "Firm Period": None,
        "Customer Name": None,
        "Customer Code": None,
        "Firm Start": None,
        "Firm End": None
    }

    pdf = None
    try:
        pdf = pdfplumber.open(pdf_path)
        first_page = pdf.pages[0]
        text = first_page.extract_text()

        # Purchase Schedule
        match_schedule = re.search(r"Purchase Schedule No\.?:\s*(\S+)", text, re.IGNORECASE)
        if match_schedule:
            header_data["Purchase Schedule No"] = match_schedule.group(1)

        # Firm Period
        match_firm = re.search(r"Firm Period\s*:\s*(.+)", text)
        if match_firm:
            firm_period = match_firm.group(1).strip()
            header_data["Firm Period"] = firm_period
            # Parse into datetime objects
            start_str, end_str = firm_period.split(" to ")
            header_data["Firm Start"] = datetime.strptime(start_str.strip(), "%d-%m-%Y")
            header_data["Firm End"]   = datetime.strptime(end_str.strip(), "%d-%m-%Y")

        # Match against customer library
        for name, code in customer_lib.items():
            if name in text:
                header_data["Customer Name"] = name
                header_data["Customer Code"] = code
                break

    except Exception as e:
        print(f"⚠️ Error reading PDF header: {e}")

    finally:
        if pdf:
            pdf.close()

    return header_data

# ==============================
# TABLE EXTRACTION
# ==============================
def extract_firm_period_rows(pdf_path: str, header_data: dict):
    """Normalize rows into [PurchaseScheduleNo, CustomerCode, PartNumber, Date, Qty]."""
    results = []
    start_date, end_date = header_data["Firm Start"], header_data["Firm End"]
    sched_no = header_data["Purchase Schedule No"]
    cust_code = header_data["Customer Code"]

    with pdfplumber.open(pdf_path) as pdf:
        
        # Debug: Print all tables found
        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()
            for t_index, table in enumerate(tables, start=1):
                print(f"\n=== Page {page_num} | Table {t_index} ===")
                for r_index, row in enumerate(table):
                    for c_index, cell in enumerate(row):
                        print(f"Row {r_index}, Col {c_index}: {cell}")


        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue

                headers = table[0]
                date_cols = {}

                # Identify which headers are dates inside Firm Period
                for i, h in enumerate(headers):
                    try:
                        d = parse_date(h)
                        if start_date <= d <= end_date:
                            date_cols[i] = d
                    except:
                        pass

                # Process rows
                for row in table[1:]:
                    part_number = row[1]
                    if not is_valid_part_number(part_number):
                        continue

                    for i, d in date_cols.items():
                        qty = clean_cell(row[i])
                        if qty is None:
                            qty = 0
                        results.append([
                            sched_no,
                            cust_code,
                            part_number,
                            d.strftime("%d/%m/%Y"),
                            qty
                        ])
    return results

# ==============================
# MAIN SCRIPT
# ==============================
def main():
    pdf_path = r"DI.pdf"

    # Step 1: Header
    header = extract_header(pdf_path, customer)
    print("📄 Header Data:")
    for k, v in header.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
