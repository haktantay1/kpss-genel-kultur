# -*- coding: utf-8 -*-
"""Build questions.json: extract Genel Kültür questions + answers (2001-2017)."""
import fitz, re, io, json
from parse_core import PDF, page_reading_text, page_rows_text, parse_questions, clean

doc = fitz.open(PDF)

def final_clean(t):
    """Light final polish of extracted Turkish text."""
    if not t:
        return ""
    t = t.replace("·", "").replace("•", "").replace("¬", "").replace("­", "")
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s+([,.;:?!])", r"\1", t)      # space before punctuation
    t = t.strip(" .-—•·")
    return t.strip()

def clean_opt(v):
    """Clean an option, removing trailing stray markers that bled in from the
    next question / running header (e.g. a lone 'A' or 'A)' after the text)."""
    v = final_clean(v)
    for _ in range(3):
        nv = re.sub(r"\s+[A-E]\)?$", "", v)             # trailing lone option marker
        nv = re.sub(r"\s+(Diğer sayfaya.*|ÖSYM.*)$", "", nv, flags=re.I)
        nv = nv.strip(" .-—·")
        if nv == v:
            break
        v = nv
    return v

# ------------------------------------------------------------------
# Per-year config.
#   cover    : year cover page (questions start after it)
#   q_end    : last page of the question region (page before answers/solutions)
#   ans      : ("type", page_lo, page_hi)
#       grid        -> single GK answer grid page(s): num->letter pairs
#       grid4       -> combined GY+GK grid, 4-cycle [GY,GY,GK,GK], take GK
#       gridlabel   -> one page with "GENEL YETENEK"..then "GENEL KÜLTÜR".. take GK
#       soln        -> solution text pages, runs GY then GK, take GK (answer+explanation)
#       image       -> handled separately (vision)
# ------------------------------------------------------------------
YEARS = {
 2001: dict(gk=13, q_end=21,  ans=("soln", 22, 30)),
 2002: dict(gk=42, q_end=51,  ans=("soln", 52, 60)),
 2003: dict(gk=72, q_end=80,  ans=("soln", 81, 90)),
 2004: dict(gk=103,q_end=112, ans=("soln", 113, 122)),
 2005: dict(gk=135,q_end=145, ans=("soln", 146, 154)),
 2006: dict(gk=170,q_end=183, ans=("grid", 185, 185)),
 2007: dict(gk=210,q_end=223, ans=("grid", 225, 225)),
 2008: dict(gk=252,q_end=265, ans=("grid", 267, 267)),
 2009: dict(gk=295,q_end=309, ans=("grid", 311, 311)),
 2010: dict(gk=339,q_end=353, ans=("grid", 355, 355)),
 2011: dict(gk=369,q_end=397, ans=("soln", 405, 409)),
 2012: dict(gk=430,q_end=441, ans=("grid4", 442, 442)),
 2013: dict(gk=477,q_end=488, ans=("grid4", 489, 489)),
 2014: dict(gk=527,q_end=538, ans=("grid", 540, 540)),
 2015: dict(gk=574,q_end=584, ans=("grid", 586, 586)),
 2016: dict(gk=622,q_end=632, ans=("image", 633, 633)),  # answers via vision
 2017: dict(gk=675,q_end=687, ans=("gridlabel", 689, 689)),
}

# ---------------- question extraction ----------------
GK_KW = ["osmanlı","selçuklu","göktürk","uygur","hun","savaş","antlaş","padişah",
    "anayasa","madde","cumhurbaşkan","meclis","milletvekili","tbmm","atatürk","inkılap",
    "lozan","misak","coğraf","iklim","akarsu","nüfus","bölge","ova","dağ","deniz",
    "devlet","kağan","beylik","fatih","sultan","hükümdar","ilke","laik","cumhuriyet",
    "edebiyat","kanun","hak","özgürlük","mahkeme","yönetim","vilayet","il ","bakan"]

MATH_RE = re.compile(r"[=√∫∑]|\bkaçtır\b|\bkaç\b.*\?|x\s*[+\-=]|\d+\s*[+\-x×/]\s*\d+|m\(|üçgen|denklem|tamsay")

def score_gk(stem):
    s = stem.lower()
    return sum(1 for k in GK_KW if k in s)

