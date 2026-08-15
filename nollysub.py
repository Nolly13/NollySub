#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════╗
║   NollySub — Anime Türkçe Altyazı İndirici          ║
║   Netflix, AnimeTosho, Nyaa & Dijital Platformlar    ║
╚══════════════════════════════════════════════════════╝

Anime için Türkçe altyazıları (NollySub) arayıp .srt / .ass / torrent olarak
indiren masaüstü program.

Kaynaklar:
  - AnimeTosho JSON API
  - Nyaa.si RSS API
  - SubsPlease RSS API
  - OpenSubtitles.com REST API
  - SubDL.com API
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import subprocess
import shutil
import os
import sys
import json
import zipfile
import io
import webbrowser
import configparser
import xml.etree.ElementTree as ET
import re
from pathlib import Path

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import requests
except ImportError:
    print("'requests' kütüphanesi bulunamadı. Kuruluyor...")
    os.system(f"{sys.executable} -m pip install requests")
    import requests


# ══════════════════════════════════════════════════════
# YAPILANDIRMA
# ══════════════════════════════════════════════════════

APP_NAME = "NollySub"
APP_VERSION = "1.2.0"
APP_TITLE = f"{APP_NAME} — Anime Türkçe Altyazı İndirici v{APP_VERSION}"

CONFIG_DIR = Path.home() / ".nollysub"
CONFIG_FILE = CONFIG_DIR / "config.ini"
DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads" / "NollySub Altyazılar"

# API Endpoints
OPENSUBTITLES_API = "https://api.opensubtitles.com/api/v1"
SUBDL_API = "https://api.subdl.com/api/v1"
ANIMETOSHO_API = "https://feed.animetosho.org/json"

# ══════════════════════════════════════════════════════
# RENK TEMASI (Karanlık Tema)
# ══════════════════════════════════════════════════════

COLORS = {
    "bg_deepest": "#0a0a14",
    "bg_deep": "#0f0f1e",
    "bg_surface": "#161628",
    "bg_elevated": "#1c1c36",
    "bg_input": "#12122a",
    "accent": "#E50914",
    "accent_hover": "#ff2d38",
    "accent_light": "#ff6b6b",
    "success": "#22c55e",
    "info": "#3b82f6",
    "warning": "#f59e0b",
    "text_primary": "#e4e4e7",
    "text_secondary": "#a1a1aa",
    "text_muted": "#71717a",
    "text_faint": "#52525b",
    "border": "#2a2a4a",
    "border_light": "#3a3a5a",
    "highlight_row": "#1a1a3e",
    "scrollbar": "#3a3a5a",
}

LANG_MAP = {
    "tur": "Türkçe 🇹🇷",
    "tr": "Türkçe 🇹🇷",
    "eng": "İngilizce 🇬🇧",
    "en": "İngilizce 🇬🇧",
    "jpn": "Japonca 🇯🇵",
    "ja": "Japonca 🇯🇵",
    "ger": "Almanca 🇩🇪",
    "deu": "Almanca 🇩🇪",
    "fre": "Fransızca 🇫🇷",
    "fra": "Fransızca 🇫🇷",
    "spa": "İspanyolca 🇪🇸",
    "es": "İspanyolca 🇪🇸",
    "und": "Bilinmeyen (und)",
}


# ══════════════════════════════════════════════════════
# AYAR YÖNETİCİSİ
# ══════════════════════════════════════════════════════

