---
title: "Tools"
date: 2023-10-01T22:48:51+02:00
draft: false
showToc: true
TocOpen: false
description: "Here I describe which tools I am using."
disableShare: true
disableHLJS: false
searchHidden: false
hidemeta: true
---

## System

### Operating System

I am using Linux systems. In the past i tried Ubuntu and Manjaro. Currently I am using Fedora and Gnome as the desktop and are very happy with it.

### Browser

Currently I am using mainly Libre Wolf and Brave. But I am switching more and more to the Libre Wolf side. This has a simple reason: I do not want to support anything related to Chrome. Google is trying to break to free and open web with things like web integrity and I want as much distance to that as possible. Apart from that are wolves really cool^^

### User-Cloud

For this one I do not know if the heading is fitting perfectly. I mean something like OneDrive or iCloud which manage at least all your data but in most cases a lot more. In this area I am using Nextcloud. I have a managed one hosted by Hetzner. This works great but for my personal data this is not ideal because of the lack of **good** end to end encryption in Nextcloud. So my goal is to setup an home server and host the Nextcloud there myself. But that is a project for the future. For now it is ok.

### File Encryption

If I want to encrypt my files in addition to local disk encryption or the server side encryption of the Nextcloud I am using Cryptomator. With this tool i can easily create high security safes wich are end to end encrypted. A also nice thing is that I can use it perfectly on the phone. It also integrates very well with the Nextcloud.

### Mail

As my mail service I am using Tutanota. They have encryption and seem like a very nice company to me.

### VPN

My VPN is Mullvad and I really like them. They are awesome. They are located in Sweden which is very good for an VPN provider. This is because the law there does not allow the police to confiscate something that is not there. In this case this is data about the user of the VPN. Mullvad does not collect personal data of their users. You do not even use an E-Mail address to identify your account. Instead you get a unique identifier digit. It also would be possible to pay for the VPN in cash. Of course they have a zero log policy. In addition to that they now have no disks in their VPN servers so even by accident no logs can be created.

## Hardware Security Key

I am using a hardware security key by Yubico: The Yubikey. It supports a lot of 2FA protocols.

## Mobile Phone

I actively decided to use an Open Source operating system on my phone. In my opinion I can not trust a proprietary project. And for a operating systems I need a lot of trust. So there is no other option for me than using custom Android ROMs. Linux phones would be nice but I do not think they are ready yet. Custom Android ROMs are really good nowadays and can be used nearly as easily as stock Android. Currently I am using an Pixel 7 Pro with Graphene OS installed. Previously I used LineageOS on an One Plus 9 Pro. It now feels like haven. Graphene is **so much better** than Lineage. It is even more secure and has hardening against zero days. The installation was pretty straight forward and could be done by anyone who can read and press a view buttons.

## Cloud / Hosting

I am using the Hetzner cloud provider to host all of my stuff. Hetzner offers IaaS (Infrastructure as a Service). Everything is deployed in a Kubernetes-Cluster which was set up by the Kube-Hetzner Terraform provider. All of my deployments are open source. They can be found here.
