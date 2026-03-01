import html
from markdown import markdown
evd = """```
<script>alert(1)</script>
```"""
escaped_evd = html.escape(evd)
markdown_content = f"""
  - evd:
    ```
    {escaped_evd}
    ```
"""
print(markdown(markdown_content, extensions=['fenced_code']))
