#!/usr/bin/env python3
"""
Download podcast episodes from an RSS feed with optional date filters.

Examples:
    # Limit only (newest first)
    python download_podcasts.py https://example.com/feed.xml --limit 5

    # Start date only
    python download_podcasts.py https://example.com/feed.xml --start-date 2024-01-01

    # Between dates
    python download_podcasts.py https://example.com/feed.xml \\
        --start-date 2024-01-01 --end-date 2024-02-01 --limit 5
"""

import datetime as dt
import email.utils
import pathlib
import re
import shutil
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from utilities.utility import save_json, merge_metadata, get_prior_metadata

def parse_iso_date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid date format '{value}'. Use YYYY-MM-DD.") from exc


def parse_pub_date(date_str: str) -> Optional[dt.datetime]:
    """Parse common RSS pubDate formats into an aware datetime."""
    if not date_str:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(date_str)
    except Exception:
        return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def fetch_feed(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "MyRiddleRiddle/1.0"})
    try:
        with urllib.request.urlopen(req) as response:
            return response.read()
    except Exception as exc:
        raise SystemExit(f"Failed to fetch RSS feed: {exc}") from exc


def _text(node: Optional[ET.Element]) -> str:
    return (node.text or "").strip() if node is not None else ""


def _localname(tag: str) -> str:
    return tag.split("}", 1)[-1] if tag else tag


def find_child_by_localname(element: ET.Element, name: str) -> Optional[ET.Element]:
    for child in element:
        if _localname(child.tag) == name:
            return child
    return None


def parse_duration_to_seconds(raw: str) -> Optional[int]:
    if not raw:
        return None
    raw = raw.strip()
    if raw.isdigit():
        return int(raw)
    parts = raw.split(":")
    if not all(part.isdigit() for part in parts):
        return None
    parts = [int(part) for part in parts]
    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds
    return None


def parse_int(value: Optional[str]) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def parse_float(value: Optional[str]) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def extract_items(feed_xml: bytes) -> List[Dict[str, Any]]:
    """Extract relevant fields from an RSS feed."""
    try:
        root = ET.fromstring(feed_xml)
    except ET.ParseError as exc:
        raise SystemExit(f"RSS parsing error: {exc}") from exc

    channel = root.find("channel")
    if channel is None:
        return []

    items: List[Dict[str, Any]] = []
    for item in channel.findall("item"):
        title = _text(item.find("title"))
        pub_date_raw = _text(item.find("pubDate"))
        pub_dt = parse_pub_date(pub_date_raw)
        enclosure = item.find("enclosure")
        enclosure_url = enclosure.get("url") if enclosure is not None else ""
        enclosure_length = parse_int(enclosure.get("duration")) if enclosure is not None else None
        enclosure_type = enclosure.get("type") if enclosure is not None else None

        media_content = find_child_by_localname(item, "content")
        media_url = media_content.get("url") if media_content is not None else ""
        media_bitrate = parse_float(media_content.get("bitrate")) if media_content is not None else None
        media_duration = parse_int(media_content.get("duration")) if media_content is not None else None
        media_size = parse_int(media_content.get("fileSize")) if media_content is not None else None
        media_type = media_content.get("type") if media_content is not None else None

        audio_url = enclosure_url or media_url
        if not audio_url:
            audio_url = _text(item.find("link"))
        if not audio_url:
            continue  # Cannot download without an audio URL

        duration_el = find_child_by_localname(item, "duration")
        duration_raw = _text(duration_el)
        duration_seconds = media_duration if media_duration is not None else parse_duration_to_seconds(duration_raw)
        duration_source = None
        if media_duration is not None:
            duration_source = "media:content"
        elif duration_raw:
            duration_source = "itunes:duration"

        items.append(
            {
                "title": title or "untitled",
                "published": pub_dt,
                "published_raw": pub_date_raw,
                "description": _text(item.find("description")),
                "guid": _text(item.find("guid")),
                "audio_url": audio_url,
                "feed_size_bytes": media_size if media_size is not None else enclosure_length,
                "duration_seconds": duration_seconds,
                "duration_raw": duration_raw,
                "duration_source": duration_source,
                "bitrate_kbps_feed": media_bitrate,
                "mime_type": media_type or enclosure_type,
            }
        )
    return items


def sanitize_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")
    return cleaned or "episode"


def file_extension_from_url(url: str) -> str:
    ext = pathlib.Path(urllib.parse.urlparse(url).path).suffix
    return ext if ext else ".mp3"


def download_audio(url: str, dest_dir: pathlib.Path, title: str) -> pathlib.Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    base_name = sanitize_filename(title)
    ext = file_extension_from_url(url)
    candidate = dest_dir / f"{base_name}{ext}"
    counter = 1
    while candidate.exists():
        candidate = dest_dir / f"{base_name}_{counter}{ext}"
        counter += 1

    req = urllib.request.Request(url, headers={"User-Agent": "MyRiddleRiddle/1.0"})
    try:
        with urllib.request.urlopen(req) as response, candidate.open("wb") as outfile:
            shutil.copyfileobj(response, outfile)
    except Exception as exc:
        raise SystemExit(f"Download failed for {url}: {exc}") from exc
    return candidate


