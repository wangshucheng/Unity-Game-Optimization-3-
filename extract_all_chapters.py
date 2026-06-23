from pypdf import PdfReader
import re
import sys

PDF = "Unity Game Optimization - Third Edition.pdf"
READER = PdfReader(PDF)


def clean_text(text):
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # remove page footer like [ 123 ]
        if re.match(r"^\[\s*\d+\s*\]$", stripped):
            continue
        # remove standalone chapter number at top of page
        if re.match(r"^\d+$", stripped):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def extract_chapter(start_pdf, end_pdf, output_file):
    output = []
    for i in range(start_pdf - 1, end_pdf):
        try:
            text = READER.pages[i].extract_text()
        except Exception as e:
            print(f"Error extracting page {i+1}: {e}")
            text = ""
        if not text:
            continue
        cleaned = clean_text(text)
        output.append(f"\n\n=== PDF page {i + 1} ===\n\n")
        output.append(cleaned)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("".join(output))
    print(f"Extracted pages {start_pdf}-{end_pdf} to {output_file}")


# Actual PDF page numbers, derived from Table of Contents + 16 offset
CHAPTERS = {
    "1": ("chapter1_raw.txt", 24, 60),
    "2": ("chapter2_raw.txt", 61, 121),
    "3": ("chapter3_raw.txt", 122, 141),
    "4": ("chapter4_raw.txt", 142, 172),
    "5": ("chapter5_raw.txt", 173, 208),
    "6": ("chapter6_raw.txt", 209, 260),
    "7": ("chapter7_raw.txt", 261, 275),
    "8": ("chapter8_raw.txt", 276, 336),
    "9": ("chapter9_raw.txt", 337, 360),
    "10": ("chapter10_raw.txt", 361, 381),
}

chapter = sys.argv[1]
output, start, end = CHAPTERS[chapter]
extract_chapter(start, end, output)
