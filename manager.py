from deluge_client import DelugeRPCClient
from tracker_requirements import TRACKER_REQS
from secrets import host, port, username, password
import datetime
import argparse
from urllib.parse import urlparse
from torrent_stat import TorrentStat
import copy
import sys
import json
import pdb

def was_downloaded_to_raspi():
    # idea - make a json file of the files that are downloaded off the seedbox
    # have a script on the raspi update that json file when rsync runs
    # if the file is finished, then update json.
    # then this script checks that json file, potentially to remove torrents
    # once they've reached their minimum seeding requirements and been
    # downloaded (at least, if I want to keep them)
    pass


def gigs_left_on_disk():
    import os
    stats = os.statsvfs()
    return stats.f_bsize * stats.f_bavail / 1024**3


class DelugeHelper:
    def __init__(self):
        self.login()

    def login(self):
        self.client = DelugeRPCClient(host, port, username, password)
        self.client.connect()

    def get_torrents(self):
        # list of keys? https://forum.deluge-torrent.org/viewtopic.php?t=54793
        res_torrents = self.client.call('core.get_torrents_status', {},
                              ['name', 'progress', 'ratio', 'tracker',
                               'seeding_time', 'total_size'])

        torrents = [TorrentStat(_id, torrent[b'name'], torrent[b'ratio'], torrent[b'seeding_time'], torrent[b'tracker'])
                    for _id, torrent in res_torrents.items()]
        return torrents

    def delete_torrent(self, torrent_id):
        self.client.core.remove_torrent(torrent_id, remove_data=True)


def print_all_stats(torrent_stats, sort='seeding_time_left'):
    sorted_list = sorted([r for r in torrent_stats if getattr(r, sort) is not None], key=lambda x: getattr(x, sort))
    for r in sorted_list:
        print(r)


def list_fodder_torrents(torrents):
    with open('do_not_rsync.json') as json_file:
        data = json.load(json_file)
    fodder = []
    for t in torrents:
        for skip in data:
            if skip in t.name:
                t.mark_as_fodder()
                fodder.append(t)
    return fodder

def auto_delete(deluge_helper, request_confirmation):
    for torrent in list_fodder_torrents(deluge_helper.get_torrents()):
        if torrent.ratio == 0:
            ans = input(f'Are you sure you want to delete {torrent.name}? (y/n) ')
            if ans == 'y':
                print(f'Deleting {torrent.name}')
                deluge_helper.delete_torrent(torrent.id)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--done', action='store_true')
    parser.add_argument('--sort', type=str, default='name')
    parser.add_argument('-lf', '--list-fodder', action='store_true')
    parser.add_argument('--delete', type=str)
    args = parser.parse_args()

    deluge_helper = DelugeHelper()
    torrents = deluge_helper.get_torrents()

    if args.list_fodder:
        import pprint
        pp = pprint.PrettyPrinter()
        pp.pprint(list_fodder_torrents(torrents))

    if args.delete:
        deluge_helper.delete_torrent(args.delete)

    if args.sort and args.sort not in ['ratio', 'name']:
        print('Must specify sort of an accepted type (see code)')
        sys.exit(1)


    if args.all:
        print_all_stats(torrents, args.sort)
    elif args.done:
        for torrent in sorted(torrents, key=lambda x: getattr(x, args.sort)):
            if torrent.can_stop_seeding():
                print(torrent)


if __name__ == '__main__':
    main()

# Script ideas
# Would love to use this script to help me figure out what to rsync down to my home server
# i.e. A particular torrent is close to meeting the torrent requirements, but isn't synced off the seedbox,
# so I should rsync that next, instead of just going in alphabetical order.
# (Although, if I can figure out why my download speeds are only a couple Mbps, maybe this won't be as relevant.)

# Should keep a list of files I don't care about keeping (and am just using to get my ratio up)
# Check that list against the list of torrents that have finished seeding, delete those.
