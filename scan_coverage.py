"""Module scan_coverage."""


import os
import ast
import sys

def check_file(filepath):
    """Execute check file.

        Args:
            filepath: The filepath.
        """

    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
        except SyntaxError:
            return []
    
    missing = []
    
    # Check module docstring
    if not ast.get_docstring(tree):
        missing.append((1, "Module", "Missing module docstring"))

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_") and node.name != "__init__":
                continue # Skip private methods (optional, but good for noise reduction if strictly public APIs)
            if not ast.get_docstring(node):
                missing.append((node.lineno, f"Function '{node.name}'", "Missing docstring"))
        elif isinstance(node, ast.ClassDef):
            if not ast.get_docstring(node):
                missing.append((node.lineno, f"Class '{node.name}'", "Missing docstring"))

    return missing

def scan_repo(root_dir):
    """Execute scan repo.

        Args:
            root_dir: The root_dir.
        """

    report = {}
    total_files = 0
    total_issues = 0
    
    exclude_dirs = {'.git', '.venv', 'venv', '__pycache__', 'docs', 'node_modules', 'dist', 'build', '.idea', '.vscode'}

    for root, dirs, files in os.walk(root_dir):
        # Modify dirs in-place to skip excluded directories
        # print(f"DEBUG: Checking {root}, Dirs: {dirs}")
        original_dirs = list(dirs)
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        # if len(dirs) != len(original_dirs):
        #    print(f"DEBUG: Excluded {[d for d in original_dirs if d not in dirs]}")
        
        for file in files:
            if file.endswith(".py") and file != "__init__.py": # Skip empty inits checks, they are often just for packaging
                filepath = os.path.join(root, file)
                issues = check_file(filepath)
                if issues:
                    report[filepath] = issues
                    total_issues += len(issues)
                total_files += 1
                
    return report, total_files, total_issues

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scan_coverage.py <repo_root>")
        sys.exit(1)
        
    repo_root = sys.argv[1]
    print(f"Scanning {repo_root}...")
    report, files, issues = scan_repo(repo_root)
    
    for filepath, file_issues in report.items():
        rel_path = os.path.relpath(filepath, repo_root)
        for line, target, msg in file_issues:
             print(f"{rel_path}:{line} - {target}: {msg}")
             
    print(f"\nSummary: Scanned {files} files. Found {issues} missing docstrings.")