#!/usr/bin/env python3
"""
Prospect Analyzer — AI Sales Team for Claude Code
Fetches a company website and extracts structured data for prospect analysis.

Usage:
    python3 analyze_prospect.py --url <url> --output json
    python3 analyze_prospect.py --help
"""

import argparse
import json
import re
import ssl
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Lightweight HTML helpers
# ---------------------------------------------------------------------------

class TagCollector(HTMLParser):
    """Minimal HTML parser that collects tags, attributes, and text."""

    def __init__(self):
        super().__init__()
        self.title = ""
        self.meta = {}
        self.headings = []
        self.links = []
        self.scripts = []
        self.text_chunks = []
        self.json_ld = []
        self._in_title = False
        self._in_script = False
        self._script_type = ""
        self._script_buf = ""
        self._current_tag = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self._current_tag = tag
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = attrs_dict.get("name", attrs_dict.get("property", "")).lower()
            content = attrs_dict.get("content", "")
            if name and content:
                self.meta[name] = content
        elif tag == "a":
            href = attrs_dict.get("href", "")
            text = attrs_dict.get("title", "")
            self.links.append({"href": href, "text": text})
        elif tag == "script":
            src = attrs_dict.get("src", "")
            if src:
                self.scripts.append(src)
            stype = attrs_dict.get("type", "")
            if "ld+json" in stype:
                self._in_script = True
                self._script_type = "ld+json"
                self._script_buf = ""
        elif tag in ("h1", "h2", "h3"):
            pass  # text collected in handle_data

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_script:
            self._in_script = False
            if self._script_type == "ld+json":
                try:
                    self.json_ld.append(json.loads(self._script_buf))
                except json.JSONDecodeError:
                    pass
        self._current_tag = ""

    def handle_data(self, data):
        stripped = data.strip()
        if self._in_title:
            self.title += stripped
        elif self._in_script:
            self._script_buf += data
        elif self._current_tag in ("h1", "h2", "h3"):
            self.headings.append({"level": self._current_tag, "text": stripped})
        if stripped:
            self.text_chunks.append(stripped)


# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------

