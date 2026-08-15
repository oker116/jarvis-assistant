import json
import re
import sys
from html import unescape
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen


UA = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 Chrome/126 Safari/537.36"
)


def fetch(url, timeout=20):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def textify(html):
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.I | re.S)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.I | re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", unescape(html)).strip()


def clean_fb_url(url):
    if not url:
        return None

    if "facebook.com" not in url.lower():
        return None

    parsed = urlparse(url)
    path = parsed.path.strip("/")

    if not path:
        return None

    blocked = (
        "share",
        "sharer",
        "groups",
        "events",
        "marketplace",
        "watch",
        "reel",
        "photo",
        "login",
        "plugins",
    )

    if any(path.startswith(x) for x in blocked):
        return None

    return f"https://www.facebook.com/{path}"


def search_pages(query, limit=5):
    import base64
    import html as html_module
    from urllib.parse import quote, parse_qs, urlparse

    search_url = (
        "https://www.bing.com/search?q="
        + quote(f"site:facebook.com {query}")
    )

    req = Request(
        search_url,
        headers={
            "User-Agent": UA,
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    with urlopen(req, timeout=20) as response:
        html = response.read().decode("utf-8", "ignore")

    found = []
    seen = set()

    blocks = re.findall(
        r'<li[^>]*class="[^"]*b_algo[^"]*"[^>]*>(.*?)</li>',
        html,
        flags=re.I | re.S,
    )

    def resolve_bing(url):
        url = html_module.unescape(url)
        parsed = urlparse(url)
        encoded = parse_qs(parsed.query).get("u", [None])[0]

        if not encoded:
            return url

        try:
            if encoded.startswith("a1"):
                encoded = encoded[2:]

            padded = encoded + "=" * (-len(encoded) % 4)

            return base64.b64decode(
                padded
            ).decode("utf-8", "ignore")

        except Exception:
            return url

    for block in blocks:
        urls = re.findall(
            r'<a[^>]+href="([^"]+)"',
            block,
            flags=re.I,
        )

        for raw_url in urls:
            final_url = resolve_bing(raw_url)
            fb_url = clean_fb_url(final_url)

            if not fb_url or fb_url in seen:
                continue

            seen.add(fb_url)

            title_match = re.search(
                r'<h2[^>]*>.*?<a[^>]*>(.*?)</a>',
                block,
                flags=re.I | re.S,
            )

            title = query

            if title_match:
                title = html_module.unescape(
                    re.sub(
                        r"<[^>]+>",
                        "",
                        title_match.group(1),
                    )
                ).strip()

            found.append({
                "name": title,
                "facebook": fb_url,
            })

            if len(found) >= limit:
                return found

    return found

def research_page(item):
    fb_url = item["facebook"]

    result = {
        "name": item.get("name"),
        "facebook": {
            "exists": True,
            "url": fb_url,
            "recent_posts": False,
        },
        "website": {
            "success": False,
            "url": None,
            "domain": None,
            "cta": {
                "detected": False,
                "buttons": [],
            },
            "contact": {
                "whatsapp": False,
                "phones": [],
                "emails": [],
            },
            "commercial_signals": {
                "has_offer_language": False,
                "has_pricing": False,
                "has_contact_intent": False,
            },
        },
        "ads": {
            "running": False,
            "historical": False,
            "creative_count": 0,
            "ad_library_url": None,
        },
    }

    try:
        html = fetch(fb_url)
        body = textify(html)

        title = re.search(
            r"<title[^>]*>(.*?)</title>",
            html,
            flags=re.I | re.S,
        )

        if title:
            result["name"] = (
                re.sub(r"\s+", " ", unescape(title.group(1)))
                .strip()
            )

        result["facebook"]["recent_posts"] = bool(
            re.search(
                r"followers|following|posts|likes",
                body,
                flags=re.I,
            )
        )

        links = re.findall(
            r'href=["\']([^"\']+)["\']',
            html,
            flags=re.I,
        )

        for href in links:
            href = unescape(href)
            absolute = urljoin(fb_url, href)
            low = absolute.lower()

            if (
                absolute.startswith("http")
                and "facebook.com" not in low
                and "instagram.com" not in low
                and "messenger.com" not in low
            ):
                if not result["website"]["url"]:
                    result["website"]["url"] = absolute
                    result["website"]["domain"] = urlparse(
                        absolute
                    ).netloc
                    result["website"]["success"] = True

            if (
                "wa.me/" in low
                or "api.whatsapp.com" in low
                or "whatsapp.com/send" in low
            ):
                result["website"]["contact"]["whatsapp"] = True

        phones = re.findall(
            r"(?:\+20|0020|0)?1[0125]\d{8}",
            body.replace(" ", ""),
        )

        emails = re.findall(
            r"[A-Za-z0-9._%+-]+@"
            r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            body,
        )

        result["website"]["contact"]["phones"] = list(
            dict.fromkeys(phones)
        )[:5]

        result["website"]["contact"]["emails"] = list(
            dict.fromkeys(emails)
        )[:5]

    except Exception as exc:
        result["facebook"]["error"] = str(exc)

    name_for_search = quote(
        result.get("name") or item["facebook"]
    )

    result["ads"]["ad_library_url"] = (
        "https://www.facebook.com/ads/library/"
        "?active_status=all"
        "&ad_type=all"
        "&country=EG"
        f"&q={name_for_search}"
    )

    return result


def discover(query, limit=5):
    pages = search_pages(query, limit)
    return [research_page(x) for x in pages]


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]).strip()

    if not query:
        print(
            'Usage: python3 -m integrations.sales.meta_discovery "restaurant Cairo"'
        )
        raise SystemExit(1)

    data = discover(query, 5)

    print(json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
    ))
