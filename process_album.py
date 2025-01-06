#!/usr/bin/env python3

# TODO ADD CONFIG

import yaml
import argparse
from pathlib import Path
import tempfile
import zipfile
import subprocess
import json
import shutil
import playlist_add_album

def load_config(config_name: str) -> dict:
    config_files = list(Path.home().joinpath('.config').glob(f'{config_name}.[yml yaml]*'))
    config_files += list(Path.home().joinpath('.config', config_name).glob(f'{config_name}.[yml yaml]*'))

    for config_file in config_files:
        with open(config_file) as c:
            config = yaml.safe_load(c)
            if config:
                return config
    return {}

def validate_config(config: dict):
    keys = {
        str: ['archive_dir', 'music_dir'],
        list: ['playlists', 'music_file_types']
    }
        
    for var_type, key_list in keys.items():
        for key in key_list:
            try:
                if type(config[key]) != var_type:
                    raise TypeError(f"'{key}' not type '{var_type}'")
            except KeyError:
                pass

def yes_no(prompt: bool) -> bool:
    answer = input(f"{prompt} (y/n) ").lower().strip()[:1]
    if answer == 'y':
        return True
    return False

def get_music_files(dir: Path, music_file_types: list[str]) -> list[Path]:
    music_files = []
    for file in Path(dir).iterdir():
        if file.is_file() and file.suffix in music_file_types:
            music_files.append(file)
    
    for file in Path(dir).iterdir():
        if file.is_dir():
            music_files = music_files + get_music_files(file, music_file_types)
    return music_files

def get_music_metadata(music_file: Path) -> tuple[str, str, str]:
    try:
        metadata = subprocess.check_output(['ffprobe',
                                            '-v', 'quiet',
                                            '-print_format', 'json=compact=1',
                                            '-show_format',
                                            music_file])
        try:
            metadata = json.loads(metadata)
            try:
                tags = metadata['format']['tags']

                if 'ARTIST' in tags:
                    track_artist = tags['ARTIST']
                elif 'artist' in tags:
                    track_artist = tags['artist']
                else:
                    raise KeyError('artist')

                if 'ALBUM' in tags:
                    track_album = tags['ALBUM']
                elif 'album' in tags:
                    track_album = tags['album']
                else:
                    raise KeyError('album')

                if 'TITLE' in tags:
                    track_title = tags['TITLE']
                elif 'title' in tags:
                    track_title = tags['title']
                else:
                    raise KeyError('title')

                return track_artist, track_album, track_title
            except KeyError as e:
                raise Exception(f"Error: Tag {e} not found in \"{music_file}\"")
        except json.JSONDecodeError as e:
            raise Exception(f"Error: Unable to parse json ouput from ffprobe for \"{music_file}\" {e}")
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error: ffprobe error for \"{music_file}\" {e}")

def auto_detect(dir: Path, music_file_types: list[str]) -> tuple[str, str]:
    music_files = get_music_files(dir, music_file_types)
    for music_file in music_files:
        return get_music_metadata(music_file)[:-1]

def get_root_album_dir(dir: Path, music_file_types: list[str], root=True) -> Path | None:
    '''
    Recursively look for music files prioritizing files over directories
    '''
    for file in Path(dir).iterdir():
        if file.is_file() and file.suffix in music_file_types:
            return file.parent
    
    for file in Path(dir).iterdir():
        if file.is_dir():
            recursive_call = get_root_album_dir(file, music_file_types, False)
            if recursive_call != None:
                return recursive_call
    if root:
        raise SystemExit(f"Error: Unable to find music files with extensions {music_file_types} in \"{dir}\"")
    else:
        return None

def process_album_replay_gain(album_dir: Path):
    print(f"Processing ReplayGain for \"{album_dir}\"")
    subprocess.check_output(['rsgain', 'easy', album_dir])

