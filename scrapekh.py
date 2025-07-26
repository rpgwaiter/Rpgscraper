#!/usr/bin/env python

import urllib.request
import os
import multiprocessing as mp
import argparse
from parallelbar import progress_imapu

from bs4 import BeautifulSoup
from colorama import Fore, Style
from colorama.ansi import clear_line
from multiprocessing import Process


# Argument must end in a slash (for now)
# if sys.argv[1] is not None:
# 	rip_root_folder = sys.argv[1]
# else:
rip_root_folder = "/mnt/public/Radio/khrip/"
base_url = "https://downloads.khinsider.com"
real_upstream = "https://eta.vgmtreasurechest.com"

#################################
# GLOBALS
#################################
procs = []
full_rip = False  # If true, scan every album

# TODO:
# There's some albums that clearly aren't in the right spot. Make a list of them and compensate for not having them.
# Make a TUI.

# These use the nomenclature of the downloads site. This isn't the way I personally would have organized it,
# But I get the feeling that they came to their senses and kept their old naming convention for compatibility.
# Note that some systems are not included because... I don't really want a bunch of anime music right now.
array_systems = [
    # '3do',
    # 'amiga',
    # 'arcade',
    # 'atari-8bit',
    # 'atari-st',
    # 'cd-i',
    # 'commodore-64',
    # "fm-towns",
    # 'gameboy',
    # 'gameboy-advance',
    # 'ms-dos',
    # "msx",
    # "msx2",
    # 'neo-geo',
    # 'nintendo-64',
    # 'nintendo-nes',
    # 'nintendo-snes',
    # "pc-8801",
    "pc-9801",
    # "pc-fx",
    # 'playstation',
    # 'sega-dreamcast',
    # 'sega-game-gear',
    # 'sega-master-system',
    # 'sega-mega-drive-genesis',
    # "sharp-x1",
    # 'spectrum',
    # "turbografx-16",
    # 'virtual-boy',
    # "x68000",
]


# Making this its own function in case I want to change the method later
def get_page(url):
    good_url = f"{base_url}{url}" if url.startswith("/") else url
    return urllib.request.urlopen(good_url)


def get_albums(soup):
    # Gets a list of all a tags, the whole thing
    link_array_unf = soup.find_all("a")
    album_list = set()

    # Adds all albums to set
    for fulllink in link_array_unf:
        link = fulllink.get("href")
        # print(f"get_albums: LINK: {link}")
        if link and link.startswith("/game-soundtracks/album/"):
            album_list.add(link)
    return album_list


# Gets a set of song links from an album link
def get_songs(album_link, album_name):
    soup_album_link = BeautifulSoup(get_page(album_link), "html.parser")

    # Finds all links in album page
    array_album_unf = soup_album_link.find_all("a")
    the_set = set()  # Holds links to song pages

    # Loops through all links, finds links to songs
    for link_album_unf in array_album_unf:
        link2 = link_album_unf.get("href")
        if str(link2).startswith("/game-soundtracks/album/" + album_name) and "change_log" not in link2:
            the_set.add((f"{base_url}{link2}"))
    return the_set


# Takes a link to the song, finds the file and downloads it.
def download_song(args):
    try:
        song_link, save_dir = args
        soup_song_page = BeautifulSoup(get_page(song_link), "html.parser")
        all_links = [x.get("href") for x in soup_song_page.find_all("a")]

        flac_link = ([x for x in all_links if x and ".flac" in x][:1] or [None])[0]
        mp3_link = ([x for x in all_links if x and ".mp3" in x][:1] or [None])[0]
        good_link = flac_link or mp3_link

        # This is just the name of the mp3, fixes url encoding like %20
        mp3_filename = urllib.parse.unquote(good_link.split("/")[-1])
        mp3_fullpath = f"{save_dir}/{mp3_filename}"

        # If the mp3 file doesn't exist..
        if not os.path.isfile(mp3_fullpath) and good_link:
            try:
                response = get_page(good_link)
                # print(f"\n{Fore.CYAN}{Style.DIM}[-] DOWNLOADING: {mp3_fullpath}{Style.NORMAL}", end='')
                # Actually saves the song
                data = response.read()
                with open(mp3_fullpath, "wb") as this_song:
                    this_song.write(data)
                print(clear_line(), end='')
            except OSError as e:
                print(e)
        return 0
    except:
        print(f"ERROR w/ Song: {args[0]}")
        return 0