def fetch_url(url, timeout=10):
    """Fetch a URL and return (status_code, html_string). Returns (None, None) on failure."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ProspectAnalyzer/1.0)"}
    req = Request(url, headers=headers)
    try:
        resp = urlopen(req, timeout=timeout, context=ctx)
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.status, resp.read().decode(charset, errors="replace")
    except HTTPError as exc:
        return exc.code, None
    except (URLError, OSError, Exception):
        return None, None


def parse_html(html):
    """Parse HTML and return a TagCollector."""
    collector = TagCollector()
    try:
        collector.feed(html)
    except Exception:
        pass
    return collector


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

TECH_SIGNATURES = {
    "WordPress": [r"wp-content", r"wp-includes", r'name="generator".*?WordPress'],
    "Shopify": [r"cdn\.shopify\.com", r"Shopify\.theme"],
    "HubSpot": [r"hs-scripts\.com", r"hbspt", r"hubspot"],
    "Webflow": [r"webflow\.com", r"Webflow"],
    "Next.js": [r"_next/static", r"__NEXT_DATA__"],
    "React": [r"react\.production\.min", r"react-dom"],
    "Vue.js": [r"vue\.min\.js", r"vue\.runtime"],
    "Angular": [r"angular\.min\.js", r"ng-version"],
    "Gatsby": [r"gatsby", r"___gatsby"],
    "Squarespace": [r"squarespace\.com", r"static\.squarespace"],
    "Wix": [r"wix\.com", r"parastorage\.com"],
    "Google Analytics": [r"google-analytics\.com", r"gtag/js", r"googletagmanager"],
    "Segment": [r"cdn\.segment\.com", r"analytics\.js"],
    "Intercom": [r"intercom", r"widget\.intercom\.io"],
    "Drift": [r"drift\.com", r"js\.driftt\.com"],
    "Stripe": [r"js\.stripe\.com", r"stripe"],
    "Salesforce": [r"force\.com", r"salesforce"],
}

SOCIAL_PATTERNS = {
    "linkedin": r"linkedin\.com/(?:company|in)/[\w-]+",
    "twitter": r"(?:twitter|x)\.com/[\w]+",
    "facebook": r"facebook\.com/[\w.]+",
    "instagram": r"instagram\.com/[\w.]+",
    "youtube": r"youtube\.com/(?:c/|channel/|@)[\w-]+",
    "github": r"github\.com/[\w-]+",
}

INDUSTRY_KEYWORDS = {
    "SaaS": ["saas", "software as a service", "cloud platform", "subscription"],
    "Fintech": ["fintech", "financial technology", "payments", "banking"],
    "Healthcare": ["healthcare", "health tech", "medical", "patient", "clinical"],
    "E-commerce": ["ecommerce", "e-commerce", "online store", "shop", "retail"],
    "EdTech": ["edtech", "education", "learning platform", "courses"],
    "Cybersecurity": ["security", "cyber", "threat", "vulnerability"],
    "AI/ML": ["artificial intelligence", "machine learning", "ai-powered", "deep learning"],
    "DevTools": ["developer", "devtools", "api", "sdk", "infrastructure"],
    "MarTech": ["marketing", "martech", "analytics", "campaign", "automation"],
    "HRTech": ["hr tech", "human resources", "recruiting", "talent"],
}


def extract_company_name(parsed):
    """Extract company name from multiple sources."""
    for key in ("og:site_name", "application-name"):
        if key in parsed.meta:
            return parsed.meta[key]
    if parsed.title:
        name = parsed.title.split("|")[0].split("-")[0].split("—")[0].strip()
        if name:
            return name
    for h in parsed.headings:
        if h["level"] == "h1" and h["text"]:
            return h["text"]
    return ""


def extract_description(parsed):
    """Extract company description."""
    for key in ("description", "og:description", "twitter:description"):
        if key in parsed.meta:
            return parsed.meta[key]
    return ""


def detect_tech_stack(html, parsed):
    """Detect technologies used on the site."""
    detected = []
    combined = html + " ".join(parsed.scripts)
    for tech, patterns in TECH_SIGNATURES.items():
        for pat in patterns:
            if re.search(pat, combined, re.IGNORECASE):
                detected.append(tech)
                break
    generator = parsed.meta.get("generator", "")
    if generator and generator not in detected:
        detected.append(generator)
    return list(set(detected))


def extract_social_links(html):
    """Extract social media profile URLs."""
    found = {}
    for platform, pattern in SOCIAL_PATTERNS.items():
        matches = re.findall(r"https?://" + pattern, html, re.IGNORECASE)
        if matches:
            found[platform] = list(set(matches))[:3]
    return found


def detect_industry(html):
    """Detect likely industry from page content."""
    text_lower = html.lower()
    scores = {}
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[industry] = score
    sorted_industries = sorted(scores.items(), key=lambda x: -x[1])
    return [ind for ind, _ in sorted_industries[:3]]


def extract_team_members(html):
    """Extract team member information from team/about pages."""
    members = []
    # Look for JSON-LD Person schemas
    for match in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL):
        try:
            data = json.loads(match.group(1))
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and item.get("@type") == "Person":
                    members.append({
                        "name": item.get("name", ""),
                        "title": item.get("jobTitle", ""),
                        "url": item.get("url", ""),
                    })
        except (json.JSONDecodeError, TypeError):
            pass
    # Look for common card patterns: name in h3/h4 + title in p/span
    card_pattern = re.compile(
        r'<(?:h[2-4]|strong)[^>]*>\s*([\w\s.\'-]{2,40})\s*</(?:h[2-4]|strong)>\s*'
        r'(?:<[^>]*>)*\s*(?:<(?:p|span|div)[^>]*>\s*'
        r'([\w\s,&/\'-]{2,60})\s*</(?:p|span|div)>)',
        re.IGNORECASE,
    )
    for m in card_pattern.finditer(html):
        name = m.group(1).strip()
        title = m.group(2).strip()
        if name and title and not any(c in name for c in "<>&"):
            members.append({"name": name, "title": title, "url": ""})
    seen = set()
    unique = []
    for m in members:
        key = m["name"].lower()
        if key not in seen and m["name"]:
            seen.add(key)
            unique.append(m)
    return unique[:20]


def extract_pricing_info(html):
    """Detect pricing tiers from a pricing page."""
    tiers = []
    price_matches = re.findall(r'\$\s*(\d[\d,]*(?:\.\d{2})?)\s*(?:/\s*(?:mo|month|yr|year|user))?', html, re.IGNORECASE)
    tier_names = re.findall(r'(?:Free|Starter|Basic|Pro|Professional|Business|Enterprise|Growth|Scale|Team|Premium)\s*(?:Plan)?', html, re.IGNORECASE)
    for i, name in enumerate(list(set(tier_names))[:5]):
        price = price_matches[i] if i < len(price_matches) else "Contact Sales"
        tiers.append({"tier": name.strip(), "price": f"${price}" if isinstance(price, str) and price[0].isdigit() else price})
    if not tiers and price_matches:
        for i, p in enumerate(price_matches[:4]):
            tiers.append({"tier": f"Tier {i + 1}", "price": f"${p}"})
    return tiers


def detect_job_postings(html):
    """Detect if a careers page has job listings."""
    job_indicators = [
        r"open\s*positions", r"job\s*openings", r"we.*?re\s*hiring",
        r"career\s*opportunities", r"apply\s*now", r"join\s*our\s*team",
        r"current\s*openings", r"view\s*all\s*jobs",
    ]
    for pattern in job_indicators:
        if re.search(pattern, html, re.IGNORECASE):
            return True
    return False


def extract_contact_info(html):
    """Extract contact email and phone from page."""
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', html)
    phones = re.findall(r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', html)
    filtered_emails = [e for e in emails if not e.endswith((".png", ".jpg", ".svg", ".gif"))]
    return {
        "emails": list(set(filtered_emails))[:5],
        "phones": list(set(phones))[:3],
    }


def estimate_company_size(html):
    """Detect company size signals."""
    signals = {}
    emp_match = re.search(r'(\d[\d,]*)\+?\s*(?:employees?|team\s*members?|people)', html, re.IGNORECASE)
    if emp_match:
        signals["estimated_employees"] = emp_match.group(1).replace(",", "")
    loc_patterns = re.findall(r'(?:offices?\s*in|locations?\s*in|headquartered\s*in)\s*([A-Z][\w\s,]+)', html)
    if loc_patterns:
        signals["locations_mentioned"] = [l.strip() for l in loc_patterns[:5]]
    for marker in ["Series A", "Series B", "Series C", "Series D", "IPO", "public company"]:
        if marker.lower() in html.lower():
            signals["funding_stage"] = marker
            break
    return signals


# ---------------------------------------------------------------------------
# Main analysis pipeline
# ---------------------------------------------------------------------------

SUBPAGES = ["/about", "/team", "/pricing", "/careers", "/blog", "/contact",
            "/about-us", "/our-team", "/leadership", "/jobs"]


def analyze(url):
    """Run full prospect analysis on a URL."""
    parsed_url = urlparse(url)
    if not parsed_url.scheme:
        url = "https://" + url
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    result = {
        "url": url,
        "company_name": "",
        "description": "",
        "industry_signals": [],
        "tech_stack": [],
        "social_links": {},
        "team_members": [],
        "pricing_tiers": [],
        "has_job_postings": False,
        "contact_info": {"emails": [], "phones": []},
        "company_size_signals": {},
        "pages_analyzed": [],
        "errors": [],
    }

    # Fetch homepage
    status, html = fetch_url(url)
    if not html:
        result["errors"].append(f"Failed to fetch homepage (status: {status})")
        return result

    home_parsed = parse_html(html)
    result["pages_analyzed"].append(url)
    result["company_name"] = extract_company_name(home_parsed)
    result["description"] = extract_description(home_parsed)
    result["tech_stack"] = detect_tech_stack(html, home_parsed)
    result["social_links"] = extract_social_links(html)
    result["industry_signals"] = detect_industry(html)
    result["contact_info"] = extract_contact_info(html)
    result["company_size_signals"] = estimate_company_size(html)

    all_html = html

    # Fetch subpages
    for path in SUBPAGES:
        sub_url = urljoin(base, path)
        sub_status, sub_html = fetch_url(sub_url, timeout=8)
        if sub_status == 200 and sub_html:
            result["pages_analyzed"].append(sub_url)
            all_html += sub_html

            if "team" in path or "about" in path or "leadership" in path:
                members = extract_team_members(sub_html)
                result["team_members"].extend(members)
            if "pricing" in path:
                result["pricing_tiers"] = extract_pricing_info(sub_html)
            if "career" in path or "job" in path:
                result["has_job_postings"] = detect_job_postings(sub_html)
            if "contact" in path:
                contact = extract_contact_info(sub_html)
                result["contact_info"]["emails"] = list(set(result["contact_info"]["emails"] + contact["emails"]))
                result["contact_info"]["phones"] = list(set(result["contact_info"]["phones"] + contact["phones"]))

    # Merge social links from all pages
    extra_social = extract_social_links(all_html)
    for platform, urls in extra_social.items():
        if platform not in result["social_links"]:
            result["social_links"][platform] = urls

    # Deduplicate team members
    seen = set()
    unique_members = []
    for m in result["team_members"]:
        key = m["name"].lower()
        if key not in seen:
            seen.add(key)
            unique_members.append(m)
    result["team_members"] = unique_members[:20]

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Prospect Analyzer — Fetch and analyze a company website for sales intelligence.",
        epilog="Example: python3 analyze_prospect.py --url https://example.com --output json",
    )
    parser.add_argument("--url", required=True, help="Company website URL to analyze")
    parser.add_argument("--output", choices=["json"], default="json", help="Output format (default: json)")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds (default: 10)")
    args = parser.parse_args()

    result = analyze(args.url)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
