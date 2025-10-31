import pdfplumber
import re
import pytesseract
import os
import cv2
import pandas as pd
import datetime


customer = {
    "Hong Leong Yamaha Motor Sdn Bhd": "46829-P",
    # Add more customers if needed
}

# ==============================
# HEADER EXTRACTION
# ==============================
def extract_header(page, customer_lib: dict) -> dict:
    header_data = {
        "Purchase Schedule No": None,
        "Firm Period": None,
        "Customer Name": None,
        "Customer Code": None,
        "Firm Start": None,
        "Firm End": None,
    }

    try:
        text = page.extract_text() or ""

        # Purchase Schedule
        match_schedule = re.search(r"Purchase Schedule No\.?:\s*(\S+)", text, re.IGNORECASE)
        if match_schedule:
            header_data["Purchase Schedule No"] = match_schedule.group(1)

        # Firm Period
        match_firm = re.search(r"Firm Period\s*:\s*(.+)", text)
        if match_firm:
            firm_period = match_firm.group(1).strip()
            header_data["Firm Period"] = firm_period
            start_str, end_str = firm_period.split(" to ")
            header_data["Firm Start"] = datetime.datetime.strptime(start_str.strip(), "%d-%m-%Y")
            header_data["Firm End"] = datetime.datetime.strptime(end_str.strip(), "%d-%m-%Y")

        # Customer
        for name, code in customer_lib.items():
            if name in text:
                header_data["Customer Name"] = name
                header_data["Customer Code"] = code
                break

    except Exception as e:
        print(f"⚠️ Error reading PDF header: {e}")

    return header_data

# ==============================
# PART EXTRACTION
# ==============================
def extract_part(page, page_no=1):
    partdetails = []
    table = page.extract_table()
    if not table:
        return partdetails

    for row_idx, row in enumerate(table[1:], start=1):  # skip header row
        if row and row[0]:
            parts = row[0].split("\n")
            if len(parts) == 2:
                part_desc, part_num = parts[0].strip(), parts[1].strip()
                partdetails.append({
                    "page": page_no,
                    "row": row_idx,
                    "part_desc": part_desc,
                    "part_num": part_num,
                    "qty_img": None,
                    "qty_ocr": None,
                    "qty_values": None,
                })
    return partdetails

# ==============================
# CROP HELPERS
# ==============================
def percent_bbox(page, x0_pct, top_pct, x1_pct, bottom_pct):
    """
    Convert percentage values into absolute bbox.
    """
    x0 = page.width * x0_pct
    x1 = page.width * x1_pct
    top = page.height * (1 - top_pct)
    bottom = page.height * (1 - bottom_pct)
    return (x0, top, x1, bottom)

def crop_region(page, bbox_pct=(0.285, 0.75, 0.81, 0.25)):
    """
    Crop region defined in percentages and return CroppedPage.
    """
    bbox = percent_bbox(page, *bbox_pct)
    cropped_page = page.crop(bbox)
    print(f"✅ Cropped region (bbox={bbox})")
    return cropped_page

# ==============================
# OCR HELPER (ROW → 16 COLS)
# ==============================
def ocr_row_by_cells(row_img_path, num_cols=16, pad=3):
    """
    Split row image into equal 16 columns, OCR each cell.
    Blank = '0'. Pad allows tuning column width.
    """
    img = cv2.imread(row_img_path, cv2.IMREAD_GRAYSCALE)
    h, w = img.shape
    cell_width = w // num_cols

    results = []
    for i in range(num_cols):
        x0 = max(i * cell_width - pad, 0)
        x1 = min((i+1) * cell_width + pad, w)
        cell = img[0:h, x0:x1]

        text = pytesseract.image_to_string(cell, config="--psm 7 digits").strip()
        if text == "":
            results.append("0")
        else:
            results.append(re.sub(r"\D", "", text))  # keep digits only

    return results

