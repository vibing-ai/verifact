#!/usr/bin/env python3
import os
import re
import sys


def remove_unused_imports(file_path):
    """Remove unused imports identified by ruff F401 errors."""
    # Run ruff to identify unused imports
    import subprocess

    result = subprocess.run(
        ["ruff", "check", "--select=F401,F811", file_path], capture_output=True, text=True
    )

    if not result.stdout:
        print(f"No unused imports found in {file_path}")
        return

    # Extract the unused imports from ruff output
    unused_imports = []
    for line in result.stdout.split("\n"):
        if not line:
            continue

        if "F401" in line or "F811" in line:
            parts = line.split("'")
            if len(parts) >= 3:
                unused_import = parts[1]
                unused_imports.append(unused_import)

    if not unused_imports:
        print(f"No actionable unused imports found in {file_path}")
        return

    # Read the file
    with open(file_path) as f:
        content = f.read()

    # Process lines to remove unused imports
    lines = content.split("\n")
    new_lines = []

    for line in lines:
        skip_line = False

        # Check if this line has an unused import
        for unused_import in unused_imports:
            if re.search(
                rf"\bfrom\s+.+\s+import\s+.*\b{re.escape(unused_import)}\b", line
            ) or re.search(rf"\bimport\s+.*\b{re.escape(unused_import)}\b", line):
                # Handle cases like 'from x import a, b, c'
                if "," in line and "import" in line:
                    # Split the line at the import keyword
                    import_idx = line.find("import")
                    if import_idx > 0:
                        before_import = line[: import_idx + 6]  # 'import' is 6 chars
                        after_import = line[import_idx + 6 :]

                        # Parse what's being imported
                        imports = [i.strip() for i in after_import.split(",")]
                        new_imports = [i for i in imports if unused_import not in i]

                        if new_imports:
                            # Rebuild the import line without the unused import
                            new_line = before_import + ", ".join(new_imports)
                            new_lines.append(new_line)
                        else:
                            # All imports on this line are unused
                            skip_line = True
                else:
                    skip_line = True
                break

        if not skip_line:
            new_lines.append(line)

    # Write back to the file
    with open(file_path, "w") as f:
        f.write("\n".join(new_lines))

    print(f"Cleaned {len(unused_imports)} unused imports in {file_path}")


def process_directory(directory):
    """Process all Python files in a directory and its subdirectories."""
    for root, _dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                print(f"Processing {file_path}...")
                remove_unused_imports(file_path)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
        if os.path.isdir(target):
            process_directory(target)
        elif os.path.isfile(target) and target.endswith(".py"):
            remove_unused_imports(target)
        else:
            print(f"Error: {target} is not a Python file or directory")
    else:
        print("Usage: python clean_imports.py <file_or_directory>")
