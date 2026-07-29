#!/usr/bin/env python3
"""
newpost — scan posts/ for .md files not in manifest.json and add them one by one.

usage:
  python3 tools/newpost.py            # interactive: walks through each new file
  python3 tools/newpost.py --dry-run  # just show what would be processed

for each .md file in posts/ whose slug is not in manifest.json, prompts for
title, date, tags, and excerpt, then updates manifest.json. newest-first.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "posts" / "manifest.json"
POSTS_DIR = ROOT / "posts"


def prompt(msg: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{msg}{suffix}: ").strip()
    return val or default


def prompt_yn(msg: str, default: bool = False) -> bool:
    suffix = "(Y/n)" if default else "(y/N)"
    val = input(f"{msg} {suffix}: ").strip().lower()
    if not val:
        return default
    return val in ("y", "yes")


def load_manifest() -> list[dict]:
    if not MANIFEST.exists():
        return []
    try:
        return json.loads(MANIFEST.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"manifest.json is malformed: {e}")


def save_manifest(posts: list[dict]) -> None:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    posts.sort(key=lambda p: p.get("date", ""), reverse=True)
    MANIFEST.write_text(json.dumps(posts, indent=2) + "\n")


def find_new_files(known_slugs: set[str]) -> list[Path]:
    if not POSTS_DIR.exists():
        return []
    return sorted(
        p for p in POSTS_DIR.glob("*.md")
        if p.stem not in known_slugs
    )


def process_file(md_path: Path, existing: list[dict]) -> dict | None:
    """prompt for one file's metadata; return entry or None if skipped."""
    slug = md_path.stem
    print()
    print(f"=== {md_path.name} ===")
    print(f"  slug: {slug}")
    # show a preview of the body so they know what the post is about
    body = md_path.read_text().strip()
    preview = body[:200].replace("\n", " ")
    if len(body) > 200:
        preview += "..."
    if preview:
        print(f"  preview: {preview}")

    if not prompt_yn("  add this to the manifest?", default=True):
        print("  skipped")
        return None

    title = prompt("  title", default=slug.replace("-", " "))
    date_str = prompt("  date (YYYY-MM-DD)", default=date.today().isoformat())
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        sys.exit(f"  invalid date: {date_str!r} (expected YYYY-MM-DD)")

    tags_raw = prompt("  tags (comma-separated, optional)", default="")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    excerpt = prompt("  excerpt (optional)", default="")

    entry = {"slug": slug, "title": title, "date": date_str}
    if tags:
        entry["tags"] = tags
    if excerpt:
        entry["excerpt"] = excerpt
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(
        description="add posts/*.md files to manifest.json, one by one"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="only show which files would be processed")
    args = parser.parse_args()

    posts = load_manifest()
    known = {p["slug"] for p in posts}
    new_files = find_new_files(known)

    if not new_files:
        print("no new .md files found in posts/")
        return 0

    print(f"found {len(new_files)} new file{'s' if len(new_files) != 1 else ''}:")
    for f in new_files:
        print(f"  - {f.name}")

    if args.dry_run:
        return 0

    added = []
    for md_path in new_files:
        entry = process_file(md_path, posts)
        if entry is not None:
            posts.append(entry)
            added.append(entry)

    if not added:
        print("\nnothing added")
        return 0

    save_manifest(posts)

    print()
    print(f"updated {MANIFEST.relative_to(ROOT)}")
    print(f"added {len(added)} post{'s' if len(added) != 1 else ''}:")
    for e in added:
        print(f"  - {e['slug']} ({e['date']}): {e['title']}")
    print()
    print("next: review, then commit and push:")
    print("  git add posts/")
    print(f"  git commit -m 'add {len(added)} new post{'s' if len(added) != 1 else ''}'")
    print("  git push")
    return 0


if __name__ == "__main__":
    sys.exit(main())