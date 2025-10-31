import pdfplumber
import re
from datetime import datetime
import pytesseract
import os
import cv2

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
            header_data["Firm Start"] = datetime.strptime(start_str.strip(), "%d-%m-%Y")
            header_data["Firm End"] = datetime.strptime(end_str.strip(), "%d-%m-%Y")

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
    num_rows = len(parts_for_page)
    if num_rows == 0:
        print("⚠️ No part rows detected for this page")
        return partdetails

    row_height = cropped_page.height / 13
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

    for idx, part in enumerate(parts_for_page):
        row_idx = num_rows - idx - 1
        top = y1 - row_idx * row_height
        bottom = y1 - (row_idx + 1) * row_height

        # ✅ Apply row offsets and clamp
        row_bottom = max(bottom + ROW_BOTTOM_OFFSET, y0)
        row_top    = min(top + ROW_TOP_OFFSET, y1)

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

        # Firm crop (top portion of row)
        half_h = int(h * FIRM_RATIO)
        y0_f = max(0, FIRM_TOP_OFFSET)
        y1_f = max(0, half_h - FIRM_BOTTOM_OFFSET)

        if y1_f <= y0_f:
            print(f"⚠️ Skipping firm crop for row {idx+1}, invalid firm bounds")
            continue

        firm_img = img[y0_f:y1_f, :]

        # Save Firm-only image
        firm_file = f"{out_dir}/page{page_num}_row{idx+1}_firm.png"
        cv2.imwrite(firm_file, firm_img)

        # Folder for firm columns
        row_folder = f"{out_dir}/page{page_num}_row{idx+1}_firm"
        os.makedirs(row_folder, exist_ok=True)

        # Split firm row into columns
        cell_width = w // num_cols
        values = []
        for col_idx in range(num_cols):
            cx0 = max(col_idx * cell_width - pad, 0)
            cx1 = min((col_idx + 1) * cell_width + pad, w)
            cell = firm_img[:, cx0:cx1]

            # Save each column
            col_file = f"{row_folder}/col{col_idx+1}.png"
            cv2.imwrite(col_file, cell)

            # OCR the column
            text = pytesseract.image_to_string(cell, config="--psm 7 digits").strip()
            if text == "":
                values.append("0")
            else:
                values.append(re.sub(r"\D", "", text))

        # Store firm-only details
        new_partdetails.append({
            "page": page_num,
            "row": idx+1,
            "part_desc": part["part_desc"],
            "part_num": part["part_num"],
            "qty_img": firm_file,
            "qty_values": values,
            "qty_ocr": "|".join(values)
        })

        print(f"✅ Page {page_num} Row {idx+1} Firm OCR: {'|'.join(values)}")

    return new_partdetails

# ==============================
# MAIN
# ==============================
def main():
    pdf_path = r"DI.pdf"
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
    import pandas as pd
    df = pd.DataFrame(all_partdetails)
    df.to_csv("output.csv", index=False)
    print("✅ Saved all results to output.csv")


if __name__ == "__main__":
    main()
