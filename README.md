# AI DDR (Detailed Diagnostic Report) Generator

An AI-powered system that ingests inspection reports and thermal documents, extracts and merges observations, handles conflicts and missing data, and outputs a structured client-friendly Detailed Diagnostic Report (DDR).

## Requirements

- Python 3.10+
- Google Gemini API key (free at [Google AI Studio](https://aistudio.google.com/apikey))

## Installation

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your Gemini API key:

```bash
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY=your-key
```

## Usage

### Web App (Recommended)

Start the web server:

```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser. Upload inspection and/or thermal documents, choose output format, and click "Generate Report". Download the report when ready.

### CLI

```bash
python main.py --inspection path/to/inspection.pdf --thermal path/to/thermal.pdf --output ddr_report.md
```

### With sample files

```bash
python main.py --inspection samples/inspection_report.txt --thermal samples/thermal_report.txt --output ddr_report.md
```

### Options

| Option | Description |
|--------|-------------|
| `--inspection` | Path to inspection report (PDF, DOCX, or TXT) |
| `--thermal` | Path to thermal report (PDF, DOCX, or TXT) |
| `--output`, `-o` | Output file path |
| `--format`, `-f` | Output format: `markdown`, `json`, or `html` (default: markdown) |
| `--model`, `-m` | Gemini model (default: gemini-2.0-flash) |
| `--verbose`, `-v` | Print intermediate progress |

### Examples

```bash
# Markdown output (default)
python main.py --inspection samples/inspection_report.txt --thermal samples/thermal_report.txt -o report.md

# JSON output
python main.py --inspection samples/inspection_report.txt --thermal samples/thermal_report.txt -o report.json -f json

# HTML output
python main.py --inspection samples/inspection_report.txt --thermal samples/thermal_report.txt -o report.html -f html

# Verbose mode
python main.py --inspection samples/inspection_report.txt --thermal samples/thermal_report.txt -o report.md -v
```

## Supported Input Formats

- **PDF** – via pdfplumber (with PyPDF2 fallback)
- **DOCX** – via python-docx
- **TXT** – plain text (UTF-8, Latin-1, or CP1252)

## Output Structure

The generated DDR includes seven sections:

1. **Property Issue Summary** – High-level bullet summary
2. **Area-wise Observations** – Grouped by location
3. **Probable Root Cause** – Only when evidence supports it
4. **Severity Assessment** – With reasoning
5. **Recommended Actions** – Prioritized, evidence-based
6. **Additional Notes** – Context and limitations
7. **Missing or Unclear Information** – Explicitly stated as "Not Available" when needed

## Project Structure

```
├── src/
│   ├── parser.py       # Document parsing (PDF, DOCX, TXT)
│   ├── extractor.py    # LLM extraction per document
│   ├── merger.py       # Deduplication, merge, conflict handling
│   ├── generator.py    # DDR generation
│   └── pipeline.py     # Orchestration
├── templates/          # Web app HTML templates
├── static/             # Web app CSS
├── prompts/
│   ├── extraction.yaml
│   └── generation.yaml
├── schemas/
│   └── ddr_schema.json
├── samples/            # Example input documents
├── app.py              # Web app entry point
├── main.py             # CLI entry point
└── requirements.txt
```

## Rules

- Does not invent facts not present in the documents
- Surfaces conflicts when information disagrees
- Uses "Not Available" when information is missing
- Uses simple, client-friendly language
- Designed to work on similar reports, not only sample files
