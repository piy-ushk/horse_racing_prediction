import re
html = open('mombetsu.html', encoding='utf-8').read()
m = re.search(r'<tr class="HorseList.*?</tr>', html, re.DOTALL)
if m:
    with open('mombetsu_row.txt', 'w', encoding='utf-8') as f:
        f.write(m.group(0))
else:
    print("No HorseList row found!")