# ==============================
# CROP ROWS + OCR COLUMNS
# ==============================
def crop_qty_rows(cropped_page, partdetails, page_num=1, out_dir="rows_out", num_cols=16, pad=3):
    os.makedirs(out_dir, exist_ok=True)

    parts_for_page = [p for p in partdetails if p["page"] == page_num]
    if not parts_for_page:
        print(f"⚠️ No part rows detected for page {page_num}")
        return partdetails

    expected_rows = 13
    row_height = cropped_page.height / expected_rows
    x0, y0, x1, y1 = cropped_page.bbox

    # ==============================
    # CONFIGURATION
    # ==============================
    ROW_TOP_OFFSET = -2       # adjust overlap: negative shrinks top, positive expands
    ROW_BOTTOM_OFFSET = 2     # adjust overlap: positive shrinks bottom, negative expands

    FIRM_RATIO = 0.50         # default: cut row in half (50%). Adjust if Firm is not exactly half
    FIRM_TOP_OFFSET = 0       # trim inside firm crop from the top
    FIRM_BOTTOM_OFFSET = 0    # trim inside firm crop from the bottom
    # ==============================

    new_partdetails = []

    # loop over detected part numbers, position on fixed 13-row grid
    for idx, part in enumerate(parts_for_page):
        row_idx = expected_rows - idx - 1

        top = y1 - row_idx * row_height
        bottom = y1 - (row_idx + 1) * row_height

        # clamp with offsets
        row_bottom = max(bottom + ROW_BOTTOM_OFFSET, y0)
        row_top = min(top + ROW_TOP_OFFSET, y1)

        if row_top <= row_bottom:
            print(f"⚠️ Skipping invalid row {idx+1}")
            continue

        row_bbox = (x0, row_bottom, x1, row_top)
        row_img = cropped_page.crop(row_bbox).to_image(resolution=300)

        # Save full row image
        row_file = f"{out_dir}/page{page_num}_row{idx+1}.png"
        row_img.save(row_file, format="PNG")

        # Load row into cv2
        img = cv2.imread(row_file, cv2.IMREAD_GRAYSCALE)
        h, w = img.shape

        # Firm crop (top half)
        half_h = int(h * FIRM_RATIO)
        y0_f = max(0, FIRM_TOP_OFFSET)
        y1_f = max(0, half_h - FIRM_BOTTOM_OFFSET)
        if y1_f <= y0_f:
            print(f"⚠️ Skipping firm crop for row {idx+1}, invalid bounds")
            continue

        firm_img = img[y0_f:y1_f, :]

        # Save Firm-only image
        firm_file = f"{out_dir}/page{page_num}_row{idx+1}_firm.png"
        cv2.imwrite(firm_file, firm_img)

        # Folder for firm columns
        row_folder = f"{out_dir}/page{page_num}_row{idx+1}_firm"
        os.makedirs(row_folder, exist_ok=True)

        # Split into columns + OCR
        cell_width = w // num_cols
        values = []
        for col_idx in range(num_cols):
            cx0 = max(col_idx * cell_width - pad, 0)
            cx1 = min((col_idx + 1) * cell_width + pad, w)
            cell = firm_img[:, cx0:cx1]

            col_file = f"{row_folder}/col{col_idx+1}.png"
            cv2.imwrite(col_file, cell)

            text = pytesseract.image_to_string(cell, config="--psm 7 digits").strip()
            values.append(re.sub(r"\D", "", text) if text else "0")

        # Update part info directly
        qty_str = "|".join(values)
        part["qty_img"] = firm_file
        part["qty_values"] = values
        part["qty_ocr"] = qty_str

        new_partdetails.append(part)

        # ✅ Print with actual OCR values
        print(f"✅ Page {page_num} Row {idx+1} Firm OCR: {qty_str}")

    return new_partdetails


def expand_to_db_rows(header, partdetails):
    """
    Explanation of this function:
    Transform the extracted parts into database-ready records.
    Each quantity value (qty_values[n]) corresponds to a date 
    in the Firm Period range. 
    The result can be inserted into a SQL table later.
    """

    records = []

    # Get firm start and end dates from header
    start_date = header.get("Firm Start")
    end_date = header.get("Firm End")

    # Validate header dates (check if found in header)
    if not start_date or not end_date:
        print("⚠️ Missing Firm period, skipping date expansion")
        return []

    # --------------------------------------------
    # 🔍 Step 1: Create a list of all dates in the firm period
    # --------------------------------------------
    # Example: 2025-10-01 → 2025-10-15
    # datetime.timedelta(days=i) adds i days to start_date
    # .date() converts to just date (without time)
    # --------------------------------------------
    date_range = [
        (start_date + datetime.timedelta(days=i)).date()
        for i in range((end_date - start_date).days + 1)
    ]

    # --------------------------------------------
    # 🔍 Step 2: Loop through each part
    # --------------------------------------------
    for part in partdetails:
        qty_values = part.get("qty_values", [])

        # Loop through each date + index
        for idx, current_date in enumerate(date_range):

            # Match quantity by index position
            # if there are fewer qty_values than dates, default to 0
            qty = str(qty_values[idx]) if idx < len(qty_values) else "0"

            # Build one complete record for this date & part
            record = {
                "PurchaseSchedule": header.get("Purchase Schedule No"),
                "Date": current_date.strftime("%Y-%m-%d"),
                "CustomerName": header.get("Customer Name"),
                "CustomerCode": header.get("Customer Code"),
                "PartDesc": part.get("part_desc"),   # ✅ FIXED
                "PartNum": part.get("part_num"),     # ✅ FIXED
                "Qty": qty,
            }

            records.append(record)

    return records

# ==============================
# MAIN
# ==============================
def main():
    pdf_path = r"DI_02.pdf"
    all_partdetails = []

    with pdfplumber.open(pdf_path) as pdf:
        header = None

        for page_num, page in enumerate(pdf.pages, start=1):
            print(f"\n📄 Processing Page {page_num}")

            # Step 1: Header (first page only)
            if page_num == 1:
                header = extract_header(page, customer)
                print("📄 Header Data:")
                for k, v in header.items():
                    print(f"{k}: {v}")

            # Step 2: Extract part numbers
            partdetails = extract_part(page, page_no=page_num)

            if not partdetails:
                print(f"⚠️ No parts found on page {page_num}, skipping...")
                continue

            # Step 3: Crop qty region
            cropped_page = crop_region(page)

            # Step 4: Crop rows & OCR columns
            partdetails = crop_qty_rows(
                cropped_page,
                partdetails,
                page_num=page_num,
                num_cols=16,
                pad=3
            )

            all_partdetails.extend(partdetails)

    # Show sample
    print("\n📊 Final Results (first 5):")
    for p in all_partdetails[:5]:
        print(p)

    # Optional: Save to CSV for inspection
    df = pd.DataFrame(all_partdetails)
    df.to_csv("output.csv", index=False)
    print("✅ Saved all results to output.csv")

    # Transform for database and show direct in database
    db_rows = expand_to_db_rows(header, all_partdetails)

    # Show database-ready structure in terminal
    df_db = pd.DataFrame(db_rows)                   # Create DataFrame from db_rows using pandas built-in function DataFrame(Need to check the logic and usage) !!!!
    print("\n📊 DATABASE-READY STRUCTURE PREVIEW:")
    print(df_db.head(20).to_markdown(index=False))
    print(f"\nTotal records: {len(df_db)} rows")



    


if __name__ == "__main__":
    main()
