"""Core: column-aware reading-order text + question parsing. Test harness."""
import fitz, re, io, sys, unicodedata

PDF = r"C:\Users\PC\Downloads\Çıkmış KPSS Sınav Soruları 2001-2018 (Kolektif) (z-library.sk, 1lib.sk, z-lib.sk).pdf"

def cluster_rows(words, ytol=3.5):
    words = sorted(words, key=lambda w: ((w[1]+w[3])/2, w[0]))
    rows, cur, cury = [], [], None
    for w in words:
        yc = (w[1]+w[3])/2
        if cury is None or abs(yc-cury) <= ytol:
            cur.append(w); cury = yc if cury is None else (cury+yc)/2
        else:
            rows.append(cur); cur=[w]; cury=yc
    if cur: rows.append(cur)
    return rows

def row_text(row):
    row = sorted(row, key=lambda w: w[0])
    return " ".join(w[4] for w in row)

def find_gutter(words, pw):
    """Find a vertical gutter (column split x) by minimizing word crossings."""
    lo, hi = pw*0.40, pw*0.62
    best_cx, best_cross = None, None
    for i in range(41):
        cx = lo + i*(hi-lo)/40
        cross = sum(1 for w in words if w[0] < cx-2 and w[2] > cx+2)
        if best_cross is None or cross < best_cross:
            best_cross, best_cx = cross, cx
    left = [w for w in words if (w[0]+w[2])/2 < best_cx]
    right = [w for w in words if (w[0]+w[2])/2 >= best_cx]
    if best_cross <= max(4, 0.02*len(words)) and len(left) >= 8 and len(right) >= 8:
        return best_cx
    return None

def page_rows_text(page):
    """Single-column reading: cluster all words into rows by y, sort each by x.
    Used for answer-key grids where columns must stay aligned per row."""
    words = [w for w in page.get_text("words")]
    if not words:
        return ""
    return "\n".join(row_text(r) for r in cluster_rows(words))

def page_reading_text(page, force_single=False):
    """Return text in proper reading order, handling 2-column layout."""
    words = [w for w in page.get_text("words")]
    if not words:
        return ""
    if force_single:
        return "\n".join(row_text(r) for r in cluster_rows(words))
    pw = page.rect.width
    cx = find_gutter(words, pw)
    if cx is not None:
        left = [w for w in words if (w[0]+w[2])/2 < cx]
        right = [w for w in words if (w[0]+w[2])/2 >= cx]
        parts = []
        for col in (left, right):
            for r in cluster_rows(col):
                parts.append(row_text(r))
        return "\n".join(parts)
    else:
        return "\n".join(row_text(r) for r in cluster_rows(words))

# ---------- text cleanup ----------
SOFT = "­"
NOISE_SUB = re.compile(
    r"(Diğer\s*sayfaya\s*geçiniz\.?|ÖSYM|OSYM\d*"
    r"|GENEL\s*KÜLTÜR\s*TESTİ|GENEL\s*YETENEK\s*TESTİ"
    r"|KÜLTÜR\s*TESTİ|YETENEK\s*TESTİ"
    r"|GENEL\s*KÜLTÜR(?!\w)|GENEL\s*YETENEK(?!\w)"
    r"|[A-E]?\s*KİTAPÇIĞI|KAMU\s*PERSONEL\s*SEÇME\s*SINAVI"
    r"|KPSS\s*[/\w\-]*\s*/?\s*(20\d{2})?"
    r"|Bu\s*testte\s*\d+\s*soru\s*vardır\.?"
    r"|Cevaplarınızı,[^.]*işaretleyiniz\.?"
    r"|(ayrılan\s*)?kısmına\s*işaretleyiniz\.?"
    r"|https?://\S+)", re.I)

def strip_noise(t):
    t = NOISE_SUB.sub(" ", t)
    # stray standalone page numbers / lone digits surrounded by spaces
    t = re.sub(r"\s+\d{1,3}\s*$", " ", t)
    return t

def clean(t):
    t = t.replace(SOFT, "")
    t = re.sub(r"(\w)[­\-]\s*\n\s*(\w)", r"\1\2", t)   # de-hyphenate across newlines
    t = re.sub(r"\s*\n\s*", " ", t)
    # de-hyphenate line-break hyphens that became "word- word" (no space before -)
    t = re.sub(r"(\w)-\s+(\w)", r"\1\2", t)
    t = strip_noise(t)
    t = re.sub(r"[ \t]+", " ", t).strip()
    return t

def split_options(seg):
    """Find A) B) C) D) E) in order (case-insensitive), return dict."""
    opts = {}
    letters = ["A","B","C","D","E"]
    positions = []
    start = 0
    for L in letters:
        m = re.search(rf"(?i)(?<![A-Za-zÇĞİÖŞÜçğıöşü0-9]){L}[\)\}}]", seg[start:])
        if not m:
            positions.append(None); continue
        positions.append(start+m.start())
        start = start + m.end()
    found = [(letters[i],positions[i]) for i in range(5) if positions[i] is not None]
    for idx,(L,pos) in enumerate(found):
        endpos = found[idx+1][1] if idx+1 < len(found) else len(seg)
        txt = seg[pos+2:endpos].strip(" .")
        opts[L]=strip_noise(txt).strip(" .")
    return opts

QSTART = re.compile(r"(?m)^\s*(\d{1,3})\s*\.")
def parse_questions(text):
    """text: reading-order page text. Returns list of (num, stem, options)."""
    text = text.replace(SOFT,"")
    # find question starts at line beginnings
    lines = text.split("\n")
    # rebuild with markers; we treat a line starting with 'N.' as a question start
    blocks=[]
    cur=None
    for ln in lines:
        m = re.match(r"^\s*(\d{1,3})\s*\.\s*(.*)", ln)
        if m and 1 <= int(m.group(1)) <= 60:
            if cur: blocks.append(cur)
            cur=[int(m.group(1)), m.group(2)]
        elif cur is not None:
            cur[1]+= " "+ln
    if cur: blocks.append(cur)
    out=[]
    for num, body in blocks:
        body = clean(body)
        # drop test-instruction preamble blocks
        if re.match(r"^(Bu\s*testte|Cevaplarınızı|Bu\s*kitapçık)", body, re.I):
            continue
        # stem = before first A)
        mA = re.search(r"(?i)(?<![A-Za-zÇĞİÖŞÜçğıöşü0-9])A[\)\}]", body)
        if not mA:
            out.append((num, body, {}))
            continue
        stem = body[:mA.start()].strip()
        seg = body[mA.start():]
        opts = split_options(seg)
        out.append((num, stem, opts))
    return out

if __name__=="__main__":
    doc=fitz.open(PDF)
    out=[]
    for a in sys.argv[1:]:
        p=int(a)
        page=doc[p-1]
        txt=page_reading_text(page)
        qs=parse_questions(txt)
        out.append(f"\n\n############ PAGE {p}: {len(qs)} questions ############")
        for num,stem,opts in qs:
            out.append(f"\n[{num}] {stem}")
            for L in ["A","B","C","D","E"]:
                if L in opts: out.append(f"   {L}) {opts[L]}")
    io.open("parsed.txt","w",encoding="utf-8").write("\n".join(out))
    print("wrote parsed.txt")
