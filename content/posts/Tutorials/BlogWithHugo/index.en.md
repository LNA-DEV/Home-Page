---
title: "How to create and host a Blog with Hugo for free"
date: 2022-08-19T15:59:48+02:00
draft: false
tags: ["Tutorial", "Hugo", "Blog"]
categories: ["Tutorial"]
showToc: true
TocOpen: false
description: "In this blog post we will discuss how to build and deploy your own blog with Hugo."
disableShare: true
disableHLJS: false
searchHidden: false
sitemap:
  priority: 0.8
---


## Introduction

In this post I will teach you how to set up a blog like this with hugo and GitHub-Pages.

## What you need

- GitHub-Account
- Markdown Knowledge
- Basic understanding of Pipelines (This time GitHub-Actions)
- Basic understanding of Git

## Repository

All the actions below must be executed in a repository connected to GitHub.

## Hugo

### Install Hugo

#### Snap (Linux)

```sh
snap install hugo --channel=extended
```

#### Chocolatey (Windows)

```ps
choco install hugo-extended -confirm
```

#### Homebrew (Mac / Linux)

``` sh
brew install hugo
```

If you need more information or installation options: 
[Hugo - Docs - Installation](https://gohugo.io/getting-started/installing/)

### Create a new project

```sh
hugo new site <name of site> -f yml
```

### Theme

#### Install a theme

In this tutorial we will use the [PaperMod-Theme](https://github.com/adityatelange/hugo-PaperMod) for Hugo.

1. Go to [PaperMod-Theme](https://github.com/adityatelange/hugo-PaperMod) and download the repo
2. Create a folder themes/PaperMod in your hugo project
3. Paste the files in the themes/PaperMod folder in your hugo project

#### Configure the theme

To configure the theme you must change the content of the config.yaml. Change it until it fits your needs. Further 
documentation about specific parameters can be found on the 
[PaperMod-GitHub-Page](https://github.com/adityatelange/hugo-PaperMod).

##### Example YAML

```yaml
baseURL: "https://examplesite.com/"
title: ExampleSite
paginate: 5
theme: PaperMod

enableRobotsTXT: true
buildDrafts: false
buildFuture: false
buildExpired: false

googleAnalytics: UA-123-45

minify:
  disableXML: true
  minifyOutput: true

params:
  env: production # to enable Google Analytics, opengraph, twitter-cards and schema.
  title: ExampleSite
  description: "ExampleSite description"
  keywords: [Blog, Portfolio, PaperMod]
  author: Me
  # author: ["Me", "You"] # multiple authors
  images: ["<link or path of image for opengraph, twitter-cards>"]
  DateFormat: "January 2, 2006"
  defaultTheme: auto # dark, light
  disableThemeToggle: false

  ShowReadingTime: true
  ShowShareButtons: true
  ShowPostNavLinks: true
  ShowBreadCrumbs: true
  ShowCodeCopyButtons: false
  ShowWordCount: true
  ShowRssButtonInSectionTermList: true
  UseHugoToc: true
  disableSpecial1stPost: false
  disableScrollToTop: false
  comments: false
  hidemeta: false
  hideSummary: false
  showtoc: false
  tocopen: false

  assets:
    # disableHLJS: true # to disable highlight.js
    # disableFingerprinting: true
    favicon: "<link / abs url>"
    favicon16x16: "<link / abs url>"
    favicon32x32: "<link / abs url>"
    apple_touch_icon: "<link / abs url>"
    safari_pinned_tab: "<link / abs url>"

  label:
    text: "Home"
    icon: /apple-touch-icon.png
    iconHeight: 35

  # profile-mode
  profileMode:
    enabled: false # needs to be explicitly set
    title: ExampleSite
    subtitle: "This is subtitle"
    imageUrl: "<img location>"
    imageWidth: 120
    imageHeight: 120
    imageTitle: my image
    buttons:
      - name: Posts
        url: posts
      - name: Tags
        url: tags

  # home-info mode
  homeInfoParams:
    Title: "Hi there \U0001F44B"
    Content: Welcome to my blog

  socialIcons:
    - name: twitter
      url: "https://twitter.com/"
    - name: stackoverflow
      url: "https://stackoverflow.com"
    - name: github
      url: "https://github.com/"

  analytics:
    google:
      SiteVerificationTag: "XYZabc"
    bing:
      SiteVerificationTag: "XYZabc"
    yandex:
      SiteVerificationTag: "XYZabc"

  cover:
    hidden: true # hide everywhere but not in structured data
    hiddenInList: true # hide on list pages and home
    hiddenInSingle: true # hide on single page

  editPost:
    URL: "https://github.com/<path_to_repo>/content"
    Text: "Suggest Changes" # edit text
    appendFilePath: true # to append file path to Edit link

  # for search
  # https://fusejs.io/api/options.html
  fuseOpts:
    isCaseSensitive: false
    shouldSort: true
    location: 0
    distance: 1000
    threshold: 0.4
    minMatchCharLength: 0
    keys: ["title", "permalink", "summary", "content"]
menu:
  main:
    - identifier: categories
      name: categories
      url: /categories/
      weight: 10
    - identifier: tags
      name: tags
      url: /tags/
      weight: 20
    - identifier: example
      name: example.org
      url: https://example.org
      weight: 30
# Read: https://github.com/adityatelange/hugo-PaperMod/wiki/FAQs#using-hugos-syntax-highlighter-chroma
pygmentsUseClasses: true
markup:
  highlight:
    noClasses: false
    # anchorLineNos: true
    # codeFences: true
    # guessSyntax: true
    # lineNos: true
    # style: monokai
```

### Using a post template

```path
/archetypes/
```

All files in the directory above can be used as templates for posts. The default.md file is the default file for 
generating new posts. All other files must be specified while creating a post.

### Create a Post

I would always use the hugo commands to generate the files because it copies the standard configuration in the new file. 
I would generate the .md files always in the posts sub-folder (If you want to create a post 😉). Only files from this 
folder will be shown as posts.

```sh
hugo new <filePath>
```

#### Example

```sh
hugo new posts/BlogWithHugo.md
```

### Build the page

The hugo command builds the project into a website. The files created are stored in the /public/ folder.

```sh
hugo
```

### Debug the page

To view the page in the browser run the command below. There will be a link displayed which references the local hosted 
webpage.

```sh
hugo serve
```

## Build and Deployment / Pipeline

### Setup GitHub-Pages

1. Go into the settings of your repo
2. Select the GitHubPages tab
3. Set the source to GitHubActions

<!-- Only works if running -->
![GitHubPages Settings](/BlogWithHugo/GitHubPages.png)

### Add Pipeline YAML

Create following file.

```path
.github/workflows/HugoBuildAndDeploy.yaml
```

Insert the following code into the file and adjust it to your needs. I described what I was doing per comments.  

In this pipeline we will checkout the repo build it and after that deploy it to GitHub-Pages.

```yaml
name: HugoBuildAndDeploy

on:
  workflow_dispatch: # To have the ability to run the workflow manually

  push:
    branches: [main]

env:
  NAME: LNA-DEV-Blog #TODO Change to your project name

jobs:
  HugoBuild:
    runs-on: ubuntu-latest

    steps:
      # Checkout the repository
      - uses: actions/checkout@v3

      # Install Hugo
      - run: sudo snap install hugo

      # Build the hugo repository
      - run: hugo
        working-directory: ./${{ env.NAME }}/

      # Zip the Artifact for GitHubPages deployment
      - name: Archive artifact
        shell: bash
        if: runner.os != 'Windows'
        run: tar -cvf ${{ runner.temp }}/artifact.tar -C ./${{ env.NAME }}/public .

      # Create a build artifact
      - name: Upload a Build Artifact
        uses: actions/upload-artifact@v3.1.0
        with:
          name: github-pages
          path: ${{ runner.temp }}/artifact.tar

  DeployToGithubPages:
    needs: HugoBuild

    # Setup GitHubPages
    permissions:
      pages: write
      id-token: write

    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}

    # Deploy the artifact
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v1
```
