import html
from markdown import markdown
evd = """```
[Click me](javascript:alert(1))
```"""
escaped_evd = html.escape(evd)
markdown_content = f"""
  - evd:
    ```
    {escaped_evd}
    ```
"""
print(markdown(markdown_content, extensions=['fenced_code']))
