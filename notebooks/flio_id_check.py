"""Scan a folder for measurement_info.html files and report any with an invalid patient ID.

A valid ID looks like "AIREADI, xxxx", where xxxx is four digits and the
first digit is one of 1, 2, 4, 5, 7 or 8.

Usage:
    python qc/patient_id_qc.py [-o report.csv] [-u unique.csv] [-w workers]
"""

import argparse
import csv
import os
import re
from multiprocessing import Pool

from tqdm import tqdm

INPUT_FOLDER = r"F:\flio_raw"
HTML_NAME = "measurement_info.html"

ID_CELL = re.compile(r'<td class="patient_info_row"[^>]*>\s*(AIREADI[^<]*?)\s*</td>')
VALID_ID = re.compile(r"^AIREADI,\s*([124578]\d{3})$")


def iter_files(root):
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.lower() == HTML_NAME:
                yield os.path.join(dirpath, name)


def check_file(path):
    """Return (patient_id, issue) for a file, or None if valid."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            html = f.read()
    except Exception as e:
        return "", f"read error: {e}"

    m = ID_CELL.search(html)
    if m is None:
        return "", "missing patient ID"

    raw = m.group(1)
    if not VALID_ID.match(raw):
        return raw, "invalid format"

    return None


def check_file_with_path(path):
    result = check_file(path)
    return None if result is None else (path, *result)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-o", "--output", default="invalid_patient_ids_F.csv")
    parser.add_argument("-u", "--unique-output", default="invalid_patient_ids_unique_F.csv")
    parser.add_argument("-w", "--workers", type=int, default=os.cpu_count())
    args = parser.parse_args()

    print("Input folder:", INPUT_FOLDER)
    files = list(tqdm(iter_files(INPUT_FOLDER), desc="Scanning", unit=" file"))
    print("Total files:", len(files))

    invalid = 0
    unique = set()
    with open(args.output, "w", newline="", encoding="utf-8-sig") as f, Pool(args.workers) as pool:
        writer = csv.writer(f)
        writer.writerow(["file_path", "patient_id", "issue"])

        results = pool.imap_unordered(check_file_with_path, files, chunksize=8)
        for row in tqdm(results, total=len(files)):
            if row is not None:
                writer.writerow(row)
                invalid += 1
                unique.add(row[1])

    with open(args.unique_output, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["patient_id"])
        writer.writerows([u] for u in sorted(unique))

    print(f"Done. Invalid: {invalid}  Report: {args.output}")
    print(f"Unique patient_id: {len(unique)}  Report: {args.unique_output}")


if __name__ == "__main__":
    main()