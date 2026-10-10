#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nekoBT API & Torznab Client (Python)
nekoBT (https://nekobt.to) Anime & Fansub Tracker için bağımsız API istemcisi ve ayrıştırıcısı.

Sıfır bağımlılıklı (zero-dependency) olup standart Python kütüphaneleri (urllib, xml.etree.ElementTree)
ile Torznab RSS ve JSON API'si üzerinden torrent & magnet araması ve doğrudan indirme sağlar.
"""

import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple, Union

NEKOBT_BASE_URL = "https://nekobt.to"
TORZNAB_API_URL = "https://nekobt.to/api/torznab/api"
JSON_API_URL = "https://nekobt.to/api/v1"
WIKI_URL = "https://wiki.nekobt.to"

DEFAULT_USER_AGENT = "NollySub/1.2.0 (Windows NT 10.0; Win64; x64) Mozilla/5.0"
TORZNAB_NS = {"torznab": "http://torznab.com/schemas/2015/feed"}


def format_file_size(size_bytes: Union[int, str]) -> str:
    """Bayt cinsinden dosya boyutunu okunabilir formata dönüştürür."""
    try:
        b = int(size_bytes)
        if b <= 0:
            return "0 B"
        if b < 1024:
            return f"{b} B"
        elif b < 1024 * 1024:
            return f"{b / 1024:.1f} KiB"
        elif b < 1024 * 1024 * 1024:
            return f"{b / (1024 * 1024):.1f} MiB"
        else:
            return f"{b / (1024 * 1024 * 1024):.2f} GiB"
    except (ValueError, TypeError):
        return str(size_bytes) or "?"


def parse_nekobt_tags(title_or_tags: str) -> Dict[str, Any]:
    """
    nekoBT başlıklarında yer alan etiketleri ayrıştırır.
    Örnek: {Tags:L0;V9;C1;A=ja,en;S=en,tr,frfr;}
    """
    result = {
        "raw": "",
        "level": None,
        "video": None,
        "codec": None,
        "audio_langs": [],
        "sub_langs": [],
        "has_turkish_sub": False,
        "has_turkish_audio": False,
    }

    if not title_or_tags:
        return result

    m = re.search(r"\{Tags:([^}]+)\}", title_or_tags, re.IGNORECASE)
    if not m:
        # Doğrudan etiket dizesi verilmiş olabilir
        tag_str = title_or_tags.strip("{}")
    else:
        tag_str = m.group(1)

    result["raw"] = tag_str

    parts = [p.strip() for p in tag_str.split(";") if p.strip()]
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            k = k.strip().upper()
            vals = [x.strip().lower() for x in v.split(",") if x.strip()]
            if k == "A":
                result["audio_langs"] = vals
            elif k == "S":
                result["sub_langs"] = vals
            elif k == "F":
                # Fansub dilleri
                result["fansub_langs"] = vals
        else:
            # L0 (Level), V9 (Video), C1 (Codec) gibi bayraklar
            up = p.upper()
            if up.startswith("L"):
                result["level"] = up
            elif up.startswith("V"):
                result["video"] = up
            elif up.startswith("C"):
                result["codec"] = up

    # Türkçe altyazı & ses tespiti
    tr_variants = {"tr", "tur", "turkish", "türkçe", "turkce", "tr-tr", "trtr"}
    if any(s in tr_variants or s.startswith("tr") for s in result["sub_langs"]):
        result["has_turkish_sub"] = True
    if any(a in tr_variants or a.startswith("tr") for a in result["audio_langs"]):
        result["has_turkish_audio"] = True

    return result


def extract_group_name(title: str) -> str:
    """Başlıktan fansub / salım grubu adını çıkarır. Örn: [Erai-raws] -> Erai-raws"""
    m = re.match(r"^\s*\[([^\]]+)\]", title)
    if m:
        return m.group(1).strip()
    return "nekoBT"


def search_nekobt(
    query: Optional[str] = None,
    sub_lang: Optional[str] = None,
    audio_lang: Optional[str] = None,
    batch: Optional[bool] = None,
    apikey: Optional[str] = None,
    limit: int = 50,
    timeout: int = 15,
) -> Dict[str, Any]:
    """
    nekoBT Torznab API (RSS) üzerinden arama yapar.

    Parametreler:
        query: Aranacak metin (None ise son eklenen torrentler döner)
        sub_lang: Altyazı dili filtresi (örn: 'tr', 'en')
        audio_lang: Ses dili filtresi (örn: 'ja', 'en')
        batch: True/False batch torrent filtresi
        apikey: İsteğe bağlı nekoBT API anahtarı
        limit: Alınacak maksimum öğe sayısı (varsayılan 50)
        timeout: İstek zaman aşımı süresi (saniye)

    Dönen Değer:
        {"total": int, "results": List[dict]}
    """
    params: Dict[str, str] = {"t": "search"}

    if query:
        params["q"] = query.strip()
    if sub_lang:
        params["sub_lang"] = sub_lang.strip()
    if audio_lang:
        params["audio_lang"] = audio_lang.strip()
    if batch is not None:
        params["batch"] = "true" if batch else "false"
    if apikey:
        params["apikey"] = apikey.strip()

    url = f"{TORZNAB_API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/rss+xml, application/xml, text/xml",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
    except Exception as e:
        raise RuntimeError(f"nekoBT API isteği başarısız oldu: {e}")

    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        raise RuntimeError(f"nekoBT XML ayrıştırma hatası: {e}")

    items = root.findall(".//item")
    if limit and limit > 0:
        items = items[:limit]

    results: List[Dict[str, Any]] = []

    for item in items:
        title_el = item.find("title")
        title = title_el.text if title_el is not None and title_el.text else ""

        guid_el = item.find("guid")
        guid = guid_el.text if guid_el is not None and guid_el.text else ""

        link_el = item.find("link")
        link = link_el.text if link_el is not None and link_el.text else ""

        pubdate_el = item.find("pubDate")
        pub_date = pubdate_el.text if pubdate_el is not None and pubdate_el.text else ""

        # Torznab özel öznitelikleri
        attrs: Dict[str, str] = {}
        for attr in item.findall("torznab:attr", TORZNAB_NS):
            name = attr.attrib.get("name")
            val = attr.attrib.get("value", "")
            if name:
                attrs[name] = val

        seeders = int(attrs.get("seeders", 0)) if attrs.get("seeders", "").isdigit() else 0
        leechers = int(attrs.get("leechers", 0)) if attrs.get("leechers", "").isdigit() else 0
        peers = int(attrs.get("peers", 0)) if attrs.get("peers", "").isdigit() else (seeders + leechers)
        downloads = int(attrs.get("grabs", 0)) if attrs.get("grabs", "").isdigit() else 0
        info_hash = attrs.get("infohash", "")
        size_bytes = int(attrs.get("size", 0)) if attrs.get("size", "").isdigit() else 0
        magnet_link = attrs.get("magneturl") or (link if link.startswith("magnet:") else "")

        # Torrent ID çıkarma (guid: https://nekobt.to/torrents/{id})
        torrent_id = None
        m_id = re.search(r"/torrents/(\d+)", guid)
        if m_id:
            torrent_id = m_id.group(1)

        # Doğrudan .torrent indirme bağlantısı
        torrent_url = None
        if torrent_id:
            torrent_url = f"{JSON_API_URL}/torrents/{torrent_id}/download"
            if apikey:
                torrent_url += f"?apikey={urllib.parse.quote(apikey.strip())}"

        # Etiket analizi
        tag_info = parse_nekobt_tags(title)

        # Başlık ve metin üzerinden ek Türkçe kontrolü
        t_lower = title.lower()
        if any(k in t_lower for k in ["tr", "turkish", "türkçe", "turkce", "tac", "oishi", "ani-tr"]):
            tag_info["has_turkish_sub"] = True

        uploader = extract_group_name(title)

        results.append({
            "id": torrent_id,
            "title": title,
            "guid": guid,
            "view_url": guid,
            "torrent_url": torrent_url,
            "magnet_link": magnet_link,
            "info_hash": info_hash,
            "size_bytes": size_bytes,
            "size_human": format_file_size(size_bytes),
            "seeders": seeders,
            "leechers": leechers,
            "peers": peers,
            "downloads": downloads,
            "pub_date": pub_date,
            "uploader": uploader,
            "tags": tag_info,
            "has_turkish_sub": tag_info["has_turkish_sub"],
            "has_turkish_audio": tag_info["has_turkish_audio"],
            "tvdb_id": attrs.get("tvdbid"),
            "tmdb_id": attrs.get("tmdbid"),
            "anilist_id": attrs.get("anilistid"),
        })

    return {
        "total": len(results),
        "results": results,
    }


def download_torrent_file(
    torrent_id_or_url: str,
    apikey: Optional[str] = None,
    timeout: int = 30,
) -> Tuple[bytes, str]:
    """
    nekoBT'den doğrudan .torrent dosyasını indirir.

    Dönen Değer:
        (content_bytes, dosya_adi)
    """
    url = torrent_id_or_url.strip()
    if url.isdigit():
        url = f"{JSON_API_URL}/torrents/{url}/download"

    if apikey and "apikey=" not in url:
        sep = "&" if "?" in url else "?"
        url += f"{sep}apikey={urllib.parse.quote(apikey.strip())}"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/x-bittorrent, */*",
        },
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content = resp.read()
        cd = resp.headers.get("content-disposition", "")
        filename = None

        if "filename=" in cd:
            # UTF-8 veya normal dosya adını al
            m_utf8 = re.search(r"filename\*=UTF-8''([^;\r\n]+)", cd, re.IGNORECASE)
            if m_utf8:
                filename = urllib.parse.unquote(m_utf8.group(1).strip().strip('"\''))
            else:
                m_plain = re.search(r'filename=["\']?([^"\';\r\n]+)["\']?', cd)
                if m_plain:
                    filename = urllib.parse.unquote(m_plain.group(1).strip())

        if not filename:
            m_num = re.search(r"/torrents/(\d+)/download", url)
            if m_num:
                filename = f"nekobt_{m_num.group(1)}.torrent"
            else:
                filename = "nekobt_release.torrent"

        return content, filename


if __name__ == "__main__":
    print("Testing nekobt_api.py with a live search query...")
    try:
        data = search_nekobt("Ranma", limit=5)
        print(f"Success! Found {data['total']} items.")
        for i, item in enumerate(data["results"], 1):
            tr_badge = "[TR SUB]" if item["has_turkish_sub"] else ""
            print(f" {i}. {item['title'][:75]}... ({item['size_human']}, Seeders: {item['seeders']}) {tr_badge}")
            print(f"    Torrent URL: {item['torrent_url']}")
            print(f"    Magnet: {item['magnet_link'][:50]}...")
    except Exception as err:
        print(f"Error during test: {err}")
