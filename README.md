# 🇹🇷 KPSS Genel Kültür — Akıllı Çalışma Sistemi

2001–2017 yılları arasındaki gerçek KPSS Genel Kültür sorularını, **bilimsel olarak kanıtlanmış öğrenme yöntemleriyle** çalıştıran, kurulum gerektirmeyen tek dosyalık bir web uygulaması.

> 📱 **Canlı:** <https://haktantay1.github.io/kpss-genel-kultur/> — telefonda aç, “Ana Ekrana Ekle” de, uygulama gibi çevrimdışı kullan (PWA).

- **801 gerçek çıkmış soru** — hepsi resmî ÖSYM cevap anahtarlarıyla doğrulanmış
- **Aralıklı tekrar (SM-2 algoritması)** — her soruyu tam unutmak üzereyken karşına çıkarır
- **Aktif hatırlama, serpiştirme (interleaving), zayıf konu takibi**
- **Sınav simülasyonu** (60 soru, geri sayım, net hesabı)
- İstatistikler, seri (streak) takibi, karanlık mod, mobil uyumlu, çevrimdışı çalışır

---

## 🚀 Çalıştırma

Makinede Node gerekmez. İki yol var:

**1) Yerel sunucu (önerilir):**
```powershell
cd C:\Users\PC\kpss-app
python -m http.server 8099
```
Tarayıcıda: <http://localhost:8099>

**2) Doğrudan açma:** `index.html` dosyasına çift tıkla. (Veri `questions.js` içinde gömülü `<script>` ile yüklendiği için çoğu tarayıcıda `file://` üzerinden de açılır.)

---

## 🧠 Uygulanan öğrenme metodolojileri

| Yöntem | Nasıl uygulandı |
|---|---|
| **Spaced Repetition (SM-2)** | Her cevaptan sonra verdiğin "ne kadar iyi biliyordun?" puanı, sorunun bir sonraki gösterim tarihini hesaplar. Yanlışlar yarın, iyi bildiklerin günler/haftalar sonra gelir. |
| **Active Recall** | Cevap baştan gösterilmez; önce sen seçersin, sonra doğrusu + açıklama açılır. |
| **Interleaving** | Aynı konudan art arda soru gelmez; kategoriler round-robin ile karıştırılır. |
| **Desirable Difficulty** | Yanlış/zor sorular sık, kolaylar seyrek tekrarlanır. |
| **Testing Effect** | "Tekrar zamanı" kuyruğu, geçmiş soruları bilimsel aralıklarla yeniden test eder. |

Tüm ilerleme **yalnızca senin tarayıcında** (`localStorage`) saklanır — sunucuya hiçbir şey gönderilmez.

---

## 📊 Veri kapsamı

| | |
|---|---|
| Toplam soru | **801** |
| Yıllar | 2001–2015, 2017 (16 yıl) |
| Kategoriler | Tarih (286), İnkılap Tarihi (200), Coğrafya (173), Vatandaşlık (114), Kültür & Güncel (28) |
| Açıklamalı soru | 223 (erken yılların çözüm metinlerinden) |

**Neden 2016 ve 2018 yok?** Kaynak PDF'de bu iki yılın cevap anahtarı/soruları **taranmış görüntü** olarak gömülü (metin katmanı yok), bu yüzden güvenilir biçimde çıkarılamadı. Sadece cevabı kesin olarak doğrulanabilen sorular dâhil edildi — eksik cevaplı tek bir soru bile eklenmedi.

Erken yıllarda (2001–2005) harita/şekil/tablo içeren bazı Coğrafya soruları, PDF'de görüntü olduğu için çıkarılamadı; bu yıllarda ~60 yerine ~37 soru var.

---

## 🔧 Veri setini yeniden üretme

Sorular `build_dataset.py` ile kaynak PDF'den çıkarılır:

```powershell
python -m pip install pymupdf
python build_dataset.py          # -> questions.json üretir
# questions.js'i tazele:
python -c "import io; d=io.open('questions.json',encoding='utf-8').read(); io.open('questions.js','w',encoding='utf-8').write('window.KPSS_DATA = '+d+';')"
```

| Dosya | Görev |
|---|---|
| `parse_core.py` | PDF metnini sütun-farkında okuyan ve soruları/şıkları ayrıştıran çekirdek |
| `build_dataset.py` | Yıl-yıl soru + cevap eşleştirme, kategorize etme, `questions.json` üretimi |
| `extract_all.py` | PDF'in tam metnini ve yapı haritasını döken yardımcı araç |
| `index.html` | Uygulamanın tamamı (HTML + CSS + JS, sıfır bağımlılık) |
| `questions.js` / `questions.json` | Çıkarılmış soru verisi |

> Not: `build_dataset.py` içindeki `PDF` yolu, kaynak PDF'i işaret eder. Farklı bir konumda ise güncelle.

## 📱 Telefona kurma (PWA)

- **iPhone (Safari):** Linki aç → Paylaş ⎙ → **“Ana Ekrana Ekle”**.
- **Android (Chrome):** Linki aç → çıkan **“Ekle”** çubuğuna dokun (veya menü ⋮ → “Uygulamayı yükle”).
- İlk açılıştan sonra **internet olmadan da** çalışır (service worker önbelleğe alır).

## 🔄 Güncelleme

Kodu/soruları değiştirdikten sonra:
```powershell
git add -A; git commit -m "guncelleme"; git push
```
GitHub Pages 1–2 dakikada yeniden yayınlar. Kullanıcıların yeni sürümü alması için `sw.js` içindeki `CACHE = "kpss-gk-v1"` sürümünü artır (örn. `-v2`).

