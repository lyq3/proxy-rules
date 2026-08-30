#!/usr/bin/env python3
"""从种子清单 + 上游 geosite 生成多格式规则集。只依赖标准库。

crypto-nonus = seed/crypto-domains.txt
             ∪ 上游 category-cryptocurrency 中匹配 seed/crypto-brands.txt 的马甲域名
             - seed/crypto-exclude.txt
ai-us        = 上游 category-ai-!cn ∪ seed/ai-extra.txt - seed/ai-exclude.txt
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
SEED = ROOT / "seed"
DIST = ROOT / "dist"
UPSTREAM = "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite"


def fetch(name):
    url = f"{UPSTREAM}/{name}.list"
    with urllib.request.urlopen(url, timeout=60) as r:
        if r.status != 200:
            raise SystemExit(f"上游 {url} 返回 {r.status}")
        return r.read().decode()


def read_seed(name):
    """读种子文件，返回域名列表。支持 # 整行注释和行尾注释。"""
    out = []
    for line in (SEED / name).read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def parse_upstream(text):
    """上游 .list：'+.x.com' 是后缀匹配，裸 'x.com' 是精确匹配。"""
    suffix, exact = set(), set()
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("+."):
            suffix.add(line[2:])
        elif line.startswith("full:"):
            exact.add(line[5:])
        else:
            exact.add(line)
    return suffix, exact


def brand_match(upstream_suffix, brands):
    """只从上游的 '+.' 条目里捞，且要求域名首段 fullmatch <brand>[a-z0-9]*。

    这两个约束一起把 bybit-exchange.github.io（裸条目 + 带连字符）挡在外面。
    """
    pats = [re.compile(rf"{re.escape(b)}[a-z0-9]*\Z") for b in brands]
    return {h for h in upstream_suffix if any(p.match(h.split(".")[0]) for p in pats)}


def drop_excluded(domains, excludes):
    return {d for d in domains
            if not any(d == e or d.endswith("." + e) for e in excludes)}


def collapse(suffix, exact):
    """删掉被父域后缀规则覆盖的冗余条目。"""
    def covered(d, against):
        parts = d.split(".")
        return any(".".join(parts[i:]) in against for i in range(1, len(parts)))
    suffix = {d for d in suffix if not covered(d, suffix)}
    exact = {d for d in exact if d not in suffix and not covered(d, suffix)}
    return sorted(suffix), sorted(exact)


def write(name, suffix, exact, header):
    DIST.mkdir(exist_ok=True)
    note = "\n".join(f"# {l}" for l in header.splitlines())

    (DIST / f"{name}.list").write_text(
        note + "\n"
        + "".join(f"DOMAIN-SUFFIX,{d}\n" for d in suffix)
        + "".join(f"DOMAIN,{d}\n" for d in exact))

    (DIST / f"{name}.yaml").write_text(
        note + "\npayload:\n"
        + "".join(f"  - '+.{d}'\n" for d in suffix)
        + "".join(f"  - '{d}'\n" for d in exact))

    rule = {}
    if exact or suffix:
        rule["domain"] = sorted(set(exact) | set(suffix))
    if suffix:
        rule["domain_suffix"] = [f".{d}" for d in suffix]
    (DIST / f"{name}.json").write_text(
        json.dumps({"version": 2, "rules": [rule]}, indent=2, ensure_ascii=False) + "\n")

    print(f"{name}: {len(suffix)} suffix + {len(exact)} exact")


def main():
    crypto_up_suffix, _ = parse_upstream(fetch("category-cryptocurrency"))
    ai_up_suffix, ai_up_exact = parse_upstream(fetch("category-ai-!cn"))

    brands = read_seed("crypto-brands.txt")
    matched = brand_match(crypto_up_suffix, brands)
    crypto_ex = read_seed("crypto-exclude.txt")
    crypto_suffix = drop_excluded(set(read_seed("crypto-domains.txt")) | matched, crypto_ex)
    write(*("crypto-nonus",) + collapse(crypto_suffix, set()),
          header="crypto-nonus —— 拒绝美国 IP 的加密货币交易所\n"
                 "由 https://github.com/lyq3/proxy-rules 自动构建，勿手工编辑")

    ai_ex = read_seed("ai-exclude.txt")
    ai_suffix = drop_excluded(ai_up_suffix | set(read_seed("ai-extra.txt")), ai_ex)
    ai_exact = drop_excluded(ai_up_exact, ai_ex)
    write(*("ai-us",) + collapse(ai_suffix, ai_exact),
          header="ai-us —— 需要美国 IP 的 AI 服务（已剔除 Kimi / Moonshot）\n"
                 "由 https://github.com/lyq3/proxy-rules 自动构建，勿手工编辑")

    if not matched:
        sys.exit("品牌关键词一条都没捞到，上游格式可能变了")


if __name__ == "__main__":
    main()