def write_metadata(entries: List[Dict[str, Any]], metadata_path: pathlib.Path) -> None:
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = []
    for entry in entries:
        published = entry.get("published")
        if isinstance(published, dt.datetime):
            published_value = published.isoformat()
        else:
            published_value = published if published else None

        serializable.append(
            {
                "title": entry.get("title") or "untitled",
                "published": published_value,
                "published_raw": entry.get("published_raw"),
                "description": entry.get("description"),
                "guid": entry.get("guid"),
                "audio_url": entry.get("audio_url"),
                "mime_type": entry.get("mime_type"),
                "feed_size_bytes": entry.get("feed_size_bytes"),
                "file_size_bytes": entry.get("file_size_bytes"),
                "bitrate_kbps": entry.get("bitrate_kbps"),
                "bitrate_source": entry.get("bitrate_source"),
                "duration_seconds": entry.get("duration_seconds"),
                "duration_source": entry.get("duration_source"),
                "file_path": str(entry.get("file_path")) if entry.get("file_path") else None,
            }
        )

    save_json(serializable, metadata_path)


def download_podcasts(
    rss_url,
    start_date=None,
    end_date=None,
    limit=None,
    output_dir=None,
    metadata_file=None,
    sort_order: str = "desc",
) -> None:
    if start_date is None and end_date is None and limit is None:
        raise SystemExit("Provide at least one of start_date, end_date, or limit.")

    start_date_parsed = parse_iso_date(start_date) if start_date else None
    end_date_parsed = parse_iso_date(end_date) if end_date else None
    if start_date_parsed and end_date_parsed and end_date_parsed < start_date_parsed:
        raise SystemExit("end-date cannot be earlier than start-date.")

    sort_order_normalized = (sort_order or "desc").lower()
    if sort_order_normalized not in {"asc", "desc"}:
        raise SystemExit("sort_order must be 'asc' or 'desc'.")

    output_dir = pathlib.Path(output_dir or 'downloads')
    metadata_path = pathlib.Path(metadata_file) if metadata_file else output_dir / "metadata.json"

    prior_metadata, existing_files_by_url = get_prior_metadata(metadata_path)

    print(f"Fetching feed from {rss_url}...")
    feed_xml = fetch_feed(rss_url)
    items = extract_items(feed_xml)
    if not items:
        raise SystemExit("No items found in the feed.")

    def in_range(item: Dict[str, Any]) -> bool:
        pub = item["published"]
        if not pub:
            return False
        pub_date = pub.date()
        if start_date_parsed and pub_date < start_date_parsed:
            return False
        if end_date_parsed and pub_date > end_date_parsed:
            return False
        return True

    filtered = [item for item in items if in_range(item)]
    if not filtered:
        raise SystemExit("No episodes found within the specified date range.")

    # Newest-first ordering before limiting the download count.
    filtered.sort(key=lambda x: x["published"], reverse=(sort_order_normalized == "desc"))
    max_items = limit if (isinstance(limit, int) and limit > 0) else None
    to_download = filtered[:max_items] if max_items else filtered

    downloaded_entries = []
    new_download_count = 0
    for episode in to_download:
        base_name = sanitize_filename(episode["title"])
        ext = file_extension_from_url(episode["audio_url"])

        existing_path = existing_files_by_url.get(episode["audio_url"])
        if not existing_path or not existing_path.exists():
            matching_files = sorted(output_dir.glob(f"{base_name}*{ext}"))
            existing_path = next((path for path in matching_files if path.is_file()), None)

        used_existing_file = existing_path is not None
        if used_existing_file:
            audio_path = existing_path
            print(f"Skipping download (already exists): {episode['title']} -> {audio_path}")
        else:
            audio_path = download_audio(episode["audio_url"], output_dir, episode["title"])
            new_download_count += 1
            print(f"Downloaded: {episode['title']} -> {audio_path}")

        episode["file_path"] = audio_path

        # File size and fidelity calculations
        file_size_bytes = audio_path.stat().st_size
        duration_seconds = episode.get("duration_seconds")
        duration_source = episode.get("duration_source")
        feed_size = episode.get("feed_size_bytes")

        bitrate_kbps = episode.get("bitrate_kbps_feed")
        bitrate_source = "feed" if bitrate_kbps is not None else None

        size_for_calc = file_size_bytes or feed_size
        if bitrate_kbps is None and duration_seconds:
            if size_for_calc and duration_seconds > 0:
                bitrate_kbps = (size_for_calc * 8) / duration_seconds / 1000
                bitrate_source = "calculated_from_size_and_duration"

        if duration_seconds is None and bitrate_kbps:
            if bitrate_kbps > 0:
                duration_seconds = (file_size_bytes * 8) / (bitrate_kbps * 1000)
                duration_source = "estimated_from_bitrate_and_size"

        episode.update(
            {
                "file_size_bytes": file_size_bytes,
                "bitrate_kbps": bitrate_kbps,
                "bitrate_source": bitrate_source,
                "duration_seconds": duration_seconds,
                "duration_source": duration_source,
            }
        )
        downloaded_entries.append(episode)

    combined_metadata = merge_metadata(prior_metadata, downloaded_entries)
    write_metadata(combined_metadata, metadata_path)
    print(f"Saved metadata for {len(downloaded_entries)} episode(s) "
          f"({new_download_count} new download(s)) to {metadata_path}")
