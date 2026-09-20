"""Helper to build notebooks programmatically as nbformat JSON, then they are executed
with jupyter nbconvert --execute. Not itself a notebook."""
import nbformat as nbf


def build(cells, path):
    nb = nbf.v4.new_notebook()
    nb['cells'] = cells
    nb['metadata'] = {
        'kernelspec': {'display_name': 'Python 3 (ml venv)', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python', 'version': '3.10'},
    }
    with open(path, 'w') as f:
        nbf.write(nb, f)
    print(f"wrote {path}")


def md(text):
    return nbf.v4.new_markdown_cell(text)


def code(text):
    return nbf.v4.new_code_cell(text)
