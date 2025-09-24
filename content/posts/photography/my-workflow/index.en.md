---
title: "My photography workflow"
date: 2025-09-24T21:19:00+02:00
draft: false
tags: ["Photography", "Darktable", "Linux", "Photography Workflow", "Open Source"]
categories: ["Photography"]
showToc: true
TocOpen: false
description: "An overview of my photography workflow, including the tools I use and how I manage my photos."
disableShare: true
disableHLJS: false
searchHidden: false
sitemap:
  priority: 0.8
cover:  
  image: camera.jpg
  alt: "A photo of my hand holding a camera with the lens looking into the lens of the camera taking the photo."  
  relative: true  
  hidden: false  
  hiddenInList: false
---

I spent the last couple of weeks going through all my photographs I took in the last two years (and more) and edited my best shots. In this post I want to share what I learned, which tools I use and describe my workflow from taking the photos, over editing them, to publishing them on my webpage and social media. I am in no way an expert photographer, but I think it might be useful to those who are hobby photographers like me, interested in open source photo editing, or just curious.

## The camera itself

When I started photographing with my `Panasonic G91` I mostly used the full automatic mode. That is pretty easy but not very optimal in my opinion. After reviewing a couple of images I took during that time, I saw that a couple of images had settings that did not make very much sense. The aperture priority mode I tried with this camera made a lot of a difference. In this mode, you set the ISO and aperture and the camera automatically determines the appropriate shutter speed. This mode gives you a lot more control over how the image looks because you set the aperture consciously. I also got a pretty good feeling for which light conditions required which settings, because I chose two of the three myself and had a good look at what shutter speed the camera chose.

Sometime this year I got a new `Nikon Z8`, which changed a lot for me. I bought three prime lenses instead of a zoom lens, which I had with the Panasonic. Those prime lenses force me into being a bit more creative when taking the shot. Those lenses are a 20mm, a 50mm and a 100mm macro. The 50mm was quite unspectacular for me because it looks like a normal image. The tele lens felt quite natural to me, which was really nice. But I realized that macro was a lot harder than I thought. Even with image stabilizers it's hard to get your subject into focus and have a nice bokeh without having everything, or mostly everything, blurred out. My wide-angle lens first felt odd, but after using it for a bit, I fell in love with it. I think this is the hardest lens, but I have produced some really cool looking images with it. Overall, I am quite happy with those lenses.

Having no zoom lens is quite another way of photographing. It means you cannot always take the shots you want to because you cannot change your focal length quickly in the field. I often had my other lenses with me, but changing them always takes a bit. But I think maybe that's a good thing from time to time. So you can take the same route several times and force yourself into thinking a bit out of the box and experiment with different focal lengths.

On my recent trip to Sweden, I used filters for the first time. They are a game changer when photographing landscapes with a tripod. Those smooth images when using an ND filter to photograph water are just awesome. I think I created one or two good waterfall photographs. I also tried a CPL filter and the combination of ND + CPL, but do not really know when to use what. I am still trying to figure that out, so I take most of the time a shot with and without CPL.

## Photomanagement

I am a Linux user because it is the only available option which offers a good open source experience with a lot of software. And being open source and privacy-friendly are requirements for me to protect my freedom. Therefore classical image editors like Lightroom are out of the question for me. Firstly, because they are neither open source nor do they work on my Fedora system (or any other Linux system without dirty workarounds). And secondly, because I really do not like Adobe and its very ugly subscription model.

But that's no problem at all because there is a similar and in some cases even better, alternative to Lightroom called Darktable. It is free and open source software (FOSS) and available for all of the big operating systems. It offers the capability to manage big libraries of photos and edit them in a non-destructive way.

I have all my images in a library folder which is synchronized to all my devices using Nextcloud (also FOSS), but other tools like Syncthing could be used. Ensuring all my photos are only in one place and synchronized assures that I do not have duplicates or lose something because it was not backed up correctly.

If I come back from a shoot and want to save my images, I load them into a new folder under the library folder. I give every shoot a name to know what I can expect. Those shoot folders are saved in the following format: `library/<year>/<shootName>`

After saving all my files, which are now already safely backed up, I go through them and pick what is going to be deleted and give the rest of the images a rating to prioritize them while editing. I work with stars for the rating.

| Rating   | What it means                        |
| -------- | ------------------------------------ |
| rejected | To be deleted                        |
| 0 / 1    | Unrated / ToDo                       |
| 2        | Bad photo but wanna keep             |
| 3        | Maybe worth editing                  |
| 4        | Will be edited                       |
| 5        | One of the better shots I have taken |

I then edit first all five-star images and then the four-star ones. I previously did only the sorting of the images right after the shoot, but this had the disadvantage that I needed to do a **lot** of work in the last few weeks to edit all of the photos I wanted to. For the future, my plan is to edit them right away after the shoot to have only small bits of work and not so much at once. A nice bonus is that if you edit images not long after the shoot, you still have in mind the intention you had while shooting.

Besides the stars, I also use colors to manage my photos. I, for example, use red for the images I have already published/exported and purple for private images I do not want to export for now — if, for example, a person I know is on them, but they do not want to be online.

## Editing

After editing all my photos, I seem to have built a habit about which modules I use most on my images. And what I am most happy about is that I can see that my edited photographs look much better now than in the beginning, where I struggled to be better than the JPG produced by the camera. I am sure I can learn **a lot more** in this area, but think that needs time and maybe some guidance. But for now, I want to share with you how I am editing my images.

### Base *style*

I have a style in Darktable which I apply to every image I start editing and go from there. In this style I activate color balance RGB and increase the global brilliance and global saturation. I activate denoise (profiled) and local contrast at the default settings and set the color calibration to "as shot in camera."

### Manual edits

I then edit the photo manually to fit my liking. I first try haze removal and take a look if it is improving the image. Most of the time I then increase the local contrast a bit and sometimes add a bit of contrast over the filmic RGB module. But that's not that often happening. After that, I check if the shadows and highlights module helps the image and play around with the settings of it a bit. In color balance RGB I try to set everything so the image feels right. Most of the time only brilliance and saturation, but sometimes also chroma. I use crop and rotate the image to make it as pleasing to my eye as possible. If there are any smudges on the camera lens, I remove them with retouch. Sometimes I also use sharpen, but I do it less and less.

## Exporting

I publish all my images to my website and syndicate them from there to all social media platforms. I have changed quite a bit in the process since my last automation posts, but that is a topic for another time. For now what is important is that I publish for the web. Therefore, I do a few things before publishing, like setting some notes on the image which describe what can be seen. That information is later used to set an alt tag which is used for people with screen readers, like for example some blind people use. Besides that, I also add tags which are used later as hashtags for social media. I seldom set a description, which in my case gets displayed as a text next to the image. But in some cases, I want the viewer to have some information and then I can provide it with that. I also set publisher and rights so that all the important metadata is set.

---

I hope you could learn something from my reflections about my photography journey or at least have found it interesting to read. I will continue to learn both getting better photographing skills and editing skills and maybe write about it in the future. I hope I can see some progress then 😄
