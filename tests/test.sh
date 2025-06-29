#!/usr/bin/env bash
set -e

mkdir -p music-dir
mkdir -p archive-dir
mkdir -p playlists

rm -r music-dir/*
rm -r archive-dir/*
rm playlists/*
echo -n "#EXTM3U" > playlists/test.m3u8

../process_album.py -b -g archive-dir -m music-dir -z samples/*.zip -p playlists/test.m3u8
../process_album.py -b -g archive-dir -m music-dir -s samples/*.flac -p playlists/test.m3u8
