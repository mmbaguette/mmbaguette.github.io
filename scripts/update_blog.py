"""Rebuild the Blog list in index.html from my Substack posts.

Fetches the newest posts from Substack's archive endpoint (it includes each
post's subtitle and tags, which the RSS feed doesn't) and rewrites everything
between the BLOG:START and BLOG:END comments in index.html.
Exits with an error, changing nothing, if Substack can't be reached.
"""
import html
import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

FEED = "https://alimohammedali3.substack.com/api/v1/archive?sort=new&limit=50"
PAGE = Path(__file__).resolve().parents[2] / "index.html"
START, END = "<!-- BLOG:START -->", "<!-- BLOG:END -->"


def fetch_posts():
    req = urllib.request.Request(FEED, headers={"User-Agent": "Mozilla/5.0 (portfolio blog updater)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def render(posts):
    items = []
    for p in posts:
        if p.get("audience") not in (None, "everyone"):  # skip paid-only posts
            continue
        title = html.escape(p["title"])
        url = html.escape(p["canonical_url"], quote=True)
        date = datetime.fromisoformat(p["post_date"].replace("Z", "+00:00")).strftime("%b %Y")
        subtitle = (p.get("subtitle") or "").strip()
        tags = [t["name"] for t in p.get("postTags") or [] if not t.get("hidden")]
        lines = [
            '    <div class="post">',
            f'      <h3><a href="{url}">{title}</a></h3>',
            f'      <p class="meta">{date}</p>',
        ]
        if subtitle:
            lines.append(f"      <p>{html.escape(subtitle)}</p>")
        if tags:
            chips = "".join(f'<span class="tag">{html.escape(t)}</span>' for t in tags)
            lines.append(f'      <div class="tags">{chips}</div>')
        lines.append("    </div>")
        items.append("\n".join(lines))
    if not items:
        items.append('    <p class="meta">No posts yet.</p>')
    return "\n".join(items)


def main():
    try:
        posts = fetch_posts()
    except Exception as e:  # network error, Substack blocking the runner, bad JSON
        print(f"Could not fetch Substack posts: {e}", file=sys.stderr)
        return 1
    page = PAGE.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(page):
        print("BLOG markers not found in index.html", file=sys.stderr)
        return 1
    new = pattern.sub(lambda _: f"{START}\n{render(posts)}\n    {END}", page)
    if new != page:
        PAGE.write_text(new, encoding="utf-8")
        print(f"Blog list updated ({len(posts)} posts).")
    else:
        print("Blog list already up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
