#!/usr/bin/env python3
"""
Extract Python code from .iqpython files.

Usage:
    python extract_iqpython.py <input.iqpython> [output.py]
    python extract_iqpython.py --all  # Extract all .iqpython files to iqpython/
"""

import json
import sys
import os
from pathlib import Path


def extract_python_code(iqpython_path: str) -> str:
    """Extract the textContent (Python code) from an .iqpython file."""
    with open(iqpython_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    code = data.get('textContent', '')
    # Convert escaped newlines to actual newlines
    code = code.replace('\\n', '\n').replace('\\t', '\t')
    return code


def extract_robot_config(iqpython_path: str) -> dict:
    """Extract the robotConfig from an .iqpython file."""
    with open(iqpython_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('robotConfig', [])


def save_extracted_code(code: str, output_path: str):
    """Save extracted code to a .py file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(code)
    print(f"Extracted: {output_path}")


def extract_all(project_dir: str = None):
    """Extract all .iqpython files in the project to iqpython/ directory."""
    if project_dir is None:
        project_dir = Path(__file__).parent.parent
    else:
        project_dir = Path(project_dir)

    output_dir = project_dir / 'iqpython'
    output_dir.mkdir(exist_ok=True)

    # Find all .iqpython files
    iqpython_files = list(project_dir.glob('*.iqpython'))

    if not iqpython_files:
        print(f"No .iqpython files found in {project_dir}")
        return []

    extracted = []
    for iq_file in iqpython_files:
        # Skip Zone.Identifier files
        if 'Zone.Identifier' in iq_file.name:
            continue

        output_name = iq_file.stem + '.py'
        output_path = output_dir / output_name

        try:
            code = extract_python_code(str(iq_file))
            save_extracted_code(code, str(output_path))
            extracted.append(str(output_path))
        except Exception as e:
            print(f"Error extracting {iq_file}: {e}")

    return extracted


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == '--all':
        project_dir = sys.argv[2] if len(sys.argv) > 2 else None
        extract_all(project_dir)
    else:
        input_path = sys.argv[1]

        if len(sys.argv) > 2:
            output_path = sys.argv[2]
        else:
            # Default: same name with .py extension in iqpython/ dir
            input_file = Path(input_path)
            output_dir = input_file.parent / 'iqpython'
            output_dir.mkdir(exist_ok=True)
            output_path = str(output_dir / (input_file.stem + '.py'))

        code = extract_python_code(input_path)
        save_extracted_code(code, output_path)


if __name__ == '__main__':
    main()
