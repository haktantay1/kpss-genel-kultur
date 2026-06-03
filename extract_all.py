"""Full extraction + structural map of the KPSS PDF."""
import fitz, re, io

PDF = r"C:\Users\PC\Downloads\Çıkmış KPSS Sınav Soruları 2001-2018 (Kolektif) (z-library.sk, 1lib.sk, z-lib.sk).pdf"
doc = fitz.open(PDF)
N = doc.page_count

pages = []
for i in range(N):
    pages.append(doc[i].get_text("text"))

# 1) Dump everything with page markers
with io.open("all_text.txt", "w", encoding="utf-8") as f:
    for i, t in enumerate(pages):
        f.write(f"\n\n===== PAGE {i+1} =====\n")
        f.write(t)

# 2) Structure map
report = []
report.append(f"TOTAL PAGES: {N}\n")

# markers we care about
markers = {
    "COZUM": re.compile(r"ÇÖZÜM", re.I),
    "CEVAP_ANAHTARI": re.compile(r"CEVAP\s*ANAHTAR", re.I),
    "YANIT": re.compile(r"\bYAN[İI]T\b", re.I),
    "CEVAP": re.compile(r"\bCEVAP\b", re.I),
    "DOGRU_CEVAP": re.compile(r"DO[ĞG]RU\s*CEVAP", re.I),
    "SORU_VE_COZUM": re.compile(r"SORU\s*VE\s*ÇÖZÜM", re.I),
}
year_re = re.compile(r"(20\d{2})\s*KPSS|KPSS\s*[/-]?\s*(20\d{2})|(20\d{2})\b")
qnum_re = re.compile(r"(?m)^\s*(\d{1,3})\.")
# answer-key style: a letter answer near a number, e.g. "1. A" "1) A" "1-A" "1 A"
ansrow_re = re.compile(r"\b\d{1,3}\s*[\.\)\-:]?\s*[A-E]\b")

report.append("\n--- PAGES with solution/answer markers ---")
for i, t in enumerate(pages):
    hits = []
    for name, rx in markers.items():
        c = len(rx.findall(t))
        if c:
            hits.append(f"{name}={c}")
    if hits:
        report.append(f"p{i+1}: " + ", ".join(hits))

report.append("\n--- YEAR section starts (pages whose first 200 chars name a year + KPSS) ---")
for i, t in enumerate(pages):
    head = t[:200]
    m = re.search(r"(20\d{2})\s*KPSS", head)
    if m:
        oneline = " ".join(head.split())[:90]
        report.append(f"p{i+1}: {oneline}")

report.append("\n--- Per-page question-number count & answer-row count (first/last nums) ---")
for i, t in enumerate(pages):
    qs = qnum_re.findall(t)
    ans = ansrow_re.findall(t)
    if qs:
        report.append(f"p{i+1}: qnums={len(qs)} [{qs[0]}..{qs[-1]}]  ansrows={len(ans)}")
    elif len(ans) >= 8:
        report.append(f"p{i+1}: *ANSWERKEY?* ansrows={len(ans)} qnums=0")

with io.open("structure_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(report))

print("done. all_text.txt + structure_report.txt written. pages:", N)
