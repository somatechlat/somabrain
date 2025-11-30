import re, sys, pathlib

repo_root = pathlib.Path(__file__).parent

logger_import_line = 'from common.logging import logger'

def ensure_logger_import(content: str) -> str:
    if logger_import_line in content:
        return content
    # Find the last import line
    lines = content.splitlines()
    import_idx = -1
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            import_idx = i
    # Insert after the last import
    if import_idx >= 0:
        lines.insert(import_idx + 1, logger_import_line)
    else:
        # No imports, insert at top
        lines.insert(0, logger_import_line)
    return '\n'.join(lines) + '\n'

def replace_except_raise(content: str) -> str:
    """Replace bare `except Exception: raise` with logged raise blocks."""
    pattern1 = re.compile(r'except\s+Exception\s*:\s*raise(?:\s*#.*)?')
    pattern2 = re.compile(r'except\s+Exception\s+as\s+(\w+)\s*:\s*raise(?:\s*#.*)?')

    def repl1(match):
        return 'except Exception as exc:\\n    logger.exception("Exception caught: %s", exc)\\n    raise'

    def repl2(match):
        var = match.group(1)
        return f'except Exception as {var}:\\n    logger.exception("Exception caught: %s", {var})\\n    raise'

    content = pattern2.sub(repl2, content)
    content = pattern1.sub(repl1, content)
    return content

for py_path in repo_root.rglob('*.py'):
    try:
        text = py_path.read_text()
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
    new_text = replace_except_raise(text)
    new_text = ensure_logger_import(new_text)
    if new_text != text:
        py_path.write_text(new_text)
        print(f'Updated {py_path}')