def main():
    prog = 'process_album'

    try:
        config = load_config(prog)
        validate_config(config)
    except Exception as e:
        raise SystemExit(f"Config Error: {e}")

    if 'music_file_types' in config:
        music_file_types = config['music_file_types']
    else:
        music_file_types = ['.flac', '.mp3', '.m4a', '.ogg']

    description = "Copy/archive album, process ReplayGain, and add them to playlist."
    usage = """%(prog)s [-h] [-g ARCHIVE_DIR] [-m MUSIC_DIR] [-p PLAYLIST]
                     (-b | -a ARTIST -n ALBUM)
                     (-z ZIP | -d ALBUM_DIR)"""
    epilog = "Arguments override options set in configuration file."
    parser = argparse.ArgumentParser(prog=prog, description=description, usage=usage, epilog=epilog)
    parser.add_argument('-b', '--auto-detect', action='store_true')
    parser.add_argument('-a', '--artist')
    parser.add_argument('-n', '--album')
    parser.add_argument('-g', '--archive-dir', required=False if 'archive_dir' in config else True)
    parser.add_argument('-m', '--music-dir', required=False if 'music_dir' in config else True)
    parser.add_argument('-p', '--playlists', action='append')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-z', '--zip')
    group.add_argument('-d', '--album-dir')
    args = parser.parse_args()

    if not args.auto_detect and (not args.artist or not args.album):
        parser.error("arguments -b/--auto-detect or -a/--artist -n/--album are required")

    config_args = ['archive_dir', 'music_dir', 'playlists']
    for config_arg in config_args:
        if config_arg in config and not getattr(args, config_arg, None):
            setattr(args, config_arg, config[config_arg])

        if type(getattr(args, config_arg, None)) == str and getattr(args, config_arg, None) == '' :
            raise SystemExit(f"Error: '{config_arg}' set to blank string ''")

    if args.zip != None:
        tmp_dir = tempfile.TemporaryDirectory()
        with zipfile.ZipFile(args.zip, 'r', metadata_encoding= 'utf-8') as z:
            z.extractall(tmp_dir.name)

        album_dir = get_root_album_dir(Path(tmp_dir.name), music_file_types)

        if args.auto_detect:
            artist_name, album_name = auto_detect(Path(tmp_dir.name), music_file_types)

    elif args.album_dir != None:
        album_dir = get_root_album_dir(Path(args.album_dir), music_file_types)

        if args.auto_detect:
            artist_name, album_name = auto_detect(Path(args.album_dir), music_file_types)

    if not args.auto_detect:
        artist_name = args.artist
        album_name = args.album

    # Prepare dirs
    archive_artist_dir = Path(args.archive_dir).joinpath(artist_name).expanduser().resolve()
    music_artist_dir = Path(args.music_dir).joinpath(artist_name).expanduser().resolve()
    archive_artist_dir.mkdir(parents=True, exist_ok=True)
    music_artist_dir.mkdir(parents=True, exist_ok=True)

    # Create music archive zip
    music_archive_zip = Path(archive_artist_dir, f'{artist_name} - {album_name}.zip')
    if music_archive_zip.is_file() and not yes_no(f"Overwrite archive album zip \"{music_archive_zip}\"?"):
        create_archive = False
    else:
        create_archive = True
    if create_archive:
        with zipfile.ZipFile(music_archive_zip, 'w') as z:
            for file in album_dir.rglob('*'):
                z.write(file, file.relative_to(album_dir))

    # Copy to music dir
    music_album_dir = Path(music_artist_dir, f'{artist_name} - {album_name}')
    if music_album_dir.is_dir() and not yes_no(f"Overwrite music album \"{music_album_dir}\"?"):
        create_music = False
    else:
        create_music = True
    if create_music:
        try:
            shutil.copytree(album_dir, music_album_dir, dirs_exist_ok=True)
        except shutil.Error as e:
            raise SystemExit(f"Error: Could not copy album to \"{msic_album_dir}\"")
        process_album_replay_gain(music_album_dir)

    if args.playlists:
        for playlist in args.playlists:
            for music_file in sorted(music_album_dir.iterdir()):
                if music_file.is_file() and music_file.suffix in music_file_types:
                    try:
                        playlist_add_album.add_track_to_playlist(music_file, Path(playlist).expanduser().resolve())
                    except Exception as e:
                        print(e)
                        print(f"Error: Unable to add song \"{music_file}\" to playlist \"{playlist}\"")

if __name__ == '__main__':
    main()
