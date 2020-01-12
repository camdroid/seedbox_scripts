from deluge_client import DelugeRPCClient
from tracker_requirements import TRACKER_REQS
from secrets import host, port, username, password
import datetime
import argparse
from urllib.parse import urlparse
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


def get_req_seeding_time_for_tracker(tracker_url):
    tried_parse = urlparse(tracker_url).netloc.split('.')
    if 'digitalcore' in tried_parse:
        tracker = 'digitalcore'
    elif 'torrentleech' in tried_parse:
        tracker = 'torrentleech'
    elif 'leech' in tried_parse:
        tracker = 'torrentleech'
    elif 'archive' in tried_parse:
        # Internet Archive
        tracker = 'archive'
    elif 'torrentseeds' in tried_parse:
        tracker = 'torrentseeds'
    else:
        tracker = ''
    return TRACKER_REQS.get(tracker, {}).get('seeding_time')


def gigs_left_on_disk():
    import os
    stats = os.statsvfs()
    return stats.f_bsize * stats.f_bavail / 1024**3


class TorrentStat:
    def __init__(self, _id=None, name=None, ratio=0, seeding_time=0, tracker=None):
        self._id = _id.decode('utf-8')
        self.name = name.decode('utf-8')
        self.ratio = ratio
        self.seeding_time = seeding_time
        self.tracker = tracker.decode('utf-8')
        self.seeding_time_left = self.get_seeding_time_left()
        self.fodder = False

    def is_done_downloading(self):
        return self.seeding_time > 0

    def can_stop_seeding(self):
        return self.meets_tracker_reqs()

    def mark_as_fodder(self):
        self.fodder = True

    def meets_tracker_reqs(self):
        if self.ratio > 1:
            return True
        if self.seeding_time_left is None:
            return False
        if self.seeding_time_left.total_seconds() < 0:
            return True
        return False

    def __str__(self):
        if not self.is_done_downloading():
            seeding_output = f'Still downloading...'
        elif self.can_stop_seeding():
            seeding_output = f'Ratio: {self.ratio}'
        elif self.seeding_time_left is None:
            seeding_output = f'No requirement data for tracker {self.tracker[:40]}'
        else:
            seeding_output = f'{self.seeding_time_left} left to seed'

        extra = ''
        if self.fodder:
            extra = f'{self._id}'
        return f'{self.name[:25]}:\t\t{seeding_output}\t\t{extra}'

    def __repr__(self):
        return str(self)

    def get_seeding_time_left(self):
        time_left = get_req_seeding_time_for_tracker(self.tracker)
        if not time_left:
            return None
        hr_seeding_time = datetime.timedelta(seconds=self.seeding_time)
        hr_seeding_req = datetime.timedelta(seconds=time_left)
        return hr_seeding_req - hr_seeding_time

    def get_reqd_seeding_time_in_seconds(self):
        return TRACKER_REQS[self.tracker]


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
        for skip in data['do_not_sync']:
            if skip in t.name:
                t.mark_as_fodder()
                fodder.append(t)
    return fodder


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
