import urllib.request
import os
from bs4 import BeautifulSoup
from colorama import Fore
from multiprocessing import Process
import time
import shutil

#################################
# GLOBALS
#################################
rip_root_folder = "khrip/"
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
	# 'amiga',
	# 'arcade',
	# 'atari-8bit',
	# 'atari-st',
	# 'cd-i',
	# 'commodore-64',
	# 'fm-towns',
	# 'gameboy',
	# 'gameboy-advance',
	# 'ms-dos',
	# 'msx',
	# 'msx2',
	# 'neo-geo',
	# 'nintendo-64',
	# 'nintendo-nes',
	# 'nintendo-snes',
	# 'pc-8801',
	# 'pc-9801',
	# 'pc-fx',
	# 'playstation',
	# 'sega-dreamcast',
	# 'sega-game-gear',
	# 'sega-master-system',
	# 'sega-mega-drive-genesis',
	# 'sharp-x1',
	# 'spectrum',
	# 'turbografx-16',
	# 'virtual-boy',
	'x68000'
]


# Making this its own function in case I want to change the method later
def get_page(url):
	page = urllib.request.urlopen(url)
	return page


def get_albums(soup):
	# Gets a list of all a tags, the whole thing
	link_array_unf = soup.find_all("a")
	the_list = []

	# Adds all albums to set
	for fulllink in link_array_unf:
		link = fulllink.get("href")
		if link.startswith('https://downloads.khinsider.com/game-soundtracks/album/'):
			if verbose:
				print("Link: {0}, adding to set.".format(link))
			print("Mapping albums... ({0})".format(link))
			album_name = link.split("https://downloads.khinsider.com/game-soundtracks/album/")[1]
			the_list.append((link, get_songs(link, album_name)))
	return the_list


# Gets a set of songs from an album link
def get_songs(album_link, album_name):
	soup_album_link = BeautifulSoup(get_page(album_link), 'html.parser')

	# Finds all links in album page
	array_album_unf = soup_album_link.find_all("a")
	the_set = set()  # Holds links to song pages

	# Loops through all links, finds links to songs
	for link_album_unf in array_album_unf:
		link2 = link_album_unf.get("href")
		if str(link2).startswith("/game-soundtracks/album/" + album_name):
			if verbose:
				print("{0} -- Adding to song set".format(link2))
			the_set.add(("https://downloads.khinsider.com/" + link2))
	return the_set


# Takes a link to the song, finds the file and downloads it.
def download_song(song_link):
	soup_song_page = BeautifulSoup(get_page(song_link), 'html.parser')

	link_array_song = soup_song_page.find_all("a", style="color: #21363f;")
	mp3_link = ""

	# This loops grabs the direct link
	for link_song_full in link_array_song:
		link_song = link_song_full.get("href")
		if link_song.startswith("http://23.237.126.42/"):
			mp3_link = link_song

	# This is just the name of the mp3, fixes url encoding like %20
	mp3_filename = urllib.parse.unquote(mp3_link.split("/")[-1])

	# Makes directory needed
	savedir = rip_root_folder + what_system + "/" + album_name
	try:
		if not os.path.exists(savedir):
			os.makedirs(savedir)
	except OSError:
		pass

	mp3_fullpath = savedir + "/" + mp3_filename

	# If the mp3 file doesn't exist..
	if not os.path.isfile(mp3_fullpath):
		try:
			if verbose:
				print('Process ID: {0}'.format(os.getpid()))
			response = get_page(mp3_link)
			print(Fore.BLUE + "DOWNLOADING: " + mp3_fullpath)
			# Actually saves the song
			data = response.read()
			song = open(mp3_fullpath, "wb")
			song.write(data)
			song.close()
		except OSError:
			pass
	return 0


# Scans the number of subfolders in a given folder
def get_local_albums(system):
	num_soundtracks = 0
	for root, dirs, files in os.walk(rip_root_folder + system):
		num_soundtracks += len(dirs)
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
print("Number of systems getting scraped: {0}".format(len(array_systems)))


# MAIN LOOP
for what_system in array_systems:
	print("===== CURRENT SYSTEM: {0} =====".format(what_system))
	print("https://downloads.khinsider.com/game-soundtracks/" +
												what_system)
	soup_system = BeautifulSoup(get_page("https://downloads.khinsider.com/game-soundtracks/" +
												what_system), 'html.parser')

	print("Getting remote list of soundtracks...")
	local_num_soundtracks = get_local_albums(what_system)
	set_of_albums = get_albums(soup_system)

	print("NUMBER OF REMOTE {0} SOUNDTRACKS = {1}".format(what_system, len(set_of_albums)))
	print("NUMBER OF LOCAL {0} SOUNDTRACKS = {1}".format(what_system, local_num_soundtracks))

	# If there's the same number of local and remote soundtracks, skip the system
	if len(set_of_albums) == local_num_soundtracks and full_rip:
		print("You have every {0} soundtrack. Moving on to the next system...".format(what_system))

	# If there's a new soundtrack, run the script
	else:
		# Loops through the whole set of albums
		for link_album in set_of_albums:
			print(link_album)
			album_name = (link_album[0].split("https://downloads.khinsider.com/game-soundtracks/album/"))[1]

			# Gets album name from current url
			print(Fore.GREEN + "####################################################")
			print("Current Album: {0}".format(album_name))
			print("####################################################")

			set_of_song_pages = link_album[1]
			num_local_songs = get_local_songs(album_name)
			num_remote_songs = len(set_of_song_pages)
			print("[LOCAL]  Number of songs in {0}: {1}".format(album_name, num_local_songs))
			print("[REMOTE] Number of songs in {0}: {1}".format(album_name, num_remote_songs))

			if num_local_songs == num_remote_songs and not full_rip:
				print("Got the whole soundtrack, moving on...")
			else:

				# if there's more stuff locally than there is remotely, start over
				# Will remove once script is more solid in case they delete stuff on site
				if num_local_songs > num_remote_songs:
					print("There's a difference here, this is fucky. Deleting folder and starting over.")
					shutil.rmtree(rip_root_folder + what_system + "/" + album_name)
					time.sleep(5)

				for song in set_of_song_pages:
					# Branches out new processes to download stuff faster
					proc = Process(target=download_song, args=(song,))
					procs.append(proc)
					proc.start()


				for proc in procs:
					proc.join()