def is_mathish(stem, opts):
    if MATH_RE.search(stem):
        # but allow if it's clearly GK (history dates etc.)
        if score_gk(stem) >= 2: return False
        return True
    # options mostly numeric -> math
    vals = list(opts.values())
    if vals:
        numlike = sum(1 for v in vals if re.fullmatch(r"[\d\s.,/x+\-]*", v or ""))
        if numlike >= max(3, len(vals)-1): return True
    return False

def extract_year_questions(year):
    """Collect GK questions from the GK start page to q_end; dedup by number.
    Math/garbled GY-tail items lose the dedup to the real GK text questions."""
    cfg = YEARS[year]
    best = {}   # num -> (rank, page, stem, opts)
    for p in range(cfg["gk"], cfg["q_end"]+1):
        txt = page_reading_text(doc[p-1])
        if not txt.strip():
            continue
        for num, stem, opts in parse_questions(txt):
            if not (1 <= num <= 60):
                continue
            mathish = is_mathish(stem, opts)
            # rank: prefer non-math, more options, longer stem, more GK keywords
            rank = (0 if mathish else 1, len(opts), score_gk(stem), len(stem))
            if num not in best or rank > best[num][0]:
                best[num] = (rank, p, stem, opts)
    return {num: (p, stem, opts) for num,(r,p,stem,opts) in best.items()}

# ---------------- answer extraction ----------------
def grid_pairs(text):
    """Walk tokens; number(1-60) followed by letter A-E or İPTAL -> pair list (in order)."""
    toks = text.replace("\n"," ").split()
    pairs = []
    i = 0
    while i < len(toks):
        m = re.fullmatch(r"(\d{1,2})[.\)]?", toks[i])
        if m and 1 <= int(m.group(1)) <= 60:
            # find next non-empty token that is a letter or İPTAL
            j = i+1
            while j < len(toks) and toks[j].strip()=="":
                j += 1
            if j < len(toks):
                lt = toks[j].strip().upper().replace("İ","I")
                mm = re.fullmatch(r"([A-E])[.\)]?", toks[j].strip())
                if mm:
                    pairs.append((int(m.group(1)), mm.group(1)))
                    i = j+1; continue
                if lt.startswith("IPTAL"):
                    pairs.append((int(m.group(1)), None))
                    i = j+1; continue
        i += 1
    return pairs

def _grid_text(lo, hi):
    # single-column row reading keeps "num. letter" aligned per visual row
    return "\n".join(page_rows_text(doc[p-1]) for p in range(lo,hi+1))

def answers_grid(lo, hi):
    pairs = grid_pairs(_grid_text(lo,hi))
    res = {}
    for n,l in pairs:
        if n not in res: res[n]=l
    return {n:(l,None) for n,l in res.items()}

def answers_grid4(lo, hi):
    pairs = grid_pairs(_grid_text(lo,hi))
    res = {}
    for idx,(n,l) in enumerate(pairs):
        if idx % 4 in (2,3):      # 4-cycle [GY,GY,GK,GK] -> GK entries
            if n not in res: res[n]=l
    return {n:(l,None) for n,l in res.items()}

def answers_gridlabel(lo, hi):
    # Layout: GY answers (1..60) then GK answers (1..60). Section headers are
    # clustered at the top, so the GK answer for a number is its LAST occurrence.
    pairs = grid_pairs(_grid_text(lo,hi))
    res = {}
    for n,l in pairs:
        res[n] = l                     # later (GK) overwrites earlier (GY)
    return {n:(l,None) for n,l in res.items()}

ANS_RE = re.compile(r"(?:Yanıt|YANIT|Cevap|CEVAP)\s*:?\s*([A-E])")
def answers_soln(lo, hi):
    text = "\n".join(page_reading_text(doc[p-1]) for p in range(lo,hi+1))
    # split into numbered solution blocks
    lines = text.split("\n")
    blocks, cur = [], None
    prevnum = 0
    for ln in lines:
        m = re.match(r"^\s*(\d{1,2})\s*\.\s*(.*)", ln)
        if m and 1 <= int(m.group(1)) <= 60:
            if cur: blocks.append(cur)
            cur=[int(m.group(1)), m.group(2)]
        elif cur is not None:
            cur[1]+= " "+ln
    if cur: blocks.append(cur)
    # solutions appear as GY 1..60 then GK 1..60 in order; the GK answer for a
    # number is its LAST occurrence (GK comes after GY).
    res={}
    for num, body in blocks:
        am = ANS_RE.findall(body)
        if not am: continue
        letter = am[-1]
        expl = ANS_RE.sub("", clean(body)).strip(" .")
        res[num]=(letter, expl if len(expl)>15 else None)   # later overwrites earlier -> GK
    return res

