# Tables in the preview

Plain markdown. This tab keeps exactly what is typed; the right pane draws each table.

## Emoji in a wrapped header

| h1 | emoji 😀 | very very very very very very very very very very very very very very very very very very very very long header | x |
|:--|--:|:-:|---|
| a | b | c | d |

## CJK in a wrapped header

| 日本語 | h2 | very very very very very very very very very very very very very very very very very very very very long header | x |
|:--|--:|:-:|---|
| a | b | c | d |

## ASCII control

| h1 | emoji xx | very very very very very very very very very very very very very very very very very very very very long header | x |
|:--|--:|:-:|---|
| a | b | c | d |

## A normal table

| Item | Qty | Notes | Status |
|:--|--:|:-:|---|
| Apples 🍎 | 12 | fresh, from the market | ok |
| 日本語のメモ | 3 | wide characters wrap inside a narrow column when the pane is small | check |
| Plain text | 1250 | short | ok |

## Bold and italic in cells

| Style | Example | Notes |
|:--|:-:|--:|
| **bold** | *italic* | ***both*** |
| a **bold phrase that is long enough to wrap onto a second line** here | mixed *it* and **bd** | 日本語 **太字** |
| plain | `code` | **b**old inside a word |

## Long words, accents, Korean, symbols

| Link | Accents | Korean | Symbols |
|:--|:-:|--:|:-:|
| https://example.com/a/really/long/path/that/never/breaks/at/all/anywhere/ok?x=1&y=2 | Ünïcödé é ä ñ | 안녕하세요 세계 | ★ ✓ → ≤ € |
| short | e + combining: é | 한국어 | ☆ ✗ ← ≥ £ |

## Cannot draw faithfully: must fall back to the old text layout

| Flag | Text |
|:--|:-:|
| 🇯🇵 Japan | 👍🏽 ok |
| 👨‍👩‍👧 family | plain |

## Arabic: also falls back

| Arabic | Latin |
|:--|--:|
| مرحبا بالعالم | hello |
