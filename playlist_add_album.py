#!/usr/bin/env python3

import argparse
from pathlib import Path
import subprocess
import json
import process_album

def relative(target: Path, origin: Path) -> Path:
    target = target.resolve()
    origin = origin.resolve()
    try:
        return target.relative_to(origin)
    except ValueError:
        return Path('..').joinpath(relative(target, origin.parent))

def generate_m3u8_entry(music_file: Path, playlist_file: Path) -> tuple[str, str]:
    try:
        streams = subprocess.check_output(['ffprobe', '-v', 'quiet', '-print_format', 'json=compact=1', '-show_streams', music_file])
        try:
            streams = json.loads(streams)
            try:
                audio_stream = {}
                for stream in streams['streams']:
                    if stream['codec_type'] == 'audio':
                        audio_stream = stream
                track_duration = round(float(audio_stream['duration']))
                track_artist, track_album, track_title = process_album.get_music_metadata(music_file)
                track_relative_path = relative(music_file, playlist_file.parent)

                return f'#EXTINF:{track_duration},{track_title}', f'{track_relative_path}'
            except KeyError as e:
                raise Exception(f"Error: Tag {e} not found in \"{music_file}\"")
        except json.JSONDecodeError as e:
            raise Exception(f"Error: Unable to parse json ouput from ffprobe for \"{music_file}\" {e}")
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error: ffprobe error for \"{music_file}\" {e}")

def append_m3u8_entry(m3u8_entry: tuple[str, str], playlist_file: Path):
    if playlist_file.suffix != '.m3u8':
        raise Exception(f"Error: \"{playlist_file}\" is not a '.m3u8' playlist file")
    with open(playlist_file, 'a+') as p:
        p.seek(0)
        for line in p.read().splitlines():
            if line in m3u8_entry:
                print(f"\"{m3u8_entry[1]}\" already in playlist skipping...")
                return

        p.write(f'\n{m3u8_entry[0]}\n{m3u8_entry[1]}')
        print(f"Added \"{m3u8_entry[1]}\" to playlist \"{playlist_file}\"")

def add_track_to_playlist(music_file: Path, playlist: Path):
    m3u8_entry = generate_m3u8_entry(music_file, Path(playlist))
    append_m3u8_entry(m3u8_entry, Path(playlist))
        
def main():
    description = "Add album to playlist(s)."
    parser = argparse.ArgumentParser(prog="album-playlist", description=description)
    parser.add_argument('-d', '--album-dir', required=True)
    parser.add_argument('-p', '--playlist', action='append', required=True)
    args = parser.parse_args()

    music_file_types = ['.flac', '.mp3', '.m4a', '.ogg']

    for file in sorted(Path(args.album_dir).iterdir()):
        if file.is_file() and file.suffix in music_file_types:
            for playlist in args.playlist:
                try:
                    add_track_to_playlist(file, Path(playlist))
                except Exception as e:
                    print(e)
                    print(f"Error: Unable to add song \"{music_file}\" to playlist \"{playlist}\"")

if __name__ == '__main__':
    main()
