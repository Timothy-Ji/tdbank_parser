# tdbank_parser

Quick project to help with parsing TD bank statements.

## Structure
- `src/` - Source code directory
- `main.py` - Entry point
- `requirements.txt` - Python dependencies

## Usage
Install dependencies:
```bash
pip install -r requirements.txt
```

Run the main script:
```bash
Parse to CSV
python src/tdparsetocsv.py
```

Virtual environment (recommended):

Create the venv (already created in this project as `.venv`):

```bash
python3 -m venv .venv
```

Activate it:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Windows (cmd.exe)
.\.venv\Scripts\activate.bat
```

Then install dependencies into the venv:

```bash
pip install -r requirements.txt
```
