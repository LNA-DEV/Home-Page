---
title: "Tor Hidden Service Docker"
date: 2024-12-08T12:31:02+01:00
draft: false
# aliases: ["/first"]
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

In this blogpost I want to share my experiences of publishing my website to the ***"darknet"***. In detail I want to host my existing clearweb page on tor. Because I am already using a webserver I only want to host the hidden service and relay my normal webserver. I will do this locally in a Kubernetes cluster so you could also do it the same way if you want to **only** host over Tor and not in the clearweb.

First of all we need to generate a `.onion` domain name and private key. For this we can run the following command locally. Replace `<pattern>` with a regex pattern which should be included in your domain name.

```sh
docker run -it --rm --entrypoint shallot strm/tor-hiddenservice-nginx <pattern>
```

The output should be something like this:

```txt
------------------------------------------------------------------
Found matching domain after 85422487 tries: lnadevs3nbjoh6n2.onion
------------------------------------------------------------------
-----BEGIN RSA PRIVATE KEY-----
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
-----END RSA PRIVATE KEY-----
```


```
FROM debian:bullseye

RUN apt-get update && apt-get install -y tor && rm -rf /var/lib/apt/lists/*

CMD ["tor"]
```

kubectl create secret generic tor-service-secret --from-file=private-key=private-key-file -n {{ .Values.namespace }}









<!-- New -->



# Tor website

## Get the domain

https://github.com/cathugger/mkp224o


docker run --rm -it -v $PWD:/keys ghcr.io/cathugger/mkp224o:master -d /keys as


throw files into tor-data