# Scans the number of subfolders in a given folder
def get_local_albums(system):
    num_soundtracks = 0
    for root, dirs, files in os.walk(rip_root_folder + system):
        num_soundtracks += len(dirs)
    return int(num_soundtracks)


## TODO: only look for .flac and .mp3
def get_local_songs(path):
    return sum(1 for file in os.listdir(path) if os.path.isfile(os.path.join(path, file))) or 0

# use a process pool to quickly grab all songs in an album
def parallel_album_grab(args):
    album_url = args[0]
    system = args[1]
    album_name = album_url.split("/game-soundtracks/album/")[-1]

    save_dir = f"{rip_root_folder}{system}/{album_name}"
    created = False
    try: # ensure it exists
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            created = True
    except OSError:
        pass

    set_of_song_pages = list(get_songs(album_url, album_name))
    num_local_songs = get_local_songs(save_dir)
    num_remote_songs = len(set_of_song_pages)

    if num_local_songs >= num_remote_songs and not full_rip:
        print(Fore.GREEN + f"Got {album_name} already, moving on...")
    else:
        print(
            Fore.GREEN + "####################################################"
        )
        print(f"{Fore.MAGENTA}>> {Fore.BLUE}Current Album: {album_name} {Fore.MAGENTA}<<{Fore.GREEN}")
        print(f"[LOCAL] Number of songs in {album_name}: {num_local_songs}")
        print(
            f"[REMOTE] Number of songs in {album_name}: {num_remote_songs}"
        )
        if created:
            print(f"[!] CREATED DIR: {save_dir}")
        print("####################################################")
        mp_iter = list(map(lambda x: (x, save_dir), set_of_song_pages))
        # with mp.Pool(processes=mp.cpu_count()) as pool:
        progress_imapu(download_song, mp_iter, total=len(set_of_song_pages), chunk_size=5)
def scrape_everything():
    print("===================================================")
    print("================ Starting Scrape ==================")
    print("===================================================")
    print(f"Number of systems getting scraped: {len(array_systems)}")

    # MAIN LOOP
    for what_system in array_systems:
        print(f"===== CURRENT SYSTEM: {what_system} =====")
        soup_system = BeautifulSoup(
            get_page(f"{base_url}/game-soundtracks/{what_system}"), "html.parser"
        )

        print("Getting remote list of soundtracks...")
        local_num_soundtracks = get_local_albums(what_system)
        set_of_albums = get_albums(soup_system)

        print(f"NUMBER OF REMOTE {what_system} SOUNDTRACKS = {len(set_of_albums)}")
        print(f"NUMBER OF LOCAL {what_system} SOUNDTRACKS = {local_num_soundtracks}")

        # If there's the same number of local and remote soundtracks, skip the system
        if len(set_of_albums) == local_num_soundtracks and full_rip:
            print(f"You have every {what_system} soundtrack. Moving on...")

        # If there's a new soundtrack, run the script
        else:
            for album_url in set_of_albums:
                parallel_album_grab((album_url, what_system))


def main():
    parser = argparse.ArgumentParser(
        prog="khscraper",
        description="Scrapes music from khinsider against their ToS, so probably don't use it.",
        epilog="Keep It Based."
    )
    parser.add_argument('-a', '--album', type=str) # Should be a full album url
    parser.add_argument('--system', type=str) # Should be a local path
    args = parser.parse_args()
    print(args)
    if args.album and args.system:
        url = args.album
        system = args.system
        print(f"Downloading {system} soundtrack for {url.split('/')[-1]}")
        parallel_album_grab((url, system))
    else:
        scrape_everything()

if __name__ == "__main__":
    main()
