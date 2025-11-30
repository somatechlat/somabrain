import os
import re

#!/usr/bin/env python3

def fix_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    changed = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        # match except Exception as exc: or except Exception:
            pass
        if re.match(r'except\s+Exception(\s+as\s+\w+)?\s*:\s*$', stripped):
            base_indent = line[:len(line)-len(stripped)]
            # look ahead to next non-blank line
            j = i+1
            while j < len(lines) and lines[j].strip() == '':
                j += 1
            if j < len(lines):
                next_line = lines[j]
                next_stripped = next_line.lstrip()
                if next_stripped.startswith('logger.exception') or next_stripped.startswith('raise'):
                    desired_indent = base_indent + '    '
                    if not next_line.startswith(desired_indent):
                        lines[j] = desired_indent + next_stripped
                        changed = True
        i += 1
    if changed:
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"Fixed {path}")

def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ''))
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith('.py'):
                fix_file(os.path.join(dirpath, fn))

if __name__ == '__main__':
    main()
