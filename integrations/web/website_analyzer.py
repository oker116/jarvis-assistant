import json
import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


class WebsiteAnalyzer:

    def __init__(self):
        self.version = "1.0"
        self.timeout = 15

    def analyze(self, url):

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(X11; Linux x86_64) "
                        "AppleWebKit/537.36 "
                        "Chrome/120 Safari/537.36"
                    )
                },
                allow_redirects=True
            )

            response.raise_for_status()

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Website request timed out."
            }

        except requests.exceptions.RequestException as error:
            return {
                "success": False,
                "error": str(error)
            }

        html = response.text

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        title = self._clean(
            soup.title.get_text()
            if soup.title
            else ""
        )

        description = ""

        meta_description = soup.find(
            "meta",
            attrs={"name": "description"}
        )

        if meta_description:
            description = self._clean(
                meta_description.get("content", "")
            )

        headings = []

        for tag in soup.find_all(
            ["h1", "h2", "h3"]
        )[:20]:

            text = self._clean(
                tag.get_text(" ", strip=True)
            )

            if text:
                headings.append(text)

        page_text = self._clean(
            soup.get_text(" ", strip=True)
        )

        buttons = []

        for element in soup.find_all(
            ["button", "a"]
        ):

            text = self._clean(
                element.get_text(" ", strip=True)
            )

            if not text:
                continue

            lowered = text.lower()

            keywords = [
                "buy",
                "book",
                "contact",
                "call",
                "whatsapp",
                "order",
                "shop",
                "get started",
                "احجز",
                "احجز الآن",
                "تواصل",
                "اتصل",
                "واتساب",
                "اطلب",
                "شراء",
                "اشترى",
                "اشتر",
                "ابدأ"
            ]

            if any(
                keyword in lowered
                for keyword in keywords
            ):
                buttons.append(text)

        links = []

        for anchor in soup.find_all(
            "a",
            href=True
        ):

            href = anchor.get("href", "")

            full_url = urljoin(
                response.url,
                href
            )

            links.append(full_url)

        whatsapp = any(
            "wa.me" in link.lower()
            or "whatsapp.com" in link.lower()
            for link in links
        )

        phone_numbers = self._find_phone_numbers(
            page_text
        )

        emails = self._find_emails(
            page_text
        )

        tracking = self._detect_tracking(
            html
        )

        forms = len(
            soup.find_all("form")
        )

        images = len(
            soup.find_all("img")
        )

        return {
            "success": True,

            "url": response.url,

            "domain": urlparse(
                response.url
            ).netloc,

            "status_code": response.status_code,

            "title": title,

            "description": description,

            "headings": headings,

            "cta": {
                "detected": bool(buttons),
                "buttons": buttons[:20]
            },

            "contact": {
                "whatsapp": whatsapp,
                "phones": phone_numbers[:10],
                "emails": emails[:10]
            },

            "tracking": tracking,

            "forms": forms,

            "images": images,

            "commercial_signals": {
                "has_offer_language":
                    self._has_offer_language(page_text),

                "has_pricing":
                    self._has_pricing(page_text),

                "has_contact_intent":
                    bool(buttons or phone_numbers or emails)
            },

            "analyzer_version": self.version
        }

    @staticmethod
    def _clean(text):

        return re.sub(
            r"\s+",
            " ",
            str(text)
        ).strip()

    @staticmethod
    def _find_emails(text):

        pattern = (
            r"[A-Za-z0-9._%+-]+"
            r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
        )

        return list(
            dict.fromkeys(
                re.findall(
                    pattern,
                    text
                )
            )
        )

    @staticmethod
    def _find_phone_numbers(text):

        pattern = (
            r"(?:\+?\d[\d\s().-]{7,}\d)"
        )

        results = re.findall(
            pattern,
            text
        )

        cleaned = []

        for number in results:

            number = re.sub(
                r"\s+",
                " ",
                number
            ).strip()

            if number not in cleaned:
                cleaned.append(number)

        return cleaned

    @staticmethod
    def _detect_tracking(html):

        html_lower = html.lower()

        systems = {}

        systems["facebook_pixel"] = (
            "fbq(" in html_lower
            or "connect.facebook.net" in html_lower
        )

        systems["google_analytics"] = (
            "google-analytics.com" in html_lower
            or "googletagmanager.com" in html_lower
            or "gtag(" in html_lower
        )

        systems["google_tag_manager"] = (
            "googletagmanager.com" in html_lower
        )

        systems["tiktok_pixel"] = (
            "analytics.tiktok.com" in html_lower
            or "ttq." in html_lower
        )

        systems["snap_pixel"] = (
            "sc-static.net/scevent.min.js" in html_lower
            or "snaptr(" in html_lower
        )

        systems["linkedin_insight"] = (
            "snap.licdn.com" in html_lower
            or "linkedin.com/insight" in html_lower
        )

        systems["detected"] = [
            name
            for name, found in systems.items()
            if found is True
        ]

        return systems

    @staticmethod
    def _has_offer_language(text):

        lowered = text.lower()

        keywords = [
            "discount",
            "sale",
            "offer",
            "limited time",
            "free",
            "خصم",
            "عرض",
            "مجانا",
            "مجاناً",
            "لفترة محدودة"
        ]

        return any(
            keyword in lowered
            for keyword in keywords
        )

    @staticmethod
    def _has_pricing(text):

        patterns = [
            r"\$\s?\d+",
            r"\d+\s?\$",
            r"€\s?\d+",
            r"\d+\s?جنيه",
            r"\d+\s?ريال",
            r"\d+\s?درهم"
        ]

        return any(
            re.search(
                pattern,
                text,
                re.IGNORECASE
            )
            for pattern in patterns
        )


if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:

        print(
            "Usage: python3 "
            "website_analyzer.py "
            "<URL>"
        )

        raise SystemExit(1)

    analyzer = WebsiteAnalyzer()

    result = analyzer.analyze(
        sys.argv[1]
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )
