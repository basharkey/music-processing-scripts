#!/usr/bin/env bash

rm -r music-dir/*
rm -r archive-dir/*
rm playlists/*
echo -n "#EXTM3U" > playlists/test.m3u8

../process_album.py -b -g archive-dir -m music-dir -z samples/*.zip -p playlists/test.m3u8
../process_album.py -b -g archive-dir -m music-dir -s samples/*.flac -p playlists/test.m3u8
