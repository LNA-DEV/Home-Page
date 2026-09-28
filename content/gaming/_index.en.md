---
title: "Gaming"
draft: false
description: "The games I have played, with playtime and achievements."
disableShare: true
searchHidden: false
hideNewsletter: true
hidemeta: true
# HTML only. A section emits an RSS feed of its pages by default, and these are
# one generated, undated page per game — nothing here wants a feed.
outputs: [HTML]
sitemap:
  priority: 0.3
params:
  # layouts/_default/list.html renders this page's body (the grid) and nothing
  # else. The game pages below it come from the content adapters next to this
  # file (_content.*.gotmpl → layouts/partials/game-pages.html); without the
  # theme, PaperMod's list would append all of them as post entries.
  theme: gaming-home
---

{{< gamingList >}}
