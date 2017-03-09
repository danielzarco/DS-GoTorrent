#Authors: Daniel Zarco,Carlos Rincón 
#Distributed Systems, ETSE

from pyactor.context import set_context, create_host, sleep, shutdown
import random

class Tracker(object):
    _tell = ['announce', 'init_start','stop_interval', 'reduce_tiempo', 'elimina_peers']
    _ask = ['print_swarm', 'get_peers']
    _ref = ['announce']
    swarm = {}

    """
    Concretely, the announce method has two parameters, the hash or id of the torrent to be downloaded,
    and the reference to the peer that wants to participate in the swarm. For simplicity, you can use the file
    name as id. Note that, like in BitTorrent , the peer must periodically announce its presence in the swarm.
    The tracker removes peers from the swarm than do not announce themselves in a period of 10 seconds.
    The signature of this method is:
    announce(torrent_hash, peer_ref)
    """
    def announce(self, torrent_id, peer_ref):
        print "Announce " + peer_ref
        if torrent_id in self.swarm:
            #print 'El torrent existe en el swarm'
            if peer_ref in self.swarm[torrent_id]:
                self.swarm[torrent_id][peer_ref] = 10
                #print peer_ref + " existe en el sistema"
            else:
                #print "Peer not found in in the swarm, adding it..."
                self.swarm[torrent_id].update({peer_ref: 10})
        else:
            #print "Torrent not found. Adding torrent..."
            self.swarm[torrent_id] = {peer_ref: 10}
        print self.swarm

        peer = h.lookup(peer_ref)
        friends = self.get_peers(torrent_id)
        friends.remove(peer_ref)
        print friends
        peer.get_friends(friends)

    def print_swarm(self):
        print self.swarm

    #inicia los intervalos
    def init_start(self):
        self.interval0= self.host.interval(1, self.proxy, "reduce_tiempo")
        self.interval1 = self.host.interval(10, self.proxy, "elimina_peers")

    def stop_interval(self):
        print "stopping tracker's interval"
        self.interval0.set()
        self.interval1.set()

    #Decrementa contador de cada peer
    def reduce_tiempo(self):
        print "reducing"
        torrents = self.swarm.keys()
        for torrent in torrents:
            for peer in self.swarm[torrent].keys():
                    self.swarm[torrent][peer] -= 1

    #Elimina un peer si no se anuncia en 10 segundos
    def elimina_peers(self):
        print "Removing"
        torrents = self.swarm.keys()
        for torrent in torrents:
            for peer in self.swarm[torrent].keys():
                if self.swarm[torrent][peer] <= 0:
                    del self.swarm[torrent][peer]


    # The get_peers method is used to obtain a list of peers participating in this download. The tracker
    # returns a fixed number of random peers from the swarm. The signature of this method is:
    # neighbors  get_peers(torrent_hash)
    def get_peers(self, torrent_id):
        peer_list = list(self.swarm[torrent_id].keys())
        final_list = list(random.sample(peer_list, min(5,len(peer_list))))
        return final_list

class Peer(object):
    _tell = ['start_announcing', 'announcing', 'add_tracker', 'stop_interval', 'get_friends', 'init_data', 'push', 'get_data']
    _ask = ['get_id', 'receive_data']
    _ref = ['announcing', 'push']
    friends = []
    data = {}

    def get_id(self):
        return self.id

    def add_tracker(self, tracker):
        self.tracker = tracker
        print "Tracker added " , self.tracker

    def start_announcing(self, time, torrent):
        self.interval0 = self.host.interval(time, self.proxy, "announcing", torrent)
        #self.host.later(10, self.proxy, "stop_interval")

    def stop_interval(self):
        print "stopping inpeer.print_data()terval"
        self.interval0.set()

    #Call to the announce method of the tracker
    def announcing(self, torrent):
        #print self.get_id()+" Announcing "+torrent
        #self.tracker.init_start()
        self.tracker.announce(torrent, self.get_id())

    #Method to receive the list of neighbours
    def get_friends(self, friends):
        self.friends = friends
        print "------------------ open---------------"
        print self.get_id() , self.friends
        print "------------------ close -------------"

    def print_data(self):
        print self.data

    #Initializing the string to share (seed)
    def init_data(self):
        self.data = {0:'G', 1:'O', 2:'T', 3:'O', 4:'R', 5:'R', 6:'E', 7:'N', 8:'T'}
        print self.data

    #Save the chunk of data sent by another peer
    def receive_data(self, chunk_id, chunk_data):
        if chunk_id not in self.data:
            self.data[chunk_id] = chunk_data

    #Best friends are the neighbours of one peer
    def push(self, chunk_id, chunk_data):
        best_friends = random.sample(self.friends, min(2,len(self.friends)))
        for best_friend in best_friends:
            #Sends data to best friend
            h.lookup(best_friend).receive_data(chunk_id, chunk_data)

if __name__ == "__main__":
    set_context()
    h = create_host()

    tracker = h.spawn('tracker', Tracker)
    ref = h.lookup('tracker')

    peer = h.spawn('peer0', Peer)
    peer1 = h.spawn('peer1', Peer)
    peer2 = h.spawn('peer2', Peer)
    peer3 = h.spawn('peer3', Peer)
    peer4 = h.spawn('peer4', Peer)

    peer.init_data()

    peer.add_tracker(tracker)
    peer1.add_tracker(tracker)
    peer2.add_tracker(tracker)
    peer3.add_tracker(tracker)
    peer4.add_tracker(tracker)

    tracker.init_start()        #Start removing inactive peers
    peer.start_announcing(1, 'torrent1')
    peer1.start_announcing(1, 'torrent1')
    peer2.start_announcing(1, 'torrent1')
    peer3.start_announcing(1, 'torrent1')
    peer4.start_announcing(1, 'torrent1')


    sleep(1)
    #peer.push(0, 'G')
    #peer1.print_data()
    #peer2.print_data()
    #peer3.print_data()
    #peer4.print_data()

    #print tracker.get_peers('torrent1')
    print "----------------------------------------"
    ref.print_swarm()
    print "Disconnecting peer0..."
    peer.stop_interval()
    peer1.stop_interval()
    peer2.stop_interval()
    peer3.stop_interval()
    peer4.stop_interval()

    sleep(10)
    tracker.print_swarm()
    tracker.stop_interval()

    tracker.print_swarm()

    sleep(1)
    shutdown()
