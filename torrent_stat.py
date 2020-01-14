from urllib.parse import urlparse
from tracker_requirements import TRACKER_REQS
import datetime

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
        if True:
        # if self.fodder:
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


