from pathlib import Path

root = Path(r"C:\Users\teert\OneDrive\Documents\Teerth Projects\Uber nyc TLC Dataset")

clear_roots = [
    root / "algorithms",
    root / "models",
    root / "rag",
    root / "backend",
    root / "frontend" / "src",
    root / "tests",
]

replacements = {
    ".py": "# TODO: implement this module from scratch.\n",
    ".jsx": "export default function Placeholder() {\n  return <div>TODO: implement me</div>;\n}\n",
    ".js": "export default function Placeholder() {\n  return <div>TODO: implement me</div>;\n}\n",
    ".css": "/* TODO: implement styles */\n",
    ".html": "<!doctype html>\n<html>\n  <body>TODO: implement the UI.</body>\n</html>\n",
    ".md": "# TODO\n",
    ".sql": "-- TODO: implement the SQL logic.\n",
}

count = 0
for base in clear_roots:
    if not base.exists():
        continue
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "package.json":
            continue
        suffix = path.suffix.lower()
        if suffix in {".ipynb", ".pt", ".pkl"}:
            path.unlink(missing_ok=True)
            count += 1
            continue
        if suffix in replacements:
            path.write_text(replacements[suffix], encoding="utf-8")
            count += 1
        else:
            path.write_text("TODO\n", encoding="utf-8")
            count += 1

print(f"Cleared {count} files")
