#!/usr/bin/env bash
# Wordcount je Kapitel basierend auf texcount (Paket texlive-extra-utils).
# Ergebnis wird als Markdown in wordcount.md im Stammverzeichnis gespeichert.

texcount -inc -sub=section -html thesis_main.tex | pandoc -f html -t markdown -o wordcount.md
