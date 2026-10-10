#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nyaa.si Single-File API Client & Parser (Python Port)
Ported from kernelginar/nyaa-api (https://gitlab.com/kernelginar/nyaa-api)

Herhangi bir harici kütüphaneye (bs4 vb.) ihtiyaç duymayan, sıfır bağımlılıklı (zero-dependency)
ve tek dosyalık Nyaa.si API istemcisi ve HTML ayrıştırıcısı.
"""

import html
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Union

NYAA_BASE_URL = "https://nyaa.si"


class CategoriesMeta(type):
    def __getitem__(cls, key):
        return getattr(cls, key)


class AnimeCategories:
    ALL = "1_0"
    MUSIC_VIDEO = "1_1"
    ENGLISH_TRANSLATED = "1_2"
    NON_ENGLISH_TRANSLATED = "1_3"
    RAW = "1_4"

    def __getitem__(self, key):
        return getattr(self, key)


class AudioCategories:
    ALL = "2_0"
    LOSSLESS = "2_1"
    LOSSY = "2_2"

    def __getitem__(self, key):
        return getattr(self, key)


class LiteratureCategories:
    ALL = "3_0"
    ENGLISH_TRANSLATED = "3_1"
    NON_ENGLISH_TRANSLATED = "3_2"
    RAW = "3_3"

    def __getitem__(self, key):
        return getattr(self, key)


class LiveActionCategories:
    ALL = "4_0"
    ENGLISH_TRANSLATED = "4_1"
    IDOL_PROMOTIONAL_VIDEO = "4_2"
    NON_ENGLISH_TRANSLATED = "4_3"
    RAW = "4_4"

    def __getitem__(self, key):
        return getattr(self, key)


class PicturesCategories:
    ALL = "5_0"
    GRAPHICS = "5_1"
    PHOTOS = "5_2"

    def __getitem__(self, key):
        return getattr(self, key)


class SoftwareCategories:
    ALL = "6_0"
    APPLICATIONS = "6_1"
    GAMES = "6_2"

    def __getitem__(self, key):
        return getattr(self, key)


class CATEGORIES:
    ALL = "0_0"
    ANIME = AnimeCategories()
    AUDIO = AudioCategories()
    LITERATURE = LiteratureCategories()
    LIVE_ACTION = LiveActionCategories()
    PICTURES = PicturesCategories()
    SOFTWARE = SoftwareCategories()

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        return {
            "ALL": "0_0",
            "ANIME": {
                "ALL": "1_0",
                "MUSIC_VIDEO": "1_1",
                "ENGLISH_TRANSLATED": "1_2",
                "NON_ENGLISH_TRANSLATED": "1_3",
                "RAW": "1_4",
            },
            "AUDIO": {
                "ALL": "2_0",
                "LOSSLESS": "2_1",
                "LOSSY": "2_2",
            },
            "LITERATURE": {
                "ALL": "3_0",
                "ENGLISH_TRANSLATED": "3_1",
                "NON_ENGLISH_TRANSLATED": "3_2",
                "RAW": "3_3",
            },
            "LIVE_ACTION": {
                "ALL": "4_0",
                "ENGLISH_TRANSLATED": "4_1",
                "IDOL_PROMOTIONAL_VIDEO": "4_2",
                "NON_ENGLISH_TRANSLATED": "4_3",
                "RAW": "4_4",
            },
            "PICTURES": {
                "ALL": "5_0",
                "GRAPHICS": "5_1",
                "PHOTOS": "5_2",
            },
            "SOFTWARE": {
                "ALL": "6_0",
                "APPLICATIONS": "6_1",
                "GAMES": "6_2",
            },
        }


class FILTER_TYPES:
    NO_FILTER = 0
    NO_REMAKES = 1
    TRUSTED_ONLY = 2


class SORT_FIELDS:
    ID = "id"
    SIZE = "size"
    COMMENTS = "comments"
    SEEDERS = "seeders"
    LEECHERS = "leechers"
    DOWNLOADS = "downloads"


class SORT_ORDERS:
    ASCENDING = "asc"
    DESCENDING = "desc"


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
}


def decode_html_entities(raw_text: Optional[str]) -> str:
    """HTML entity kodlarını çözer (&amp; -> &, &#39; -> ' vb.)."""
    if not raw_text or not isinstance(raw_text, str):
        return ""
    return html.unescape(raw_text)


def strip_html_tags(raw_html: Optional[str]) -> str:
    """HTML etiketlerini temizler ve metni döndürür."""
    if not raw_html or not isinstance(raw_html, str):
        return ""
    cleaned = re.sub(r"<[^>]*>", "", raw_html)
    return decode_html_entities(cleaned).strip()


def extract_attribute_value(element_html: str, attribute_name: str) -> Optional[str]:
    """Bir HTML etiketinden belirli bir öznitelik değerini çeker."""
    pattern = rf'{attribute_name}=["\']([^"\']*)["\']'
    match = re.search(pattern, element_html, re.IGNORECASE)
    return decode_html_entities(match.group(1)) if match else None


def parse_category_data(category_cell_html: str) -> Dict[str, str]:
    """Kategori hücresinden kategori kodu ve adını ayrıştırır."""
    link_match = re.search(
        r'<a\s+[^>]*href=["\']/\?c=([0-9_]+)["\'][^>]*title=["\']([^"\']*)["\']',
        category_cell_html,
        re.IGNORECASE,
    )
    if not link_match:
        return {"code": CATEGORIES.ALL, "name": "Unknown"}

    return {
        "code": link_match.group(1),
        "name": decode_html_entities(link_match.group(2)),
    }


def parse_title_and_comments(title_cell_html: str) -> Dict[str, Any]:
    """Başlık hücresinden torrent ID, başlık ve yorum sayısını ayrıştırır."""
    comment_match = re.search(
        r'<a\s+[^>]*class=["\'][^"\']*comments[^"\']*["\'][^>]*>[\s\S]*?(\d+)</a>',
        title_cell_html,
        re.IGNORECASE,
    )
    comment_count = int(comment_match.group(1)) if comment_match else 0

    view_link_match = re.search(
        r'<a\s+[^>]*href=["\']/view/(\d+)["\'][^>]*title=["\']([^"\']*)["\'][^>]*>([\s\S]*?)</a>',
        title_cell_html,
        re.IGNORECASE,
    )

    if not view_link_match:
        # Alternatif: title özniteliği olmayabilir, direkt inner text kullanılabilir
        view_link_fallback = re.search(
            r'<a\s+[^>]*href=["\']/view/(\d+)["\'][^>]*>([\s\S]*?)</a>',
            title_cell_html,
            re.IGNORECASE,
        )
        if not view_link_fallback:
            return {"torrent_id": None, "title": "", "comment_count": comment_count}

        torrent_id = view_link_fallback.group(1)
        title = strip_html_tags(view_link_fallback.group(2))
    else:
        torrent_id = view_link_match.group(1)
        raw_title = view_link_match.group(2) or strip_html_tags(view_link_match.group(3))
        title = decode_html_entities(raw_title)

    return {
        "torrent_id": torrent_id,
        "title": title,
        "comment_count": comment_count,
    }


def parse_download_links(link_cell_html: str, base_url: str = NYAA_BASE_URL) -> Dict[str, Optional[str]]:
    """İndirme hücresinden .torrent bağlantısı ve magnet linkini ayrıştırır."""
    torrent_file_match = re.search(r'href=["\'](/download/\d+\.torrent)["\']', link_cell_html, re.IGNORECASE)
    magnet_match = re.search(r'href=["\'](magnet:\?[^"\']+)["\']', link_cell_html, re.IGNORECASE)

    torrent_rel = torrent_file_match.group(1) if torrent_file_match else None
    torrent_url = f"{base_url.rstrip('/')}{torrent_rel}" if torrent_rel else None
    magnet_link = decode_html_entities(magnet_match.group(1)) if magnet_match else None

    return {
        "torrent_url": torrent_url,
        "magnet_link": magnet_link,
    }


def extract_info_hash_from_magnet(magnet_uri: Optional[str]) -> Optional[str]:
    """Magnet URI içerisinden 40 karakterlik BitTorrent info hash (BTIH) bilgisini çeker."""
    if not magnet_uri:
        return None
    match = re.search(r"xt=urn:btih:([a-zA-Z0-9]+)", magnet_uri, re.IGNORECASE)
    return match.group(1).lower() if match else None


def parse_numeric_cell(cell_html: str) -> int:
    """Hücredeki metni tam sayıya dönüştürür."""
    text = strip_html_tags(cell_html).replace(",", "")
    try:
        return int(text)
    except ValueError:
        return 0


def parse_date_cell(date_cell_html: str) -> Dict[str, Any]:
    """Tarih hücresinden Unix zaman damgası ve metin tarihini ayrıştırır."""
    ts_str = extract_attribute_value(date_cell_html, "data-timestamp")
    timestamp = int(ts_str) if ts_str and ts_str.isdigit() else None
    date_str = strip_html_tags(date_cell_html)
    return {
        "timestamp": timestamp,
        "date_string": date_str,
    }


def parse_row_classification(opening_row_tag: str) -> Dict[str, bool]:
    """<tr> etiketinin class değerine göre trusted, remake veya batch durumunu tespit eder."""
    cls_attr = extract_attribute_value(opening_row_tag, "class") or ""
    tokens = cls_attr.split()
    return {
        "is_trusted": "success" in tokens,
        "is_remake": "danger" in tokens,
        "is_batch": "info" in tokens,
    }


def parse_table_row(row_html: str, base_url: str = NYAA_BASE_URL) -> Optional[Dict[str, Any]]:
    """Tek bir Nyaa sonuç tablosu satırını (<tr>) zengin sözlük yapısına dönüştürür."""
    cells = re.findall(r"<td[\s\S]*?</td>", row_html, re.IGNORECASE)
    if not cells or len(cells) < 8:
        return None

    open_tag_match = re.search(r"<tr[^>]*>", row_html, re.IGNORECASE)
    opening_tag = open_tag_match.group(0) if open_tag_match else ""

    classification = parse_row_classification(opening_tag)
    category_data = parse_category_data(cells[0])
    title_data = parse_title_and_comments(cells[1])
    links = parse_download_links(cells[2], base_url)
    date_data = parse_date_cell(cells[4])

    torrent_id = title_data["torrent_id"]
    view_url = f"{base_url.rstrip('/')}/view/{torrent_id}" if torrent_id else None

    return {
        "id": torrent_id,
        "title": title_data["title"],
        "category": category_data,
        "torrent_url": links["torrent_url"],
        "magnet_link": links["magnet_link"],
        "info_hash": extract_info_hash_from_magnet(links["magnet_link"]),
        "view_url": view_url,
        "file_size": strip_html_tags(cells[3]),
        "timestamp": date_data["timestamp"],
        "upload_date": date_data["date_string"],
        "seeders": parse_numeric_cell(cells[5]),
        "leechers": parse_numeric_cell(cells[6]),
        "downloads": parse_numeric_cell(cells[7]),
        "comments_count": title_data["comment_count"],
        "is_trusted": classification["is_trusted"],
        "is_remake": classification["is_remake"],
        "is_batch": classification["is_batch"],
    }


def parse_pagination_data(html_content: str) -> Dict[str, Any]:
    """Sayfalama (pagination) bilgilerini çıkarır."""
    pag_match = re.search(r'<ul\s+class=["\']pagination["\']>([\s\S]*?)</ul>', html_content, re.IGNORECASE)
    if not pag_match:
        return {
            "current_page": 1,
            "has_next_page": False,
            "total_pages": 1,
        }

    pag_html = decode_html_entities(pag_match.group(1))
    active_match = re.search(r'<li\s+class=["\']active["\']>\s*<a[^>]*>(\d+)', pag_html, re.IGNORECASE)
    current_page = int(active_match.group(1)) if active_match else 1

    page_numbers = [int(p) for p in re.findall(r'[?&]p=(\d+)', pag_html)]
    max_page = max(page_numbers) if page_numbers else current_page
    total_pages = max(current_page, max_page)
    has_next = ('rel="next"' in pag_html) or (total_pages > current_page)

    return {
        "current_page": current_page,
        "has_next_page": has_next,
        "total_pages": total_pages,
    }


def parse_nyaa_html(html_content: str, base_url: str = NYAA_BASE_URL) -> Dict[str, Any]:
    """Ham HTML metnini ayrıştırarak sonuç listesi ve sayfalama verisini döndürür."""
    if not html_content or not isinstance(html_content, str):
        return {
            "results": [],
            "pagination": {"current_page": 1, "has_next_page": False, "total_pages": 1},
        }

    tbody_match = re.search(r"<tbody>([\s\S]*?)</tbody>", html_content, re.IGNORECASE)
    if not tbody_match:
        return {
            "results": [],
            "pagination": parse_pagination_data(html_content),
        }

    row_matches = re.findall(r"<tr[\s\S]*?</tr>", tbody_match.group(1), re.IGNORECASE)
    results = []
    for row in row_matches:
        parsed_row = parse_table_row(row, base_url)
        if parsed_row:
            results.append(parsed_row)

    return {
        "results": results,
        "pagination": parse_pagination_data(html_content),
    }


def build_search_url(
    query: str = "",
    category: str = CATEGORIES.ALL,
    filter: int = FILTER_TYPES.NO_FILTER,
    page: int = 1,
    sort_by: Optional[str] = None,
    sort_order: str = SORT_ORDERS.DESCENDING,
    base_url: str = NYAA_BASE_URL,
) -> str:
    """Arama parametrelerine göre Nyaa.si URL'ini oluşturur."""
    params = {
        "f": str(filter),
        "c": str(category),
        "q": query or "",
    }
    if page > 1:
        params["p"] = str(page)
    if sort_by:
        params["s"] = str(sort_by)
        params["o"] = str(sort_order)

    base = base_url.rstrip("/")
    query_str = urllib.parse.urlencode(params)
    return f"{base}/?{query_str}"


def search_nyaa(
    query: str = "",
    category: str = CATEGORIES.ALL,
    filter: int = FILTER_TYPES.NO_FILTER,
    page: int = 1,
    sort_by: Optional[str] = None,
    sort_order: str = SORT_ORDERS.DESCENDING,
    base_url: str = NYAA_BASE_URL,
    timeout: int = 15,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Nyaa.si üzerinde arama yapar ve ayrıştırılmış sonuçları döndürür.
    """
    request_url = build_search_url(
        query=query,
        category=category,
        filter=filter,
        page=page,
        sort_by=sort_by,
        sort_order=sort_order,
        base_url=base_url,
    )

    req_headers = dict(DEFAULT_HEADERS)
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(request_url, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_bytes = resp.read()
            html_content = content_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        raise RuntimeError(f"Nyaa.si isteği başarısız oldu ({request_url}): {e}") from e

    parsed_data = parse_nyaa_html(html_content, base_url=base_url)

    return {
        "query": query,
        "category": category,
        "filter": filter,
        "request_url": request_url,
        "results": parsed_data["results"],
        "pagination": parsed_data["pagination"],
    }


class NyaaClient:
    """Nesne tabanlı Nyaa.si istemcisi."""

    def __init__(self, base_url: str = NYAA_BASE_URL, timeout: int = 15):
        self.base_url = base_url
        self.timeout = timeout

    def search(
        self,
        query: str = "",
        category: str = CATEGORIES.ALL,
        filter: int = FILTER_TYPES.NO_FILTER,
        page: int = 1,
        sort_by: Optional[str] = None,
        sort_order: str = SORT_ORDERS.DESCENDING,
    ) -> Dict[str, Any]:
        return search_nyaa(
            query=query,
            category=category,
            filter=filter,
            page=page,
            sort_by=sort_by,
            sort_order=sort_order,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    def download_torrent(self, torrent_url: str, timeout: int = 30) -> bytes:
        """Belirtilen .torrent dosyasını indirir ve baytlarını döndürür."""
        req = urllib.request.Request(torrent_url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()


# Modül düzeyinde takma adlar (JS API uyumluluğu için)
searchNyaa = search_nyaa
parseNyaaHtml = parse_nyaa_html
buildSearchUrl = build_search_url


if __name__ == "__main__":
    print("Testing nyaa_api.py with a live search query...")
    try:
        res = search_nyaa(
            query="Frieren",
            category=CATEGORIES.ANIME.ENGLISH_TRANSLATED,
            filter=FILTER_TYPES.NO_FILTER,
            sort_by=SORT_FIELDS.SEEDERS,
            sort_order=SORT_ORDERS.DESCENDING,
        )
        print(f"URL: {res['request_url']}")
        print(f"Toplam {len(res['results'])} sonuç bulundu. Sayfa: {res['pagination']['current_page']}/{res['pagination']['total_pages']}")
        for item in res["results"][:3]:
            print(f"- [{item['category']['name']}] {item['title']}")
            print(f"  Boyut: {item['file_size']} | Seed: {item['seeders']} | Leech: {item['leechers']} | Güvenilir: {item['is_trusted']}")
            print(f"  Torrent: {item['torrent_url']}")
            print(f"  Hash: {item['info_hash']}")
    except Exception as err:
        print(f"Test hatası: {err}")