def extract_year_answers(year):
    typ, lo, hi = YEARS[year]["ans"]
    if typ=="grid":      return answers_grid(lo,hi)
    if typ=="grid4":     return answers_grid4(lo,hi)
    if typ=="gridlabel": return answers_gridlabel(lo,hi)
    if typ=="soln":      return answers_soln(lo,hi)
    if typ=="image":     return {}   # filled via vision later
    return {}

# ---------------- categorization ----------------
CATS = {
 "ATATURK":["atatürk","mustafa kemal","inkılap","inkılâp","kurtuluş savaş","milli mücadele",
   "millî mücadele","lozan","sevr","mondros","misak-ı milli","misakımilli","misak-ı millî",
   "sakarya savaş","inönü savaş","cumhuriyet'in ilan","saltanat","halifeli","tevhid-i tedrisat",
   "harf inkıl","harf devrim","şapka","laiklik","devletçilik","halkçılık","milliyetçilik",
   "cumhuriyetçilik","inkılapçılık","amasya","erzurum kongre","sivas kongre","havza",
   "mudanya","montrö","montreux","hatay","menemen","şeyh sait","kabotaj","tekke","medeni kanun",
   "kılık kıyafet","soyadı kanun","aşar","teşkilat-ı esasiye","tbmm'nin aç",
   "millet mektep","halkevi","halkevleri","köy enstit","türk tarih kurum","türk dil kurum",
   "tekke ve zaviye","maarif","latin alfabe","yeni türk alfabe","tevhid","cumhuriyet dönem",
   "atatürk dönem","atatürk ilke","çok partili","terakkiperver","serbest cumhuriyet"],
 "VATANDASLIK":["anayasa","anayasal","cumhurbaşkan","milletvekili","yasama","yürütme","yargı",
   "bakanlar kurulu","başbakan","anayasa mahkeme","danıştay","yargıtay","sayıştay","hâkim",
   "hakimler ve savcı","tüzük","yönetmelik","kanun hükmünde","hak ve özgür","temel hak",
   "temel hak ve hürriyet","seçme ve seçilme","siyasi parti","belediye","il özel idare","muhtar",
   "yerel yönetim","mahalli idare","olağanüstü hal","dokunulmazlık","egemenlik","kuvvetler ayrılığı",
   "meclis başkan","genel oy","referandum","halk oylama","tüzel kişi","idari yargı","ombudsman"],
 "COGRAFYA":["coğraf","iklim","akarsu","nehir","ırmak"," göl","dağ sıra","plato","yayla","yağış",
   "sıcaklık ","nem oran","yağmur","kar yağ","erozyon","yer şekil","yerşekil","enlem","boylam","meridyen",
   "paralel ","rüzgâr","rüzgar","kıyı","yarımada","jeoloji","bitki örtüsü","heyelan",
   "deprem","fay hattı","volkan","delta","nüfus yoğun","nüfus piramit","iç göç","kentleş",
   "tarımsal","ekili alan","baraj","hidroelektrik","linyit","ulaşım",
   "turizm geliri","ihracat","ithalat","sanayi kol","ekonomik faaliyet","karadeniz ikl",
   "akdeniz ikl","karasal ikl","muson","ova","verimli","yükselti","matematik konum","özel konum"],
 "GUNCEL":["edebiyat","roman","öykü","şair","şiir","şâir","destan","divan edebiyat",
   "tiyatro","ressam","müzik","beste","heykel","sinema","film","ödül",
   "unesco","nato","birleşmiş millet","avrupa birliği","avrupa konsey","imf","opec","oecd","dünya bankas",
   "enflasyon","gsyih","gsmh","borsa","merkez bankas","gazete","dergi",
   "olimpiyat","nobel","festival","müze ","edebî","sanatçı","minyatür","hat sanat","çini","ebru"],
 "TARIH":["osmanlı","selçuklu","göktürk","kök türk","uygur"," hun","beylik","padişah","sultan",
   "fatih","kanuni","yavuz","kağan","hükümdar","fetih","fethi","divan","yeniçeri","tımar",
   "islamiyet","islam dünya","halife","abbasi","emevi","bizans","haçlı","ipek yolu","baharat yolu",
   "orhun","tanzimat","meşrutiyet","sened-i ittifak","ıslahat","kavimler göç","mısır","pers",
   "iskender","anadolu selçuklu","büyük selçuklu","karahanlı","gazneli","türgiş","avar","hazar",
   "anlaşma","antlaşma","ahdname","cülus","şehzade","enderun","devşirme","lale devri","duraklama",
   "gerileme","kuruluş dönem","yükselme dönem"," taht"],
}
PRIORITY = ["ATATURK","VATANDASLIK","COGRAFYA","GUNCEL","TARIH"]
WEIGHT = {"ATATURK":1.4,"VATANDASLIK":1.4,"COGRAFYA":1.0,"GUNCEL":1.0,"TARIH":1.1}
def categorize(stem, opts):
    s = (stem + " " + " ".join(opts.values())).lower()
    raw = {c: sum(1 for k in CATS[c] if k in s) for c in CATS}
    if max(raw.values()) == 0:
        return "TARIH"                 # safest default for uncategorized GK
    scores = {c: raw[c]*WEIGHT[c] for c in CATS}
    mx = max(scores.values())
    for c in PRIORITY:                 # tie-break by specificity priority
        if abs(scores[c]-mx) < 1e-9:
            return c
    return "TARIH"

