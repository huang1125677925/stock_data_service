import os
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://tushare.pro"
PAGE_URL = urljoin(BASE_URL, "/document/2")
LOCAL_PAGE_PATH = os.path.join(
    os.path.dirname(__file__),
    "page.html",
)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tushare_docs")


def ensure_dir(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def slugify(text: str) -> str:
    # Keep Chinese and alphanum, replace spaces and unsafe chars with underscore
    text = text.strip()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "untitled"


def load_local_nav() -> BeautifulSoup:
    with open(LOCAL_PAGE_PATH, "r", encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    return soup


def get_jstree(nav_soup: BeautifulSoup):
    jstree = nav_soup.select_one("#jstree")
    if not jstree:
        jstree = nav_soup.select_one("nav.sidebar")
    if not jstree:
        raise RuntimeError("未找到侧边导航 #jstree 或 nav.sidebar")
    return jstree


def find_top_level_categories(nav_soup: BeautifulSoup):
    jstree = get_jstree(nav_soup)
    # top-level categories are direct children of the root UL
    top_level_items = []
    for li in jstree.select(":scope > ul > li"):
        a = li.find("a")
        if not a:
            continue
        title = a.get_text(strip=True)
        if not title:
            continue
        top_level_items.append({"title": title, "li": li})
    if not top_level_items:
        raise RuntimeError("未在导航中找到一级目录")
    return top_level_items


def extract_third_level_links(top_li):
    """
    支持两种结构：
    1) 三级结构：顶级 -> 二级(li>a) -> 三级(ul>li>a)
    2) 两级结构：顶级 -> 直接子项(li>a) 视为三级（无二级分组）
    """
    third_level = []

    # 找到顶级下的第一个子UL（有的结构可能包裹多层，这里选择最近的）
    first_ul = top_li.find("ul")
    if not first_ul:
        return third_level

    # 遍历顶级UL的第一层子LI（二级候选）
    for level2_li in first_ul.find_all("li", recursive=False):
        level2_title_a = level2_li.find("a", recursive=False)
        level2_title = level2_title_a.get_text(strip=True) if level2_title_a else ""

        nested_ul = level2_li.find("ul", recursive=False)
        if nested_ul:
            # 三级：二级下有子UL
            for level3_li in nested_ul.find_all("li", recursive=False):
                a = level3_li.find("a")
                if not a:
                    continue
                href = a.get("href")
                text = a.get_text(strip=True)
                if href and text:
                    third_level.append({
                        "level2": level2_title,
                        "text": text,
                        "href": href,
                    })
        else:
            # 两级：直接子项当作三级（无二级分组）
            if level2_title_a:
                href = level2_title_a.get("href")
                text = level2_title
                if href and text:
                    third_level.append({
                        "level2": "",  # 无分组
                        "text": text,
                        "href": href,
                    })
    return third_level


def fetch_content_div(url: str) -> tuple[str, str]:
    # Returns (title, inner_html)
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    content = soup.select_one("div.content.col-md-9.col-sm-8.col-xs-12") or soup.select_one("div.content")
    if not content:
        # As a fallback, look for main document section
        document = soup.select_one("#document")
        content = document if document else soup.body
    # Try to get a meaningful title
    title_node = content.find(["h1", "h2", "h3"]) if content else None
    title_text = title_node.get_text(strip=True) if title_node else ""
    inner_html = content.decode() if content else ""
    return title_text, inner_html


def save_markdown(top_level: str, category: str, name: str, source_url: str, title: str, html: str) -> str:
    top_slug = slugify(top_level)
    cat_slug = slugify(category) if category else ""
    name_slug = slugify(name)
    out_dir = os.path.join(OUTPUT_DIR, top_slug) if not cat_slug else os.path.join(OUTPUT_DIR, top_slug, cat_slug)
    ensure_dir(out_dir)
    filename = f"{name_slug}.md"
    out_path = os.path.join(out_dir, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# {title or name}\n\n")
        f.write(f"源链接: {source_url}\n\n")
        f.write("<!-- 以下为原始HTML内容，Markdown可直接渲染 -->\n\n")
        f.write(html)
        f.write("\n")
    return out_path


def main():
    ensure_dir(OUTPUT_DIR)
    soup = load_local_nav()
    top_categories = find_top_level_categories(soup)

    saved_total = 0
    for top in top_categories:
        top_title = top["title"]
        if top_title == "股票数据":
            # 已抓取过，跳过
            continue
        links = extract_third_level_links(top["li"])
        if not links:
            print(f"[SKIP] 一级目录 '{top_title}' 未发现三级目录，跳过")
            continue

        print(f"开始抓取一级目录 '{top_title}' 的三级目录，共 {len(links)} 项……")
        for item in links:
            href = item["href"]
            full_url = urljoin(BASE_URL, href) if href.startswith("/") else href
            try:
                title, inner_html = fetch_content_div(full_url)
                out_path = save_markdown(
                    top_level=top_title,
                    category=item["level2"],
                    name=item["text"],
                    source_url=full_url,
                    title=title or item["text"],
                    html=inner_html,
                )
                saved_total += 1
                print(f"[OK] {top_title} / {item['level2']} / {item['text']} -> {out_path}")
                time.sleep(0.8)
            except Exception as e:
                print(f"[ERR] {top_title} / {item['level2']} / {item['text']} @ {full_url}: {e}")

    print(f"完成：已新增保存 {saved_total} 个 Markdown 文件到 {OUTPUT_DIR}")


if __name__ == "__main__":
    main()