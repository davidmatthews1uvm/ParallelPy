from __future__ import print_function

from queue import Queue
from multiprocessing import cpu_count, Pool, TimeoutError

import sys
from parallelpy.utils import Work, Letter
from parallelpy.constants import *

class intra_node_dispatcher_core(object):
    def __init__(self):
        self.num_workers = cpu_count()
        self.pool = Pool(processes=(self.num_workers))
        self.current_work = [None]* self.num_workers  # each result is placed in here.
        self.current_work_ids = [None]* self.num_workers  # each result is placed in here.
        self.completed_work = Queue() # keep track of work which needs to be returned.

        self.idle_work = Queue() # record which indicies of the  current_work array are empty.
        for i in range(self.num_workers):
            self.idle_work.put(i)

    def is_done(self):
        return self.completed_work.qsize() == 0 and self.idle_work.qsize() == self.num_workers

    def has_work_to_return(self):
        # #print("Node %d has %d work to return" % (rank, self.completed_work.qsize()))
        return self.completed_work.qsize() != 0

    def get_completed_work(self):
        return self.completed_work.get()

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
        self.current_work[work_idx] = self.pool.apply_async(work.complete_work)
        cpu_cnt = work.cpus_requested()
        self.current_work_ids[work_idx] = (work_id, cpu_cnt)

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
            letter = None
            try:
                letter = self.current_work[i].get(timeout=timeout)
            except TimeoutError:
                pass
                # #print("Get work had a timeout error")
            if letter is not None:
                self.current_work[i] = None
                self.idle_work.put(i)
                work_id, cpu_cnt = self.current_work_ids[i]
                # print(cpu_cnt)
                self.completed_work.put((work_id, letter))
                self.current_work_ids[i] = None

def main_loop():
    from mpi4py import MPI
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    assert rank != 0, "intra node dispatcher can not have rank of 0"
    import os
    # print(os.getpid())
    sent_request_for_work = False
    in_idle = True
    intra_nd = intra_node_dispatcher_core()
    work_requested = 0
    min_work_request = 1
    while True:
        # print("node %d says hi" %rank)
        intra_nd.check_work()  # check if there is new completed work.
        # handle current mode + exit messages
        if comm.Iprobe(source=0, tag=MODE_MSG):
            #print("Node %d getting next mode message" % rank)
            mode_id = comm.recv(source=0, tag=MODE_MSG)
            print("Node %d got mode id: %d " % (rank, mode_id))
            if mode_id == QUIT_MODE:
                exit(0)
            elif mode_id == ENTER_IDLE_MODE:
                # print("Node %d Entering Idle Mode" %rank, flush=True)
                in_idle = True
                work_requested = 0
            elif mode_id == EXIT_IDLE_MODE:
                # print("Node %d Exiting Idle Mode" % rank, flush=True)
                in_idle = False
                min_work_request = 1
                assert intra_nd.is_done(), "node %d, not all work finished. Can't exit idle" %rank
            else:
                raise NotImplementedError("Unknown mode ID")

        # if we have work to return, return it
        if intra_nd.has_work_to_return():
            id, letter = intra_nd.get_completed_work()
           # print("Node %d returning %d" %(rank, id), flush=True)
            comm.send((id, letter), dest=0, tag=RETURN_WORK)  # send the id and letter of the completed work.
            # comm.send(letter, dest=0, tag=RETURN_WORK) # send the letter we are returning
            #print("Node %d returned %d" %(rank, id))

        # if we have requested work and it has been sent, process.
        if comm.Iprobe(source=0, tag=GET_WORK):
            #print("Node %d getting work" %rank)
            work = comm.recv(source=0, tag=GET_WORK)  # get the work
            #print("Node %d beginning processing work %d" %(rank, work[0]))
            if (work is None):
                min_work_request += 1
                work_requested = 0

            else:
                intra_nd.insert_work(work)  # add the work to the queue
                work_requested -= work[1].cpus_requested()

        if not in_idle:
            amount_idle = intra_nd.amount_idle()
            if work_requested == 0 and amount_idle >= min_work_request:
                work_requested = amount_idle
                comm.send(amount_idle, dest=0, tag=NEED_WORK)  # send the request for more work
                print("Node %d requesting %d work" %(rank, work_requested))


if __name__ == '__main__':
    main_loop()