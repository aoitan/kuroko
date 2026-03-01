import html
from markdown import markdown
text = "[Click me](javascript:alert(1))"
print(markdown(text))
