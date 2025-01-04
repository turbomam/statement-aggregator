import csv
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

import click

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def detect_file_type(filepath: Path) -> str:
    """
    Detects the file type based on its extension.

    Args:
        filepath: The path to the file.

    Returns:
        "csv" or "tsv" if the extension is recognized, otherwise raises ValueError.
    """
    if filepath.suffix.lower() == ".csv":
        return "csv"
    elif filepath.suffix.lower() == ".tsv":
        return "tsv"
    else:
        raise ValueError(f"Unsupported file type: {filepath.suffix}")


def read_file(filepath: Path) -> Tuple[List[str], List[List[str]]]:
    """
    Reads a CSV or TSV file and returns its header and data rows.

    Args:
        filepath: The path to the file.

    Returns:
        A tuple containing the header (list of column names) and data rows (list of lists).
    """
    filetype = detect_file_type(filepath)
    logging.info(f"Reading {filetype} file: {filepath}")

    with open(filepath, "r", encoding="utf-8") as file:
        if filetype == "csv":
            reader = csv.reader(file)
        else:  # tsv
            reader = csv.reader(file, delimiter="\t")
        header = next(reader)  # Read the header row
        data = list(reader)
    return header, data


def write_tsv(filepath: Path, header: List[str], data: List[List[str]]):
    """
    Writes data to a TSV file.

    Args:
        filepath: The path to the output file.
        header: The header row (list of column names).
        data: The data rows (list of lists).
    """
    logging.info(f"Writing to TSV file: {filepath}")

    with open(filepath, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, delimiter="\t")
        writer.writerow(header)
        writer.writerows(data)


@click.command()
@click.option(
    "-o",
    "--output",
    "output_filepath",
    required=True,
    type=click.Path(path_type=Path),
    help="Path to the output TSV file.",
)
@click.argument("input_filepaths", required=True, nargs=-1, type=click.Path(exists=True, path_type=Path))
def aggregate_statements(output_filepath: Path, input_filepaths: List[Path]):
    """
    Aggregates bank and insurance statements from multiple CSV or TSV files into a single TSV file, removing duplicates.
    It also reports the number of input and output rows and logs any column composition differences between input files.

    INPUT_FILEPATHS: An open ended number of input files.
    """

    all_data: Set[Tuple[str, ...]] = set()
    column_diffs: List[Tuple[str, str]] = []
    first_file_header: List[str] = []
    total_input_rows = 0
    total_output_rows = 0

    # Create a set to store headers and quickly check for differences
    headers_set: Set[Tuple[str, ...]] = set()

    for filepath in input_filepaths:
        try:
            header, data = read_file(filepath)
            total_input_rows += len(data)

            # Convert to tuples for set operations
            header_tuple = tuple(header)

            # Check if the header is different from the first file's header
            if not first_file_header:
                first_file_header = header
            elif header_tuple != tuple(first_file_header):
                # Track column differences
                headers_set.add(header_tuple)
                for i, column in enumerate(header):
                    if i >= len(first_file_header) or column != first_file_header[i]:
                        column_diffs.append((filepath.name, column))

            # Add data rows to the set (duplicates are automatically handled)
            for row in data:
                all_data.add(tuple(row))

        except Exception as e:
            logging.error(f"Error processing {filepath}: {e}")

    total_output_rows = len(all_data)

    # Write the aggregated data to a new TSV file
    if all_data:
        write_tsv(output_filepath, first_file_header, [list(row) for row in all_data])

    # Log the column differences
    if column_diffs:
        logging.warning("Column composition differences found:")
        for filename, column_name in column_diffs:
            logging.warning(f"  {filename}: {column_name}")
    else:
        logging.info("All input files have the same column composition.")

    # Log number of rows
    logging.info(f"Total input rows: {total_input_rows}")
    logging.info(f"Total output rows (after deduplication): {total_output_rows}")

    # Report unique headers
    if len(headers_set) > 0:
        logging.warning(f"Found {len(headers_set)} unique headers (in addition to the first file's header):")
        for header in headers_set:
            logging.warning(f"  {header}")


if __name__ == "__main__":
    aggregate_statements()