# ---------------- main ----------------
def main():
    questions = []
    report = []
    for year in sorted(YEARS):
        qs = extract_year_questions(year)
        ans = extract_year_answers(year)
        kept = 0
        for num in sorted(qs):
            p, stem, opts = qs[num]
            a = ans.get(num)
            letter = a[0] if a else None
            expl = a[1] if a else None
            stem = final_clean(stem)
            opts = {k: clean_opt(v) for k, v in opts.items() if clean_opt(v)}
            # quality gates: must have an answer, >=4 non-empty options,
            # the correct option present, and a real stem
            if not letter or letter not in opts:
                continue
            if len(opts) < 4 or len(stem) < 12:
                continue
            if is_mathish(stem, opts):
                continue
            # drop failed option splits: an option still containing another
            # A)-E) marker, a leaked question stem ('?'), or an absurd length
            if any(re.search(r"[A-E][)}]\s+\w", v) for v in opts.values()):
                continue
            if any(("?" in v or len(v) > 200) for v in opts.values()):
                continue
            questions.append({
                "id": f"{year}-GK-{num:02d}",
                "year": year, "section": "GENEL_KULTUR",
                "num": num, "category": categorize(stem, opts),
                "questionText": stem,
                "options": opts,
                "correctAnswer": letter,
                "explanation": final_clean(expl) if expl else "",
                "difficulty": 3,
            })
            kept += 1
        report.append(f"{year}: found={len(qs)} answers={len(ans)} kept={kept}")

    from collections import Counter
    cats = Counter(r["category"] for r in questions)
    yrs = Counter(r["year"] for r in questions)
    withexp = sum(1 for r in questions if r["explanation"])
    out = {"questions": questions,
           "metadata": {"total": len(questions), "yearRange": "2001-2017 (2016, 2018 excluded: scanned-image source)",
                        "generated": "from official ÖSYM answer keys & solutions",
                        "categories": dict(cats), "byYear": dict(sorted(yrs.items()))}}
    io.open("questions.json","w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,separators=(",",":")))
    rep = "\n".join(report)
    rep += f"\n\nTOTAL: {len(questions)} questions (all with verified answers)"
    rep += f"\nwith explanation: {withexp}"
    rep += "\nby category: "+", ".join(f"{k}={v}" for k,v in cats.most_common())
    io.open("build_report.txt","w",encoding="utf-8").write(rep)
    print(rep)

if __name__=="__main__":
    main()
