# proxy-rules

两个规则集，供代理客户端按 URL 订阅、分配到不同出口节点。

| 规则集 | 内容 | 该走的节点 |
|---|---|---|
| `crypto-nonus` | 拒绝美国 IP 的加密货币交易所（Binance / OKX / Bybit / HTX / Gate / MEXC / Bitget / KuCoin 等 21 家及其全部马甲域名、API/WS 端点） | **非美节点**（日本） |
| `ai-us` | 需要美国 IP 的 AI 服务（OpenAI / Anthropic / Gemini / Copilot / Perplexity 等） | **美国节点** |

## 订阅地址


```
https://raw.githubusercontent.com/lyq3/proxy-rules/main/dist/crypto-nonus.<ext>
https://raw.githubusercontent.com/lyq3/proxy-rules/main/dist/ai-us.<ext>
```

| 客户端 | `<ext>` | 备注 |
|---|---|---|
| mihomo / Clash.Meta | `mrs` | `behavior: domain`，`format: mrs`（推荐，体积最小） |
| mihomo / Clash.Meta | `yaml` | `behavior: domain`，`format: yaml` |
| sing-box | `srs` | `type: remote`，`format: binary` |
| **Shadowrocket** / Surge / Loon / QX | `list` | `DOMAIN-SUFFIX` 纯文本，见下方专节 |
| sing-box（源文件，调试用） | `json` | 未编译的 rule-set 源 |

### mihomo 配置片段

```yaml
rule-providers:
  crypto-nonus:
    type: http
    behavior: domain
    format: mrs
    url: "https://raw.githubusercontent.com/lyq3/proxy-rules/main/dist/crypto-nonus.mrs"
    path: ./ruleset/crypto-nonus.mrs
    interval: 86400
  ai-us:
    type: http
    behavior: domain
    format: mrs
    url: "https://raw.githubusercontent.com/lyq3/proxy-rules/main/dist/ai-us.mrs"
    path: ./ruleset/ai-us.mrs
    interval: 86400

rules:
  - RULE-SET,crypto-nonus,JP        # 日本出口
  - RULE-SET,ai-us,US               # 美国出口
```

### Shadowrocket 配置片段

Shadowrocket 只吃 `.list`（不支持 `.mrs` / `.srs`）。

**方式一：改配置文件**（配置 → 选中配置 → 右侧 ⓘ → 编辑）

```conf
[Rule]
RULE-SET,https://raw.githubusercontent.com/lyq3/proxy-rules/main/dist/crypto-nonus.list,JP
RULE-SET,https://raw.githubusercontent.com/lyq3/proxy-rules/main/dist/ai-us.list,US
# ... 其余规则
FINAL,PROXY
```

`JP` / `US` 换成你配置里实际的策略组名，必须一字不差。

**方式二：App 内加**（首页 → 底部「配置」以外的「规则」标签 → 右上 + → 类型选 `RULE-SET`）
URL 填上面那两条，策略选对应节点。

两点注意：

- **首次添加时必须能连上 `raw.githubusercontent.com`**，否则规则集是空的。建议先开全局代理再添加。
- Shadowrocket 不会自动更新远程规则集，靠配置里的 `[General]` 段控制：

  ```conf
  [General]
  update-url = <你的配置订阅地址>
  ```

  没有订阅地址的话，就在「配置」页下拉刷新手动更新。规则集本身每天由 CI 重建，拉一次就是最新的。

### sing-box 配置片段

```json
{
  "route": {
    "rule_set": [
      { "type": "remote", "tag": "crypto-nonus", "format": "binary",
        "url": "https://raw.githubusercontent.com/lyq3/proxy-rules/main/dist/crypto-nonus.srs" },
      { "type": "remote", "tag": "ai-us", "format": "binary",
        "url": "https://raw.githubusercontent.com/lyq3/proxy-rules/main/dist/ai-us.srs" }
    ],
    "rules": [
      { "rule_set": "crypto-nonus", "outbound": "JP" },
      { "rule_set": "ai-us",        "outbound": "US" }
    ]
  }
}
```

## 为什么不直接用上游

上游 `MetaCubeX/meta-rules-dat` 的 `category-cryptocurrency` 是「加密货币」分类，不是「拒绝美国 IP」分类：

- 它把 `coinbase.com` / `kraken.com` / `gemini.com` / `binance.us` 这些**美国持牌所**跟 Binance 全球站混在一起。整包甩到日本出口，方向正好反了。
- 它缺 `api.gateio.ws`（Gate 官方 API 端点）和 `gate.com`（2024 年起的新主域）；Phemex / Blofin / WEEX / LBank / CoinEx / Poloniex / Backpack 整家缺失。

`category-ai-!cn` 质量够好，本仓库只在其基础上剔除 Kimi / Moonshot（国内 AI，走美国节点反而慢）。

## 构建

```
seed/crypto-domains.txt   权威域名，无条件写入（重点补上游缺的 API 端点）
seed/crypto-brands.txt    品牌关键词，从上游捞同品牌马甲域名
seed/crypto-exclude.txt   排除名单（binance.us 等美国实体）
seed/ai-extra.txt         AI 增补
seed/ai-exclude.txt       AI 排除（kimi / moonshot）
```

`python3 build.py` 生成 `dist/*.{list,yaml,json}`（纯标准库，无依赖）。
`.mrs` / `.srs` 需要 mihomo / sing-box 二进制编译，由 GitHub Actions 完成。

CI 每天 UTC 20:00（北京 04:00）跑一次，改动 `seed/` 或 `build.py` 后 push 也会触发。

## 维护

交易所是否封美国 IP 会随监管变动（KuCoin 2025 年才退出美国市场）。发现某家变了，改 `seed/` 里对应文件即可，不用碰 `build.py`。
