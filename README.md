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

- 🌸 **Entegre Anime & Altyazı Veritabanları**:
  - 🐱 **nekoBT** (Anime Tracker & Fansub Topluluğu — Torznab RSS & API, doğrudan .torrent & magnet indirme)
  - ⚡ **AnimeTosho** (JSON API entegrasyonu — Torrent & Altyazılar)
  - 🍙 **Nyaa.si** (Gelişmiş Web API & Parser — kernelginar/nyaa-api)
  - 🍿 **SubsPlease** (Multi-Sub Release Akışı)
  - 🌐 **OpenSubtitles.com** (REST API v1)
  - 📦 **SubDL.com** (Altyazı Arşivi)

- 🎯 **Dinamik Çoklu Kaynak Filtreleme**:
  - Arama sonuçlarında sağ orta panelden tek tıkla veya çoklu seçimle kaynakları filtreleme (Nyaa.si, AnimeTosho, OpenSubtitles, SubDL, nekoBT, SubsPlease).

- 🎨 **Windows 11 Fluent Design Kullanıcı Arayüzü**:
  - Windows 11 Dark Mica renk paleti, yerel karanlık başlık çubuğu (DWM Immersive Dark Mode), modern Fluent kartları, pill butonları ve akıcı görsel hiyerarşi.

- 🖥️ **Tam Ekran & Responsive Pencere Desteği**:
  - Altyazı çıkarma, dublaj değiştirici ve format dönüştürücü pencerelerinde ekrana tam oturan, esnek ve dinamik genişleyen responsive tablo ve liste tasarımı.

- 🎬 **Gelişmiş MKV & MP4 Araç Kutusu**:
  - **MKV -> MP4 Video Dönüştürücü**: MKV formatındaki video dosyalarını saniyeler içinde kalite kaybı olmadan (Hızlı Remux) veya tam yeniden kodlama (H.264/AAC) ile `.mp4` formatına dönüştürür.
  - **MKV / MP4 Dublaj & Ses İzi Değiştirici**: MKV ve MP4 videolarının varsayılan ses izini toplu veya tekli olarak yeniden kodlamadan fiziki olarak değiştirir.
  - **MKV Altyazı Çıkarıcı**: `.mkv` dosyalarının içerisindeki gömülü altyazıları tek tıkla `.srt` / `.ass` dosyası olarak dışarı aktarır.

- 🔄 **Toplu Altyazı Format Dönüştürücü**:
  - Çoklu altyazı dosyalarını veya tüm bir klasörü saniyeler içinde toplu olarak `.srt`, `.ass`, `.vtt` veya düz metin (`.txt`) formatlarına dönüştürür.

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
- **Windows için (Tek Tıkla)**: `Başlat.bat` veya `run.bat` dosyasına çift tıklayın.
- **Terminalden**:
```bash
py nollysub.py
# veya
python nollysub.py
```

---

## ⚙ Kaynaklar & API Yapılandırması

**NollySub**, varsayılan olarak **nekoBT**, **AnimeTosho**, **Nyaa.si** ve **SubsPlease** veritabanlarını hiçbir API anahtarı gerektirmeden doğrudan kullanır.

İsteğe bağlı olarak **OpenSubtitles**, **SubDL** ve kişiselleştirilmiş **nekoBT** hesap servislerine erişmek için:
1. Uygulamadaki `⚙️ Ayarlar` butonuna tıklayın.
2. `🔑 Key Al (Tek Tıkla)` veya `ℹ️ Info / Wiki Aç` butonlarına basarak tarayıcıda açılan sayfadan API anahtarınızı ilgili kutucuğa yapıştırın ve kaydedin.

---

## 🛠 Proje Yapısı

```
NollySub/
├── assets/
│   ├── logo.png          # Yüksek çözünürlüklü proje logosu
│   ├── logo_avatar.png   # Yuvarlatılmış UI logosu
│   └── icon.ico          # Windows ikon dosyası
├── nekobt_api.py         # nekoBT Torznab & Torrent istemcisi
├── nyaa_api.py           # Nyaa.si bağımsız API ayrıştırıcısı
├── nollysub.py           # Ana uygulama giriş noktası
├── requirements.txt      # Gerekli Python kütüphaneleri
├── Başlat.bat            # Windows başlatıcı
├── .gitignore            # Git yoksayma kuralları
└── README.md             # Proje dokümantasyonu
```

---

## 📄 Lisans

Bu proje MIT Lisansı ile lisanslanmıştır.
