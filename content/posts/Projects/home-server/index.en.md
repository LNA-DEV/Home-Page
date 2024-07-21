---
title: "How I build my home server"
date: 2024-07-21T19:04:10+02:00
draft: false
tags: ["first"]
categories: ["first"]
showToc: true
TocOpen: false
description: "Desc Text."
disableShare: true
disableHLJS: false
searchHidden: false
sitemap:
  priority: 0.8
---

There are many reasons someone would want to have a home server. In this post I want to explain my reasons and how I build / setup everything.

## Why I need a home server

For me there are few main reasons why I wanted to get started with selfhosting. I think my journey began about two years ago in 2022 when I first was playing around with a Synology NAS. This helped me a bit with some of the goals I have. Having a Synology NAS improved my independency especially from big tech and other nightmares and therefore also improved my privacy. But after a while I had a feeling that something wasn't quite right with this setup. First the Synology software is not **Open Source** and therefore there are still **privacy** concerns. Also Synology is a taiwanese company and the situation with China was warring me therefore. (There would be a lot of bigger problems in tech but it was still warring me.)

So the next step was building my own NAS / home server with custom **Open Source** software. I explain this more in depth later in the post. For now just say I build my own server about a year ago in 2023 and now have all my data at home in a environment I trust and am able to control fully. So I achieved a lot of independence of the shady big tech companies.

Cost can be advantage or disadvantage if you start to selfhost. On the one side you have to pay for your hardware and electricity your server consumes but on the other side you can cancel a couple of subcriptions which are also pretty expensive. For example are you probably using some sort of cloud storage. (Or at least you should be using something like that in my opinion.) Having a bit of data in such a storage can have high costs. For example buying OneDrive which is included in the MS Personal subscription costs about 6$ a month. Other cloud storages like a hosted Nextcloud might even be more expensive.

![Screenshot of the OneDrive price](onedrive-costs.png)

But I must admit in my case the cost of selfhosting is not an advantage. But if you are living in country with cheaper elecricity this might differ.

(Just to mention it: OneDrive and a lot of other big tech tools scan your files for illegal content and use filters that might report you to law enforcement. This tools are known to make mistakes and so a image of your child on the beach can lead to your Microsoft account being suspended in the best case and a meeting with the local police in the worst case. Something like that will never happen if you are selfhosting. Be aware!)

Another good point for having a home lab is all the knowledge you get from it. You have to think about the hardware set everything up physically, you need to learn about RAID, about the operating systems and the software you are running, not to mention security and setting up a safe environment. There is a lot to learn on this journey!

Last but not least I want to mention a small point I think is notable. If you are building all of this for you it is really easy to give a few other people access to the services you are running. So you can help out your friends and family to have a better privacy and generally speaking all of the benefits I was talking about.

## Hardware

![Picture of my home server from the inside.](server.jpg)

(Looks a bit messy I know 😅 But I somehow like it 😜)

As you can see am I using a old PC as my server. This has the advantage that I only needed to buy the hard drives to support my storage needs but also the downside is that electricity consumption is rather high. Last time I measured with all my apps running it consumed about 60W. A fresh build could be optimized for electricity consumption which can save you a lot of money if you want the server to run 24/7.

I chose to not do a hardware RAID because I am using the ZFS file system. I will explain this in detail in the software part.

### ECC memory?

I sadly do not have ECC RAM but if you can get one I would recommend it. Error correction code RAM is able to correct wrong bits which makes the system more secure against some hardware attacks and especially more reliable. It is no complete dealbreaker not having it (especially because its kind of rare in the consumer world in the moment) but having it is a nice addon.

### Uninterrupted power supply (UPS)

I bought a UPS to support my server in case of electricity outages. The UPS has a battery which can keep my server at life for about 15 minutes than it gives a signal to the server which is configured to shut down before the battery of the UPS runs out. This makes sure that first of all most of the electricity outages never make a problem at all because they are shorter than the battery time and secondly that if the power is gone for a while the server shuts itself down gracefully.

### Full specs

CPU: TODO  
RAM: 32 GB TODO  
HDD: TODO  
SSD: TODO  
GPU: NVIDIA GTX 970  

## Why I chose TrueNAS Scale

Now to the in my opinion most important part the operating system. I chose TrueNAS Scale for a couple of reasons. First of all I wanted to have something that is Open Source. I also need to run apps on the system and definetly need some sort of RAID / software RAID. TrueNAS Scale has it all. It is based on Linux and lead by the company iXsystems. For applications it supports Docker and Kubernetes as well as own VMs. I am actually not really using the VMs yet but I really like Kubernetes and also Docker. So this was great news for me. These technologies allow you basically to run every app you like on it because most of the apps are or can be containerized. In addition to this the system uses OpenZFS as file system which is pretty cool in my opinion. We will take a look at it in the next part.

### RAID and ZFS

### Setup of the software

### How I move files  

## What apps do I run

### TrueCharts and why I do not use them anymore

### NPM Reverse proxy and setup

### Nextcloud

### Home Assistant

### Jellyfin

### What else could you run