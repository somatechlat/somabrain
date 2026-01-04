"""Module auto_doc."""


import os
import ast
import sys
import re

def to_camel_case(snake_str):
    """Execute to camel case.

        Args:
            snake_str: The snake_str.
        """

    return "".join(x.capitalize() for x in snake_str.lower().split("_"))

def generate_docstring(node, type_):
    """Execute generate docstring.

        Args:
            node: The node.
            type_: The type_.
        """

    name = node.name
    # Clean name
    clean_name = name.lstrip("_")
    words = clean_name.split("_")
    
    if type_ == "Module":
        return f'"""Module providing {clean_name} functionality."""'
    
    if type_ == "Class":
        # Check for specific patterns
        if "Request" in name or "Response" in name:
            return f'"""Data model for {clean_name}."""'
        if "Exception" in name or "Error" in name:
            return f'"""Exception raised for {clean_name}."""'
        return f'"""{to_camel_case(name)} class implementation."""'

    if type_ == "Function":
        desc = "Execute"
        if name.startswith("get_"):
            desc = "Retrieve"
            clean_name = " ".join(words[1:])
        elif name.startswith("set_"):
            desc = "Set"
            clean_name = " ".join(words[1:])
        elif name.startswith("is_") or name.startswith("has_"):
            desc = "Check if"
            clean_name = " ".join(words[1:])
        elif name == "__init__":
            return '"""Initialize the instance."""'
        elif name == "__str__":
            return '"""Return string representation."""'
        elif name == "__repr__":
            return '"""Return object representation."""'
        
        args = [a.arg for a in node.args.args if a.arg != 'self' and a.arg != 'cls']
        
        doc = f'"""{desc} {clean_name.replace("_", " ")}.'
        
        if args:
            doc += '\n\n    Args:'
            for arg in args:
                doc += f'\n        {arg}: The {arg}.'
        
        # Check for return structure (naive)
        doc += '\n    """'
        return doc

class DocstringInjector(ast.NodeTransformer):
    """Docstringinjector class implementation."""

    def __init__(self, source_lines):
        """Initialize the instance."""

        self.source_lines = source_lines
        self.changes = [] # List of (line_index, text)
    
    def visit_Module(self, node):
        """Execute visit Module.

            Args:
                node: The node.
            """

        if not ast.get_docstring(node):
            self.changes.append((0, generate_docstring(node, "Module")))
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node):
        """Execute visit FunctionDef.

            Args:
                node: The node.
            """

        if not ast.get_docstring(node):
            # Find the line after def
            # This is tricky with decorators. source_lines[node.lineno-1] is the def line usually
            # We want to insert after the def line and indentation
            indent = self.get_indentation(node.lineno)
            doc = generate_docstring(node, "Function")
            # Indent the docstring
            doc_indented = "\n".join(indent + "    " + line if line else "" for line in doc.split("\n"))
            self.changes.append((node.body[0].lineno - 1, doc_indented)) # Insert before first body statement? No.
            # Inserting as the first statement of the body is safer.
        self.generic_visit(node)
        return node
    
    def visit_AsyncFunctionDef(self, node):
        """Execute visit AsyncFunctionDef.

            Args:
                node: The node.
            """

        self.visit_FunctionDef(node)
        return node

    def visit_ClassDef(self, node):
        """Execute visit ClassDef.

            Args:
                node: The node.
            """

        if not ast.get_docstring(node):
            indent = self.get_indentation(node.lineno)
            doc = generate_docstring(node, "Class")
            doc_indented = "\n".join(indent + "    " + line if line else "" for line in doc.split("\n"))
            self.changes.append((node.body[0].lineno - 1, doc_indented))
        self.generic_visit(node)
        return node

    def get_indentation(self, lineno):
        """Retrieve indentation.

            Args:
                lineno: The lineno.
            """

        line = self.source_lines[lineno - 1]
        return line[:len(line) - len(line.lstrip())]

def process_file(filepath):
    """Execute process file.

        Args:
            filepath: The filepath.
        """

    with open(filepath, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    source_lines = source_code.splitlines()
    
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        print(f"Skipping {filepath}: SyntaxError")
        return

    # We can't really use NodeTransformer for text insertion easily without messing up formatting.
    # Better approach: Collect insertion points and text, then reconstruct.
    
    insertions = [] # (lineno (0-indexed insertion point), text)
    
    missing_module = True
    if ast.get_docstring(tree):
        missing_module = False
    
    if missing_module:
        insertions.append((0, f'"""Module {os.path.basename(filepath).replace(".py", "")}."""\n'))

    for node in ast.walk(tree):
         if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
             if not ast.get_docstring(node):
                 # Where to insert?
                 # Start of body
                 body_start_line = node.body[0].lineno - 1
                 
                 # Determine indentation from the def line
                 # node.lineno is 1-indexed
                 def_line = source_lines[node.lineno - 1]
                 indent = def_line[:len(def_line) - len(def_line.lstrip())] + "    "
                 
                 type_ = "Class" if isinstance(node, ast.ClassDef) else "Function"
                 ds = generate_docstring(node, type_)
                 
                 # Format docstring with indentation
                 ds_lines = ds.split('\n')
                 formatted_ds = indent + ds_lines[0] # First line has indentation
                 for l in ds_lines[1:]:
                     formatted_ds += '\n' + (indent + l if l else '')
                 formatted_ds += '\n'
                 
                 insertions.append((body_start_line, formatted_ds))
                 
    # Apply insertions in reverse order to keep lineno valid
    insertions.sort(key=lambda x: x[0], reverse=True)
    
    for lineno, text in insertions:
        source_lines.insert(lineno, text)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("\n".join(source_lines))
    print(f"Fixed {filepath}")

def scan_and_fix(root_dir):
    """Execute scan and fix.

        Args:
            root_dir: The root_dir.
        """

    exclude_dirs = {'.git', '.venv', 'venv', '__pycache__', 'docs', 'node_modules', 'dist', 'build', '.idea', '.vscode'}
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith(".py"):
                process_file(os.path.join(root, file))

if __name__ == "__main__":
    scan_and_fix(sys.argv[1])