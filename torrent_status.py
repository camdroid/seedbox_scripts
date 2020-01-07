from deluge_client import DelugeRPCClient
from secrets import host, port, username, password

def login():
    client = DelugeRPCClient(host, port, username, password)
    client.connect()
    return client

client = login()
torrent_names = client.call('core.get_torrents_status', {}, ['name'])
print(torrent_names)
