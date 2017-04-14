from pyactor.context import set_context, create_host, sleep, shutdown, interval
from random import sample, choice
from pyactor.exceptions import TimeoutError
from pyactor.proxy import *

data_size = 9


class Printer(object):
    _tell = ['to_print']

    @staticmethod
    def to_print(string):
        print string


class Tracker(object):
    _tell = ['announce', 'init_start', 'stop_interval', 'reduce_time', 'add_printer', 'print_swarm']
    _ask = ['get_peers']
    _ref = ['announce', 'get_peers', 'add_printer']

    def __init__(self):
        self.swarm = {}
        self.printer = None
        self.interval_reduce = None

    def add_printer(self, printer1):
        self.printer = printer1

    def announce(self, torrent_id, peer1):
        if torrent_id in self.swarm.keys():
            self.swarm[torrent_id][peer1] = 10
        else:
            self.swarm[torrent_id] = {peer1: 10}

    def init_start(self):
        self.interval_reduce = interval(self.host, 1, self.proxy, "reduce_time")

    def stop_interval(self):
        self.interval_reduce.set()

    def reduce_time(self):
        for torrent in self.swarm.keys():
            for peer_t in self.swarm[torrent].keys():
                self.swarm[torrent][peer_t] -= 1
                if self.swarm[torrent][peer_t] <= 0:
                    del self.swarm[torrent][peer_t]

    def get_peers(self, torrent_id):
        peer_list = self.swarm[torrent_id].keys()
        return sample(peer_list, min(3, len(peer_list)))

    def print_swarm(self):
        print self.swarm


class Peer(object):
    _tell = ['add_tracker', 'add_printer', 'start_announcing', 'stop_announcing', 'announcing',
             'receive_friends', 'init_data', 'save_gossips']
    _ask = ['finish', 'get_gossips']
    _ref = ['add_tracker', 'add_printer', 'start_announcing', 'announcing', 'receive_friends', 'init_data']

    def __init__(self):
        self.friends_ref = []
        self.data = {}
        self.gossips = []
        self.finished = False
        self.tracker = None
        self.printer = None
        self.interval_friends = None
        self.interval_announce = None

    def save_gossips(self):
        self.gossips.append(len(self.data))

    def get_gossips(self):
        return self.gossips

    def add_tracker(self, track):
        self.tracker = track

    def finish(self):
        self.finished = True

    def add_printer(self, printer1):
        self.printer = printer1

    def start_announcing(self, time, torrent):
        self.interval_announce = interval(self.host, time, self.proxy, "announcing", torrent)
        self.interval_friends = interval(self.host, 2, self.proxy, "receive_friends", torrent)

    def stop_announcing(self):
        self.interval_announce.set()
        self.interval_friends.set()

    def announcing(self, torrent):
        self.tracker.announce(torrent, self.id)

    def receive_friends(self, torrent):
        try:
            friends = self.tracker.get_peers(torrent)
            self.friends_ref = []
            for f in friends:
                if f != self.id:
                    self.friends_ref.append(h.lookup(f))
        except TimeoutError:
            pass

    def init_data(self, filename):
        global data_size
        data = {}
        torrent = open(filename, 'r').read()
        pos = 0
        for char in torrent:
            data[pos] = char
            pos += 1
        del data[pos - 1]
        data_size = pos - 1
        self.data = data


class Push(Peer):
    _tell = Peer._tell + ['start_pushing', 'stop_pushing', 'pushing', 'push']
    _ref = Peer._ref + ['push']

    def __init__(self):
        super(Push, self).__init__()
        self.interval_push = None

    def start_pushing(self):
        self.interval_push = interval(self.host, 1, self.proxy, "pushing")

    def stop_pushing(self):
        self.interval_push.set()

    def pushing(self):
        for friend in self.friends_ref:
            if self.data:
                try:
                    chunk = choice(self.data.items())
                    friend.push(chunk[0], chunk[1])
                except TimeoutError:
                    pass

    def push(self, chunk_id, chunk_data):
        global cont
        if self.finished is False:
            self.data[chunk_id] = chunk_data
            self.printer.to_print(self.id + " " + str(self.data))
            if gossip_type == 1:
                self.save_gossips()
            if len(self.data.keys()) == data_size:
                self.finished = True
                self.printer.to_print(self.id + " has finished")
                cont += 1


