from markdown import markdown
print("Normal:")
print(markdown('''```
<script>alert(1)</script>
```''', extensions=['fenced_code']))
print("Escaped:")
print(markdown('''```
&lt;script&gt;alert(1)&lt;/script&gt;
```''', extensions=['fenced_code']))
