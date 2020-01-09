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

def torrents_with_full_ratio(torrents):
    tcopy = copy.deepcopy(torrents)
    for tid, info in torrents.items():
        if info[b'ratio'] < 1:
            tcopy.pop(tid)
    return [_id.decode('utf-8') for _id in tcopy]

def torrent_has_full_ratio(torrents, tid):
    return torrents[tid][b'ratio'] > 1

def torrent_meets_tracker_reqs(torrents, tid):
    # Assumes all trackers are satisfied if you seed at least 1:1
    # I think this is true?
    if torrent_has_full_ratio(torrents, tid):
        return True
    info = torrents[tid]
    reqd_time = get_req_seeding_time_for_tracker(info[b'tracker'])
    if info[b'seeding_time'] > reqd_time:
        return True
    return False

def torrents_that_meet_tracker_reqs(torrents):
    results = []
    for tid, info in torrents.items():
        if torrent_meets_tracker_reqs(torrents, tid):
            results.append(tid)
    return results

def get_title_for_torrents(torrents, tids):
    # TODO having to convert everything to/from binary is going to get real
    # old, real fast.
    # pdb.set_trace()
    return [torrents[tid][b'name'] for tid in tids]

def check_if_torrent_downloaded(torrent):
    with open('fully_downloaded.txt') as downloads:
        for line in downloads:
            if torrent[b'name'].decode('utf-8') in line:
                return True
    return False

def get_req_seeding_time_for_tracker(tracker_url):
    # pdb.set_trace()
    tried_parse = urlparse(tracker_url).netloc.decode('utf-8').split('.')
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
    return TRACKER_REQS.get(tracker, {}).get('seeding_time', 0)


class TorrentStat:
    def __init__(self, name=None, ratio=0, seeding_time=0, tracker=None):
        self.name = name
        self.ratio = ratio
        self.seeding_time = seeding_time
        self.tracker = tracker
        self.seeding_time_left = self.get_seeding_time_left()

    def __str__(self):
        hr_seeding_time = datetime.timedelta(seconds=self.seeding_time)
        hr_seeding_req = datetime.timedelta(seconds=get_req_seeding_time_for_tracker(self.tracker))
        # return f'{self.name}:\t{self.ratio:.2f}\t{hr_seeding_time}/{hr_seeding_req}'
        return f'{self.name}:{self.seeding_time_left}'

    def get_seeding_time_left(self):
        hr_seeding_time = datetime.timedelta(seconds=self.seeding_time)
        hr_seeding_req = datetime.timedelta(seconds=TRACKER_REQS.get(self.tracker, 0))
        return hr_seeding_req - hr_seeding_time


    def get_reqd_seeding_time_in_seconds(self):
        return TRACKER_REQS[self.tracker]

def print_all_stats(torrents):
    # Name, ratio, seeding_time/required time
    results = []
    for t in torrents.values():
        res = TorrentStat(t[b'name'], t[b'ratio'], t[b'seeding_time'], t[b'tracker'])
        results.append(res)
    sorted_list = sorted(results, key=lambda x: x.seeding_time_left)
    for r in sorted_list:
        print(r)




def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true')
    args = parser.parse_args()

    client = login()
    # list of keys? https://forum.deluge-torrent.org/viewtopic.php?t=54793
    torrents = client.call('core.get_torrents_status', {},
                          ['name', 'progress', 'ratio', 'tracker',
                           'seeding_time', 'total_size'])

    if args.all:
        print_all_stats(torrents)
        import sys
        sys.exit(0)

    # tids = torrents_with_full_ratio(torrents)
    tids = torrents_that_meet_tracker_reqs(torrents)
    for tid in tids:
        if check_if_torrent_downloaded(torrents[tid]):
            print(torrents[tid][b'name'].decode('utf-8'), "is downloaded and meets tracker seeding requirements. Can be safely deleted.")


if __name__ == '__main__':
    main()