class Pull(Peer):
    _tell = Peer._tell + ['start_pulling', 'stop_pulling', 'pulling', 'receive_pull']
    _ask = Peer._ask + ['pull']
    _ref = Peer._ref + ['pull', 'receive_pull']

    def __init__(self):
        super(Pull, self).__init__()
        self.interval_pull = None

    def start_pulling(self):
        self.interval_pull = interval(self.host, 1, self.proxy, "pulling")

    def stop_pulling(self):
        self.interval_pull.set()

    def pulling(self):
        if self.finished is False:
            chunks = list(set(range(data_size)) - set(self.data.keys()))
            if chunks:
                for friend in self.friends_ref:
                    try:
                        future = friend.pull(choice(chunks), future=True)
                        future.add_callback('receive_pull')
                    except IndexError:
                        pass
                    except TimeoutError:
                        pass

    def pull(self, chunk_id):
        try:
            return [chunk_id, self.data[chunk_id]]
        except KeyError:
            return None

    def receive_pull(self, future):
        global cont
        msg = future.result()  # msg brings chunk_id and chunk_data
        if self.finished is False:
            if msg:
                self.data[msg[0]] = msg[1]
                self.printer.to_print(self.id + " " + str(self.data))
                if len(self.data.keys()) == data_size:
                    self.finished = True
                    self.printer.to_print(self.id + " has finished")
                    cont += 1
            self.save_gossips()


class Hybrid(Pull, Push):
    _tell = Pull._tell + Push._tell + ['start_hybrid', 'stop_hybrid', 'push_pull']

    def __init__(self):
        super(Hybrid, self).__init__()
        self.interval_hybrid = None

    def start_hybrid(self):
        self.interval_hybrid = interval(self.host, 1, self.proxy, "push_pull")

    def stop_hybrid(self):
        self.interval_hybrid.set()

    def push_pull(self):
        self.pushing()
        self.pulling()


if __name__ == "__main__":

    print "1-Push, 2-Pull, 3-Hybrid"
    try:
        gossip_type = int(raw_input('Enter the gossip type:'))
    except ValueError:
        print "Not a number"

    n_peers = 0
    try:
        n_peers = int(raw_input("Enter the number of peers: "))
    except ValueError:
        print "Not a number"

    if gossip_type == 1:
        peer_class = Push
    elif gossip_type == 2:
        peer_class = Pull
    else:
        peer_class = Hybrid

    peers = []

    set_context()
    h = create_host()

    printer = h.spawn('printer', Printer)
    tracker = h.spawn('tracker', Tracker)
    tracker.add_printer(printer)

    seed = h.spawn('seed', peer_class)
    seed.finish()
    seed.add_tracker(tracker)
    seed.add_printer(printer)
    seed.init_data('torrent.txt')

    for i in range(0, n_peers):
        peer = h.spawn("peer" + str(i), peer_class)
        peer.add_tracker(tracker)
        peer.add_printer(printer)
        peers.append(peer)

    tracker.init_start()  # Start removing inactive peers
    seed.start_announcing(10, 'torrent1')
    for p in peers:
        p.start_announcing(10, 'torrent1')

    cont = 0
    # Begin gossip cycles
    if gossip_type == 1:
        seed.start_pushing()
        for p in peers:
            p.start_pushing()
    elif gossip_type == 2:
        for p in peers:
            p.start_pulling()
    else:
        seed.start_pushing()
        for p in peers:
            p.start_hybrid()

    completed = False
    while completed is False:
        if cont == n_peers:
            completed = True
    # End of gossip cycles
    if gossip_type == 1:
        seed.stop_pushing()
        for i in peers:
            i.stop_pushing()

    elif gossip_type == 2:
        for i in peers:
            i.stop_pulling()

    else:
        seed.stop_pushing()
        for i in peers:
            i.stop_hybrid()

    print "Stopping announce..."
    seed.stop_announcing()
    for i in peers:
        i.stop_announcing()

    sleep(15)
    print "SWARM:"
    tracker.print_swarm()
    tracker.stop_interval()
    sleep(.1)

    var = 0
    average_gossips = 0
    print "GOSSIP RESULTS:"
    if gossip_type == 1:
        print "-PUSH"
    elif gossip_type == 2:
        print "-PULL"
    else:
        print "-HYBRID"
    print "PEER   | GOSSIPS | DATA PER GOSSIP"
    for peer in peers:
        values = peer.get_gossips()
        gossips = len(values)
        print "peer", var, "|   ", gossips, "   |", values
        var += 1
        average_gossips += gossips
    print "AVERAGE GOSSIPS :", average_gossips / n_peers

    shutdown()

