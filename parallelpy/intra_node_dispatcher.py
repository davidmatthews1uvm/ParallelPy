from __future__ import print_function
import sys
import pickle
from queue import Queue
from collections import deque
from multiprocessing import cpu_count, Pool, TimeoutError

from mpi4py import MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()
assert rank != 0, "intra node dispatcher can not have rank of 0"

import sys

# used to create tmp directories to enable high speed creation of files on the distributed file system
import uuid

# import the message tags
from parallelpy.constants import *
# import parallelpy objects
from parallelpy.parallel_evaluate import Work

# Update the system path so that this process has the same python module names as the main python process.
if len(sys.argv) > 1:
    sys.path.insert(0, sys.argv[1])


class intra_node_dispatcher(object):
    def __init__(self, session_id):
        self.session_id = session_id
        self.num_workers = cpu_count()
        self.max_over_commit_level = 2.0
        self.pool = Pool(processes=int(self.num_workers * self.max_over_commit_level))
        self.current_work = [None]* self.num_workers  # each result is placed in here.
        self.current_work_ids = [None]* self.num_workers  # each result is placed in here.
        self.completed_work = Queue() # keep track of work which needs to be returned.

        self.idle_work = Queue() # record which indicies of the  current_work array are empty.
        for i in range(self.num_workers):
            self.idle_work.put(i)

    def get_size(self):
        return self.num_workers

    def is_done(self):
        return self.completed_work.qsize() == 0 and self.idle_work.qsize() == self.num_workers

    def has_work_to_return(self):
        # #print("Node %d has %d work to return" % (rank, self.completed_work.qsize()))
        return self.completed_work.qsize() != 0

    def get_completed_work(self):
        work_to_return = []
        while True:
            try:
                work_to_return.append(self.completed_work.get_nowait())
            except:
                break
        return work_to_return

    def amount_idle(self):
        """
        Checks if this node has idle resources -- and could use more work to be full.
        :return: True if needs work, False otherwise
        """
        return self.idle_work.qsize()

    def insert_work(self, work_tup):
        """
        Starts processing the given work; if the queue is already full will fail.
        :param work: a tuple of the id of the work and the work to evaluate
        :return: None
        """
        work_id, work = work_tup
        assert isinstance(work, Work), "work must be of type Work"
        assert self.idle_work.qsize() != 0, "queue is full; can not add work"
        work_idx = self.idle_work.get()
        self.current_work[work_idx] = self.pool.apply_async(work.complete_work, kwds={"work_directory":self.session_id})
        self.current_work_ids[work_idx] = work_id

    def check_work(self, timeout=0, debug=False):
        """
        Checks to see if any work has completed. If so, updates the current_work, amount_idle and completed_work array and queues.

        Tune the speed you call this based on your application.
        :return: None.
        """
        # #print(self.current_work_ids)
        if debug:
            import time
            for work in self.current_work:
                print(work)
            time.sleep(1)
        for i in range(self.num_workers):
            if self.current_work[i] is None:
                continue
            try:
                letter = self.current_work[i].get(timeout=timeout)
                self.current_work[i] = None
                self.idle_work.put(i)
                work_id = self.current_work_ids[i]
                self.completed_work.put((work_id, letter))
                self.current_work_ids[i] = None
            except TimeoutError:
                pass
                # #print("Get work had a timeout error")



if __name__ == '__main__':
    send_queue = deque()
    session_id = str(uuid.uuid1())
    intra_nd = intra_node_dispatcher(session_id)

    comm.send(intra_nd.get_size(), dest=0, tag=SIZE_MSG)

    while True:
        intra_nd.check_work() # check if there is new completed work.
        # handle current mode + exit messages
        if comm.Iprobe(source=0, tag=MODE_MSG):
            print("Node %d waiting for mode msg" %rank)
            mode_id = comm.recv(source=0, tag=MODE_MSG)
            print("Node %d got mode msg" %rank)
            if mode_id == QUIT_MODE:
                exit(0)

            else:
                raise NotImplementedError("Unknown mode ID")

        # if we have work to return, return it
        elif intra_nd.has_work_to_return():
            if len(send_queue) != 0 and send_queue[0][0].Test():
                send_queue.popleft()
            work_to_return = intra_nd.get_completed_work()
            if work_to_return == []:
                print("Failed to get work to return, continuing")
                continue
            to_send = pickle.dumps(work_to_return)
            # print("Node %d returning %d work" %(rank, len(work_to_return)), flush=True)
            req = comm.Isend(to_send, dest=0, tag=RETURN_WORK) # send the id and letter of the completed work.
            send_queue.append((req, to_send))

            # print("Node %d returned %d work" %(rank, len(work_to_return)))
        elif comm.Iprobe(source=0, tag=GET_WORK):
            # print("Node %d waiting for work" % rank)
            work_array  = comm.recv(source=0, tag=GET_WORK)  # get the work
            # print("Node %d got work" % rank)
            for work in work_array:
                intra_nd.insert_work(work)  # add the work to the queue
