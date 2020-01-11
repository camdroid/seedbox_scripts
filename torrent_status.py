from deluge_client import DelugeRPCClient
from tracker_requirements import TRACKER_REQS
from secrets import host, port, username, password
import datetime
import argparse
from urllib.parse import urlparse
import copy
import pdb

def login():
    client = DelugeRPCClient(host, port, username, password)
    client.connect()
    return client

def was_downloaded_to_raspi():
    # idea - make a json file of the files that are downloaded off the seedbox
    # have a script on the raspi update that json file when rsync runs
    # if the file is finished, then update json.
    # then this script checks that json file, potentially to remove torrents
    # once they've reached their minimum seeding requirements and been
    # downloaded (at least, if I want to keep them)
    pass


def check_if_torrent_downloaded(torrent):
    with open('fully_downloaded.txt') as downloads:
        for line in downloads:
            if torrent[b'name'].decode('utf-8') in line:
                return True
    return False

def get_req_seeding_time_for_tracker(tracker_url):
    # pdb.set_trace()
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


class TorrentStat:
    def __init__(self, _id=None, name=None, ratio=0, seeding_time=0, tracker=None):
        # pdb.set_trace()
        self._id = _id.decode('utf-8')
        self.name = name.decode('utf-8')
        self.ratio = ratio
        self.seeding_time = seeding_time
        self.tracker = tracker.decode('utf-8')
        self.seeding_time_left = self.get_seeding_time_left()

    def is_done_downloading(self):
        return self.seeding_time > 0

    def can_stop_seeding(self):
        return self.meets_tracker_reqs()

    def meets_tracker_reqs(self):
        if self.ratio > 1:
            return True
        if self.seeding_time_left is None:
            return False
        if self.seeding_time_left.total_seconds() < 0:
            return True
        return False

    def __str__(self):
        if not self.can_stop_seeding():
            seeding_output = f'{self.seeding_time_left} left to seed'
        else:
            seeding_output = f'Ratio: {self.ratio}'
        return f'{self.name[:25]}:\t\t{seeding_output}'

    def __repl__(self):
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


def print_all_stats(torrent_stats):
    sorted_list = sorted([r for r in torrent_stats if r.seeding_time_left is not None], key=lambda x: x.seeding_time_left)
    for r in sorted_list:
        print(r)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--done', action='store_true')
    args = parser.parse_args()

    client = login()
    # list of keys? https://forum.deluge-torrent.org/viewtopic.php?t=54793
    res_torrents = client.call('core.get_torrents_status', {},
                          ['name', 'progress', 'ratio', 'tracker',
                           'seeding_time', 'total_size'])

    torrents = [TorrentStat(_id, torrent[b'name'], torrent[b'ratio'], torrent[b'seeding_time'], torrent[b'tracker'])
                for _id, torrent in res_torrents.items()]

    if args.all:
        print_all_stats(torrents)
    elif args.done:
        for torrent in torrents:
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
