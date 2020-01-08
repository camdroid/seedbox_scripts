from deluge_client import DelugeRPCClient
from tracker_requirements import TRACKER_REQS
from secrets import host, port, username, password
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
    from urllib.parse import urlparse
    if 'digitalcore' in urlparse(info[b'tracker']).netloc.decode('utf-8').split('.'):
        tracker = 'digitalcore'
    else:
        tracker = 'torrentleech'
    if info[b'seeding_time'] > TRACKER_REQS[tracker]['seeding_time']:
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

def main():
    client = login()
    # list of keys? https://forum.deluge-torrent.org/viewtopic.php?t=54793
    torrents = client.call('core.get_torrents_status', {},
                          ['name', 'progress', 'ratio', 'tracker',
                           'seeding_time', 'total_size'])

    # tids = torrents_with_full_ratio(torrents)
    tids = torrents_that_meet_tracker_reqs(torrents)
    for tid in tids:
        if check_if_torrent_downloaded(torrents[tid]):
            print(torrents[tid][b'name'].decode('utf-8'), " is downloaded and meets tracker seeding requirements. Can be safely deleted.")


if __name__ == '__main__':
    main()
