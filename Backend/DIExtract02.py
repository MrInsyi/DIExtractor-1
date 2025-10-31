import pdfplumber

def extract_parts(pdf_path):
    results = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue

                for row in table[1:]:  # skip header row
                    col0 = row[0]
                    if not col0:
                        continue

                    # Split Part Name and Part Number
                    parts = col0.split("\n")
                    if len(parts) == 2:
                        part_name, part_number = parts
                    else:
                        # if formatting error, keep first as name
                        part_name, part_number = parts[0], None

                    results.append({
                        "Part Name": part_name.strip(),
                        "Part Number": part_number.strip() if part_number else None
                    })
    return results


def main():
    pdf_path = r"DI.pdf"
    parts = extract_parts(pdf_path)
    data = extract_parts

    print("📄 Extracted Part List:")
    for p in parts[:10]:  # preview first 10
        print(p)


if __name__ == "__main__":
    main()
