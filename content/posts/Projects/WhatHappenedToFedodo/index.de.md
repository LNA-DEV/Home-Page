---
title: "Warum habe ich aufgehört an Fedodo zu arbeiten?"
date: 2023-11-23T20:23:22+01:00
draft: true
tags: ["Projekte", "Fedodo", "ActivityPub", "Social Media", "Coding", "Open Source", "Überarbeiten"]
categories: ["Projekte"]
showToc: true
TocOpen: false
description: "Ich habe für ein halbes Jahr einer Social-Media-Plattform namens Fedodo entwickelt. Nach dieser doch recht langen Zeit habe ich die Entwicklung pausiert / gestoppt. Aber warum?"
disableShare: true
disableHLJS: false
searchHidden: false
---

## Was ist Fedodo?

Zunächst einmal, um sicherzustellen, dass jeder auf dem gleichen Stand ist, muss ich erklären was Fedodo ist und warum ich angefangen habe es zu entwickeln.

Mit dem Aufstieg von [Mastodon](https://joinmastodon.org/) wuchs mein Interesse am [ActivityPub](https://www.w3.org/TR/activitypub/) Protokoll immer mehr. Mir gefällt die Idee, eine große dezentrale Plattform zu haben, welche mit den "walled gardens" der großen Tech-Unternehmen konkurrieren kann. Das [ActivityPub](https://www.w3.org/TR/activitypub/) Protokoll schien genau das Richtige hierfür zu sein.

Bislang wurden Plattformen für einen bestimmten Anwendungsfall entwickelt:

- [Mastodon](https://joinmastodon.org/) als Alternative zu Twitter.
- [Pixelfed](https://pixelfed.org/) als Alternative zu Instagram.
- [Lemmy](https://join-lemmy.org/) als Alternative zu Reddit.
- Und die Liste geht weiter...

Das wollte ich anders machen. Ich denke, dass es nicht optimal ist, für jede dieser Plattformen einen eigenen ActivityPub-Server zu entwickeln. Also war meine Idee, einen ActivityPub-Server zu erstellen, der nicht nur das [ActivityPub-Server-zu-Server](https://www.w3.org/TR/activitypub/#server-to-server-interactions)-Protokoll implementiert, sondern auch das [ActivityPub-Client-zu-Server](https://www.w3.org/TR/activitypub/#client-to-server-interactions)-Protokoll. Dieses Client-zu-Server-Protokoll war zu dieser Zeit nicht besonders weit verbreitet. Aber es würde es jedem ermöglichen, ein Frontend seiner Wahl mit dem gleichen Server zu verwenden. Außerdem benötigt nun jeder Benutzer nur noch einen Account, da Fedodo eine Funktion bietet, die es ermöglicht mehrere ActivityPub-Actors pro Benutzerkonto zu benutzen.

Als Teil von Fedodo wollte ich nicht nur den Server entwickeln, sondern auch eine Reihe an Frontends. Im Detail habe ich ein [Mastodon](https://joinmastodon.org/) ähnliches Frontend entwickelt und war auf einem guten Weg eine [Pixelfed](https://pixelfed.org/) ähnliche Benutzeroberfläche fertigzustellen.

## Die Entwicklung

Ich habe im Dezember 2022 mit der Entwicklung von Fedodo begonnen und bis August 2023 intensiv daran gearbeitet. Insgesamt habe ich also etwa acht Monate in das Projekt investiert.

Während dieser Zeit habe ich erfolgreich einen ActivityPub Server entwickelt. Obwohl es vielleicht notwendig wäre, ihm etwas mehr Aufmerksamkeit zu schenken, hier und da einige Tests zu schreiben und ein paar Dinge zu beheben, funktioniert er insgesamt trotzdem gut. Zusätzlich dazu hatte ich eine grundlegende [Mastodon](https://joinmastodon.org/) ähnliche App nahezu fertig und habe erhebliche Fortschritte bei der Entwicklung der [Pixelfed](https://pixelfed.org/) Alternative gemacht.

Für mich ist dies ein bedeutender Erfolg, auf welchen ich auch ein bisschen stolz bin. Ich hatte sogar die Gelegenheit, an einem Podcast teilzunehmen, der von einem großen deutschen Tech-YouTuber gehostet wird und über ActivityPub zu sprechen. Das ist für mich eine Ehre. ([Zur Episode](https://www.youtube.com/watch?v=yP4yN1vyn5s))

## Was ist das Problem?

Während der Entwicklungsphase habe ich ungefähr 380 Stunden ausschließlich dem coden gewidmet. Hinzu kommt die Zeit, die ich über das Projekt nachgedacht habe und keinen Editor geöffnet hatte (und auch ich nicht getrackt habe). Das macht etwa anderthalb Stunden pro Tag nur für das Coden. **Jeden Tag** in diesen acht Monaten. Nur mit dem deutschen Mindestlohn bezahlt, würde das 4715€ ergeben. Es sind also eine erhebliche Menge an Zeit und Mühe in das Fedodo-Projekt geflossen.

Das Problem ist, dass ich dies zusätzlich zu einer 40-Stunden-Arbeitswoche gemacht habe. Also waren meine gesamten Arbeitsstunden pro Woche bei etwa 50 Stunden.

Ich genieße es in meiner Freizeit zu coden. Für mich ist es ein spaßiges Hobby. Das Problem bei großen Projekten wie Fedodo ist, dass du irgendwann nicht mehr so begeistert davon bist wie zu Beginn. Und nach einiger Zeit wird sogar ein Hobbyprojekt zu Arbeit. Und das, denke ich, ist das eigentliche Problem.

Wenn ich an kleinen Projekten arbeite, für die ich begeistert bin, fühlt es sich nicht wie Arbeit an. Aber bei Fedodo war das nach vier bis fünf Monaten anders. Und dann wirkt sich der Effekt von 50 Stunden pro Woche aus.

Ich würde niemandem empfehlen, an einem Projekt dieser Größe zu arbeiten. Ich denke, alles was du in weniger als einem halben Jahr vollständig abschließen kannst, ist in Ordnung. Aber wenn du das Gefühl hast, dass du in deiner Freizeit arbeitest, lohnt es sich aus meiner Sicht meist nicht. Also mach weiterhin kleinere Projekte und verliere nicht den Spaß am Programmieren und Entwickeln.

Eine andere Option wäre, sich einer vergleichbar großen Community anzuschließen und an einem Open-Source-Projekt zu arbeiten. Dort könntest man kleine Dinge tun und trotzdem mit wenig Aufwand einen proportional großen Einfluss haben.

## Wie sieht die Zukunft von Fedodo aus?

Dieses Gefühl der Arbeit und persönlichen Probleme während dieser Zeit führte dazu, dass ich die Entwicklung von Fedodo pausierte und generell eine Pause vom Coden in meiner Freizeit gemacht habe.

Jetzt, einige Monate später, fange ich langsam wieder an diesen Drang zu verspüren, etwas zu erschaffen. Daher denke ich, dass es die richtige Entscheidung war weniger zu tun.

Allerdings werde ich in Zukunft nicht mehr so intensiv an Fedodo arbeiten. Angesichts der Größe des Projekts bedeutet dies wahrscheinlich, dass ich es nicht fertigstellen kann. Leider.

> **Fedodo ist einfach zu groß für mich**
