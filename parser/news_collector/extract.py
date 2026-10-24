from __future__ import annotations

from datetime import date, datetime, timezone
import json
import re
from html import unescape
from urllib.parse import urljoin

from lxml import html
import trafilatura

from .browser import Page
from .models import Article, Source, normalize_url, utcnow
from .topics import classify
from .images import candidates


class ExtractionError(ValueError):
    pass


def url_publication_day(url):
    """A date hint for scheduling only; never fabricate published_at from a URL."""
    from urllib.parse import urlsplit
    path = urlsplit(url).path
    for pattern in (r"/(20\d{2})[/-](\d{2})[/-](\d{2})(?:/|-)", r"/a/(20\d{2})(\d{2})/(\d{2})/"):
        match = re.search(pattern,path)
        if match:
            try:
                return date(*map(int,match.groups()))
            except ValueError:
                return None
    return None


def normalized_text(value):
    return "\n\n".join(re.sub(r"[ \t\r\n]+", " ", x).strip() for x in re.split(r"\n\s*\n", unescape(value or "")) if x.strip())


def discover(page: Page, source: Source, limit=500):
    tree = html.fromstring(page.html)
    urls = []
    seen = set()
    scores = {}
    links = []
    for selector in source.listing_link_selectors:
        links.extend(tree.xpath(selector))
    if not source.listing_link_selectors:
        links = tree.xpath("//a[@href]")
    for link in links:
        label = "" if isinstance(link,str) else normalized_text(link.text_content())
        href = link if isinstance(link,str) else link.get("href","")
        try:
            url = normalize_url(urljoin(page.url,href))
        except ValueError:
            continue
        if not source.accepts(url):
            continue
        topics, score = classify(label+" "+url,None,"")
        if source.collection_priority >= 65:
            score = sum({"finance":12,"economy":12,"business":5,"energy":3}.get(topic,0) for topic in topics)
        scores[url] = max(scores.get(url,0),score)
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return sorted(urls,key=lambda url:scores[url],reverse=True)[:limit]


def listing_next(page: Page, source: Source, seed: str):
    """Only explicit next-page controls within the original listing path."""
    from urllib.parse import urlsplit
    tree = html.fromstring(page.html)
    links = tree.xpath('//a[@rel="next" or @aria-label="Next page" or @aria-label="Следующая страница"]/@href | //link[@rel="next"]/@href')
    base = urlsplit(seed).path.rstrip("/") or "/"
    for link in links:
        try:
            url = normalize_url(urljoin(page.url, link))
        except ValueError:
            continue
        path = urlsplit(url).path
        inside = path == base or path.startswith(base + "/") or (base == "/" and path.startswith("/page/"))
        if source.allows_host(url) and not source.accepts(url) and inside:
            return url
    return None


def jsonld_articles(tree):
    def walk(value):
        if isinstance(value,list):
            for item in value:
                yield from walk(item)
        elif isinstance(value,dict):
            types = value.get("@type",[])
            types = [types] if isinstance(types,str) else types
            if any(t in ("NewsArticle","Article","ReportageNewsArticle","AnalysisNewsArticle") for t in types):
                yield value
            for key in ("@graph", "mainEntity"):
                if key in value:
                    yield from walk(value[key])
    for text in tree.xpath('//script[@type="application/ld+json"]/text()'):
        try:
            yield from walk(json.loads(text))
        except (ValueError,TypeError):
            continue


def parse_date(value):
    if not value or not isinstance(value,str):
        return None,"missing"
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z","+00:00"))
        if dt.tzinfo is None:
            return None,"timezone_missing"
        return dt.astimezone(timezone.utc).isoformat(),"source"
    except ValueError:
        return None,"unparsed"