class ConfigManager:
    """Uygulama ayarlarını dosyada saklar."""

    def __init__(self):
        self.config = configparser.ConfigParser()
        self._ensure_dirs()
        self.load()

    def _ensure_dirs(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        DEFAULT_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def load(self):
        if CONFIG_FILE.exists():
            self.config.read(str(CONFIG_FILE), encoding="utf-8")
        # Varsayılan değerler
        if "API" not in self.config:
            self.config["API"] = {}
        if "General" not in self.config:
            self.config["General"] = {}
        if "download_dir" not in self.config["General"]:
            self.config["General"]["download_dir"] = str(DEFAULT_DOWNLOAD_DIR)

    def save(self):
        with open(str(CONFIG_FILE), "w", encoding="utf-8") as f:
            self.config.write(f)

    def get_opensubtitles_key(self):
        return self.config["API"].get("opensubtitles_key", "").strip()

    def set_opensubtitles_key(self, key):
        self.config["API"]["opensubtitles_key"] = key
        self.save()

    def get_subdl_key(self):
        return self.config["API"].get("subdl_key", "").strip()

    def set_subdl_key(self, key):
        self.config["API"]["subdl_key"] = key
        self.save()

    def get_download_dir(self):
        d = self.config["General"].get("download_dir", str(DEFAULT_DOWNLOAD_DIR))
        return d

    def set_download_dir(self, path):
        self.config["General"]["download_dir"] = path
        self.save()

    def get_mkvtoolnix_dir(self):
        return self.config["General"].get("mkvtoolnix_dir", "").strip()

    def set_mkvtoolnix_dir(self, path):
        self.config["General"]["mkvtoolnix_dir"] = path
        self.save()

    def find_mkvtoolnix(self):
        """Sistemdeki, ayarlardaki veya Portable klasörlerdeki MKVToolNix yolunu otomatik bulur."""
        custom_dir = self.get_mkvtoolnix_dir()
        if custom_dir:
            mmerge = os.path.join(custom_dir, "mkvmerge.exe")
            mextract = os.path.join(custom_dir, "mkvextract.exe")
            mpropedit = os.path.join(custom_dir, "mkvpropedit.exe")
            if os.path.exists(mmerge) and os.path.exists(mextract):
                return mmerge, mextract, mpropedit

        # Sistem PATH ve bilinen dizinler
        possible_paths = [
            shutil.which("mkvmerge"),
            r"C:\Program Files\MKVToolNix\mkvmerge.exe",
            r"C:\Program Files (x86)\MKVToolNix\mkvmerge.exe",
            os.path.join(os.getcwd(), "MKVToolNix", "mkvmerge.exe"),
            os.path.join(os.getcwd(), "mkvmerge.exe"),
        ]

        for path in possible_paths:
            if path and os.path.exists(path):
                folder = os.path.dirname(path)
                mextract = os.path.join(folder, "mkvextract.exe")
                mpropedit = os.path.join(folder, "mkvpropedit.exe")
                if os.path.exists(mextract):
                    return path, mextract, mpropedit

        return None, None, None


# ══════════════════════════════════════════════════════
# MOTORLAR (API & RSS ENTEGRASYONLARI)
# ══════════════════════════════════════════════════════

class OpenSubtitlesEngine:
    """OpenSubtitles.com REST API v1 ile altyazı arar ve indirir."""

    NAME = "OpenSubtitles"

    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "Api-Key": self.api_key,
            "User-Agent": f"NollySub v{APP_VERSION}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def search(self, query, language="tr"):
        results = []
        try:
            url = f"{OPENSUBTITLES_API}/subtitles"
            params = {
                "query": query,
                "languages": language,
                "type": "all",
                "order_by": "download_count",
                "order_direction": "desc",
            }
            resp = requests.get(url, headers=self.headers, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("data", []):
                    attr = item.get("attributes", {})
                    files = attr.get("files", [])
                    file_id = files[0].get("file_id") if files else None
                    file_name = files[0].get("file_name") if files else "subtitle.srt"

                    feature = attr.get("feature_details", {})
                    title = feature.get("title", "") or feature.get("movie_name", "") or attr.get("release", "")

                    results.append({
                        "source": self.NAME,
                        "title": title or file_name,
                        "year": str(feature.get("year", "-")),
                        "season": str(attr.get("season_number", "-")),
                        "episode": str(attr.get("episode_number", "-")),
                        "language": attr.get("language", "tr").upper(),
                        "release": attr.get("release", "-"),
                        "uploader": attr.get("uploader", {}).get("name", "Bilinmiyor"),
                        "download_count": str(attr.get("download_count", 0)),
                        "file_id": file_id,
                        "file_name": file_name,
                        "_engine": self,
                    })
        except Exception as e:
            print(f"OpenSubtitles Hatası: {e}")

        return results

    def download(self, file_id):
        """Altyazıyı indirir ve içeriğini döndürür."""
        try:
            url = f"{OPENSUBTITLES_API}/download"
            payload = {"file_id": file_id}
            resp = requests.post(url, headers=self.headers, json=payload, timeout=15)
            if resp.status_code == 200:
                dl_data = resp.json()
                link = dl_data.get("link")
                file_name = dl_data.get("file_name", "subtitle.srt")

                sub_resp = requests.get(link, timeout=30)
                sub_resp.raise_for_status()

                return sub_resp.content, file_name
            else:
                raise Exception(f"API Hatası: {resp.status_code} - {resp.text}")
        except Exception as e:
            raise Exception(f"OpenSubtitles indirme hatası: {str(e)}")


class SubDLEngine:
    """SubDL.com API ile altyazı arar ve indirir."""

    NAME = "SubDL"

    def __init__(self, api_key):
        self.api_key = api_key

    def search(self, query, language="sd_tr"):
        results = []
        try:
            url = f"{SUBDL_API}/subtitles"
            params = {
                "api_key": self.api_key,
                "file_name": query,
                "languages": "tr,en",
                "type": "all",
            }
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status"):
                    subtitles = data.get("subtitles", [])
                    results.extend(self._parse_subtitles(subtitles))

            url2 = f"{SUBDL_API}/subtitles"
            params2 = {
                "api_key": self.api_key,
                "film_name": query,
                "languages": "tr,en",
                "type": "all",
            }
            resp2 = requests.get(url2, params=params2, timeout=15)
            if resp2.status_code == 200:
                data2 = resp2.json()
                if data2.get("status"):
                    subtitles2 = data2.get("subtitles", [])
                    results.extend(self._parse_subtitles(subtitles2))

        except Exception as e:
            print(f"SubDL Hatası: {e}")

        seen = set()
        unique_results = []
        for r in results:
            key = (r["file_id"], r["file_name"])
            if key not in seen:
                seen.add(key)
                unique_results.append(r)

        return unique_results

    def _parse_subtitles(self, subtitles):
        results = []
        for sub in subtitles:
            lang = sub.get("language", "tr")
            url_path = sub.get("url", "")
            release = sub.get("release_name", "") or sub.get("name", "")
            name = sub.get("name", "") or release
            season = sub.get("season", "-")
            episode = sub.get("episode", "-")

            results.append({
                "source": self.NAME,
                "title": name,
                "year": "-",
                "season": str(season) if season else "-",
                "episode": str(episode) if episode else "-",
                "language": str(lang).upper(),
                "release": release,
                "uploader": sub.get("author", "SubDL"),
                "download_count": str(sub.get("hi", 0)),
                "file_id": url_path,
                "file_name": f"{release or name}.zip",
                "_engine": self,
            })
        return results

    def download(self, url_path):
        """SubDL üzerinden zip/srt dosyasını indirir."""
        try:
            if not url_path.startswith("http"):
                full_url = f"https://dl.subdl.com{url_path}"
            else:
                full_url = url_path

            resp = requests.get(full_url, timeout=30)
            resp.raise_for_status()

            if url_path.endswith(".zip") or resp.content[:4] == b'PK\x03\x04':
                with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                    srt_files = [f for f in z.namelist() if f.lower().endswith(('.srt', '.ass', '.vtt'))]
                    if srt_files:
                        first_srt = srt_files[0]
                        return z.read(first_srt), os.path.basename(first_srt)

            return resp.content, "subtitle.srt"

        except Exception as e:
            raise Exception(f"SubDL indirme hatası: {str(e)}")


class NyaaEngine:
    """Nyaa.si RSS ile anime torrent & altyazılı salımları arar."""

    NAME = "Nyaa.si"

    def search(self, query, language=""):
        results = []
        seen_links = set()
        
        queries_to_try = [query]
        if "turkish" not in query.lower() and "türkçe" not in query.lower() and "tr" not in query.lower().split():
            queries_to_try.append(f"{query} Turkish")
            queries_to_try.append(f"{query} TR")

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        ns = {"nyaa": "https://nyaa.si/xmlns/nyaa"}

        for q in queries_to_try:
            try:
                url = f"https://nyaa.si/?page=rss&q={requests.utils.quote(q)}"
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    try:
                        root = ET.fromstring(resp.content)
                    except ET.ParseError:
                        continue

                    for item in root.findall("./channel/item")[:20]:
                        title = item.find("title").text if item.find("title") is not None else ""
                        link = item.find("link").text if item.find("link") is not None else ""

                        if link in seen_links:
                            continue
                        seen_links.add(link)

                        size = item.find("nyaa:size", ns).text if item.find("nyaa:size", ns) is not None else "?"
                        seeders = item.find("nyaa:seeders", ns).text if item.find("nyaa:seeders", ns) is not None else "?"

                        title_lower = title.lower()
                        if any(k in title_lower for k in ["tr", "turkish", "türkçe", "turkce", "tac", "oishi"]):
                            lang_str = "🇹🇷 Türkçe Subbed"
                        else:
                            lang_str = "🌐 Multi / ENG"

                        results.append({
                            "source": self.NAME,
                            "title": title,
                            "year": "-",
                            "season": "-",
                            "episode": "-",
                            "language": lang_str,
                            "release": f"{size} | Seeders: {seeders}",
                            "uploader": "Nyaa",
                            "download_count": seeders,
                            "file_id": link,
                            "file_name": title + (".torrent" if not link.startswith("magnet:") else ".magnet"),
                            "_engine": self,
                        })
            except Exception as e:
                print(f"Nyaa.si Hatası ({q}): {e}")

        return results

    def download(self, url):
        """Torrent dosyasını veya magnet linkini indirir/kaydeder."""
        try:
            if url.startswith("magnet:"):
                return url.encode("utf-8"), "download.magnet"
            else:
                resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
                resp.raise_for_status()
                return resp.content, "anime.torrent"
        except Exception as e:
            raise Exception(f"Nyaa indirme hatası: {str(e)}")


class SubsPleaseEngine:
    """SubsPlease anime salımlarını arar (Nyaa & SubsPlease RSS)."""

    NAME = "SubsPlease"

    def search(self, query, language=""):
        results = []
        try:
            q = f"SubsPlease {query}"
            url = f"https://nyaa.si/?page=rss&q={requests.utils.quote(q)}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            resp = requests.get(url, headers=headers, timeout=12)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                ns = {"nyaa": "https://nyaa.si/xmlns/nyaa"}
                for item in root.findall("./channel/item")[:30]:
                    title = item.find("title").text if item.find("title") is not None else ""
                    link = item.find("link").text if item.find("link") is not None else ""
                    size = item.find("nyaa:size", ns).text if item.find("nyaa:size", ns) is not None else "?"
                    seeders = item.find("nyaa:seeders", ns).text if item.find("nyaa:seeders", ns) is not None else "?"

                    results.append({
                        "source": self.NAME,
                        "title": title,
                        "year": "-",
                        "season": "-",
                        "episode": "-",
                        "language": "SubsPlease (Multi-Sub)",
                        "release": f"{size} | Seeders: {seeders}",
                        "uploader": "SubsPlease",
                        "download_count": seeders,
                        "file_id": link,
                        "file_name": title + (".torrent" if not link.startswith("magnet:") else ".magnet"),
                        "_engine": self,
                    })
        except Exception as e:
            print(f"SubsPlease Hatası: {e}")
        return results

    def download(self, url):
        try:
            if url.startswith("magnet:"):
                return url.encode("utf-8"), "download.magnet"
            else:
                resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
                resp.raise_for_status()
                return resp.content, "subsplease.torrent"
        except Exception as e:
            raise Exception(f"SubsPlease indirme hatası: {str(e)}")


class AnimeToshoEngine:
    """AnimeTosho.org JSON API ile anime torrent & altyazılı salımları arar."""

    NAME = "AnimeTosho"

    def search(self, query, language=""):
        results = []
        seen_links = set()

        queries_to_try = [query]
        if "turkish" not in query.lower() and "türkçe" not in query.lower() and "tr" not in query.lower().split():
            queries_to_try.append(f"{query} Turkish")
            queries_to_try.append(f"{query} TR")

        headers = {"User-Agent": f"NollySub v{APP_VERSION}"}

        for q in queries_to_try:
            try:
                url = f"{ANIMETOSHO_API}?q={requests.utils.quote(q)}"
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data[:25]:
                        title = item.get("title", "")
                        torrent_url = item.get("torrent_url", "")
                        magnet_uri = item.get("magnet_uri", "")
                        link = torrent_url or magnet_uri or item.get("link", "")
                        if not link or link in seen_links:
                            continue
                        seen_links.add(link)

                        size_bytes = item.get("total_size", 0)
                        if size_bytes:
                            if size_bytes < 1024 * 1024 * 1024:
                                size = f"{size_bytes / (1024 * 1024):.1f} MB"
                            else:
                                size = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
                        else:
                            size = "?"

                        seeders = item.get("seeders", "?")

                        title_lower = title.lower()
                        if any(k in title_lower for k in ["tr", "turkish", "türkçe", "turkce", "tac", "oishi", "ani-tr"]):
                            lang_str = "🇹🇷 Türkçe Subbed"
                        else:
                            lang_str = "🌐 Multi / ENG"

                        results.append({
                            "source": self.NAME,
                            "title": title,
                            "year": "-",
                            "season": "-",
                            "episode": "-",
                            "language": lang_str,
                            "release": f"{size} | Seeders: {seeders}",
                            "uploader": "AnimeTosho",
                            "download_count": str(seeders),
                            "file_id": link,
                            "file_name": title + (".torrent" if torrent_url else ".magnet"),
                            "_engine": self,
                        })
            except Exception as e:
                print(f"AnimeTosho Hatası ({q}): {e}")

        return results

    def download(self, url):
        """Torrent dosyasını veya magnet linkini indirir/kaydeder."""
        try:
            if url.startswith("magnet:"):
                return url.encode("utf-8"), "download.magnet"
            else:
                resp = requests.get(url, headers={"User-Agent": f"NollySub v{APP_VERSION}"}, timeout=30)
                resp.raise_for_status()
                return resp.content, "animetosho.torrent"
        except Exception as e:
            raise Exception(f"AnimeTosho indirme hatası: {str(e)}")


# ══════════════════════════════════════════════════════
# YARDIMCI VE DÖNÜŞTÜRÜCÜ MOTORLAR
# ══════════════════════════════════════════════════════

def is_tr_subtitle(item):
    """Bir altyazı veya salımın Türkçe olup olmadığını analiz eder."""
    lang = str(item.get("language", "")).lower()
    title = str(item.get("title", "")).lower()
    release = str(item.get("release", "")).lower()
    uploader = str(item.get("uploader", "")).lower()

    if any(k in lang for k in ["tr", "tur", "türkçe", "turkce", "turkish"]):
        return True
    if any(k in title for k in ["tr", "turkish", "türkçe", "turkce", "tac", "oishi", "ani-tr"]):
        return True
    if any(k in release for k in ["tr", "turkish", "türkçe", "turkce"]):
        return True
    if any(k in uploader for k in ["tr", "turkish", "türkçe"]):
        return True
    return False


def is_turkish_mkv_track(item):
    """MKV altyazı track'inin Türkçe olup olmadığını detaylıca analiz eder."""
    lang = str(item.get("lang") or item.get("language") or "").lower()
    lang_ietf = str(item.get("language_ietf") or "").lower()
    lang_raw = str(item.get("language_raw") or "").lower()
    name = str(item.get("name") or "").lower()
    filename = str(item.get("filename") or "").lower()

    # Dil kodları (ISO 639-1, 639-2, BCP 47)
    tr_codes = {"tur", "tr", "tr-tr", "tur-tr", "tr_tr", "tur_tr", "turkish", "türkçe", "turkce"}
    for l in [lang, lang_ietf, lang_raw]:
        if l in tr_codes or l.startswith("tr") or l.startswith("tur"):
            return True

    # Metin aramaları (Başlık / Track ismi)
    tr_terms = ["türkçe", "turkce", "turkish", "tr sub", "tur sub", "tr-sub", "tur-sub", "tr_sub", "tur_sub", "[tr]", "(tr)", "[tur]", "(tur)"]
    if any(term in name for term in tr_terms):
        return True

    # Kelime bazı isim kontrolü
    name_words = name.replace("_", " ").replace("-", " ").replace(".", " ").split()
    if any(word in ["tr", "tur", "türkçe", "turkce", "turkish"] for word in name_words):
        return True

    # Dosya adında dil uzantısı kontrolü
    if any(f".{tag}." in filename or filename.endswith(f".{tag}") for tag in ["tr", "tur", "türkçe", "turkce", "turkish"]):
        return True

    return False


def read_text_file(fpath):
    """Farklı kodlamaları (UTF-8, UTF-8-BOM, CP1254, ISO-8859-9, Latin-1) deneyerek dosyayı okur."""
    for enc in ["utf-8-sig", "utf-8", "cp1254", "iso-8859-9", "latin-1"]:
        try:
            with open(fpath, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


class SubtitleConverter:
    """Farklı altyazı formatları (vtt, ttml, ass, srt, txt) arasında dönüşüm yapar."""

    @staticmethod
    def parse_srt(srt_content):
        """SRT içeriğini detaylı, esnek ve hatasız bir şekilde ayrıştırır."""
        if not srt_content or not srt_content.strip():
            return []

        if srt_content.startswith('\ufeff'):
            srt_content = srt_content[1:]
        srt_content = srt_content.replace('\r\n', '\n').replace('\r', '\n')

        # Esnek zaman damgası deseni (00:00:01,000 / 0:00:01.00 / 01:23,456 / 4 basamaklı ms vb.)
        timestamp_re = re.compile(
            r'(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:[\.,](\d{1,4}))?\s*-->\s*(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:[\.,](\d{1,4}))?'
        )

        lines = srt_content.split('\n')
        subtitles = []

        current_start = None
        current_end = None
        current_text_lines = []

        def format_timestamp(h, m, s, ms):
            h_str = f"{int(h):02d}" if h is not None else "00"
            m_str = f"{int(m):02d}" if m is not None else "00"
            s_str = f"{int(s):02d}" if s is not None else "00"
            ms_3 = (ms + "000")[:3] if ms is not None else "000"
            return f"{h_str}:{m_str}:{s_str},{ms_3}"

        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            m = timestamp_re.search(line)
            if m:
                if current_start and current_end:
                    if current_text_lines and current_text_lines[-1].strip().isdigit():
                        current_text_lines.pop()
                    text = "\n".join(current_text_lines).strip()
                    if text:
                        subtitles.append((current_start, current_end, text))

                g = m.groups()
                current_start = format_timestamp(g[0], g[1], g[2], g[3])
                current_end = format_timestamp(g[4], g[5], g[6], g[7])
                current_text_lines = []
                i += 1
            else:
                if current_start is not None:
                    current_text_lines.append(line)
                i += 1

        if current_start and current_end:
            if current_text_lines and current_text_lines[-1].strip().isdigit():
                current_text_lines.pop()
            text = "\n".join(current_text_lines).strip()
            if text:
                subtitles.append((current_start, current_end, text))

        return subtitles

    @staticmethod
    def fmt_ass_time(t_str):
        """Zaman damgasını ASS formatına dönüştürür (H:MM:SS.cc)."""
        if not t_str:
            return "0:00:00.00"
        t_str = t_str.replace(',', '.')
        parts = t_str.split(':')
        try:
            if len(parts) == 3:
                h, m, s = parts
            elif len(parts) == 2:
                h = "0"
                m, s = parts
            else:
                return "0:00:00.00"

            sec_parts = s.split('.')
            sec = sec_parts[0]
            ms_raw = sec_parts[1] if len(sec_parts) > 1 else "0"

            h = re.sub(r'\D', '', h) or "0"
            m = re.sub(r'\D', '', m) or "0"
            sec = re.sub(r'\D', '', sec) or "0"
            ms_raw = re.sub(r'\D', '', ms_raw) or "0"

            ms_3 = (ms_raw + "000")[:3]
            cs = min(99, int(ms_3) // 10)

            return f"{int(h)}:{int(m):02d}:{int(sec):02d}.{cs:02d}"
        except Exception:
            return "0:00:00.00"

    @staticmethod
    def fmt_srt_time(ass_t_str):
        """ASS zaman damgasını SRT formatına dönüştürür (HH:MM:SS,mmm)."""
        if not ass_t_str:
            return "00:00:00,000"
        ass_t_str = ass_t_str.replace('.', ',')
        parts = ass_t_str.strip().split(':')
        try:
            if len(parts) == 3:
                h, m, s = parts
            elif len(parts) == 2:
                h = "00"
                m, s = parts
            else:
                return "00:00:00,000"

            sec_parts = s.split(',')
            sec = sec_parts[0]
            cs_raw = sec_parts[1] if len(sec_parts) > 1 else "0"

            h_num = int(re.sub(r'\D', '', h) or 0)
            m_num = int(re.sub(r'\D', '', m) or 0)
            sec_num = int(re.sub(r'\D', '', sec) or 0)
            cs_clean = re.sub(r'\D', '', cs_raw) or "0"

            ms_3 = (cs_clean + "00")[:2] + "0" if len(cs_clean) <= 2 else (cs_clean + "000")[:3]

            return f"{h_num:02d}:{m_num:02d}:{sec_num:02d},{ms_3}"
        except Exception:
            return "00:00:00,000"

    @staticmethod
    def convert_html_to_ass_tags(text):
        """HTML etiketlerini ASS etiketlerine çevirir."""
        if not text:
            return ""
        text = re.sub(r'<i>(.*?)</i>', r'{\\i1}\1{\\i0}', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<b>(.*?)</b>', r'{\\b1}\1{\\b0}', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<u>(.*?)</u>', r'{\\u1}\1{\\u0}', text, flags=re.IGNORECASE | re.DOTALL)

        def replace_font(match):
            color_attr = match.group(1).strip('"\'')
            content = match.group(2)
            if color_attr.startswith('#') and len(color_attr) == 7:
                r, g, b = color_attr[1:3], color_attr[3:5], color_attr[5:7]
                ass_color = f"&H{b}{g}{r}&"
                return f"{{\\c{ass_color}}}{content}{{\\c}}"
            return content

        text = re.sub(r'<font\s+color=([^>]+)>(.*?)</font>', replace_font, text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<[^>]+>', '', text)
        return text

    @staticmethod
    def convert_ass_tags_to_html(text):
        """ASS etiketlerini HTML / temiz metne çevirir."""
        if not text:
            return ""
        text = re.sub(r'\{\\i1\}(.*?)\{\\i0\}', r'<i>\1</i>', text)
        text = re.sub(r'\{\\b1\}(.*?)\{\\b0\}', r'<b>\1</b>', text)
        text = re.sub(r'\{\\u1\}(.*?)\{\\u0\}', r'<u>\1</u>', text)
        text = re.sub(r'\{[^}]+\}', '', text)
        return text

    @staticmethod
    def vtt_to_srt(vtt_content):
        if not vtt_content:
            return ""
        if vtt_content.startswith('\ufeff'):
            vtt_content = vtt_content[1:]
        vtt_content = vtt_content.replace('\r\n', '\n').replace('\r', '\n')

        pattern = re.compile(
            r'(?:(\d{1,2}):)?(\d{2}:\d{2}[\.,]\d{2,4})\s*-->\s*(?:(\d{1,2}):)?(\d{2}:\d{2}[\.,]\d{2,4})'
        )
        srt_lines = []
        idx = 1
        lines = vtt_content.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("WEBVTT") or line.startswith("NOTE") or line.startswith("STYLE") or line.startswith("REGION"):
                i += 1
                while i < len(lines) and lines[i].strip():
                    i += 1
                continue

            m = pattern.search(line)
            if m:
                t_line = line.split("-->")
                start_str = t_line[0].strip().replace('.', ',')
                end_str = t_line[1].split()[0].strip().replace('.', ',')
                if start_str.count(':') == 1:
                    start_str = "00:" + start_str
                if end_str.count(':') == 1:
                    end_str = "00:" + end_str

                text_lines = []
                i += 1
                while i < len(lines) and lines[i].strip() and not lines[i].strip().isdigit() and "-->" not in lines[i]:
                    t_l = re.sub(r'<[^>]+>', '', lines[i].strip())
                    if t_l:
                        text_lines.append(t_l)
                    i += 1

                if text_lines:
                    srt_lines.append(str(idx))
                    srt_lines.append(f"{start_str} --> {end_str}")
                    srt_lines.extend(text_lines)
                    srt_lines.append("")
                    idx += 1
            else:
                i += 1

        return "\n".join(srt_lines)

    @staticmethod
    def srt_to_ass(srt_content):
        header = (
            "[Script Info]\n"
            "; Script generated by NollySub Subtitle Converter\n"
            "Title: NollySub Converted Subtitle\n"
            "ScriptType: v4.00+\n"
            "WrapStyle: 0\n"
            "ScaledBorderAndShadow: yes\n"
            "YCbCr Matrix: None\n"
            "PlayResX: 1920\n"
            "PlayResY: 1080\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,20,20,20,1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )
        parsed = SubtitleConverter.parse_srt(srt_content)
        events = []

        for start, end, text in parsed:
            ass_start = SubtitleConverter.fmt_ass_time(start)
            ass_end = SubtitleConverter.fmt_ass_time(end)
            ass_text = SubtitleConverter.convert_html_to_ass_tags(text)
            ass_text = ass_text.replace('\n', '\\N')
            events.append(f"Dialogue: 0,{ass_start},{ass_end},Default,,0,0,0,,{ass_text}")

        return header + "\n".join(events)

    @staticmethod
    def ass_to_srt(ass_content):
        if not ass_content:
            return ""
        if ass_content.startswith('\ufeff'):
            ass_content = ass_content[1:]
        lines = ass_content.splitlines()

        events = []
        in_events = False
        format_headers = []
        start_idx = 1
        end_idx = 2
        text_idx = 9

        for line in lines:
            line_str = line.strip()
            if line_str.lower() == "[events]":
                in_events = True
                continue
            if in_events:
                if line_str.startswith("Format:"):
                    format_headers = [h.strip().lower() for h in line_str[7:].split(",")]
                    if "start" in format_headers:
                        start_idx = format_headers.index("start")
                    if "end" in format_headers:
                        end_idx = format_headers.index("end")
                    if "text" in format_headers:
                        text_idx = format_headers.index("text")
                elif line_str.startswith("Dialogue:"):
                    max_split = len(format_headers) - 1 if format_headers else 9
                    parts = line_str[9:].split(",", max_split)
                    if len(parts) > max(start_idx, end_idx, text_idx):
                        start_t = parts[start_idx].strip()
                        end_t = parts[end_idx].strip()
                        raw_txt = parts[text_idx].strip()
                        raw_txt = raw_txt.replace("\\N", "\n").replace("\\n", "\n")
                        clean_txt = SubtitleConverter.convert_ass_tags_to_html(raw_txt)
                        events.append((start_t, end_t, clean_txt))

        srt_blocks = []
        for idx, (start_t, end_t, txt) in enumerate(events, 1):
            srt_start = SubtitleConverter.fmt_srt_time(start_t)
            srt_end = SubtitleConverter.fmt_srt_time(end_t)
            srt_blocks.append(f"{idx}\n{srt_start} --> {srt_end}\n{txt}\n")

        return "\n".join(srt_blocks)

    @staticmethod
    def srt_to_vtt(srt_content):
        """SRT içeriğini WebVTT (.vtt) formatına dönüştürür."""
        parsed = SubtitleConverter.parse_srt(srt_content)
        vtt_lines = ["WEBVTT", ""]
        for start, end, text in parsed:
            vtt_start = start.replace(',', '.')
            vtt_end = end.replace(',', '.')
            if vtt_start.count(':') == 1:
                vtt_start = "00:" + vtt_start
            if vtt_end.count(':') == 1:
                vtt_end = "00:" + vtt_end
            clean_text = re.sub(r'\{[^}]+\}', '', text)
            vtt_lines.append(f"{vtt_start} --> {vtt_end}")
            vtt_lines.append(clean_text)
            vtt_lines.append("")
        return "\n".join(vtt_lines)

    @staticmethod
    def srt_to_txt(srt_content, clean_tags=True):
        """Zaman damgalarını ve etiketleri temizleyerek sadece konuşma metnini (.txt) çıkarır."""
        parsed = SubtitleConverter.parse_srt(srt_content)
        txt_lines = []
        for start, end, text in parsed:
            if clean_tags:
                text = re.sub(r'<[^>]+>', '', text)
                text = re.sub(r'\{[^}]+\}', '', text)
            txt_lines.append(text.strip())
        return "\n".join(txt_lines)

    @staticmethod
    def convert(content, src_ext, target_fmt, clean_tags=False):
        """Herhangi bir altyazı içeriğini hedef formata (srt, ass, vtt, txt) dönüştürür."""
        if not content or not content.strip():
            return ""

        src_ext = (src_ext or "").lower().strip()
        if src_ext and not src_ext.startswith('.'):
            src_ext = '.' + src_ext

        is_ass = "[Script Info]" in content or "Dialogue:" in content
        is_vtt = content.strip().startswith("WEBVTT")

        if is_vtt or src_ext == ".vtt":
            srt_mid = SubtitleConverter.vtt_to_srt(content)
        elif is_ass or src_ext in [".ass", ".ssa"]:
            srt_mid = SubtitleConverter.ass_to_srt(content)
        else:
            srt_mid = content

        parsed = SubtitleConverter.parse_srt(srt_mid)
        if not parsed:
            if "[Script Info]" in content or "Dialogue:" in content:
                srt_mid = SubtitleConverter.ass_to_srt(content)
                parsed = SubtitleConverter.parse_srt(srt_mid)
            elif "WEBVTT" in content or "-->" in content:
                srt_mid = SubtitleConverter.vtt_to_srt(content)
                parsed = SubtitleConverter.parse_srt(srt_mid)

        if clean_tags:
            srt_mid = re.sub(r'<[^>]+>', '', srt_mid)

        target_fmt = target_fmt.lower().replace('.', '').strip()
        if target_fmt == "srt":
            if parsed:
                blocks = []
                for idx, (start, end, txt) in enumerate(parsed, 1):
                    blocks.append(f"{idx}\n{start} --> {end}\n{txt}\n")
                return "\n".join(blocks)
            return srt_mid
        elif target_fmt == "ass":
            return SubtitleConverter.srt_to_ass(srt_mid)
        elif target_fmt == "vtt":
            return SubtitleConverter.srt_to_vtt(srt_mid)
        elif target_fmt == "txt":
            return SubtitleConverter.srt_to_txt(srt_mid, clean_tags=clean_tags)
        else:
            return srt_mid



# ══════════════════════════════════════════════════════
# MKV ARAÇLARI (ALTYAZI VE DUBLAJ/SES İZİ YÖNETİMİ)
# ══════════════════════════════════════════════════════

class MkvTools:
    """MKV dosyalarından altyazı çıkarma ve dublaj/ses parçası değiştirme işlemleri."""

    @staticmethod
    def get_tracks(mkv_path, mkvmerge_bin):
        """MKV dosyasındaki tüm parçaları (Video, Ses, Altyazı) listeler."""
        cmd = [mkvmerge_bin, "-J", mkv_path]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if res.returncode != 0:
            raise Exception("MKV dosyası okunamadı.")

        info = json.loads(res.stdout)
        tracks = []
        for t in info.get("tracks", []):
            props = t.get("properties", {})
            lang_ietf = props.get("language_ietf", "")
            lang_raw = props.get("language", "")
            lang = lang_ietf or lang_raw or "und"
            tracks.append({
                "id": t["id"],
                "type": t["type"],
                "codec": t.get("codec", ""),
                "language": lang,
                "language_ietf": lang_ietf,
                "language_raw": lang_raw,
                "name": props.get("track_name", ""),
                "default": props.get("default_track", False),
                "forced": props.get("forced_track", False),
            })
        return tracks

    @staticmethod
    def extract_subtitles(mkv_path, output_dir, mkvextract_bin, mkvmerge_bin):
        """MKV içindeki gömülü altyazıları dışarı aktarır."""
        tracks = MkvTools.get_tracks(mkv_path, mkvmerge_bin)
        sub_tracks = [t for t in tracks if t["type"] == "subtitles"]

        if not sub_tracks:
            return []

        extracted = []
        base = Path(mkv_path).stem

        for t in sub_tracks:
            tid = t["id"]
            lang = t["language"]
            codec = t["codec"].lower()

            ext = ".srt"
            if "ass" in codec or "ssa" in codec:
                ext = ".ass"
            elif "pgs" in codec or "hdmv" in codec:
                ext = ".sup"
            elif "vobsub" in codec:
                ext = ".idx"

            out_file = os.path.join(output_dir, f"{base}.{lang}.track{tid}{ext}")
            cmd = [mkvextract_bin, "tracks", mkv_path, f"{tid}:{out_file}"]

            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
            if res.returncode == 0 and os.path.exists(out_file):
                extracted.append(out_file)

        return extracted

    @staticmethod
    def set_default_audio(mkv_path, audio_track_id, mkvpropedit_bin):
        """MKV içindeki varsayılan ses (dublaj) izini değiştirir."""
        tracks = MkvTools.get_tracks(mkv_path, shutil.which("mkvmerge") or "mkvmerge")
        audio_tracks = [t for t in tracks if t["type"] == "audio"]

        cmd = [mkvpropedit_bin, mkv_path]
        for t in audio_tracks:
            is_def = "1" if t["id"] == audio_track_id else "0"
            cmd.extend(["--edit", f"track:{t['id'] + 1}", "--set", f"flag-default={is_def}"])

        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        return res.returncode == 0


# ══════════════════════════════════════════════════════
# GUI UYGULAMASI (NollySubApp)
# ══════════════════════════════════════════════════════

class NollySubApp:
    """NollySub Anime Türkçe Altyazı İndirici ana penceresi."""

    def __init__(self):
        self.config = ConfigManager()
        self.engines = []
        self.results = []
        self._init_engines()
        self._build_ui()

    def _init_engines(self):
        """API motorlarını başlat."""
        self.engines = []

        # Her zaman aktif motorlar (API Key gerektirmez)
        self.engines.append(NyaaEngine())
        self.engines.append(SubsPleaseEngine())
        self.engines.append(AnimeToshoEngine())

        os_key = self.config.get_opensubtitles_key()
        if os_key:
            self.engines.append(OpenSubtitlesEngine(os_key))

        sd_key = self.config.get_subdl_key()
        if sd_key:
            self.engines.append(SubDLEngine(sd_key))

    # ── UI OLUŞTURMA ──

    def _build_ui(self):
        """Ana pencereyi oluştur."""
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("1080x720")
        self.root.minsize(850, 580)
        self.root.configure(bg=COLORS["bg_deepest"])

        # Logo ve ikon yükleme
        self._load_app_icons()

        # Stil ayarları
        self._configure_styles()

        # Ana çerçeve
        main_frame = tk.Frame(self.root, bg=COLORS["bg_deepest"])
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Başlık çubuğu
        self._build_header(main_frame)

        # Arama bölümü
        self._build_search_section(main_frame)

        # Sonuç tablosu
        self._build_results_table(main_frame)

        # Alt çubuk (durum + indirme)
        self._build_footer(main_frame)

        # Uyarılarda bulun
        if not self.engines:
            self.root.after(500, self._show_api_setup_prompt)

    def _load_app_icons(self):
        """Uygulama logosunu ve ikonlarını yükler."""
        assets_dir = Path(__file__).parent / "assets"
        icon_path = assets_dir / "icon.ico"
        avatar_path = assets_dir / "logo_avatar.png"
        logo_path = assets_dir / "logo.png"

        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass

        self.header_logo_photo = None
        target_img = avatar_path if avatar_path.exists() else logo_path

        if target_img.exists() and HAS_PIL:
            try:
                img = Image.open(target_img).convert("RGBA")
                img = img.resize((42, 42), Image.Resampling.LANCZOS)
                self.header_logo_photo = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, self.header_logo_photo)
            except Exception as e:
                print("Logo yükleme uyarısı:", e)

    def _configure_styles(self):
        """ttk stillerini yapılandır."""
        style = ttk.Style()
        style.theme_use("clam")

        # Treeview stili
        style.configure("Dark.Treeview",
                        background=COLORS["bg_deep"],
                        foreground=COLORS["text_primary"],
                        fieldbackground=COLORS["bg_deep"],
                        borderwidth=0,
                        rowheight=38,
                        font=("Segoe UI", 10))

        style.configure("Dark.Treeview.Heading",
                        background=COLORS["bg_surface"],
                        foreground=COLORS["text_secondary"],
                        borderwidth=1,
                        relief="flat",
                        font=("Segoe UI", 10, "bold"),
                        padding=(10, 8))

        style.map("Dark.Treeview",
                  background=[("selected", COLORS["accent"])],
                  foreground=[("selected", "#ffffff")])

        style.map("Dark.Treeview.Heading",
                  background=[("active", COLORS["bg_elevated"])])

        # Scrollbar stili
        style.configure("Dark.Vertical.TScrollbar",
                        background=COLORS["bg_surface"],
                        troughcolor=COLORS["bg_deepest"],
                        bordercolor=COLORS["bg_deepest"],
                        arrowcolor=COLORS["text_muted"],
                        relief="flat")

        # İlerleme Çubuğu (Progressbar) Stili
        style.configure("Custom.Horizontal.TProgressbar",
                        troughcolor=COLORS["bg_deep"],
                        background=COLORS["accent"],
                        thickness=8,
                        borderwidth=0)

    def _build_header(self, parent):
        """Üst başlık bölümü."""
        header = tk.Frame(parent, bg=COLORS["bg_surface"], height=70)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        # Logo ve Başlık
        logo_frame = tk.Frame(header, bg=COLORS["bg_surface"])
        logo_frame.pack(side=tk.LEFT, padx=16)

        if self.header_logo_photo:
            logo_box = tk.Label(logo_frame, image=self.header_logo_photo, bg=COLORS["bg_surface"])
            logo_box.pack(side=tk.LEFT, padx=(0, 10), pady=12)
        else:
            logo_box = tk.Label(logo_frame, text=" NS ", bg=COLORS["accent"],
                                fg="white", font=("Segoe UI", 14, "bold"),
                                padx=4, pady=2)
            logo_box.pack(side=tk.LEFT, padx=(0, 10), pady=12)

        title_label = tk.Label(logo_frame, text="NollySub",
                               bg=COLORS["bg_surface"],
                               fg=COLORS["text_primary"],
                               font=("Segoe UI", 18, "bold"))
        title_label.pack(side=tk.LEFT)

        subtitle_label = tk.Label(logo_frame, text="Anime Türkçe Altyazı & Torrent İndirici",
                                  bg=COLORS["bg_surface"],
                                  fg=COLORS["text_muted"],
                                  font=("Segoe UI", 9))
        subtitle_label.pack(side=tk.LEFT, padx=(8, 0), pady=(4, 0))

        # Sağ taraf butonlar
        btn_frame = tk.Frame(header, bg=COLORS["bg_surface"])
        btn_frame.pack(side=tk.RIGHT, padx=16)

        # Araçlar Menüsü
        self.tools_menu = tk.Menu(self.root, tearoff=0,
                                  bg=COLORS["bg_elevated"], fg=COLORS["text_primary"],
                                  activebackground=COLORS["accent"], activeforeground="white",
                                  font=("Segoe UI", 10))
        self.tools_menu.add_command(label="🎬  MKV Altyazı Çıkar & Dönüştür", command=self._extract_subtitles_from_mkv_gui)
        self.tools_menu.add_command(label="🎙️  MKV Dublaj Değiştir", command=self._show_mkv_dub_changer_gui)
        self.tools_menu.add_separator()
        self.tools_menu.add_command(label="🔄  Toplu Altyazı Dönüştür (SRT / ASS / VTT / TXT)", command=self._show_subtitle_converter_gui)
        self.tools_menu.add_command(label="📌  Masaüstü Kısayolu Oluştur", command=self._create_desktop_shortcut)

        def _popup_tools_menu():
            try:
                x = tools_btn.winfo_rootx()
                y = tools_btn.winfo_rooty() + tools_btn.winfo_height() + 4
                self.tools_menu.tk_popup(x, y)
            finally:
                self.tools_menu.grab_release()

        tools_btn = tk.Button(btn_frame, text="🛠️ Araçlar ▾",
                              bg=COLORS["bg_elevated"], fg=COLORS["text_primary"],
                              font=("Segoe UI", 9, "bold"),
                              relief="flat", cursor="hand2",
                              activebackground=COLORS["border_light"],
                              activeforeground="white",
                              padx=12, pady=5,
                              command=_popup_tools_menu)
        tools_btn.pack(side=tk.LEFT, padx=4)

        folder_btn = tk.Button(btn_frame, text="📁 İndirilenler",
                               bg=COLORS["bg_elevated"], fg=COLORS["text_secondary"],
                               font=("Segoe UI", 9),
                               relief="flat", cursor="hand2",
                               activebackground=COLORS["border_light"],
                               activeforeground=COLORS["text_primary"],
                               padx=12, pady=5,
                               command=self._open_download_folder)
        folder_btn.pack(side=tk.LEFT, padx=4)

        settings_btn = tk.Button(btn_frame, text="⚙️ Ayarlar",
                                 bg=COLORS["accent"], fg="white",
                                 font=("Segoe UI", 10, "bold"),
                                 relief="flat", cursor="hand2",
                                 activebackground=COLORS["accent_hover"],
                                 activeforeground="white",
                                 padx=14, pady=5,
                                 command=self._show_settings)
        settings_btn.pack(side=tk.LEFT, padx=(8, 0))

    def _build_search_section(self, parent):
        """Arama bölümü."""
        search_frame = tk.Frame(parent, bg=COLORS["bg_deepest"])
        search_frame.pack(fill=tk.X, padx=20, pady=(20, 10))

        hint_label = tk.Label(search_frame,
                              text="🔍 Anime adı yazıp Türkçe altyazı ve torrent arayın (ör: One Piece, Solo Leveling)",
                              bg=COLORS["bg_deepest"],
                              fg=COLORS["text_muted"],
                              font=("Segoe UI", 9))
        hint_label.pack(anchor=tk.W, pady=(0, 6))

        search_row = tk.Frame(search_frame, bg=COLORS["bg_deepest"])
        search_row.pack(fill=tk.X)

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_row,
                                     textvariable=self.search_var,
                                     bg=COLORS["bg_input"],
                                     fg=COLORS["text_primary"],
                                     insertbackground=COLORS["accent"],
                                     font=("Segoe UI", 13),
                                     relief="flat",
                                     highlightthickness=2,
                                     highlightbackground=COLORS["border"],
                                     highlightcolor=COLORS["accent"],
                                     selectbackground=COLORS["accent"],
                                     selectforeground="white")
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: self._do_search())
        self.search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_search_focus_out)

        self._search_placeholder_active = True
        self._set_placeholder()

        self.search_btn = tk.Button(search_row, text="🔎  Ara",
                                    bg=COLORS["accent"], fg="white",
                                    font=("Segoe UI", 11, "bold"),
                                    relief="flat", cursor="hand2",
                                    activebackground=COLORS["accent_hover"],
                                    activeforeground="white",
                                    padx=24, pady=6,
                                    command=self._do_search)
        self.search_btn.pack(side=tk.LEFT)

        # Kaynak bilgisi
        source_frame = tk.Frame(search_frame, bg=COLORS["bg_deepest"])
        source_frame.pack(fill=tk.X, pady=(8, 0))

        engine_names = ", ".join(e.NAME for e in self.engines) if self.engines else "Yapılandırılmadı"
        engine_color = COLORS["success"] if self.engines else COLORS["warning"]

        source_label = tk.Label(source_frame,
                                text=f"Aktif veritabanları & kaynaklar: {engine_names}",
                                bg=COLORS["bg_deepest"],
                                fg=engine_color,
                                font=("Segoe UI", 8))
        source_label.pack(side=tk.LEFT)
        self.source_label = source_label

    def _set_placeholder(self):
        if self._search_placeholder_active and not self.search_var.get():
            self.search_entry.insert(0, "Anime adı girin... (ör: Death Note, Bleach, Demon Slayer)")
            self.search_entry.config(fg=COLORS["text_faint"])
            self._search_placeholder_active = True

    def _on_search_focus_in(self, event):
        if self._search_placeholder_active:
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(fg=COLORS["text_primary"])
            self._search_placeholder_active = False

    def _on_search_focus_out(self, event):
        if not self.search_var.get().strip():
            self._search_placeholder_active = True
            self._set_placeholder()

    def _build_results_table(self, parent):
        """Sonuç tablosu."""
        table_frame = tk.Frame(parent, bg=COLORS["bg_deepest"])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        table_header = tk.Frame(table_frame, bg=COLORS["bg_deepest"])
        table_header.pack(fill=tk.X, pady=(0, 8))

        self.results_label = tk.Label(table_header,
                                      text="Arama sonuçları burada görünecek",
                                      bg=COLORS["bg_deepest"],
                                      fg=COLORS["text_muted"],
                                      font=("Segoe UI", 10))
        self.results_label.pack(side=tk.LEFT)

        # Tablo kapsayıcısı
        container = tk.Frame(table_frame, bg=COLORS["bg_deep"], highlightthickness=1, highlightbackground=COLORS["border"])
        container.pack(fill=tk.BOTH, expand=True)

        columns = ("source", "title", "language", "release", "download_count")
        self.tree = ttk.Treeview(container, columns=columns, show="headings", style="Dark.Treeview", selectmode="browse")

        self.tree.heading("source", text="Kaynak", anchor=tk.W)
        self.tree.heading("title", text="Başlık / Dosya Adı", anchor=tk.W)
        self.tree.heading("language", text="Dil", anchor=tk.CENTER)
        self.tree.heading("release", text="Sürüm / Detay", anchor=tk.W)
        self.tree.heading("download_count", text="İndirme / Seeds", anchor=tk.E)

        self.tree.column("source", width=120, minwidth=100, stretch=False)
        self.tree.column("title", width=380, minwidth=220, stretch=True)
        self.tree.column("language", width=110, minwidth=85, stretch=False, anchor=tk.CENTER)
        self.tree.column("release", width=200, minwidth=140, stretch=False)
        self.tree.column("download_count", width=160, minwidth=140, stretch=False, anchor=tk.E)

        # Scrollbar
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.tree.yview, style="Dark.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", lambda e: self._download_selected())

    def _build_footer(self, parent):
        """Alt çubuk (Durum ve İndirme Butonu)."""
        footer = tk.Frame(parent, bg=COLORS["bg_surface"], height=60)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)

        # Sol: Durum Etiketi ve İlerleme Çubuğu Kapsayıcısı
        status_frame = tk.Frame(footer, bg=COLORS["bg_surface"])
        status_frame.pack(side=tk.LEFT, padx=20)

        self.status_label = tk.Label(status_frame,
                                     text="Hazır",
                                     bg=COLORS["bg_surface"],
                                     fg=COLORS["text_muted"],
                                     font=("Segoe UI", 10))
        self.status_label.pack(side=tk.LEFT)

        # İlerleme çubuğu (Özel stillendirilmiş)
        self.progress = ttk.Progressbar(status_frame, mode="indeterminate", length=180, style="Custom.Horizontal.TProgressbar")

        # Sağ: İndir Butonu
        self.download_btn = tk.Button(footer,
                                      text="⬇  Seçileni İndir",
                                      bg=COLORS["accent"], fg="white",
                                      font=("Segoe UI", 10, "bold"),
                                      relief="flat", cursor="hand2",
                                      activebackground=COLORS["accent_hover"],
                                      activeforeground="white",
                                      padx=20, pady=6,
                                      command=self._download_selected)
        self.download_btn.pack(side=tk.RIGHT, padx=20, pady=10)

    # ── İŞLEMLER VE MANTIKSAL AKIŞ ──

    def _do_search(self):
        """Aramayı başlatır (arka planda)."""
        query = self.search_var.get().strip()

        if self._search_placeholder_active or not query:
            messagebox.showwarning("Uyarı", "Lütfen bir anime adı girin.")
            return

        if not self.engines:
            self._show_api_setup_prompt()
            return

        # UI güncelle
        self.search_btn.config(state=tk.DISABLED)
        self.status_label.config(text=f"'{query}' aranıyor...", fg=COLORS["info"])
        self.progress.pack(side=tk.LEFT, padx=10)
        self.progress.start(10)

        # Tabloyu temizle
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.results = []

        # Arka plan iş parçacığı
        threading.Thread(target=self._search_thread, args=(query,), daemon=True).start()

    def _search_thread(self, query):
        """Farklı kaynaklardan paralel/sıralı arama yapar."""
        all_results = []

        def search_engine(eng):
            try:
                res = eng.search(query)
                all_results.extend(res)
            except Exception as e:
                print(f"{eng.NAME} Arama Hatası: {e}")

        threads = []
        for engine in self.engines:
            t = threading.Thread(target=search_engine, args=(engine,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Türkçe olanları en üste sırala
        all_results.sort(key=lambda x: (not is_tr_subtitle(x), x.get("title", "")))

        # UI'ya ilet
        self.root.after(0, self._on_search_complete, all_results, query)

    def _on_search_complete(self, results, query):
        """Arama tamamlandığında UI'yı günceller."""
        self.progress.stop()
        self.progress.pack_forget()
        self.search_btn.config(state=tk.NORMAL)

        self.results = results

        if not results:
            self.status_label.config(text=f"'{query}' için sonuç bulunamadı.", fg=COLORS["warning"])
            self.results_label.config(text="Sonuç bulunamadı.")
            return

        tr_count = sum(1 for r in results if is_tr_subtitle(r))
        self.status_label.config(text=f"Toplam {len(results)} sonuç bulundu ({tr_count} Türkçe).", fg=COLORS["success"])
        self.results_label.config(text=f"'{query}' — {len(results)} Sonuç ({tr_count} Türkçe)")

        for idx, item in enumerate(results):
            tags = ()
            if is_tr_subtitle(item):
                tags = ("tr_row",)

            self.tree.insert("", tk.END, iid=str(idx), values=(
                item.get("source", "-"),
                item.get("title", "-"),
                item.get("language", "-"),
                item.get("release", "-"),
                item.get("download_count", "0"),
            ), tags=tags)

        self.tree.tag_configure("tr_row", foreground="#4ade80")

    def _download_selected(self):
        """Seçili altyazı veya torrent dosyasını indirir."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen indirmek için listeden bir öge seçin.")
            return

        idx = int(selected[0])
        item = self.results[idx]
        engine = item.get("_engine")

        if not engine:
            messagebox.showerror("Hata", "İndirme motoru bulunamadı.")
            return

        file_id = item.get("file_id")
        file_name = item.get("file_name", "subtitle.srt")

        self.status_label.config(text=f"İndiriliyor: {item.get('title')}...", fg=COLORS["info"])
        self.download_btn.config(state=tk.DISABLED)

        threading.Thread(target=self._download_thread, args=(engine, file_id, file_name, item), daemon=True).start()

    def _download_thread(self, engine, file_id, file_name, item):
        """İndirme işlemini gerçekleştirir."""
        try:
            content, actual_name = engine.download(file_id)
            if not actual_name:
                actual_name = file_name

            download_dir = Path(self.config.get_download_dir())
            download_dir.mkdir(parents=True, exist_ok=True)

            save_path = download_dir / actual_name

            if save_path.exists():
                stem = save_path.stem
                ext = save_path.suffix
                save_path = download_dir / f"{stem}_1{ext}"

            with open(save_path, "wb") as f:
                f.write(content)

            self.root.after(0, self._on_download_complete, str(save_path), item)

        except Exception as e:
            self.root.after(0, self._on_download_error, str(e))

    def _on_download_complete(self, save_path, item):
        """İndirme tamamlandığında bildirim gösterir."""
        self.download_btn.config(state=tk.NORMAL)
        self.status_label.config(text=f"Başarıyla indirildi: {os.path.basename(save_path)}", fg=COLORS["success"])

        ans = messagebox.askyesno(
            "İndirme Tamamlandı! 🎉",
            f"Dosya başarıyla indirildi!\n\n📍 Kaydedilen Yer:\n{save_path}\n\nİndirilenler klasörünü açmak ister misiniz?"
        )
        if ans:
            self._open_download_folder()

    def _on_download_error(self, err_msg):
        """İndirme hatasını gösterir."""
        self.download_btn.config(state=tk.NORMAL)
        self.status_label.config(text="İndirme başarısız oldu.", fg=COLORS["accent"])
        messagebox.showerror("İndirme Hatası", f"Dosya indirilirken bir hata oluştu:\n\n{err_msg}")

    # ── EK GUI PENCERELERİ VE DİYALOGLAR ──

    def _show_api_setup_prompt(self):
        """API anahtarı ayarları iletişim kutusu."""
        ans = messagebox.askyesno(
            "API Ayarları Gerekli",
            "NollySub varsayılan olarak AnimeTosho, Nyaa.si ve SubsPlease veritabanlarını kullanır.\n\n"
            "OpenSubtitles ve SubDL arşivlerine de erişebilmek için ücretsiz API anahtarı ekleyebilirsiniz.\n\n"
            "Şimdi Ayarları açmak ister misiniz?"
        )
        if ans:
            self._show_settings()

    def _open_opensubtitles_key_page(self):
        """OpenSubtitles API key alma sayfasını açar."""
        webbrowser.open("https://www.opensubtitles.com/en/consumers")

    def _open_subdl_key_page(self):
        """SubDL API key alma sayfasını açar."""
        webbrowser.open("https://subdl.com/panel/api")

    def _show_settings(self):
        """Gelişmiş Ayarlar Penceresi."""
        settings_win = tk.Toplevel(self.root)
        settings_win.title("⚙️ NollySub — Uygulama & API Ayarları")
        settings_win.geometry("640x580")
        settings_win.minsize(600, 550)
        settings_win.configure(bg=COLORS["bg_deepest"])
        settings_win.transient(self.root)
        settings_win.grab_set()

        # Üst başlık alanı
        header_frame = tk.Frame(settings_win, bg=COLORS["bg_surface"], pady=14, padx=20)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        title_lbl = tk.Label(header_frame, text="⚙️ Uygulama & API Ayarları", bg=COLORS["bg_surface"],
                             fg=COLORS["text_primary"], font=("Segoe UI", 14, "bold"))
        title_lbl.pack(anchor=tk.W)

        sub_lbl = tk.Label(header_frame,
                           text="OpenSubtitles ve SubDL servislerinden tek tıkla ücretsiz API anahtarı alabilirsiniz.",
                           bg=COLORS["bg_surface"], fg=COLORS["text_muted"], font=("Segoe UI", 9))
        sub_lbl.pack(anchor=tk.W, pady=(2, 0))

        # Ana içerik alanı
        content_frame = tk.Frame(settings_win, bg=COLORS["bg_deepest"], padx=20, pady=16)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # 1. OPENSUBTITLES API KEY
        os_card = tk.Frame(content_frame, bg=COLORS["bg_surface"], padx=14, pady=12, highlightthickness=1, highlightbackground=COLORS["border"])
        os_card.pack(fill=tk.X, pady=(0, 12))

        os_title = tk.Label(os_card, text="🌐 OpenSubtitles.com API Key", bg=COLORS["bg_surface"],
                            fg=COLORS["text_primary"], font=("Segoe UI", 10, "bold"))
        os_title.pack(anchor=tk.W)

        os_row = tk.Frame(os_card, bg=COLORS["bg_surface"])
        os_row.pack(fill=tk.X, pady=(6, 4))

        os_var = tk.StringVar(value=self.config.get_opensubtitles_key())
        os_entry = tk.Entry(os_row, textvariable=os_var, bg=COLORS["bg_input"],
                            fg=COLORS["text_primary"], font=("Segoe UI", 10),
                            relief="flat", highlightthickness=1, highlightbackground=COLORS["border"],
                            highlightcolor=COLORS["accent"], insertbackground=COLORS["accent"])
        os_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 8))

        def get_os_key():
            self._open_opensubtitles_key_page()
            messagebox.showinfo(
                "OpenSubtitles API Key",
                "Tarayıcınızda OpenSubtitles API key alma sayfası açıldı!\n\n"
                "1. Ücretsiz üye olun / giriş yapın.\n"
                "2. 'Consumer API Key' oluşturun ve kopyalayın.\n"
                "3. Kopyaladığınız anahtarı buradaki kutuya yapıştırın."
            )

        os_btn = tk.Button(os_row, text="🔑 Key Al (Tek Tıkla)", bg=COLORS["info"], fg="white",
                           font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
                           activebackground="#2563eb", activeforeground="white",
                           padx=10, pady=4, command=get_os_key)
        os_btn.pack(side=tk.RIGHT)

        os_hint = tk.Label(os_card, text="💡 OpenSubtitles veritabanından altyazı indirmek için gereklidir.",
                           bg=COLORS["bg_surface"], fg=COLORS["text_muted"], font=("Segoe UI", 9))
        os_hint.pack(anchor=tk.W)

        # 2. SUBDL API KEY
        sd_card = tk.Frame(content_frame, bg=COLORS["bg_surface"], padx=14, pady=12, highlightthickness=1, highlightbackground=COLORS["border"])
        sd_card.pack(fill=tk.X, pady=(0, 12))

        sd_title = tk.Label(sd_card, text="📦 SubDL.com API Key", bg=COLORS["bg_surface"],
                            fg=COLORS["text_primary"], font=("Segoe UI", 10, "bold"))
        sd_title.pack(anchor=tk.W)

        sd_row = tk.Frame(sd_card, bg=COLORS["bg_surface"])
        sd_row.pack(fill=tk.X, pady=(6, 4))

        sd_var = tk.StringVar(value=self.config.get_subdl_key())
        sd_entry = tk.Entry(sd_row, textvariable=sd_var, bg=COLORS["bg_input"],
                            fg=COLORS["text_primary"], font=("Segoe UI", 10),
                            relief="flat", highlightthickness=1, highlightbackground=COLORS["border"],
                            highlightcolor=COLORS["accent"], insertbackground=COLORS["accent"])
        sd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 8))

        def get_sd_key():
            self._open_subdl_key_page()
            messagebox.showinfo(
                "SubDL API Key",
                "Tarayıcınızda SubDL API key paneli açıldı!\n\n"
                "1. SubDL hesabınıza giriş yapın.\n"
                "2. Panelinizdeki API Key'i kopyalayın.\n"
                "3. Kopyaladığınız anahtarı buradaki kutuya yapıştırın."
            )

        sd_btn = tk.Button(sd_row, text="🔑 Key Al (Tek Tıkla)", bg=COLORS["info"], fg="white",
                           font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
                           activebackground="#2563eb", activeforeground="white",
                           padx=10, pady=4, command=get_sd_key)
        sd_btn.pack(side=tk.RIGHT)

        sd_hint = tk.Label(sd_card, text="💡 SubDL geniş altyazı arşivine erişmek için gereklidir.",
                           bg=COLORS["bg_surface"], fg=COLORS["text_muted"], font=("Segoe UI", 9))
        sd_hint.pack(anchor=tk.W)

        # 3. İNDİRME KLASÖRÜ
        dl_card = tk.Frame(content_frame, bg=COLORS["bg_surface"], padx=14, pady=12, highlightthickness=1, highlightbackground=COLORS["border"])
        dl_card.pack(fill=tk.X, pady=(0, 12))

        dl_title = tk.Label(dl_card, text="📁 Altyazı İndirme Klasörü", bg=COLORS["bg_surface"],
                            fg=COLORS["text_primary"], font=("Segoe UI", 10, "bold"))
        dl_title.pack(anchor=tk.W)

        dl_row = tk.Frame(dl_card, bg=COLORS["bg_surface"])
        dl_row.pack(fill=tk.X, pady=(6, 0))

        dl_var = tk.StringVar(value=self.config.get_download_dir())
        dl_entry = tk.Entry(dl_row, textvariable=dl_var, bg=COLORS["bg_input"],
                            fg=COLORS["text_primary"], font=("Segoe UI", 10),
                            relief="flat", highlightthickness=1, highlightbackground=COLORS["border"],
                            highlightcolor=COLORS["accent"], insertbackground=COLORS["accent"])
        dl_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 8))

        def browse_folder():
            folder = filedialog.askdirectory(initialdir=dl_var.get())
            if folder:
                dl_var.set(folder)

        dl_btn = tk.Button(dl_row, text="📂 Gözat...", bg=COLORS["bg_elevated"], fg=COLORS["text_primary"],
                           font=("Segoe UI", 9), relief="flat", cursor="hand2",
                           activebackground=COLORS["border_light"], activeforeground="white",
                           padx=10, pady=4, command=browse_folder)
        dl_btn.pack(side=tk.RIGHT)

        # 4. MKVTOOLNIX SİSTEM DURUMU
        mmerge, mextract, _ = self.config.find_mkvtoolnix()
        mkv_card = tk.Frame(content_frame, bg=COLORS["bg_surface"], padx=14, pady=10, highlightthickness=1, highlightbackground=COLORS["border"])
        mkv_card.pack(fill=tk.X)

        if mmerge:
            mkv_status_lbl = tk.Label(mkv_card, text="🟢 MKVToolNix Tespit Edildi: MKV Altyazı & Dublaj araçları aktif.",
                                      bg=COLORS["bg_surface"], fg=COLORS["success"], font=("Segoe UI", 9, "bold"))
            mkv_status_lbl.pack(anchor=tk.W)
        else:
            mkv_row = tk.Frame(mkv_card, bg=COLORS["bg_surface"])
            mkv_row.pack(fill=tk.X)
            mkv_status_lbl = tk.Label(mkv_row, text="⚠️ MKVToolNix Bulunamadı: MKV altyazı çıkarma için gereklidir.",
                                      bg=COLORS["bg_surface"], fg=COLORS["warning"], font=("Segoe UI", 9))
            mkv_status_lbl.pack(side=tk.LEFT)

            def get_mkv():
                webbrowser.open("https://mkvtoolnix.download/downloads.html")

            mkv_dl_btn = tk.Button(mkv_row, text="📥 İndir", bg=COLORS["bg_elevated"], fg=COLORS["warning"],
                                   font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
                                   command=get_mkv)
            mkv_dl_btn.pack(side=tk.RIGHT)

        # Alt Butonlar
        bottom_frame = tk.Frame(settings_win, bg=COLORS["bg_surface"], pady=12, padx=20)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        def save_and_close():
            self.config.set_opensubtitles_key(os_var.get().strip())
            self.config.set_subdl_key(sd_var.get().strip())
            self.config.set_download_dir(dl_var.get().strip())

            self._init_engines()

            engine_names = ", ".join(e.NAME for e in self.engines) if self.engines else "Yapılandırılmadı"
            engine_color = COLORS["success"] if self.engines else COLORS["warning"]
            self.source_label.config(text=f"Aktif veritabanları & kaynaklar: {engine_names}", fg=engine_color)

            messagebox.showinfo("Başarılı", "Ayarlar başarıyla kaydedildi!")
            settings_win.destroy()

        save_btn = tk.Button(bottom_frame, text="💾  Ayarları Kaydet", bg=COLORS["accent"], fg="white",
                             font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
                             activebackground=COLORS["accent_hover"], activeforeground="white",
                             padx=18, pady=6, command=save_and_close)
        save_btn.pack(side=tk.RIGHT, padx=(8, 0))

        cancel_btn = tk.Button(bottom_frame, text="Kapat", bg=COLORS["bg_elevated"], fg=COLORS["text_secondary"],
                               font=("Segoe UI", 10), relief="flat", cursor="hand2",
                               activebackground=COLORS["border_light"], activeforeground="white",
                               padx=14, pady=6, command=settings_win.destroy)
        cancel_btn.pack(side=tk.RIGHT)

    def _open_download_folder(self):
        """İndirme klasörünü dosya gezgininde açar."""
        d = self.config.get_download_dir()
        if os.path.exists(d):
            os.startfile(d)
        else:
            Path(d).mkdir(parents=True, exist_ok=True)
            os.startfile(d)

    def _extract_subtitles_from_mkv_gui(self):
        """MKV'den altyazı çıkarma arayüzü (Seçenek sunan tam sürüm)."""
        mmerge, mextract, _ = self.config.find_mkvtoolnix()
        if not mextract:
            messagebox.showerror(
                "MKVToolNix Bulunamadı",
                "MKV altyazı çıkarma özelliği için sisteminizde MKVToolNix kurulu olmalıdır."
            )
            return

        files = filedialog.askopenfilenames(
            title="MKV Dosyaları Seçin",
            filetypes=[("MKV Video Dosyaları", "*.mkv")]
        )
        if not files:
            return

        # Seçilen tüm MKV dosyalarındaki altyazı izlerini topla
        all_sub_tracks = []
        for fpath in files:
            try:
                tracks = MkvTools.get_tracks(fpath, mmerge)
                for t in tracks:
                    if t["type"] == "subtitles":
                        all_sub_tracks.append({
                            "mkv_path": fpath,
                            "filename": os.path.basename(fpath),
                            "track_id": t["id"],
                            "lang": t["language"],
                            "language_ietf": t.get("language_ietf", ""),
                            "language_raw": t.get("language_raw", ""),
                            "codec": t["codec"],
                            "name": t["name"],
                            "default": t["default"],
                            "forced": t["forced"]
                        })
            except Exception as e:
                print(f"Hata ({fpath}): {e}")

        if not all_sub_tracks:
            messagebox.showinfo("Bilgi", "Seçilen MKV dosyalarında gömülü altyazı izi bulunamadı.")
            return

        # Modal Pencere Oluştur
        sub_win = tk.Toplevel(self.root)
        sub_win.title("🎬 NollySub — MKV Altyazı Seçimi ve Çıkarma")
        sub_win.geometry("820x540")
        sub_win.configure(bg=COLORS["bg_surface"])
        sub_win.transient(self.root)

        # Üst Başlık
        header_frame = tk.Frame(sub_win, bg=COLORS["bg_surface"], padx=20, pady=15)
        header_frame.pack(fill=tk.X)

        tk.Label(header_frame, text="🎬 Çıkarılacak Altyazı İzlerini Seçin", bg=COLORS["bg_surface"],
                 fg=COLORS["text_primary"], font=("Segoe UI", 13, "bold")).pack(anchor=tk.W)
        tk.Label(header_frame, text=f"Toplam {len(files)} dosya içerisinden {len(all_sub_tracks)} altyazı izi bulundu. Çıkarmak istediklerinizi seçin:",
                 bg=COLORS["bg_surface"], fg=COLORS["text_muted"], font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(2, 0))

        # Hızlı Seçim Butonları
        quick_frame = tk.Frame(sub_win, bg=COLORS["bg_surface"], padx=20)
        quick_frame.pack(fill=tk.X, pady=(0, 8))

        # Treeview Liste
        tree_container = tk.Frame(sub_win, bg=COLORS["bg_deep"], highlightthickness=1, highlightbackground=COLORS["border"])
        tree_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        columns = ("select", "filename", "track_id", "lang", "codec", "name", "flags")
        tree = ttk.Treeview(tree_container, columns=columns, show="headings", style="Dark.Treeview", selectmode="extended")

        tree.heading("select", text="Durum", anchor=tk.CENTER)
        tree.heading("filename", text="Dosya Adı", anchor=tk.W)
        tree.heading("track_id", text="Pist ID", anchor=tk.CENTER)
        tree.heading("lang", text="Dil", anchor=tk.CENTER)
        tree.heading("codec", text="Format", anchor=tk.CENTER)
        tree.heading("name", text="Başlık / İsim", anchor=tk.W)
        tree.heading("flags", text="Bayraklar", anchor=tk.CENTER)

        tree.column("select", width=85, minwidth=70, stretch=False, anchor=tk.CENTER)
        tree.column("filename", width=220, minwidth=150, stretch=True, anchor=tk.W)
        tree.column("track_id", width=65, minwidth=50, stretch=False, anchor=tk.CENTER)
        tree.column("lang", width=120, minwidth=90, stretch=False, anchor=tk.CENTER)
        tree.column("codec", width=95, minwidth=70, stretch=False, anchor=tk.CENTER)
        tree.column("name", width=140, minwidth=100, stretch=False, anchor=tk.W)
        tree.column("flags", width=100, minwidth=80, stretch=False, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=tree.yview, style="Dark.Vertical.TScrollbar")
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        selected_states = {}

        def get_lang_display(item):
            code = (item.get("lang") or "und").lower()
            if is_turkish_mkv_track(item):
                return "Türkçe 🇹🇷"
            return LANG_MAP.get(code, code.upper())

        def populate_tree():
            tree.delete(*tree.get_children())
            selected_states.clear()
            for idx, item in enumerate(all_sub_tracks):
                lang_str = get_lang_display(item)
                flags = []
                if item["default"]: flags.append("Varsayılan")
                if item["forced"]: flags.append("Zorunlu")
                flag_str = ", ".join(flags) if flags else "-"

                item_id = f"item_{idx}"
                selected_states[item_id] = True
                tree.insert("", "end", iid=item_id, values=(
                    "☑️ Seçili",
                    item["filename"],
                    f"#{item['track_id']}",
                    lang_str,
                    item["codec"].upper(),
                    item["name"] or "-",
                    flag_str
                ))

        populate_tree()

        def toggle_selection(event=None):
            sel = tree.selection()
            if not sel:
                return
            for iid in sel:
                current = selected_states.get(iid, False)
                new_state = not current
                selected_states[iid] = new_state
                vals = list(tree.item(iid, "values"))
                vals[0] = "☑️ Seçili" if new_state else "☐ Seçilmedi"
                tree.item(iid, values=vals)

        tree.bind("<Double-1>", toggle_selection)
        tree.bind("<space>", toggle_selection)

        def select_all(state=True):
            for iid in selected_states:
                selected_states[iid] = state
                vals = list(tree.item(iid, "values"))
                vals[0] = "☑️ Seçili" if state else "☐ Seçilmedi"
                tree.item(iid, values=vals)

        def select_tr_only():
            tr_count = 0
            for idx, item in enumerate(all_sub_tracks):
                iid = f"item_{idx}"
                is_tr = is_turkish_mkv_track(item)
                selected_states[iid] = is_tr
                if is_tr:
                    tr_count += 1
                vals = list(tree.item(iid, "values"))
                vals[0] = "☑️ Seçili" if is_tr else "☐ Seçilmedi"
                tree.item(iid, values=vals)

            if tr_count == 0:
                messagebox.showinfo(
                    "Türkçe Altyazı Bulunamadı",
                    "Seçilen MKV dosyalarında otomatik Türkçe altyazı etiketi tespit edilemedi.\n\n"
                    "Dilerseniz listedeki diğer altyazıları elle seçip çıkarabilirsiniz."
                )
            else:
                ans = messagebox.askyesno(
                    "Türkçe Altyazılar Seçildi 🇹🇷",
                    f"Toplam {tr_count} adet Türkçe altyazı izi başarıyla seçildi.\n\n"
                    "Altyazıları çıkarmak ve bilgisayarınıza kaydetmek için şimdi klasör seçilsin mi?"
                )
                if ans:
                    start_extraction()

        tk.Button(quick_frame, text="☑️ Tümünü Seç", bg=COLORS["bg_elevated"], fg=COLORS["text_primary"],
                  font=("Segoe UI", 9), relief="flat", cursor="hand2", padx=10, pady=3,
                  command=lambda: select_all(True)).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(quick_frame, text="☐ Temizle", bg=COLORS["bg_elevated"], fg=COLORS["text_primary"],
                  font=("Segoe UI", 9), relief="flat", cursor="hand2", padx=10, pady=3,
                  command=lambda: select_all(False)).pack(side=tk.LEFT, padx=6)

        tk.Button(quick_frame, text="🇹🇷 Sadece Türkçe", bg=COLORS["accent"], fg="white",
                  font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", padx=10, pady=3,
                  command=select_tr_only).pack(side=tk.LEFT, padx=6)

        tk.Label(quick_frame, text="💡 İpucu: Çift tıklayarak veya Boşluk tuşu ile seçimi değiştirebilirsiniz.",
                 bg=COLORS["bg_surface"], fg=COLORS["text_muted"], font=("Segoe UI", 9)).pack(side=tk.RIGHT)

        # Dönüştürme Seçenekleri Kartı
        fmt_card = tk.Frame(sub_win, bg=COLORS["bg_elevated"], padx=16, pady=8, highlightthickness=1, highlightbackground=COLORS["border"])
        fmt_card.pack(fill=tk.X, padx=20, pady=(4, 0))

        tk.Label(fmt_card, text="🎯 Hedef Format:", bg=COLORS["bg_elevated"],
                 fg=COLORS["text_primary"], font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 8))

        mkv_target_fmt = tk.StringVar(value="srt")

        for fmt_val, fmt_lbl in [("srt", "SRT (.srt)"), ("ass", "ASS (.ass)"), ("txt", "Düz Metin (.txt)"), ("original", "Orijinal Format (MKV İçindeki)")]:
            rb = tk.Radiobutton(fmt_card, text=fmt_lbl, variable=mkv_target_fmt, value=fmt_val,
                                bg=COLORS["bg_elevated"], fg="white", selectcolor=COLORS["bg_deep"],
                                activebackground=COLORS["bg_elevated"])
            rb.pack(side=tk.LEFT, padx=6)

        # Alt Butonlar
        bottom_frame = tk.Frame(sub_win, bg=COLORS["bg_surface"], padx=20, pady=12)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        def start_extraction():
            to_extract = [all_sub_tracks[int(iid.split("_")[1])] for iid, sel in selected_states.items() if sel]
            if not to_extract:
                messagebox.showwarning("Uyarı", "Lütfen en az bir altyazı izi seçin.")
                return

            out_dir = filedialog.askdirectory(title="Altyazıların Kaydedileceği Klasörü Seçin")
            if not out_dir:
                return

            target_fmt = mkv_target_fmt.get().lower()
            extracted_files = []
            failed_count = 0

            for item in to_extract:
                try:
                    fpath = item["mkv_path"]
                    tid = item["track_id"]
                    lang = item["lang"]
                    codec = item["codec"].lower()

                    raw_ext = ".srt"
                    if "ass" in codec or "ssa" in codec:
                        raw_ext = ".ass"
                    elif "pgs" in codec or "hdmv" in codec:
                        raw_ext = ".sup"
                    elif "vobsub" in codec:
                        raw_ext = ".idx"
                    elif "vtt" in codec or "webvtt" in codec:
                        raw_ext = ".vtt"

                    base = Path(fpath).stem
                    raw_out_file = os.path.join(out_dir, f"{base}.{lang}.track{tid}{raw_ext}")
                    cmd = [mextract, "tracks", fpath, f"{tid}:{raw_out_file}"]
                    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")

                    if res.returncode == 0 and os.path.exists(raw_out_file):
                        # İstenen hedef formata dönüştür
                        if target_fmt != "original" and raw_ext in [".vtt", ".ass", ".ssa", ".srt", ".txt"]:
                            try:
                                content = read_text_file(raw_out_file)
                                res_text = SubtitleConverter.convert(content, raw_ext, target_fmt)
                                final_ext = f".{target_fmt}"
                                final_out_file = os.path.join(out_dir, f"{base}.{lang}.track{tid}{final_ext}")

                                with open(final_out_file, "w", encoding="utf-8-sig") as f:
                                    f.write(res_text)

                                if os.path.abspath(raw_out_file) != os.path.abspath(final_out_file) and os.path.exists(raw_out_file):
                                    os.remove(raw_out_file)

                                extracted_files.append(final_out_file)
                            except Exception as e_conv:
                                print(f"Dönüştürme hatası: {e_conv}")
                                extracted_files.append(raw_out_file)
                        else:
                            extracted_files.append(raw_out_file)
                    else:
                        failed_count += 1
                except Exception as e:
                    print(f"Altyazı çıkarma hatası: {e}")
                    failed_count += 1

            try:
                sub_win.destroy()
            except Exception:
                pass

            if extracted_files:
                fmt_str = target_fmt.upper() if target_fmt != "original" else "Orijinal"
                ans = messagebox.askyesno(
                    "İşlem Tamamlandı 🎉",
                    f"Seçilen {len(extracted_files)} adet altyazı başarıyla çıkarıldı ve {fmt_str} formatına dönüştürüldü!\n"
                    + (f"({failed_count} altyazı çıkarılamadı)\n\n" if failed_count > 0 else "\n")
                    + f"Konum: {out_dir}\n\nKlasör açılsın mı?"
                )
                if ans and os.path.exists(out_dir):
                    os.startfile(out_dir)
            else:
                messagebox.showerror(
                    "Altyazı Çıkarılamadı",
                    "Seçilen altyazılar çıkarılırken bir sorun oluştu veya kayıt klasörüne erişilemedi.\n\n"
                    "Lütfen MKVToolNix aracının sisteminizde tam kurulu olduğundan emin olun."
                )

        tk.Button(bottom_frame, text="⚡  Altyazıları Çıkar & Dönüştür", bg=COLORS["success"], fg="white",
                  font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2", padx=20, pady=6,
                  command=start_extraction).pack(side=tk.RIGHT)

        tk.Button(bottom_frame, text="İptal", bg=COLORS["bg_elevated"], fg=COLORS["text_secondary"],
                  font=("Segoe UI", 10), relief="flat", cursor="hand2", padx=14, pady=6,
                  command=sub_win.destroy).pack(side=tk.RIGHT, padx=8)

    def _show_mkv_dub_changer_gui(self):
        """MKV dublaj/ses izi değiştirici arayüzü (Tam Çalışan Sürüm)."""
        mmerge, _, mpropedit = self.config.find_mkvtoolnix()
        if not mpropedit:
            messagebox.showerror(
                "MKVToolNix Bulunamadı",
                "Dublaj değiştirme özelliği için sisteminizde MKVToolNix kurulu olmalıdır."
            )
            return

        dub_win = tk.Toplevel(self.root)
        dub_win.title("🎙️ NollySub — MKV Dublaj & Ses İzi Değiştirici")
        dub_win.geometry("740x540")
        dub_win.configure(bg=COLORS["bg_surface"])
        dub_win.transient(self.root)

        # Üst Bilgi
        header_frame = tk.Frame(dub_win, bg=COLORS["bg_surface"], padx=20, pady=15)
        header_frame.pack(fill=tk.X)

        tk.Label(header_frame, text="🎙️ MKV Varsayılan Ses İzi (Dublaj) Ayarlayıcı", bg=COLORS["bg_surface"],
                 fg=COLORS["text_primary"], font=("Segoe UI", 13, "bold")).pack(anchor=tk.W)
        tk.Label(header_frame, text="MKV dosyasındaki varsayılan ses izini (Japonca, Türkçe, İngilizce vb.) doğrudan günceller.",
                 bg=COLORS["bg_surface"], fg=COLORS["text_muted"], font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(2, 0))

        # Dosya Seçim Alanı
        file_card = tk.Frame(dub_win, bg=COLORS["bg_elevated"], padx=15, pady=12, highlightthickness=1, highlightbackground=COLORS["border"])
        file_card.pack(fill=tk.X, padx=20, pady=5)

        selected_files = []
        file_label_var = tk.StringVar(value="Henüz dosya seçilmedi")

        tk.Label(file_card, textvariable=file_label_var, bg=COLORS["bg_elevated"],
                 fg=COLORS["text_primary"], font=("Segoe UI", 9, "bold"), anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Ses İzleri Listesi
        tracks_frame = tk.Frame(dub_win, bg=COLORS["bg_surface"], padx=20, pady=10)
        tracks_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(tracks_frame, text="Mevcut Ses İzleri (Dublajlar):", bg=COLORS["bg_surface"],
                 fg=COLORS["text_secondary"], font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))

        list_container = tk.Frame(tracks_frame, bg=COLORS["bg_deep"], highlightthickness=1, highlightbackground=COLORS["border"])
        list_container.pack(fill=tk.BOTH, expand=True)

        selected_audio_id = tk.IntVar(value=-1)
        audio_tracks = []

        inner_tracks_frame = tk.Frame(list_container, bg=COLORS["bg_deep"])
        inner_tracks_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def get_lang_display(code):
            code = (code or "und").lower()
            return LANG_MAP.get(code, code.upper())

        def load_mkv_tracks():
            nonlocal audio_tracks
            for widget in inner_tracks_frame.winfo_children():
                widget.destroy()

            if not selected_files:
                tk.Label(inner_tracks_frame, text="Lütfen yukarıdaki butondan bir MKV dosyası seçin.",
                         bg=COLORS["bg_deep"], fg=COLORS["text_muted"], font=("Segoe UI", 10)).pack(pady=40)
                return

            try:
                all_t = MkvTools.get_tracks(selected_files[0], mmerge)
                audio_tracks = [t for t in all_t if t["type"] == "audio"]

                if not audio_tracks:
                    tk.Label(inner_tracks_frame, text="Seçilen dosyada herhangi bir ses izi bulunamadı.",
                             bg=COLORS["bg_deep"], fg=COLORS["warning"], font=("Segoe UI", 10)).pack(pady=40)
                    return

                def_id = audio_tracks[0]["id"]
                for t in audio_tracks:
                    if t["default"]:
                        def_id = t["id"]
                        break
                selected_audio_id.set(def_id)

                for t in audio_tracks:
                    tid = t["id"]
                    lang_str = get_lang_display(t["language"])
                    name_str = t["name"] or "-"
                    codec_str = t["codec"].upper()
                    is_def = t["default"]

                    row = tk.Frame(inner_tracks_frame, bg=COLORS["bg_surface"], padx=12, pady=10,
                                   highlightthickness=1, highlightbackground=COLORS["border"])
                    row.pack(fill=tk.X, pady=4)

                    rb = tk.Radiobutton(row, text="", variable=selected_audio_id, value=tid,
                                        bg=COLORS["bg_surface"], selectcolor=COLORS["bg_deep"], activebackground=COLORS["bg_surface"])
                    rb.pack(side=tk.LEFT)

                    lbl_txt = f"Ses İzi #{tid+1}  |  Dil: {lang_str}  |  Format: {codec_str}  |  İsim: {name_str}"
                    if is_def:
                        lbl_txt += "  🟢 [Mevcut Varsayılan]"

                    lbl = tk.Label(row, text=lbl_txt, bg=COLORS["bg_surface"],
                                   fg=COLORS["success"] if is_def else COLORS["text_primary"],
                                   font=("Segoe UI", 10, "bold" if is_def else "normal"))
                    lbl.pack(side=tk.LEFT, padx=8)

            except Exception as e:
                tk.Label(inner_tracks_frame, text=f"MKV dosyası okunamadı: {e}",
                         bg=COLORS["bg_deep"], fg=COLORS["accent"], font=("Segoe UI", 9)).pack(pady=20)

        def browse_mkv():
            nonlocal selected_files
            files = filedialog.askopenfilenames(
                title="MKV Dosyası veya Dosyaları Seçin",
                filetypes=[("MKV Video Dosyaları", "*.mkv")]
            )
            if files:
                selected_files = list(files)
                if len(selected_files) == 1:
                    file_label_var.set(f"📄 {os.path.basename(selected_files[0])}")
                else:
                    file_label_var.set(f"📁 Toplam {len(selected_files)} adet MKV dosyası seçildi")
                load_mkv_tracks()

        tk.Button(file_card, text="📁 MKV Dosyası Seç", bg=COLORS["accent"], fg="white",
                  font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", padx=12, pady=4,
                  command=browse_mkv).pack(side=tk.RIGHT)

        load_mkv_tracks()

        # Alt İşlem Butonları
        bottom_frame = tk.Frame(dub_win, bg=COLORS["bg_surface"], padx=20, pady=15)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        def apply_default_audio():
            if not selected_files:
                messagebox.showwarning("Uyarı", "Lütfen en az bir MKV dosyası seçin.")
                return
            target_id = selected_audio_id.get()
            if target_id < 0:
                messagebox.showwarning("Uyarı", "Lütfen varsayılan yapmak istediğiniz ses izini seçin.")
                return

            success_count = 0
            for fpath in selected_files:
                try:
                    if MkvTools.set_default_audio(fpath, target_id, mpropedit, mmerge):
                        success_count += 1
                except Exception as e:
                    print(f"Hata ({fpath}): {e}")

            if success_count > 0:
                messagebox.showinfo("Başarılı 🎉", f"Toplam {success_count} MKV dosyasında varsayılan ses izi (dublaj) başarıyla güncellendi!")
                load_mkv_tracks()
            else:
                messagebox.showerror("Hata", "Varsayılan ses izi güncellenirken bir hata oluştu.")

        tk.Button(bottom_frame, text="💾  Varsayılan Ses İzini Güncelle", bg=COLORS["success"], fg="white",
                  font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2", padx=18, pady=6,
                  command=apply_default_audio).pack(side=tk.RIGHT)

        tk.Button(bottom_frame, text="Kapat", bg=COLORS["bg_elevated"], fg=COLORS["text_secondary"],
                  font=("Segoe UI", 10), relief="flat", cursor="hand2", padx=14, pady=6,
                  command=dub_win.destroy).pack(side=tk.RIGHT, padx=8)

    def _show_subtitle_converter_gui(self):
        """Toplu altyazı format dönüştürücü arayüzü (SRT, ASS, VTT, TXT)."""
        conv_win = tk.Toplevel(self.root)
        conv_win.title("🔄 NollySub — Toplu Altyazı Format Dönüştürücü")
        conv_win.geometry("860x620")
        conv_win.minsize(760, 520)
        conv_win.configure(bg=COLORS["bg_surface"])
        conv_win.transient(self.root)
        conv_win.grab_set()

        # Üst Başlık
        header_frame = tk.Frame(conv_win, bg=COLORS["bg_surface"], padx=20, pady=12)
        header_frame.pack(fill=tk.X)

        tk.Label(header_frame, text="🔄 Toplu Altyazı Format Dönüştürücü", bg=COLORS["bg_surface"],
                 fg=COLORS["text_primary"], font=("Segoe UI", 13, "bold")).pack(anchor=tk.W)
        tk.Label(header_frame, text="Birden fazla altyazı dosyasını veya bir klasördeki tüm altyazıları toplu olarak SRT, ASS, VTT veya TXT formatına dönüştürün.",
                 bg=COLORS["bg_surface"], fg=COLORS["text_muted"], font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(2, 0))

        # Kontrol Butonları (Üst Ekleme / Silme Çubuğu)
        ctrl_frame = tk.Frame(conv_win, bg=COLORS["bg_surface"], padx=20, pady=6)
        ctrl_frame.pack(fill=tk.X)

        queue_items = {}

        def update_tree_summary():
            count = len(queue_items)
            summary_label.config(text=f"Kuyrukta {count} adet dosya var")

        def add_files(file_list=None):
            if not file_list:
                file_list = filedialog.askopenfilenames(
                    title="Altyazı Dosyaları Seçin",
                    filetypes=[("Altyazı Dosyaları", "*.vtt;*.srt;*.ass;*.ssa;*.txt;*.sub")]
                )
            if not file_list:
                return

            existing_paths = set(queue_items.values())
            for fpath in file_list:
                norm_p = os.path.abspath(fpath)
                if norm_p not in existing_paths:
                    iid = f"item_{len(queue_items) + 1}_{hash(norm_p) & 0xfffffff}"
                    queue_items[iid] = norm_p
                    existing_paths.add(norm_p)

                    fname = os.path.basename(norm_p)
                    ext = (os.path.splitext(norm_p)[1].upper() or ".SRT")
                    folder = os.path.dirname(norm_p)

                    tree.insert("", "end", iid=iid, values=(
                        "⏳ Bekliyor",
                        fname,
                        ext,
                        target_fmt_var.get().upper(),
                        folder
                    ))
            update_tree_summary()

        def add_folder():
            folder = filedialog.askdirectory(title="Altyazı Dosyalarını İçeren Klasörü Seçin")
            if not folder:
                return

            sub_exts = {".srt", ".ass", ".ssa", ".vtt", ".txt", ".sub"}
            found_files = []
            for root, dirs, files in os.walk(folder):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in sub_exts:
                        found_files.append(os.path.join(root, f))

            if found_files:
                add_files(found_files)
            else:
                messagebox.showinfo("Bilgi", "Seçilen klasörde uygun altyazı dosyası bulunamadı.")

        def remove_selected():
            sel = tree.selection()
            if not sel:
                return
            for iid in sel:
                if iid in queue_items:
                    del queue_items[iid]
                tree.delete(iid)
            update_tree_summary()

        def clear_all():
            queue_items.clear()
            for child in tree.get_children():
                tree.delete(child)
            update_tree_summary()

        tk.Button(ctrl_frame, text="➕ Dosya(lar) Ekle", bg=COLORS["accent"], fg="white",
                  font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", padx=12, pady=4,
                  command=add_files).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(ctrl_frame, text="📁 Klasör Ekle", bg=COLORS["bg_elevated"], fg=COLORS["text_primary"],
                  font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", padx=12, pady=4,
                  command=add_folder).pack(side=tk.LEFT, padx=6)

        tk.Button(ctrl_frame, text="🗑️ Seçileni Çıkar", bg=COLORS["bg_elevated"], fg=COLORS["text_secondary"],
                  font=("Segoe UI", 9), relief="flat", cursor="hand2", padx=10, pady=4,
                  command=remove_selected).pack(side=tk.LEFT, padx=6)

        tk.Button(ctrl_frame, text="🧹 Listeyi Temizle", bg=COLORS["bg_elevated"], fg=COLORS["text_secondary"],
                  font=("Segoe UI", 9), relief="flat", cursor="hand2", padx=10, pady=4,
                  command=clear_all).pack(side=tk.LEFT, padx=6)

        summary_label = tk.Label(ctrl_frame, text="Kuyrukta 0 adet dosya var", bg=COLORS["bg_surface"],
                                 fg=COLORS["text_muted"], font=("Segoe UI", 9))
        summary_label.pack(side=tk.RIGHT)

        # Kuyruk Tablosu
        tree_container = tk.Frame(conv_win, bg=COLORS["bg_deep"], highlightthickness=1, highlightbackground=COLORS["border"])
        tree_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=6)

        columns = ("status", "filename", "src_fmt", "target_fmt", "folder")
        tree = ttk.Treeview(tree_container, columns=columns, show="headings", style="Dark.Treeview", selectmode="extended")

        tree.heading("status", text="Durum", anchor=tk.CENTER)
        tree.heading("filename", text="Dosya Adı", anchor=tk.W)
        tree.heading("src_fmt", text="Kaynak Format", anchor=tk.CENTER)
        tree.heading("target_fmt", text="Hedef Format", anchor=tk.CENTER)
        tree.heading("folder", text="Klasör Konumu", anchor=tk.W)

        tree.column("status", width=110, minwidth=90, stretch=False, anchor=tk.CENTER)
        tree.column("filename", width=220, minwidth=140, stretch=True, anchor=tk.W)
        tree.column("src_fmt", width=100, minwidth=80, stretch=False, anchor=tk.CENTER)
        tree.column("target_fmt", width=100, minwidth=80, stretch=False, anchor=tk.CENTER)
        tree.column("folder", width=280, minwidth=180, stretch=True, anchor=tk.W)

        scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=tree.yview, style="Dark.Vertical.TScrollbar")
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Seçenekler Kartı (Format ve Çıktı Konumu)
        opts_card = tk.Frame(conv_win, bg=COLORS["bg_elevated"], padx=16, pady=10, highlightthickness=1, highlightbackground=COLORS["border"])
        opts_card.pack(fill=tk.X, padx=20, pady=6)

        # Row 1: Hedef Format
        row1 = tk.Frame(opts_card, bg=COLORS["bg_elevated"])
        row1.pack(fill=tk.X, pady=(0, 6))

        tk.Label(row1, text="🎯 Hedef Format:", bg=COLORS["bg_elevated"], fg=COLORS["text_primary"],
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))

        target_fmt_var = tk.StringVar(value="srt")

        def on_fmt_change():
            tgt = target_fmt_var.get().upper()
            for iid in tree.get_children():
                vals = list(tree.item(iid, "values"))
                vals[3] = tgt
                tree.item(iid, values=vals)

        for fmt_val, fmt_name in [("srt", "SRT (.srt)"), ("ass", "ASS (.ass)"), ("vtt", "WebVTT (.vtt)"), ("txt", "Düz Metin (.txt)")]:
            rb = tk.Radiobutton(row1, text=fmt_name, variable=target_fmt_var, value=fmt_val,
                                bg=COLORS["bg_elevated"], fg="white", selectcolor=COLORS["bg_deep"],
                                activebackground=COLORS["bg_elevated"], command=on_fmt_change)
            rb.pack(side=tk.LEFT, padx=8)

        clean_tags_var = tk.BooleanVar(value=False)
        cb_clean = tk.Checkbutton(row1, text="✂️ HTML/Stil etiketlerini temizle", variable=clean_tags_var,
                                  bg=COLORS["bg_elevated"], fg=COLORS["text_secondary"], selectcolor=COLORS["bg_deep"],
                                  activebackground=COLORS["bg_elevated"])
        cb_clean.pack(side=tk.RIGHT)

        # Row 2: Çıktı Klasörü
        row2 = tk.Frame(opts_card, bg=COLORS["bg_elevated"])
        row2.pack(fill=tk.X)

        tk.Label(row2, text="📁 Çıktı Konumu:", bg=COLORS["bg_elevated"], fg=COLORS["text_primary"],
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))

        out_mode_var = tk.StringVar(value="same")
        custom_dir_var = tk.StringVar(value="")

        rb_same = tk.Radiobutton(row2, text="Orijinal Klasör", variable=out_mode_var, value="same",
                                 bg=COLORS["bg_elevated"], fg="white", selectcolor=COLORS["bg_deep"],
                                 activebackground=COLORS["bg_elevated"])
        rb_same.pack(side=tk.LEFT, padx=4)

        rb_custom = tk.Radiobutton(row2, text="Özel Klasör:", variable=out_mode_var, value="custom",
                                   bg=COLORS["bg_elevated"], fg="white", selectcolor=COLORS["bg_deep"],
                                   activebackground=COLORS["bg_elevated"])
        rb_custom.pack(side=tk.LEFT, padx=(12, 4))

        custom_dir_entry = tk.Entry(row2, textvariable=custom_dir_var, bg=COLORS["bg_input"],
                                    fg=COLORS["text_primary"], font=("Segoe UI", 9), relief="flat",
                                    highlightthickness=1, highlightbackground=COLORS["border"], width=30)
        custom_dir_entry.pack(side=tk.LEFT, padx=4, ipady=2)

        def browse_custom_out():
            out_mode_var.set("custom")
            d = filedialog.askdirectory(title="Dönüştürülen Altyazıların Kaydedileceği Klasörü Seçin")
            if d:
                custom_dir_var.set(d)

        btn_browse_out = tk.Button(row2, text="📂 Gözat...", bg=COLORS["bg_surface"], fg=COLORS["text_primary"],
                                   font=("Segoe UI", 8), relief="flat", cursor="hand2", padx=8, pady=2,
                                   command=browse_custom_out)
        btn_browse_out.pack(side=tk.LEFT, padx=4)

        # Alt Butonlar ve İlerleme
        bottom_frame = tk.Frame(conv_win, bg=COLORS["bg_surface"], padx=20, pady=12)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        status_lbl = tk.Label(bottom_frame, text="Hazır", bg=COLORS["bg_surface"], fg=COLORS["text_muted"], font=("Segoe UI", 9))
        status_lbl.pack(side=tk.LEFT)

        conv_progress = ttk.Progressbar(bottom_frame, mode="determinate", length=160, style="Custom.Horizontal.TProgressbar")

        def start_batch_conversion():
            if not queue_items:
                messagebox.showwarning("Uyarı", "Lütfen dönüştürülecek altyazı dosyalarını listeye ekleyin.")
                return

            target_fmt = target_fmt_var.get().lower()
            out_mode = out_mode_var.get()
            custom_dir = custom_dir_var.get().strip()
            clean_tags = clean_tags_var.get()

            if out_mode == "custom" and not custom_dir:
                messagebox.showwarning("Uyarı", "Lütfen bir çıktı klasörü seçin veya 'Orijinal Klasör' seçeneğini belirleyin.")
                return

            btn_start.config(state=tk.DISABLED)
            conv_progress.pack(side=tk.LEFT, padx=10)
            conv_progress["maximum"] = len(queue_items)
            conv_progress["value"] = 0

            converted_files = []
            failed_items = []

            for idx, (iid, fpath) in enumerate(list(queue_items.items()), 1):
                conv_progress["value"] = idx
                status_lbl.config(text=f"Dönüştürülüyor ({idx}/{len(queue_items)}): {os.path.basename(fpath)}")
                conv_win.update_idletasks()

                try:
                    content = read_text_file(fpath)
                    if not content or not content.strip():
                        raise Exception("Dosya içeriği boş veya okunamadı.")

                    base, ext = os.path.splitext(fpath)
                    res_text = SubtitleConverter.convert(content, ext, target_fmt, clean_tags=clean_tags)

                    out_ext = f".{target_fmt}"
                    if out_mode == "custom" and custom_dir:
                        out_dir = custom_dir
                        os.makedirs(out_dir, exist_ok=True)
                    else:
                        out_dir = os.path.dirname(fpath)

                    filename_stem = os.path.splitext(os.path.basename(fpath))[0]
                    if ext.lower() == out_ext.lower():
                        out_file = os.path.join(out_dir, f"{filename_stem}.converted{out_ext}")
                    else:
                        out_file = os.path.join(out_dir, f"{filename_stem}{out_ext}")

                    with open(out_file, "w", encoding="utf-8-sig") as f:
                        f.write(res_text)

                    converted_files.append(out_file)

                    vals = list(tree.item(iid, "values"))
                    vals[0] = "✅ Dönüştürüldü"
                    tree.item(iid, values=vals)

                except Exception as e:
                    failed_items.append(f"{os.path.basename(fpath)}: {e}")
                    vals = list(tree.item(iid, "values"))
                    vals[0] = "❌ Hata"
                    tree.item(iid, values=vals)

            conv_progress.pack_forget()
            btn_start.config(state=tk.NORMAL)
            status_lbl.config(text=f"İşlem Tamamlandı: {len(converted_files)} başarılı, {len(failed_items)} hata", fg=COLORS["success"])

            if converted_files:
                msg = f"Toplam {len(converted_files)} adet altyazı dosyası başarıyla .{target_fmt.upper()} formatına dönüştürüldü!"
                if failed_items:
                    msg += f"\n\nHata Alınan Dosyalar ({len(failed_items)}):\n" + "\n".join(failed_items[:5])

                ans = messagebox.askyesno("Dönüştürme Tamamlandı 🎉", f"{msg}\n\nÇıktı klasörü açılsın mı?")
                if ans:
                    out_target = os.path.dirname(converted_files[0])
                    if os.path.exists(out_target):
                        os.startfile(out_target)
            else:
                messagebox.showerror("Dönüştürme Başarısız", "Hiçbir dosya dönüştürülemedi:\n\n" + "\n".join(failed_items))

        btn_start = tk.Button(bottom_frame, text="⚡  Toplu Dönüştürmeyi Başlat", bg=COLORS["accent"], fg="white",
                              font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2", padx=18, pady=6,
                              activebackground=COLORS["accent_hover"], activeforeground="white",
                              command=start_batch_conversion)
        btn_start.pack(side=tk.RIGHT, padx=(8, 0))

        tk.Button(bottom_frame, text="Kapat", bg=COLORS["bg_elevated"], fg=COLORS["text_secondary"],
                  font=("Segoe UI", 10), relief="flat", cursor="hand2", padx=14, pady=6,
                  command=conv_win.destroy).pack(side=tk.RIGHT)


    def _create_desktop_shortcut(self):
        """Masaüstünde NollySub kısayolu (.lnk) oluşturur."""
        try:
            script_path = os.path.abspath(sys.argv[0])
            shortcut_path = str(Path.home() / "Desktop" / "NollySub.lnk")
            work_dir = os.path.dirname(script_path)
            py_exec = sys.executable

            pyw_exec = os.path.join(os.path.dirname(py_exec), "pythonw.exe")
            target_exe = pyw_exec if os.path.exists(pyw_exec) else py_exec
            icon_file = os.path.join(work_dir, "assets", "icon.ico")

            ps_command = (
                f"$WshShell = New-Object -ComObject WScript.Shell; "
                f"$Shortcut = $WshShell.CreateShortcut('{shortcut_path}'); "
                f"$Shortcut.TargetPath = '{target_exe}'; "
                f"$Shortcut.Arguments = '\"{script_path}\"'; "
                f"$Shortcut.WorkingDirectory = '{work_dir}'; "
            )
            if os.path.exists(icon_file):
                ps_command += f"$Shortcut.IconLocation = '{icon_file}'; "
            ps_command += "$Shortcut.Save()"

            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")

            if res.returncode == 0 and os.path.exists(shortcut_path):
                messagebox.showinfo(
                    "Kısayol Oluşturuldu! 📌✅",
                    f"NollySub kısayolu Masaüstünüze başarıyla eklendi!\n\n📍 Konum: {shortcut_path}"
                )
            else:
                messagebox.showerror("Kısayol Hatası", f"Kısayol oluşturulamadı:\n{res.stderr}")
        except Exception as e:
            messagebox.showerror("Hata", f"Kısayol oluşturulurken hata: {str(e)}")

    # ── ÇALIŞTIR ──

    def run(self):
        """Uygulamayı başlat."""
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"+{x}+{y}")

        self.search_entry.focus_set()
        self.root.mainloop()


# ══════════════════════════════════════════════════════
# GİRİŞ NOKTASI
# ══════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        print(f"\n  [NollySub] {APP_TITLE}\n")
    except UnicodeEncodeError:
        print(f"\n  [NollySub] Anime Turkce Altyazi Indirici\n")
    app = NollySubApp()
    app.run()
