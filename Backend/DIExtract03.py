import pdfplumber

def clean_cell_firstline(value: str):
    """Return first non-empty line, else 0."""
    if not value:
        return 0
    parts = value.split("\n")
    for p in parts:
        p = p.strip()
        if p:
            try:
                return int(p)
            except:
                return 0
    return 0

def extract_parts_and_DI(pdf_path):
    results = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue

                headers = table[0]  # date headers
                firm_period_cols = headers[2:18]  # firm period col range

                for row in table[2:]:  # skip header rows
                    if not row or not row[0]:
                        continue

                    # Split part name & number
                    parts = row[0].split("\n")
                    if len(parts) == 2:
                        part_name, part_number = parts
                    else:
                        part_name, part_number = parts[0], None

                    # Extract DI quantities
                    di_data = []
                    for i, h in enumerate(firm_period_cols, start=2):  
                        raw_cell = row[i]   # get raw content
                        print(f"DEBUG Row[{i}] Header={h} Raw={repr(raw_cell)}")  # <-- see exact format
                        
                        qty = clean_cell_firstline(raw_cell)
                        di_data.append((h, qty))
                    results.append({
                        "Part Name": part_name.strip(),
                        "Part Number": part_number.strip() if part_number else None,
                        "DI": di_data
                    })
    return results


def main():
    pdf_path = r"DI.pdf"
    data = extract_parts_and_DI(pdf_path)

    for row in data[:5]:
        print(row)


if __name__ == "__main__":
    main()