def extract_article(page: Page, source: Source, raw_path: str) -> Article:
    tree = html.fromstring(page.html)
    documents = list(jsonld_articles(tree))
    ld = next((x for x in documents if x.get("headline")),documents[0] if documents else {})
    def meta(*names):
        for name in names:
            values = tree.xpath('//meta[@property=$name or @name=$name or @itemprop=$name]/@content',name=name)
            if values and values[0].strip():
                return values[0].strip()
        return None
    h1 = tree.xpath("//h1")
    title = normalized_text(ld.get("headline") or (h1[0].text_content() if h1 else None) or meta("og:title") or "")
    if not title:
        raise ExtractionError("No article title")
    flags = []
    canonical = page.url
    declared = tree.xpath('//link[@rel="canonical"]/@href')
    if declared:
        candidate = normalize_url(urljoin(page.url,declared[0]))
        if source.accepts(candidate):
            canonical = candidate
        elif source.allows_host(candidate):
            raise ExtractionError("Canonical points to a listing or unsupported page, not an article")
        else:
            flags.append("canonical_outside_article_allowlist")
    canonical = normalize_url(canonical)
    if not source.accepts(canonical):
        raise ExtractionError("Redirected outside source article allowlist")
    raw_date = ld.get("datePublished") or meta("article:published_time","datePublished","pubdate","date")
    if not raw_date:
        dates = tree.xpath("//time[@datetime]/@datetime")
        raw_date = dates[0] if dates else None
    specific_body = any(tree.xpath(selector) for selector in source.body_selectors)
    if not documents and not raw_date and not tree.xpath("//article") and meta("og:type") != "article" and not specific_body:
        raise ExtractionError("No article evidence: no article schema, date, article element or og:type")
    published,date_status = parse_date(raw_date)
    modified,_ = parse_date(ld.get("dateModified") or meta("article:modified_time","dateModified"))
    if not published:
        flags.append("publication_date_"+date_status)
    # isAccessibleForFree=false is an explicit limit, never take hidden articleBody.
    paywall = ld.get("isAccessibleForFree") in (False,"False","false")
    method = "trafilatura"
    body = ""
    for selector in source.body_selectors:
        # Configured XPath selectors avoid an extra CSS parser dependency.
        nodes = tree.xpath(selector)
        if nodes:
            paragraphs = [normalized_text(n.text_content()) for n in nodes if not isinstance(n,str)]
            candidate = "\n\n".join(p for p in paragraphs if p)
            if len(candidate) >= source.min_text_chars:
                body,method = candidate,"source_xpath"
                break
    if not body and not paywall and isinstance(ld.get("articleBody"),str):
        body = normalized_text(html.fromstring("<div>"+ld["articleBody"]+"</div>").text_content())
        method = "jsonld_article_body"
    if not body:
        body = trafilatura.extract(page.html,url=page.url,include_comments=False,include_tables=True,
                                   favor_precision=True,no_fallback=False) or ""
    body = normalized_text(body)
    subscription = re.search(r"\b(?:try unlimited access|subscribe to unlock (?:this|the) article|explore our full range of subscriptions|get unlimited digital access|subscribe to continue reading)\b",body,re.I)
    if subscription:
        body = body[:subscription.start()].strip()
        flags.append("subscription_offer_removed")
    if len(body) < source.min_text_chars:
        raise ExtractionError(f"Insufficient article text ({len(body)} characters)")
    if len(body) < 2500 and re.search(r"наименование издания.{0,50}forbes", body, re.I):
        raise ExtractionError("Publisher registration footer instead of article text")
    if paywall:
        flags.append("publisher_marks_paid_content")
    if re.search(r"\b(?:BUSINESS WIRE|PRNewswire|press release)\b",body[:1500],re.I):
        flags.append("possible_press_release")
    # We cannot certify completeness from text length. Keep scope explicit.
    scope = "accessible_excerpt" if paywall else "extracted_article"
    authors = ld.get("author",[])
    if not isinstance(authors,list):
        authors = [authors]
    authors = [a.get("name","") if isinstance(a,dict) else a for a in authors]
    authors = [a for a in authors if isinstance(a,str) and a]
    if not authors and meta("author"):
        authors = [meta("author")]
    tags = ld.get("keywords") or []
    if isinstance(tags,str):
        tags = [x.strip() for x in tags.split(",") if x.strip()]
    language = tree.get("lang") or source.language
    article = Article(source.id,source.name,page.requested_url,canonical,title,body,
                   meta("description","og:description"),authors,language,source.publisher_country,
                   published,raw_date,date_status,modified,utcnow(),scope,method,raw_path,flags,
                   [x for x in tags if isinstance(x,str)])
    article.topics, article.relevance_score = classify(title, article.description, body)
    article.source_topics = list(source.topics)
    article.source_kind = source.source_kind
    article.images = candidates(tree,source,canonical,ld)
    return article
