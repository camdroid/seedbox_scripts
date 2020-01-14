from manager import DelugeHelper
from torrent_stat import TorrentStat
import json
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--reset', action='store_true',
                    help='Go through all torrents, regardless of whether they\'re already labeled')
args = parser.parse_args()

# TODO get this working with overriding the pre-existing file
# reset = args.reset
reset = False

saved_file = 'do_rsync.json'
unsaved_file = 'do_not_rsync.json'

torrents_to_save = []
torrents_not_to_save = []

with open(saved_file) as do_rsync:
    torrents_to_save = json.load(do_rsync) #['do_sync']

with open(unsaved_file) as do_not_rsync:
    torrents_not_to_save = json.load(do_not_rsync) #['do_not_sync']

deluge = DelugeHelper()
for torrent in deluge.get_torrents()[5:]:
    # import pdb; pdb.set_trace()
    ask_about_torrent = torrent.name not in torrents_to_save and torrent.name not in torrents_not_to_save
    if reset or ask_about_torrent:
        ans = input(f'Do you want to keep {torrent.name}?')
        if ans == 'n':
            torrents_not_to_save.append(torrent.name)
        elif ans == 'y':
            torrents_to_save.append(torrent.name)
        elif ans == 'q':
            break
        else:
            print('What?')

with open(saved_file, 'w') as do_rsync:
    json.dump(torrents_to_save, do_rsync)

with open(unsaved_file, 'w') as do_not_rsync:
    json.dump(torrents_not_to_save, do_not_rsync)

