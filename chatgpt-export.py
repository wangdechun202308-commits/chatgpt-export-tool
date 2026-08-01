#!/usr/bin/env python3
"""ChatGPT 分享链接导出工具 | 纯 Python · 跨平台 · 零依赖

用法:
  python3 chatgpt-export.py <分享链接>
  python3 chatgpt-export.py <分享链接> --out ./output
  python3 chatgpt-export.py <分享链接> --format txt --json
"""
import re, json, sys, os, ssl, urllib.request
from datetime import datetime

def unescape_js(data: bytes) -> bytes:
    out = bytearray(); i = 0
    while i < len(data):
        if data[i] != 0x5c:
            out.append(data[i]); i += 1; continue
        if i + 1 >= len(data):
            out.append(0x5c); i += 1; continue
        n = data[i + 1]
        m = {0x22: 0x22, 0x5c: 0x5c, 0x6e: 0x0a, 0x74: 0x09, 0x72: 0x0d, 0x2f: 0x2f}
        if n in m:
            out.append(m[n]); i += 2
        elif n == 0x75 and i + 5 < len(data):
            try:
                out.extend(chr(int(data[i+2:i+6].decode(), 16)).encode("utf-8")); i += 6
            except:
                out.append(0x5c); i += 1
        else:
            out.append(0x5c); i += 1
    return bytes(out)

def extract(url: str) -> dict:
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    ctx = ssl.create_default_context()
    ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    print(f"🌐 获取页面: {url}")
    resp = urllib.request.urlopen(urllib.request.Request(url, headers=headers), context=ctx, timeout=30)
    raw = resp.read()
    print(f"📄 页面大小: {len(raw):,} bytes")
    scripts = re.findall(rb'<script(?:[^>]*)>(.*?)</script>', raw, re.DOTALL)
    script = None
    for s in scripts:
        if b'enqueue("' in s and len(s) > 100000:
            script = s; break
    if script is None:
        raise RuntimeError("未找到对话数据")
    start = script.find(b'enqueue("') + 9
    end = script.rfind(b']\\n");')
    jb = script[start:end + 1]
    if jb[0:1] == b'"': jb = jb[1:]
    decoded = unescape_js(jb)
    data = json.loads(decoded)
    print(f"✅ 解析成功: {len(data)} 个元素")
    title = model = ""
    for i, item in enumerate(data):
        if isinstance(item, str):
            if item == "pageTitle" and i+1 < len(data) and isinstance(data[i+1], str):
                title = data[i+1]
            if item == "default_model_slug" and i+1 < len(data) and isinstance(data[i+1], str):
                model = data[i+1]
    texts = [item for item in data 
             if isinstance(item, str) and len(item) > 30 
             and any('\u4e00' <= c <= '\u9fff' for c in item)]
    texts.reverse()
    return {"title": title or "ChatGPT", "model": model or "Unknown",
            "url": url, "texts": texts, "total_chars": sum(len(t) for t in texts),
            "count": len(texts), "data": data}

def to_md(result: dict) -> str:
    lines = [f"# {result['title']}", "", f"**来源:** {result['url']}  |  **模型:** {result['model']}  |  **导出时间:** {datetime.now():%Y-%m-%d %H:%M}", "", "---", ""]
    for t in result["texts"]:
        lines.append(t); lines.append(""); lines.append("---"); lines.append("")
    return "\n".join(lines)

def to_txt(result: dict) -> str:
    sep = "=" * 60
    lines = [f"ChatGPT 对话 — {result['title']}", f"来源: {result['url']}", f"模型: {result['model']}", f"导出: {datetime.now():%Y-%m-%d %H:%M}", "", sep, ""]
    for t in result["texts"]:
        lines.append(t); lines.append(""); lines.append("-" * 40); lines.append("")
    return "\n".join(lines)

def main():
    import argparse as ap
    p = ap.ArgumentParser(description="ChatGPT 分享链接导出工具 (纯 Python · 跨平台)")
    p.add_argument("url", help="ChatGPT 分享链接")
    p.add_argument("--out", "-o", default=".", help="输出目录 (默认: 当前目录)")
    p.add_argument("--format", "-f", choices=["md", "txt"], default="md", help="输出格式")
    p.add_argument("--json", action="store_true", help="同时保存原始 JSON 调试数据")
    args = p.parse_args()
    
    result = extract(args.url)
    os.makedirs(args.out, exist_ok=True)
    
    slug = re.sub(r'[^\w\u4e00-\u9fff]+', '_', result["title"])[:30]
    sid = result["url"].rstrip("/").split("/")[-1][:8]
    base = os.path.join(args.out, f"chatgpt_{slug}_{sid}")
    
    if args.format == "md":
        path = base + ".md"
        with open(path, "w", encoding="utf-8") as f:
            f.write(to_md(result))
    else:
        path = base + ".txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(to_txt(result))
    
    print(f"\n✅ 已保存: {path}")
    print(f"   标题: {result['title']}")
    print(f"   模型: {result['model']}")
    print(f"   内容: ~{result['total_chars']:,} 字 / {result['count']} 段")
    
    if args.json:
        jpath = base + ".json"
        with open(jpath, "w", encoding="utf-8") as f:
            json.dump({"title": result["title"], "model": result["model"],
                       "url": result["url"], "texts": result["texts"]},
                      f, ensure_ascii=False, indent=2)
        print(f"✅ JSON: {jpath}")

if __name__ == "__main__":
    sys.exit(main())