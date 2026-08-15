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


class SubtitleConverter:
    """Farklı altyazı formatları (vtt, ttml, ass, txt) arasında dönüşüm yapar."""

    @staticmethod
    def vtt_to_srt(vtt_content):
        lines = vtt_content.splitlines()
        srt_lines = []
        idx = 1

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if line.startswith("WEBVTT") or line.startswith("NOTE") or line.startswith("STYLE"):
                i += 1
                while i < len(lines) and lines[i].strip():
                    i += 1
                continue

            if "-->" in line:
                timing = line.replace(".", ",")
                timing = re.sub(r'(\d+:\d+:\d+),(\d{3})\d*', r'\1,\2', timing)
                timing = re.sub(r'(\d+:\d+),(\d{3})\d*', r'00:\1,\2', timing)

                text_lines = []
                i += 1
                while i < len(lines) and lines[i].strip():
                    t_line = re.sub(r'<[^>]+>', '', lines[i].strip())
                    if t_line:
                        text_lines.append(t_line)
                    i += 1

                if text_lines:
                    srt_lines.append(str(idx))
                    srt_lines.append(timing)
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
            "YCbCr Matrix: None\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )
        lines = srt_content.splitlines()
        events = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if "-->" in line:
                parts = line.split("-->")
                start = parts[0].strip().replace(",", ".")
                end = parts[1].split()[0].strip().replace(",", ".")

                def fmt_time(t):
                    p = t.split(":")
                    if len(p) == 3:
                        h, m, s = p
                        sec, ms = s.split(".") if "." in s else (s, "000")
                        return f"{int(h)}:{m}:{sec}.{ms[:2]}"
                    return "0:00:00.00"

                text_lines = []
                i += 1
                while i < len(lines) and lines[i].strip():
                    text_lines.append(lines[i].strip())
                    i += 1

                txt = "\\N".join(text_lines)
                events.append(f"Dialogue: 0,{fmt_time(start)},{fmt_time(end)},Default,,0,0,0,,{txt}")
            else:
                i += 1

        return header + "\n".join(events)


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
            tracks.append({
                "id": t["id"],
                "type": t["type"],
                "codec": t.get("codec", ""),
                "language": t.get("properties", {}).get("language", "und"),
                "name": t.get("properties", {}).get("track_name", ""),
                "default": t.get("properties", {}).get("default_track", False),
                "forced": t.get("properties", {}).get("forced_track", False),
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

        mkv_btn = tk.Button(btn_frame, text="🎬 MKV Altyazı Çıkar",
                            bg=COLORS["bg_elevated"], fg=COLORS["info"],
                            font=("Segoe UI", 9, "bold"),
                            relief="flat", cursor="hand2",
                            activebackground=COLORS["border_light"],
                            activeforeground="white",
                            padx=10, pady=4,
                            command=self._extract_subtitles_from_mkv_gui)
        mkv_btn.pack(side=tk.LEFT, padx=3)

        dub_btn = tk.Button(btn_frame, text="🎙️ MKV Dublaj Değiştir",
                            bg=COLORS["bg_elevated"], fg="#a855f7",
                            font=("Segoe UI", 9, "bold"),
                            relief="flat", cursor="hand2",
                            activebackground=COLORS["border_light"],
                            activeforeground="white",
                            padx=10, pady=4,
                            command=self._show_mkv_dub_changer_gui)
        dub_btn.pack(side=tk.LEFT, padx=3)

        conv_btn = tk.Button(btn_frame, text="🔄 Altyazı Dönüştür",
                             bg=COLORS["bg_elevated"], fg=COLORS["warning"],
                             font=("Segoe UI", 9, "bold"),
                             relief="flat", cursor="hand2",
                             activebackground=COLORS["border_light"],
                             activeforeground="white",
                             padx=10, pady=4,
                             command=self._show_subtitle_converter_gui)
        conv_btn.pack(side=tk.LEFT, padx=3)

        shortcut_btn = tk.Button(btn_frame, text="📌 Kısayol Oluştur",
                                 bg=COLORS["bg_elevated"], fg=COLORS["success"],
                                 font=("Segoe UI", 9),
                                 relief="flat", cursor="hand2",
                                 activebackground=COLORS["border_light"],
                                 activeforeground="white",
                                 padx=10, pady=4,
                                 command=self._create_desktop_shortcut)
        shortcut_btn.pack(side=tk.LEFT, padx=3)

        settings_btn = tk.Button(btn_frame, text="⚙ Ayarlar",
                                 bg=COLORS["bg_elevated"], fg=COLORS["text_secondary"],
                                 font=("Segoe UI", 9),
                                 relief="flat", cursor="hand2",
                                 activebackground=COLORS["border_light"],
                                 activeforeground=COLORS["text_primary"],
                                 padx=10, pady=4,
                                 command=self._show_settings)
        settings_btn.pack(side=tk.LEFT, padx=3)

        folder_btn = tk.Button(btn_frame, text="📁 İndirilenler",
                               bg=COLORS["bg_elevated"], fg=COLORS["text_secondary"],
                               font=("Segoe UI", 9),
                               relief="flat", cursor="hand2",
                               activebackground=COLORS["border_light"],
                               activeforeground=COLORS["text_primary"],
                               padx=10, pady=4,
                               command=self._open_download_folder)
        folder_btn.pack(side=tk.LEFT, padx=3)

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
        self.tree.column("title", width=420, minwidth=250, stretch=True)
        self.tree.column("language", width=120, minwidth=90, stretch=False, anchor=tk.CENTER)
        self.tree.column("release", width=220, minwidth=150, stretch=False)
        self.tree.column("download_count", width=110, minwidth=90, stretch=False, anchor=tk.E)

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

        # Sol: Durum Etiketi
        self.status_label = tk.Label(footer,
                                     text="Hazır",
                                     bg=COLORS["bg_surface"],
                                     fg=COLORS["text_muted"],
                                     font=("Segoe UI", 9))
        self.status_label.pack(side=tk.LEFT, padx=20)

        # İlerleme çubuğu
        self.progress = ttk.Progressbar(footer, mode="indeterminate", length=150)

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

    def _show_settings(self):
        """Ayarlar penceresi."""
        settings_win = tk.Toplevel(self.root)
        settings_win.title("⚙ NollySub Ayarları")
        settings_win.geometry("540x480")
        settings_win.configure(bg=COLORS["bg_surface"])
        settings_win.transient(self.root)
        settings_win.grab_set()

        pad = {"padx": 20, "pady": 10}

        tk.Label(settings_win, text="⚙ Uygulama & API Ayarları", bg=COLORS["bg_surface"],
                 fg=COLORS["text_primary"], font=("Segoe UI", 14, "bold")).pack(anchor=tk.W, **pad)

        # OpenSubtitles Key
        os_frame = tk.Frame(settings_win, bg=COLORS["bg_surface"])
        os_frame.pack(fill=tk.X, **pad)

        tk.Label(os_frame, text="OpenSubtitles API Key:", bg=COLORS["bg_surface"],
                 fg=COLORS["text_secondary"], font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)

        os_var = tk.StringVar(value=self.config.get_opensubtitles_key())
        os_entry = tk.Entry(os_frame, textvariable=os_var, bg=COLORS["bg_input"],
                            fg=COLORS["text_primary"], font=("Segoe UI", 10), relief="flat")
        os_entry.pack(fill=tk.X, ipady=4, pady=(4, 0))

        # SubDL Key
        sd_frame = tk.Frame(settings_win, bg=COLORS["bg_surface"])
        sd_frame.pack(fill=tk.X, **pad)

        tk.Label(sd_frame, text="SubDL API Key:", bg=COLORS["bg_surface"],
                 fg=COLORS["text_secondary"], font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)

        sd_var = tk.StringVar(value=self.config.get_subdl_key())
        sd_entry = tk.Entry(sd_frame, textvariable=sd_var, bg=COLORS["bg_input"],
                            fg=COLORS["text_primary"], font=("Segoe UI", 10), relief="flat")
        sd_entry.pack(fill=tk.X, ipady=4, pady=(4, 0))

        # İndirme Klasörü
        dl_frame = tk.Frame(settings_win, bg=COLORS["bg_surface"])
        dl_frame.pack(fill=tk.X, **pad)

        tk.Label(dl_frame, text="İndirme Klasörü:", bg=COLORS["bg_surface"],
                 fg=COLORS["text_secondary"], font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)

        dl_row = tk.Frame(dl_frame, bg=COLORS["bg_surface"])
        dl_row.pack(fill=tk.X, pady=(4, 0))

        dl_var = tk.StringVar(value=self.config.get_download_dir())
        dl_entry = tk.Entry(dl_row, textvariable=dl_var, bg=COLORS["bg_input"],
                            fg=COLORS["text_primary"], font=("Segoe UI", 10), relief="flat")
        dl_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

        def browse_folder():
            folder = filedialog.askdirectory(initialdir=dl_var.get())
            if folder:
                dl_var.set(folder)

        tk.Button(dl_row, text="Gözat...", bg=COLORS["bg_elevated"], fg="white",
                  command=browse_folder, relief="flat").pack(side=tk.RIGHT, padx=(6, 0))

        # Kaydet Butonu
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

        tk.Button(settings_win, text="💾  Ayarları Kaydet", bg=COLORS["accent"], fg="white",
                  font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
                  padx=16, pady=6, command=save_and_close).pack(pady=20)

    def _open_download_folder(self):
        """İndirme klasörünü dosya gezgininde açar."""
        d = self.config.get_download_dir()
        if os.path.exists(d):
            os.startfile(d)
        else:
            Path(d).mkdir(parents=True, exist_ok=True)
            os.startfile(d)

    def _extract_subtitles_from_mkv_gui(self):
        """MKV'den altyazı çıkarma arayüzü."""
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

        out_dir = filedialog.askdirectory(title="Altyazıların Kaydedileceği Klasörü Seçin")
        if not out_dir:
            return

        count = 0
        for f in files:
            try:
                extracted = MkvTools.extract_subtitles(f, out_dir, mextract, mmerge)
                count += len(extracted)
            except Exception as e:
                print(f"Hata ({f}): {e}")

        messagebox.showinfo("İşlem Tamamlandı 🎉", f"Toplam {count} adet altyazı çıkarıldı!\n\nKonum: {out_dir}")

    def _show_mkv_dub_changer_gui(self):
        """MKV dublaj/ses izi değiştirici arayüzü."""
        mmerge, _, mpropedit = self.config.find_mkvtoolnix()
        if not mpropedit:
            messagebox.showerror(
                "MKVToolNix Bulunamadı",
                "Dublaj değiştirme özelliği için sisteminizde MKVToolNix kurulu olmalıdır."
            )
            return

        dub_win = tk.Toplevel(self.root)
        dub_win.title("🎙️ NollySub — MKV Dublaj & Ses İzi Değiştirici")
        dub_win.geometry("640x480")
        dub_win.configure(bg=COLORS["bg_surface"])
        dub_win.transient(self.root)

        tk.Label(dub_win, text="🎙️ MKV Varsayılan Ses (Dublaj) Ayarlayıcı", bg=COLORS["bg_surface"],
                 fg=COLORS["text_primary"], font=("Segoe UI", 12, "bold")).pack(anchor=tk.W, padx=20, pady=15)

    def _show_subtitle_converter_gui(self):
        """Altyazı format dönüştürücü arayüzü."""
        files = filedialog.askopenfilenames(
            title="Dönüştürülecek Altyazı Dosyalarını Seçin",
            filetypes=[("Altyazı Dosyaları", "*.vtt;*.srt;*.ass;*.txt")]
        )
        if not files:
            return

        conv_win = tk.Toplevel(self.root)
        conv_win.title("🔄 NollySub — Altyazı Format Dönüştürücü")
        conv_win.geometry("520x360")
        conv_win.configure(bg=COLORS["bg_surface"])
        conv_win.transient(self.root)

        tk.Label(conv_win, text="🔄 Altyazı Format Dönüştürücü", bg=COLORS["bg_surface"],
                 fg=COLORS["text_primary"], font=("Segoe UI", 13, "bold")).pack(anchor=tk.W, padx=20, pady=15)

        target_fmt = tk.StringVar(value="srt")

        fmt_frame = tk.Frame(conv_win, bg=COLORS["bg_surface"])
        fmt_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(fmt_frame, text="Hedef Format:", bg=COLORS["bg_surface"], fg=COLORS["text_secondary"]).pack(side=tk.LEFT)

        tk.Radiobutton(fmt_frame, text="SRT (.srt)", variable=target_fmt, value="srt",
                       bg=COLORS["bg_surface"], fg="white", selectcolor=COLORS["bg_deep"]).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(fmt_frame, text="ASS (.ass)", variable=target_fmt, value="ass",
                       bg=COLORS["bg_surface"], fg="white", selectcolor=COLORS["bg_deep"]).pack(side=tk.LEFT, padx=10)

        def start_conversion():
            fmt = target_fmt.get()
            converted = []
            failed = []

            for fpath in files:
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    base, ext = os.path.splitext(fpath)
                    ext = ext.lower()

                    if fmt == "srt":
                        if ext == ".vtt":
                            res_text = SubtitleConverter.vtt_to_srt(content)
                        else:
                            res_text = content
                        out_path = base + ".converted.srt"

                    elif fmt == "ass":
                        if ext == ".srt":
                            res_text = SubtitleConverter.srt_to_ass(content)
                        elif ext == ".vtt":
                            srt_mid = SubtitleConverter.vtt_to_srt(content)
                            res_text = SubtitleConverter.srt_to_ass(srt_mid)
                        else:
                            res_text = content
                        out_path = base + ".converted.ass"

                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(res_text)
                    converted.append(out_path)

                except Exception as e:
                    failed.append(f"{os.path.basename(fpath)}: {e}")

            if converted:
                msg = f"{len(converted)} altyazı dosyası başarıyla {fmt.upper()} formatına dönüştürüldü!"
                if failed:
                    msg += f"\n\nHatalar:\n" + "\n".join(failed)

                ans = messagebox.askyesno("Dönüştürme Tamamlandı 🎉", msg)
                if ans and converted:
                    try:
                        os.startfile(os.path.dirname(converted[0]))
                    except Exception:
                        pass
                conv_win.destroy()
            else:
                messagebox.showerror("Hata", f"Dönüştürme başarısız oldu:\n\n" + "\n".join(failed))

        tk.Button(conv_win, text="⚡  Dönüştürmeyi Başlat", bg=COLORS["accent"], fg="white",
                  font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2", padx=24, pady=6,
                  command=start_conversion).pack(pady=30)

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
