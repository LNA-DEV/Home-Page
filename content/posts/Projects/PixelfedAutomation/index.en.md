---
title: "How I automated my Pixelfed posts"
date: 2024-05-05T17:52:45+02:00
draft: false
tags: ["Pixelfed", "Fediverse", "Mastodon", "Python", "Kubernetes", "go", "Automation"]
categories: ["first"] # TODO
showToc: true
TocOpen: false
description: "I needed to automate my posts to Pixelfed. In this post I discuss how I achieved that."
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

For writing the script I went with Python. I am having mixed feelings about Python. On the one side I really dislike the way it is handling types (it doesn't lol) but on the other hand you can quickly make basic things work. So I went the (for me) experimenthus way and chose Python as my way to go.

I created this basic script which is handling all the stuff needed to create the post and make all the API and RSS handling. I go into detail on some of the methods and bits of code I find most important but I have the full code provided below if you are interested.

{{<collapse summary="The full code" >}}
Alternatively to this code block there is a up to date [Repo](https://github.com/LNA-DEV/Autouploader) on GitHub.

```python
from io import BytesIO
import os
import re
import sys
import feedparser
from datetime import datetime
import time
import random
import requests

PIXELFED_INSTANCE_URL = 'https://pixelfed.de'
PAT = os.environ.get('PIXELFED_PAT')
API_KEY = os.environ.get('API_KEY')

# Function to filter entries based on the name list
def filter_entries(entries, name_list):

    # Temp skips (for example if this image does not fit currently)
    name_list.append("P1002496.JPG")

    return [entry for entry in entries if entry.title not in name_list]

def get_already_uploaded_items():
    try:
        response = requests.get("https://api.lna-dev.net/autouploader/pixelfed")
        if response.status_code == 200:
            string_list = response.json()
            return string_list
        else:
            print(f"Failed to fetch data from API. Status code: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

def published_entry(entry_name):
    requests.post(f"https://api.lna-dev.net/autouploader/pixelfed?item={entry_name}", headers={"Authorization": f"ApiKey {API_KEY}"})

def download_image(image_url):
    response = requests.get(image_url)
    if response.status_code == 200:
        return BytesIO(response.content)
    else:
        print("Failed to download image!")
        sys.exit(1)

def publish_entry(entry):
    caption = "More at https://photo.lna-dev.net\n\n"

    for element in entry.tags:
        caption += '#' + element.term + " "

    mediaResponse = upload_media(entry)
    publish_post(caption, mediaResponse)

    published_entry(entry.title)

def upload_media(entry):
    media_url = f'{PIXELFED_INSTANCE_URL}/api/v1/media'
    headers = {
        'Authorization': f'Bearer {PAT}',
        'Accept': 'application/json'
    }
    files = {
        'file': download_image(entry.link)
    }
    data = {
        'description': re.search('alt="(.*?)"', entry.summary).group(1)
    }
    response = requests.post(media_url, headers=headers, files=files, data=data)
    if response.status_code == 200:
        return response.json()['id']
    else:
        print("Failed to upload media.")
        sys.exit(1)

def publish_post(caption, media_id):
    if caption.strip():
        post_url = f'{PIXELFED_INSTANCE_URL}/api/v1/statuses'
        headers = {
            'Authorization': f'Bearer {PAT}',
            'Accept': 'application/json'
        }
        data = {
            'status': caption,
            'media_ids[]': media_id
        }
        response = requests.post(post_url, headers=headers, data=data)
        if response.status_code == 200:
            print("Post published successfully!")
        else:
            print("Failed to publish post!")
            sys.exit(1)
    else:
        print("Caption cannot be empty.")
        sys.exit(1)

# Parse the RSS feed
feed_url = 'https://photo.lna-dev.net/index.xml'
feed = feedparser.parse(feed_url)

# Filter out entries with specific names
specific_names = get_already_uploaded_items()
filtered_entries = filter_entries(feed.entries, specific_names)

if not filtered_entries:
    print("No entries available after filtering.")
else:
    # Calculate time differences considering only month, day, hour, minute, and second
    current_time = datetime.now()
    closest_entry = None
    skipped_entries = []
    min_difference = None
    for entry in filtered_entries:
        if entry.published_parsed.tm_year == 0 or entry.published_parsed.tm_year == 1:
            skipped_entries.append(entry)
            continue  # Skip entries with invalid year
        temp = time.mktime(entry.published_parsed)
        published_time = datetime.fromtimestamp(temp)
        difference = abs(current_time.replace(year=published_time.year, tzinfo=None) - published_time)
        if min_difference is None or difference < min_difference:
            min_difference = difference
            closest_entry = entry

    if closest_entry is None:
        print("No valid entries available after filtering.")
    else:
        # Get all entries published at the same time as the closest entry
        closest_entries = [entry for entry in filtered_entries if entry.published == closest_entry.published]
        for element in skipped_entries:
            closest_entries.append(element)

        # Select a random entry from the closest entries
        random_entry = random.choice(closest_entries)

        # Print the selected entry
        print("Random entry closest to the current date/time (ignoring year):")
        print("Title:", random_entry.title)
        print("URL:", random_entry.link)
        print("Published Date:", random_entry.published)

        publish_entry(random_entry)
```
{{</collapse>}}

So lets start with the retrieval of the RSS data. To simplify this for me I used the `feedparser` library here. With that I have access to all the data of the RSS feed in a better structured way.

With this simple API call I retrieve the already uploaded posts from my personal API I mentioned above. With this data I can filter any entries in the RSS feed which I don't need to upload anymore.

```python
def get_already_uploaded_items():
    try:
        response = requests.get("https://api.lna-dev.net/autouploader/pixelfed")
        if response.status_code == 200:
            string_list = response.json()
            return string_list
        else:
            print(f"Failed to fetch data from API. Status code: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
```

After having a list of possible posts I need the script to decide which post to post next. For that I am calculating which posts are nearest to the current day and month without taking the year into the calculation.

```python
    for entry in filtered_entries:
        if entry.published_parsed.tm_year == 0 or entry.published_parsed.tm_year == 1:
            skipped_entries.append(entry)
            continue  # Skip entries with invalid year
        temp = time.mktime(entry.published_parsed)
        published_time = datetime.fromtimestamp(temp)
        difference = abs(current_time.replace(year=published_time.year, tzinfo=None) - published_time)
        if min_difference is None or difference < min_difference:
            min_difference = difference
            closest_entry = entry
```

I than select one of the closest entries randomly. I need to do this because if I would have taken many photos on one day there could be multiple items close to the current date.

Now we are ready for creating the post. Therefore I am now preparing the caption which is included in the post.

```python
def publish_entry(entry):
    caption = "More at https://photo.lna-dev.net\n\n"

    for element in entry.tags:
        caption += '#' + element.term + " "

    mediaResponse = upload_media(entry)
    publish_post(caption, mediaResponse)

    published_entry(entry.title)
```

Now to the trickiest bit: The actual posting. This was especially interesting because at the time I created this script there was a lack of documentation and I needed to somehow figure this out on my own. I also didn't find many examples searching the internet. The best I could do was looking into the Mastodon documentation (because Pixelfeds API is similar) and figuring it out on my own.

There are two important things here. First you have to upload the media first before you can make the post which than simply contains the id of the media you uploaded beforehand. And second you need to create a PAT (personal access token) and provide it via the bearer syntax to the API.

```python
def upload_media(entry):
    media_url = f'{PIXELFED_INSTANCE_URL}/api/v1/media'
    headers = {
        'Authorization': f'Bearer {PAT}',
        'Accept': 'application/json'
    }
    files = {
        'file': download_image(entry.link)
    }
    data = {
        'description': re.search('alt="(.*?)"', entry.summary).group(1)
    }
    response = requests.post(media_url, headers=headers, files=files, data=data)
    if response.status_code == 200:
        return response.json()['id']
    else:
        print("Failed to upload media.")
        sys.exit(1)

def publish_post(caption, media_id):
    if caption.strip():
        post_url = f'{PIXELFED_INSTANCE_URL}/api/v1/statuses'
        headers = {
            'Authorization': f'Bearer {PAT}',
            'Accept': 'application/json'
        }
        data = {
            'status': caption,
            'media_ids[]': media_id
        }
        response = requests.post(post_url, headers=headers, data=data)
        if response.status_code == 200:
            print("Post published successfully!")
        else:
            print("Failed to publish post!")
            sys.exit(1)
    else:
        print("Caption cannot be empty.")
        sys.exit(1)
```

That done I made a final API request to my personal API noting that I uploaded the image.

### The schedule

This part was fairly easy because I was already using a [Kubernetes]() cluster. I just needed to create a cronjob running each day and that's it.

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: pixelfed-autoupload
spec:
  schedule: "0 16 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: pixelfed-autoupload
              image: lnadev/pixelfed-autoupload:{{ .Values.autoupload.pixelfed.version }}
              imagePullPolicy: Always
              resources:
                limits:
                  memory: "128Mi" 
                  cpu: "500m" # Don't use CPU limits in K8s but that is another topic...
              env:
                - name: PIXELFED_PAT
                  valueFrom:
                    secretKeyRef:
                      name: pixelfed
                      key: pat
                - name: API_KEY
                  valueFrom:
                    secretKeyRef:
                      name: personal-api-secret
                      key: apikey
          restartPolicy: Never
      backoffLimit: 0
```
