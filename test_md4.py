import html
from markdown import markdown
text = "[Click me](javascript:alert('XSS'))"
print(markdown(text))
