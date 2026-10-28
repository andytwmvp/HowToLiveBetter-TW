$--
$-- pandoc 的 typst 模板（只認 $body$ 和幾個 -V 變量），不用 pandoc 自帶的 conf()：
$-- 自帶模板把頁面設置鎖在 conf() 裡，改不了頁眉頁腳，所以這裡自己排。
$-- 開頭到 divider 那段是 pandoc 生成的正文要用的輔助定義，照抄自 `pandoc -D typst`，別刪。
$--
#set terms(hanging-indent: 1.5em)

#set table(inset: 6pt, stroke: none)
// pandoc 把表格塞進 align(center) 裡，單元格會跟著居中，中文表格左對齊才好讀
#show table.cell: it => align(left, it)

#let horizontalRule = line(start: (25%, 0%), end: (75%, 0%))
#let divider = if "divider" in std { divider } else { horizontalRule }

#show figure.where(kind: table): set figure.caption(position: top)
#show figure.where(kind: image): set figure.caption(position: bottom)
// 長表格要能跨頁，否則整塊擠不下就留一頁白
#show figure: set block(breakable: true)
#set smartquote(enabled: false)

// ---------- 版面 ----------
#set document(title: "$booktitle$", author: "eternity4719")
#set text(
  // 西文用 typst 自帶的 Libertinus，中文按可用性往後找：CI 上是 Noto，本機是雅黑
  font: ("Libertinus Serif", "Noto Serif CJK TC", "Noto Serif SC", "Source Han Serif SC", "Noto Sans CJK TC", "Microsoft JhengHei", "SimSun"),
  size: 10.5pt, lang: "zh", region: "cn",
)
#set par(justify: false, leading: 0.78em, spacing: 0.9em)
#set list(indent: 0.6em, spacing: 0.75em)
#show raw: set text(font: ("DejaVu Sans Mono", "Noto Sans Mono CJK SC", "Consolas"), size: 9pt)
#show link: set text(fill: rgb("#1a4fb4"))
#show heading: set block(sticky: true, above: 1.5em, below: 0.65em)
#show heading.where(level: 1): set text(19pt)
#show heading.where(level: 2): set text(14pt)
#show heading.where(level: 3): set text(11.5pt)
// 每節另起一頁；weak 保證前一頁正好排滿時不多出一張空頁
#show heading.where(level: 1): it => { pagebreak(weak: true); it }

// 頁眉：左邊書名，右邊當前節名；一節的頭一頁不打頁眉
#let running-head = context {
  let next = query(selector(heading.where(level: 1)).after(here())).at(0, default: none)
  if next != none and next.location().page() == here().page() { return }
  let seen = query(selector(heading.where(level: 1)).before(here()))
  if seen.len() == 0 { return }
  set text(8.5pt, fill: luma(120))
  grid(columns: (1fr, auto), align(left)[$booktitle$], align(right)[#seen.last().body])
  v(-7pt)
  line(length: 100%, stroke: 0.4pt + luma(215))
}

// ---------- 封面 ----------
#set page(paper: "a4", margin: (x: 2.2cm, top: 2.2cm, bottom: 2cm), header: none, footer: none)
#align(center + horizon)[
  #image("/og.png", width: 100%)
  #v(1.2cm)
  #block(width: 80%)[#text(11.5pt, fill: luma(60))[$subtitle$]]
  #v(2cm)
  #text(10pt, fill: luma(90))[
    原作的繁體中文對照預覽，保留原作內容與用語，方便查找、比對來源。 \
    臺灣版閱讀說明：$site$ \
    專案與原作授權說明：$repo$
  ]
]

// ---------- 目錄 ----------
#pagebreak()
#outline(title: [目錄], depth: 1, indent: 1em)

// ---------- 正文 ----------
#pagebreak(weak: true)
#set page(header: running-head, footer: context align(center, text(8.5pt, fill: luma(120))[#counter(page).at(here()).first() / #counter(page).final().first()]))
#counter(page).update(1)

$body$
