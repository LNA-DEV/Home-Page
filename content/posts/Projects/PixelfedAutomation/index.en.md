---
title: "How I automated my Pixelfed posts"
date: 2024-05-04T17:52:45+02:00
draft: false
tags: ["first"] # TODO
categories: ["first"] # TODO
showToc: true
TocOpen: false
description: "Desc Text." # TODO
disableShare: true
disableHLJS: false
searchHidden: false
---

## My problem with posting to Pixelfed

I started with Mastodon as my first account in the [Fediverse](). After a while I found out about Pixelfed and created my account there. I kept using it for a while and even posted from time to time. My problem with posting to Pixelfed was the lack of an scheduler. I want to post regularly but I do not want to login every day and make a post manually. This feature was even announced but never finished. Even today this is not implemented. There is also an [GitHub issue](https://github.com/pixelfed/pixelfed/issues/2872) discussing this if your interest goes deeper. In the following post by Pixelfed you can see the announcement.
{{< mastodon url="https://mastodon.social/@pixelfed/107574719894032457/embed" >}}

There are some post scheduler for Mastodon out there. I tried using them with Pixelfed but nothing worked properly. I even tried the client side automatic upload feature of [Fedilab]() which posted immediately instead of at the given time. This surely was a bug I could have reported or fixed it myself. (Because Fedilab is [FOSS]())

I do not want to complain about this. It is totally fine. There are a lot of other things which need to be done in Pixelfed and the [Fediverse]() as a whole. But for me it meant I needed to implement something on my own.

## Requirements

So to solve this I needed something which can somehow talk with my Pixelfed server and make a post there. I also needed a way to know which posts I want to make. This information must include some metadata like the date taken and definitely an alt text and tags to display in Pixelfed. Another thing to keep in mind is that I needed something which "remembers" the state of my postings. Basically a list in which each post gets added if it is uploaded successfully. And finally I needed some sort of mechanism which can schedule the execution of the code.

## The automation

### RSS feed

So first of all I have a [photography page](https://photo.lna-dev.net) which has an RSS feed. I modified the feed of the page to contain an entry per image I have uploaded there. I am also using Hugo there. Therefore I wrote this little Hugo `rss.xml`.

```xml
{{- $authorEmail := site.Params.author.email -}}
{{- $authorName := site.Params.author.name }}

{{- $pctx := . -}}
{{- if .IsHome -}}{{ $pctx = .Site }}{{- end -}}
{{- $pages := slice -}}
{{- if or $.IsHome $.IsSection -}}
{{- $pages = where $pctx.RegularPages "Params.private" "ne" true }}
{{- else -}}
{{- $pages = where $pctx.Pages "Params.private" "ne" true }}
{{- end -}}
{{- $pages = where $pages "Params.rss_ignore" "ne" true -}}
{{- $limit := .Site.Config.Services.RSS.Limit -}}
{{- if ge $limit 1 -}}
{{- $pages = $pages | first $limit -}}
{{- end -}}
{{- printf "<?xml version=\"1.0\" encoding=\"utf-8\" standalone=\"yes\"?>" | safeHTML }}
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{{ if eq  .Title  .Site.Title }}{{ .Site.Title }}{{ else }}{{ with .Title }}{{.}} on {{ end }}{{ .Site.Title }}{{ end }}</title>
    <link>{{ .Permalink }}</link>
    <description>Recent content {{ if ne  .Title  .Site.Title }}{{ with .Title }}in {{.}} {{ end }}{{ end }}on {{ .Site.Title }}</description>
    <generator>Hugo -- gohugo.io</generator>
    <language>{{ site.Language.LanguageCode }}</language>{{ with site.Params.author.email }}
    <managingEditor>{{.}}{{ with $authorName }} ({{ . }}){{ end }}</managingEditor>{{ end }}{{ with $authorEmail }}
    <webMaster>{{ . }}{{ with $authorName }} ({{ . }}){{ end }}</webMaster>{{ end }}{{ with .Site.Copyright }}
    <copyright>{{.}}</copyright>{{end}}{{ if not .Date.IsZero }}
    <lastBuildDate>{{ (index $pages.ByLastmod.Reverse 0).Lastmod.Format "Mon, 02 Jan 2006 15:04:05 -0700" | safeHTML }}</lastBuildDate>{{ end }}
    {{- with .OutputFormats.Get "RSS" -}}
    {{ printf "<atom:link href=%q rel=\"self\" type=%q />" .Permalink .MediaType | safeHTML }}
    {{- end -}}

    {{- range $pages }}
    {{- if not (in .Path "/archive/") -}}
    {{ range .Resources.ByType "image" }}

    <item>
      <title>{{ .Name }}</title>
      <link>{{ .Permalink }}</link>
      <pubDate>{{ .Exif.Date.Format "Mon, 02 Jan 2006 15:04:05 -0700" | safeHTML }}</pubDate>
      {{- with $authorEmail }}<author>{{ . }}{{ with $authorName }} ({{ . }}){{ end }}</author>{{ end }}
      <guid>{{ .Permalink }}</guid>
      <media:content url="{{ .Permalink }}" type="image/jpeg"/>
      <description>
        <img src="{{ .Permalink }}" alt="{{ .Params.Alt }}"/>          
        {{- if ne .Title .Name -}}
        <p> {{ .Title }} </p>
        {{ end }}
      </description>
      {{ range .Params.Tags }}
      <category>{{ . }}</category>        
      {{- end }}
    </item>
    {{- end -}}
    {{- end -}}
    {{ end }}
    
  </channel>
</rss>
```

That done I managed the metadata of all my images in the Hugo config file and wrote an alt text and tags for all my images. (Must admit... an LLM helped me a bit with that. This made the process a lot faster, but the quality is also just okish.)

### My personal API

I even wanted to create an API for this page before this little project. So I created a new API written in **GO**. There I implemented a few endpoints which can save and read a list of filenames from and to MongoDB. I am using MongoDB because of the easy use and their free cloud storage. I will probably change that to something selfhosted in the future but for now it does its job. (I am running a K8s cluster with broken local storage right now. Need to fix this first.)  
Oh and I also made the `POST` endpoint protected by an API key so no one unauthorized can alter my data😉

Now having an API which knows which images have already bin posted I could continue to the script interacting with Pixelfed.

### The Pixelfed script

### The schedule
