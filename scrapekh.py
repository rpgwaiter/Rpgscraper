import urllib.request
import os
import time
import shutil
import sys
import time
import multiprocessing as mp
import logging

from bs4 import BeautifulSoup
from colorama import Fore
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
verbose = False

# TODO:
# There's some albums that clearly aren't in the right spot. Make a list of them and compensate for not having them.
# Make a TUI.

# These use the nomenclature of the downloads site. This isn't the way I personally would have organized it,
# But I get the feeling that they came to their senses and kept their old naming convention for compatibility.
# Note that some systems are not included because... I don't really want a bunch of anime music right now.
array_systems = [
	'3do',
	'amiga',
	'arcade',
	'atari-8bit',
	'atari-st',
	'cd-i',
	'commodore-64',
	'fm-towns',
	'gameboy',
	'gameboy-advance',
	'ms-dos',
	'msx',
	'msx2',
	'neo-geo',
	'nintendo-64',
	'nintendo-nes',
	'nintendo-snes',
	'pc-8801',
	'pc-9801',
	'pc-fx',
	'playstation',
	'sega-dreamcast',
	'sega-game-gear',
	'sega-master-system',
	'sega-mega-drive-genesis',
	'sharp-x1',
	'spectrum',
	'turbografx-16',
	'virtual-boy',
	'x68000'
]


# Making this its own function in case I want to change the method later
def get_page(url):
    if url.startswith('/game-soundtracks/'):
        good_url = f"{base_url}{url}"
    else:
        good_url = url
    return urllib.request.urlopen(good_url)


def get_albums(soup):
	# Gets a list of all a tags, the whole thing
    link_array_unf = soup.find_all("a")
    album_list = set()
    # album_list = []

    # Adds all albums to set
    for fulllink in link_array_unf:
        link = fulllink.get("href")
        # print(f"get_albums: LINK: {link}")
        if link and link.startswith('/game-soundtracks/album/'):
            album_list.add(link)

    return album_list

# Gets a set of songs from an album link
def get_songs(album_link, album_name):
    soup_album_link = BeautifulSoup(get_page(base_url + album_link), 'html.parser')

    # Finds all links in album page
    array_album_unf = soup_album_link.find_all("a")
    the_set = set()  # Holds links to song pages

    # Loops through all links, finds links to songs
    for link_album_unf in array_album_unf:
        link2 = link_album_unf.get("href")
        if str(link2).startswith("/game-soundtracks/album/" + album_name):
            if verbose:
                print(f"{link2} -- Adding to song set")
            the_set.add((f"{base_url}{link2}"))
    return the_set

# Takes a link to the song, finds the file and downloads it.
def download_song(song_link):
    soup_song_page = BeautifulSoup(get_page(song_link), 'html.parser')
    all_links = [x.get("href") for x in soup_song_page.find_all("a")]

    flac_link = ([x for x in all_links if x and ".flac" in x][:1] or [None])[0]
    mp3_link = ([x for x in all_links if x and ".mp3" in x][:1] or [None])[0]
    good_link = flac_link or mp3_link

    # Makes directory needed
    savedir = f"{rip_root_folder}{what_system}/{album_name}"
    try:
        if not os.path.exists(savedir):
            print("MAKING DIR:" + savedir)
            os.makedirs(savedir)
    except OSError:
        print(OSError)

    # This is just the name of the mp3, fixes url encoding like %20
    mp3_filename = urllib.parse.unquote(good_link.split("/")[-1])
    mp3_fullpath = f"{savedir}/{mp3_filename}"

    # If the mp3 file doesn't exist..
    if not os.path.isfile(mp3_fullpath) and good_link:
        try:
            # if verbose:
            #     print(f"Process ID: {os.getpid()}")
            # print("DOWNLOADING:" + good_link)
            response = get_page(good_link)
            print(Fore.BLUE + f"DOWNLOADING: {mp3_fullpath}")
            # Actually saves the song
            data = response.read()
            with open(mp3_fullpath, "wb") as this_song:
                this_song.write(data)
        except OSError:
            pass
    return 0


# Scans the number of subfolders in a given folder
def get_local_albums(system):
    num_soundtracks = 0
    for root, dirs, files in os.walk(rip_root_folder + system):
        num_soundtracks += len(dirs)
    # return dirs
    return int(num_soundtracks)


# Scans the number of mp3s in a given folder
def get_local_songs(album):
    path = rip_root_folder + what_system + "/" + album
    if os.path.isdir(path):
        return len([name for name in os.listdir(path) if os.path.isfile(os.path.join(path, name))])
    return 0


print("===================================================")
print("================ Starting Scrape ==================")
print("===================================================")
print(f"Number of systems getting scraped: {len(array_systems)}")


# MAIN LOOP
for what_system in array_systems:
    print(f"===== CURRENT SYSTEM: {what_system} =====")
    print(f"https://downloads.khinsider.com/game-soundtracks/{what_system}")
    soup_system = BeautifulSoup(get_page(f"{base_url}/game-soundtracks/{what_system}"), 'html.parser')

    print("Getting remote list of soundtracks...")
    local_num_soundtracks = get_local_albums(what_system)
    set_of_albums = get_albums(soup_system)

    print(f"NUMBER OF REMOTE {what_system} SOUNDTRACKS = {len(set_of_albums)}")
    print(f"NUMBER OF LOCAL {what_system} SOUNDTRACKS = {local_num_soundtracks}")

    # If there's the same number of local and remote soundtracks, skip the system
    if len(set_of_albums) == local_num_soundtracks and full_rip:
        print(f"You have every {what_system} soundtrack. Moving on to the next system...")

    # If there's a new soundtrack, run the script
    else:
        # For every album link
        for link_album in set_of_albums:
            print("CURRENTLINK: " + link_album)
            album_name = link_album.split("/game-soundtracks/album/")[-1]

            # Gets album name from current url
            print(Fore.GREEN + "####################################################")
            print(f"Current Album: {album_name}")
            print("####################################################")

            set_of_song_pages = get_songs(link_album, album_name)
            num_local_songs = get_local_songs(album_name)
            num_remote_songs = len(set_of_song_pages)
            print(f"[LOCAL] Number of songs in {album_name}: {num_local_songs}")
            print(f"[REMOTE] Number of songs in {album_name}: {num_remote_songs}")

            if num_local_songs >= num_remote_songs and not full_rip:
                print("Got the whole soundtrack, moving on...")
            else:
                with mp.Pool(processes=mp.cpu_count()) as pool:
                    pool.map(download_song, set_of_song_pages)