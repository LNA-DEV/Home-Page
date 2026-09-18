---
title: Models
description: "Die Menschen vor der Linse."
# HTML only. layouts/_default/rss.xml branches on `eq .Section "gallery"`, so
# every section below /gallery/ otherwise emits the SAME 572-photo feed — 636 KB
# per language, per build, with <link>s pointing at /gallery/models/#<uuid>,
# anchors that do not exist on this page. Nothing here wants a feed.
outputs: [HTML]
params:
  theme: models-home
---
