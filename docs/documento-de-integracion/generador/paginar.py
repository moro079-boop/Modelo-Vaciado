import sys, json, re, subprocess
pdf, heads, out = sys.argv[1:4]
H = json.load(open(heads))
n = int(re.search(r'Pages:\s+(\d+)', subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout).group(1))
pages = {}
norm = lambda s: re.sub(r'\s+', ' ', s).strip()
for p in range(1, n + 1):
    t = subprocess.run(['pdftotext', '-f', str(p), '-l', str(p), '-layout', pdf, '-'], capture_output=True, text=True).stdout
    lines = [norm(l) for l in t.splitlines()]
    for h in H:
        # la última página donde aparece como línea propia (la primera es el contenido)
        if any(l == norm(h) or l.startswith(norm(h) + ' ') and len(l) < len(norm(h)) + 3 for l in lines):
            pages[h] = p
json.dump(pages, open(out, 'w'), ensure_ascii=False)
print(len(pages), 'de', len(H))
