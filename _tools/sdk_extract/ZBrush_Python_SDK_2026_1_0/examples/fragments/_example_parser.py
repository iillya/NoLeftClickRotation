"""Contains a tool to extract code examples embedded in modules.
"""
import ast
import os
import typing
import re

HEADER: str = '''"""Code fragment for {}.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"
'''

PATH_PREFIX: str = "/../../examples/fragments"

class PyExampleParser:
    """A parser for extracting examples from Python code."""

    def __init__(self, file: str, output_dir: str, prefix: str) -> None:
        """Initializes the parser with the given Python file.
        """
        self.file: str = str(file)
        self.output_dir: str = str(output_dir)
        self.prefix: str = str(prefix)
        if not os.path.isfile(self.file):
            raise FileNotFoundError(f"File not found: {self.file}")
        
        if not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir)
        
        with open(self.file, "r", encoding="utf-8") as f:
            self.code: str = self.preprocess_file(f.read())
        
        self.out_file: str = self.file.replace(".py", "_parsed.py")
        self.tree: ast.Module = ast.parse(self.code)
        self.new_code: str = self.code
        self.lines: list[str] = self.code.splitlines()
        self.max_index: int = len(self.lines)
        
    def preprocess_file(self, content: str) -> str:
        """Preprocesses the file by removing leading/trailing empty lines in doc strings.
        """
        return re.sub(r'"""\s*(?!\s*(?:def|class|\.\.\.))', r'"""', content)

    def iter_items(self) -> typing.Iterator[tuple[str, str, ast.AST]]:
        """Yields all relevant descriptions found in the AST with their entity names and nodes.
        """
        node: ast.AST
        visited: set[ast.AST] = set()
        for node in ast.walk(self.tree):
            if node in visited:
                continue

            visited.add(node)
            if isinstance(node, ast.ClassDef):
                for child in (c for c in node.body if isinstance(c, ast.FunctionDef)):
                    visited.add(child)
                    yield f"{node.name}.{child.name}", ast.get_docstring(child) or "", child
            elif isinstance(node, ast.FunctionDef):
                yield node.name, ast.get_docstring(node) or "", node

    def process_description(self, entity_name: str, description: str, node: ast.AST) -> None:
        """Processes a single description, potentially modifying it."""
        if not description:
            return
        
        def find_example_ranges(index: int) -> typing.Iterator[tuple[int, int]]:
            """Finds the scope of the example in the description.
            """
            count: int = 0
            indent: int = 0
            start: int = -1

            while index < self.max_index:
                line: str = self.lines[index].lower()
                line_strip: str = line.strip()
                if len(line_strip) == 0:
                    index += 1
                    continue

                cur_indent: int = len(line) - len(line_strip)
                isCodeBlock: bool = line_strip.startswith(".. code-block:: python")
                isCommentEnd: bool = line_strip == '"""'

                if isCodeBlock:
                    start = index
                    indent = cur_indent

                if start != -1 and index != start and (cur_indent <= indent):
                    yield count, start, index
                    count += 1
                    start = -1
                    
                if isCommentEnd:
                    return
                
                index += 1
        
        def save_example(start: int, end: int, entity_name: str, count: int) -> None:
            """Saves the example code to a separate file and modifies the original description.
            """
            lines: list[str] = self.lines[start + 1:end]
            min_indent: int = min((len(line) - len(line.lstrip()) 
                                   for line in lines if line.strip()), default=0)
            entity_name: str = f"{self.prefix}.{entity_name}"
            header: str = HEADER.format(entity_name)
            code: str = header + "\n".join(line[min_indent:] if line else line for line in lines)

            name: str = f"{entity_name}.{count}.py".lower()
            file: str = os.path.join(self.output_dir, name)
            if os.path.exists(file):
                raise FileExistsError(f"File already exists: {file}")
            
            with open(file, "w", encoding="utf-8") as f:
                f.write(code)
            
            indent: str = " " * (max(min_indent - 4, 0))
            old : str = "\n".join(self.lines[start:end])
            new: str = (f"{indent}.. literalinclude:: {PATH_PREFIX}/{name}\n{indent}    :language: "
                        f"python\n{indent}    :lines: 7-\n")
            self.new_code = self.new_code.replace(old, new)
        
        index: int = node.lineno
        for i, start, end in find_example_ranges(index):
            save_example(start, end, entity_name, i)
    
    def run(self):
        """Run the parser and print extracted information.
        """
        for name, description, node in self.iter_items():
            self.process_description(name, description, node)

        with open(self.out_file, "w", encoding="utf-8") as f:
            f.write(self.new_code)
    
if __name__ == "__main__":
    # Delete all existing fragments first.
    for f in os.listdir("/Users/f_hoppe/git/zbrush-sdk/examples/fragments/"):
        os.remove(os.path.join("/Users/f_hoppe/git/zbrush-sdk/examples/fragments/", f))

    # Process all relevant files.
    for path, domain in [
        ("/Users/f_hoppe/git/zbrush-sdk/api/zbrush/commands.py", "zbrush.commands"),
        ("/Users/f_hoppe/git/zbrush-sdk/api/zbrush/utils.py", "zbrush.utils"),
        ("/Users/f_hoppe/git/zbrush-sdk/api/zbrush/zscript_compatibility.py", "zbrush.zscript_compatibility")]:
        parser = PyExampleParser(path, "/Users/f_hoppe/git/zbrush-sdk/examples/fragments/", domain)
        parser.run()