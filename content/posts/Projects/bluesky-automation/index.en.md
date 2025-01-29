---
title: "How to automate Bluesky posts"
date: 2025-01-29T18:50:00+02:00
draft: false
tags: ["Bluesky", "Python", "Automation", "Projects", "Tutorial", "Media", "Coding", "POSSE"]
categories: ["Projects", "Tutorial", "Media", "IndieWeb"]
showToc: true
TocOpen: false
description: "I recently created my Bluesky account and in this post, I’ll show you how I automate my posts to it."
disableShare: true
disableHLJS: false
searchHidden: false
sitemap:
  priority: 0.8
cover:  
  image: cover.jpg  
  alt: "The Bluesky logo in white with a blue background."  
  relative: true  
  hidden: false  
  hiddenInList: false
---

I had Bluesky on my radar for quite a while but never liked the way the platform was built. [^atProtoDisadvantages] But recently, I decided to give it a try. With this post, I want to share my experience automating my posts to Bluesky with you. (You can find [my profile](https://bsky.app/profile/lna-dev.net) here.)

I also wrote [a post](../pixelfed-automation/) in which I explained how to automate posts to [Pixelfed](../../media/fediverse/#pixelfed) (a [Fediverse](../../media/fediverse/) platform), which is quite similar to this one. I might refer to that post from time to time because the process is quite similar.

> This post might be a bit technical if you have no previous experience with coding / tech.

## POSSE

So, first of all, why do all this? For me, the answer is simple: I have been getting into the [IndieWeb](https://indieweb.org/) bubble for a while. As part of it, you want to build your own website, which you control and have full power over. Your website is your little garden where you put all your stuff. But because most people won’t just visit your website directly, you need a way to get your content to them. For this, automation is key.

You host all your content on your page and then build scripts and little bots that take the content from your webpage and **syndicate** it wherever you want. Whether it's the walled gardens of big tech, the [Fediverse](../../media/fediverse/) or Bluesky doesn’t matter. You just post to your website and your bots do the rest. This principle is called *Post On your Own Site Syndicate Elsewhere* or **POSSE** for short.

I might write a detailed post about the IndieWeb and [POSSE](https://www.citationneeded.news/posse/) in the future, so stay tuned!

## My data source - RSS Feed

As I already explained in my [Pixelfed Automation](../pixelfed-automation/#rss-feed) post, I have an RSS feed that contains all the data I need for publishing my images. Specifically, this includes the image URL, description, alt text and hashtags.

Your data source may vary if you have an API or something similar to access the required data. Personally, I like the idea of having an RSS feed because users of my webpage can follow the same feed and use an RSS reader to consume my content.

## The Python script

Now, onto the actual automation. I used Python because I already had my Pixelfed script, which I could reuse a lot from.

There are a couple of code blocks that I didn’t really touch. For example, the parts responsible for retrieving the image from my website, selecting which image to publish and notifying my API about the images that are now online.

Since I’ve covered these steps before, I’ll jump straight to the interesting part: how to publish to Bluesky. (If you want to know the details about the other steps, you can read them [here](../pixelfed-automation/#the-pixelfed-script).)

### Publish to Bluesky

This is where it gets interesting because we’re doing the actual publishing. First of all, there is a good Python library for Bluesky / ATproto called `atproto`. You can install it with the following command:

```sh
pip install atproto
```

After installing the right package, we can look at the code itself. First, we need a client where we pass our email and PAT (I explain how to generate one in the next section). This is enough to authenticate with Bluesky.

Next, we prepare our post. For this, I use the `TextBuilder` provided by the package to format links and hashtags correctly. After preparing our text/caption, we can use the `send_image` or `send_post` method, respectively. And that’s pretty much it! Quite easy when using the library.

```python
from atproto import Client
from atproto import client_utils

BLUESKY_PAT = os.environ.get('BLUESKY_PAT')

bsClient = Client()
bsClient.login(
    login="bluesky@lna-dev.net",
    password=BLUESKY_PAT,
)

# [...]

def publish_entry(entry):
    caption = client_utils.TextBuilder()
    caption.text("More at ")
    caption.link(text="https://lna-dev.net/en/gallery", url="https://lna-dev.net/en/gallery")
    caption.text("\n\n")

    for element in entry.tags:
        caption.tag("#" + element.term, element.term)
        caption.text(" ")

    media_url = entry.media_content[0]["url"]
    alt_text = re.search('alt="(.*?)"', entry.summary)
    alt_text = alt_text.group(1) if alt_text else "Alt not found"

    bsClient.send_image(
        text=caption,
        image=download_image(media_url),
        image_alt=alt_text,
    )

    published_entry(entry.title)
```

### How to get your Bluesky PAT

To generate a *Personal Access Token* (**PAT**), also called an *App password*, go to `Settings => Privacy and Security => App passwords` or click [here](https://bsky.app/settings/privacy-and-security).

Now you can just click `Add App Password` and copy the text. That’s it! You can now add this to your script or environment variables.

### Full code

{{<collapse summary="The full code">}}
Alternatively to this code block, there is an up-to-date [Repo](https://github.com/LNA-DEV/Autouploader) on GitHub.

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
from atproto import Client
from atproto import client_utils

BLUESKY_PAT = os.environ.get('BLUESKY_PAT')
API_KEY = os.environ.get('API_KEY')

bsClient = Client()
bsClient.login(
    login="bluesky@lna-dev.net",
    password=BLUESKY_PAT,
)

# Function to filter entries based on the name list
def filter_entries(entries, name_list):

    # Temp skips (for example if this image does not fit currently)
    # name_list.append("P1002496.JPG")

    return [entry for entry in entries if entry.title not in name_list]

def get_already_uploaded_items():
    try:
        response = requests.get("https://api.lna-dev.net/autouploader/bluesky")
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
    requests.post(f"https://api.lna-dev.net/autouploader/bluesky?item={entry_name}", headers={"Authorization": f"ApiKey {API_KEY}"})

def download_image(image_url):
    response = requests.get(image_url)
    if response.status_code == 200:
        return BytesIO(response.content)
    else:
        print("Failed to download image!")
        sys.exit(1)

def publish_entry(entry):
    caption = client_utils.TextBuilder()
    caption.text("More at ")
    caption.link(text="https://lna-dev.net/en/gallery", url="https://lna-dev.net/en/gallery")
    caption.text("\n\n")

    for element in entry.tags:
        caption.tag("#" + element.term, element.term)
        caption.text(" ")

    media_url = entry.media_content[0]["url"]
    alt_text = re.search('alt="(.*?)"', entry.summary)
    alt_text = alt_text.group(1) if alt_text else "Alt not found"

    bsClient.send_image(
        text=caption,
        image=download_image(media_url),
        image_alt=alt_text,
    )

    published_entry(entry.title)

# Parse the RSS feed
feed_url = 'https://lna-dev.net/en/gallery/index.xml'
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

## Schedule the script

After creating such a script, you need to trigger it somehow. If you are using [Kubernetes](../../../tags/kubernetes/), you may want to check out the [Pixelfed post](../pixelfed-automation/#the-schedule), which explains how to set up a Kubernetes CronJob.

For those who just have a simple server, I recommend setting up a Linux CronJob to trigger the script periodically.

<!-- Footnotes -->

[^atProtoDisadvantages]: I mainly have two big problems with Bluesky. The first is that there is already a good protocol for decentralized social networks. So why reinvent the wheel? And not only did they reinvent it, but they also made it worse. The AT protocol relies much more on centralized services controlled by Bluesky, which is completely different from [ActivityPub](../../../tags/activitypub/). The second issue is that Bluesky is a for-profit company instead of a nonprofit, which is the standard in the [Fediverse](../../media/fediverse/). What’s really alarming is that this company doesn’t yet know how it wants to make money. So, it’s realistic that the platform will get worse in the future to generate revenue.
