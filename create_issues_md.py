#!/usr/bin/env python3
"""Script to create a markdown file of linting issues from Ruff text output."""

import os
import re
from collections import defaultdict

# Parse the text output from Ruff
issues = []
rule_pattern = re.compile(r"([A-Z]\d+)")
location_pattern = re.compile(r"(.+):(\d+):(\d+): ([A-Z]\d+)(.*)")

with open("ruff_issues.txt") as f:
    for line in f:
        if line.startswith("warning:") or line.strip() == "":
            continue

        match = location_pattern.match(line.strip())
        if match:
            filepath, line_num, col_num, rule_code, message = match.groups()
            issues.append(
                {
                    "filepath": filepath,
                    "line": int(line_num),
                    "column": int(col_num),
                    "rule": rule_code,
                    "message": message.strip(),
                }
            )

# Group issues by file and rule
issues_by_file = defaultdict(list)
issues_by_rule = defaultdict(list)

for issue in issues:
    filepath = issue["filepath"]
    issues_by_file[filepath].append(issue)
    rule_code = issue["rule"]
    issues_by_rule[rule_code].append(issue)

# Create the markdown file
with open("linting_issues.md", "w") as f:
    f.write("# Verifact Linting Issues\n\n")

    # Summary
    f.write("## Summary\n\n")
    f.write(f"Total issues found: {len(issues)}\n\n")

    # Issues by rule type
    f.write("## Issues by Rule\n\n")
    f.write("| Rule | Count | Example |\n")
    f.write("|------|-------|-------------|\n")

    for rule, rule_issues in sorted(issues_by_rule.items(), key=lambda x: len(x[1]), reverse=True):
        # Get the first issue's message as an example
        example = rule_issues[0]["message"] if rule_issues else ""
        f.write(f"| {rule} | {len(rule_issues)} | {example} |\n")

    # Details by file
    f.write("\n## Issues by File\n\n")

    for filepath, file_issues in sorted(
        issues_by_file.items(), key=lambda x: len(x[1]), reverse=True
    ):
        rel_path = os.path.relpath(filepath)
        f.write(f"### {rel_path} ({len(file_issues)} issues)\n\n")

        for issue in sorted(file_issues, key=lambda x: (x["line"], x["column"])):
            line = issue["line"]
            column = issue["column"]
            code = issue["rule"]
            message = issue["message"]

            f.write(f"- **Line {line}:{column}** - {code}: {message}\n")

        f.write("\n")

print(f"Created linting_issues.md with details on {len(issues)} issues")
