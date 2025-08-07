---
title: "My photography workflow"
date: 2025-08-06T20:10:00+02:00
draft: false
tags: ["Photography", "Darktable", "Linux", "Photography Workflow", "Open Source"]
categories: ["Photography"]
showToc: true
TocOpen: false
description: "A overview of my photography workflow, including the tools I use and how I manage my photos."
disableShare: true
disableHLJS: false
searchHidden: false
sitemap:
  priority: 0.8
# cover:  
#   image: tor-project-logo.png
#   alt: "The Tor logo with a purple background and some circles on it."  
#   relative: true  
#   hidden: false  
#   hiddenInList: false
---

I spent the last couple of weeks going threw all my photographs I took in the last two years (and more) and edited my best shots. In this post I want to share what I learned which tools I use and describe my workflow from taking the photos over editing them to publishing them on my webpage and social media. I am no way an expert photographer but I think it might be useful to those who are hobby photographers like me, interested in open source photo editing or just curious.

## In the camera

When I started photographing with my `Panasonic G91` I mostly used the full automatic mode. That is pretty easy but not very optimal in my opinion. After reviewing a couple of images I did during that time I saw that a couple of images had settings that did not make very much sense. The aperture priority mode I tried with this camera made a lot of a difference. In this mode you set the ISO and aperture and the camera automatically determines the appropriate shutter speed. This mode gives you a lot more control over how the image looks like because you set the aperture consciously. I also got a pretty good feeling for in which light conditions which settings where appropriate because I chose two of the tree myself and had a good look at what shutter speed the camera chose.

Sometime this year I got a new `Nikon Z8` which changed a lot for me. I bought three prime lenses instead of a zoom lens which I had with the Panasonic. Those prime lenses force me into being a bit more creative when taking the shot. Those lenses are a 20mm, a 50mm and a 100mm macro. The 50mm was quite unsectucular for me beacause it looks like a normal image. The tele lens felt quite natural to me which was really nice. But I realised that macro was a lot harder than I thought. Even with image stabilisors its hard to get your subject into focus and have a nice bukeh without having everything or mostly everything blurred out. My wide angle lens first felt odd but after using it for a bit I fell in love with it. I think this is the hardest lens but I have produced some cool really cool looking images with it. Overall I am quite happy with those lenses.

Having no zoom lens is quite a other way of photographing. It means you cannot always take the shots you want to because you cannot change your focal lens quickly in the field. I often had my other lenses with me but changing them always takes a bit. But I think maybe thats a good thing from time to time. So you can take the same route several times and force yourself into thinking a bit out of the box and experiment with different focal lengths.

On my recent trip to Sweden I used filters for the first time. They are a game changer when photographing landscape with a tripod. Those smooth images when using a ND filter to photograph water is just awesome. I think I created the one or other good waterfall photograph. I also tried a CPL filter and the combination of ND + CPL but do not really now when to use what. I am still trying to figure that out so I take most of the time a shot with and without CPL.

## Photomanagement

I am a Linux user because it is the only available option which offers a good open source experience with a lot of software. And being open source and privacy friendly are requirements for me the protect my freedom. Therefore classical image editors like Lightroom are out of question for me. Firstly because they are neither open source nor do they work on my Fedora system (or any other Linux system without dirty workarounds). And secondly because I really do not like Adobe and its very ugly subscription model.

But thats no problem at all because there is a similar and in some cases even better alternative to Lightroom called Darktable. It is free and open source software (FOSS) and available for all of the big operating systems. It offers the capability to manage big libraries of photos and edit them in a non distructing way.

I have all my images in a library folder which is synchronised to all my devices using Nextcloud (also FOSS) but other tools like Syncthing could be used. Ensuring all my photos are only in one place and synchronised assures that I do not have duplicates or loose something because it was not backed up correctly.

If I come back from a shoot and want to save my images I load them into a new folder under the library folder. I give every shoot a name too now what I can expect. Those shoot folders are saved in the following format: `library/<year>/<shootName>`

After saving all my files which are now already savely backed up I go threw them and pick what is going to be deleted and give the rest of the images a rating to prioritize them while editing. I work with stars for the rating.

| Rating   | What it means                        |
| -------- | ------------------------------------ |
| rejected | To be deleted                        |
| 0 / 1    | Unrated / ToDo                       |
| 2        | Bad photo but wanna keep             |
| 3        | Maybe worth editing                  |
| 4        | Will be edited                       |
| 5        | One of the better shots I have taken |

## Editing

## Exporting

<!-- Looking forward to learn more see how improve in the future... -->
