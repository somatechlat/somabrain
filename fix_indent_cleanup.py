import os
import re

#!/usr/bin/env python3


def fix_file(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        if re.match(r"\s*except Exception as \w+:\s*$", line):
            # next non-blank line should be logger.exception
            j = i + 1
            # skip blank lines
            while j < len(lines) and lines[j].strip() == "":
                new_lines.append(lines[j])
                j += 1
            if j < len(lines) and re.search(r"logger\.exception", lines[j]):
                # ensure proper indentation (same as except + 4 spaces)
                indent = line[: line.find("except")]
                desired = indent + "    "
                # fix logger line indentation
                if not lines[j].startswith(desired):
                    stripped = lines[j].lstrip()
                    new_lines[-1] = desired + stripped
                # check following line(s)
                k = j + 1
                # skip blanks
                while k < len(lines) and lines[k].strip() == "":
                    new_lines.append(lines[k])
                    k += 1
                if k < len(lines):
                    next_line = lines[k]
                    # if next line is 'raise' and then a return, remove raise
                    if re.match(r"\s*raise\s*$", next_line):
                        # check following line for return
                        l = k + 1
                        while l < len(lines) and lines[l].strip() == "":
                            l += 1
                        if l < len(lines) and re.match(r"\s*return\b", lines[l]):
                            # skip the raise line
                            i = k  # will increment later to l-1
                            # add the return line later normally
                            i = l - 1
                        else:
                            # keep raise line as is
                            pass
                    # if next line is a return without raise, ensure indentation
                    elif re.match(r"\s*return\b", next_line):
                        # ensure proper indent
                        if not next_line.startswith(desired):
                            stripped = next_line.lstrip()
                            new_lines[-1] = desired + stripped
                i = j
        i += 1
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ""))
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(".py"):
                fix_file(os.path.join(dirpath, fn))


if __name__ == "__main__":
    main()
