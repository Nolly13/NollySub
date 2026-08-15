<div align="center">

<img src="assets/logo.png" width="160" height="160" alt="NollySub Logo" style="border-radius: 50%;">

# 🎬 NollySub — Anime Türkçe Altyazı & Torrent İndirici

**NollySub**, anime ve dijital içerikler için Türkçe altyazıları ve yüksek kaliteli salımları otomatik arayıp indiren, gelişmiş bir masaüstü uygulamasıdır.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6.svg)](https://www.microsoft.com/)

</div>

---

## ✨ Özellikler

- 🌸 **Entegre Anime Veritabanları**:
  - ⚡ **AnimeTosho** (JSON API entegrasyonu — Torrent & Altyazılar)
  - 🍙 **Nyaa.si** (RSS Canlı Arama)
  - 🍿 **SubsPlease** (Multi-Sub Release Akışı)
  - 🌐 **OpenSubtitles.com** (REST API v1)
  - 📦 **SubDL.com** (Altyazı Arşivi)

- 🇹🇷 **Akıllı Türkçe Altyazı Algılama**:
  - Türkçe içerikli salımları otomatik tespit eder ve sonuç listesinin en üstünde yeşil renkle vurgular.

- 🎬 **Gelişmiş MKV Araç Kutusu**:
  - **MKV Altyazı Çıkarıcı**: `.mkv` dosyalarının içerisindeki gömülü altyazıları tek tıkla `.srt` / `.ass` dosyası olarak dışarı kaydeder.
  - **MKV Dublaj & Ses İzi Değiştirici**: MKV videolarının varsayılan ses izini (Türkçe/Japonca/İngilizce) toplu veya tekli olarak değiştirir.

- 🔄 **Toplu Altyazı Format Dönüştürücü**:
  - Çoklu altyazı dosyalarını veya tüm bir klasörü saniyeler içinde toplu olarak `.srt`, `.ass`, `.vtt` veya düz metin (`.txt`) formatlarına dönüştürür.


- 🎨 **Modern & Şık Kullanıcı Arayüzü**:
  - Karanlık tema, özel karakter logosu, hızlı arama filtreleri ve masaüstü kısayolu oluşturma desteği.

---

## 🚀 Kurulum & Çalıştırma

### 1. Depoyu Klonlayın
```bash
git clone https://github.com/Nolly13/NollySub.git
cd NollySub
```

### 2. Gereksinimleri Yükleyin
```bash
pip install -r requirements.txt
```

### 3. Uygulamayı Başlatın
```bash
python nollysub.py
```
*(veya Windows üzerinde çift tıklayarak çalıştırın)*

---

## ⚙ Kaynaklar & API Yapılandırması

**NollySub**, varsayılan olarak **AnimeTosho**, **Nyaa.si** ve **SubsPlease** veritabanlarını hiçbir API anahtarı gerektirmeden doğrudan kullanır.

İsteğe bağlı olarak **OpenSubtitles** ve **SubDL** servislerine erişmek için:
1. Uygulamadaki `⚙️ Ayarlar` butonuna tıklayın.
2. `🔑 Key Al (Tek Tıkla)` butonlarına basarak tarayıcıda açılan sayfadan ücretsiz API anahtarınızı saniyeler içinde kopyalayıp ilgili kutucuğa yapıştırın ve kaydedin.

---

## 🛠 Proje Yapısı

```
NollySub/
├── assets/
│   ├── logo.png          # Yüksek çözünürlüklü proje logosu
│   ├── logo_avatar.png   # Yuvarlatılmış UI logosu
│   └── icon.ico          # Windows ikon dosyası
├── nollysub.py           # Ana uygulama giriş noktası
├── netrip.py             # Geriye dönük uyumluluk başlatıcısı
├── requirements.txt      # Gerekli Python kütüphaneleri
├── .gitignore            # Git yoksayma kuralları
└── README.md             # Proje dokümantasyonu
```

---

## 📄 Lisans

Bu proje MIT Lisansı ile lisanslanmıştır.
