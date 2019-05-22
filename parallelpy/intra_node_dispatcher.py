# Copyright 2018 David Matthews
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

from queue import Queue
from multiprocessing import cpu_count, Pool, TimeoutError

from parallelpy.utils import Work
from parallelpy.constants import *


class IntraNodeDispatcherCore(object):
    def __init__(self):
        self.num_workers = cpu_count()
        self.pool = Pool(processes=self.num_workers)
        self.current_work = [None] * self.num_workers  # each result is placed in here.
        self.current_work_ids = [None] * self.num_workers  # each result is placed in here.
        self.completed_work = Queue()  # keep track of work which needs to be returned.

        self.idle_work = Queue()  # record which indicies of the  current_work array are empty.
        for i in range(self.num_workers):
            self.idle_work.put(i)

    def is_done(self):
        return self.completed_work.qsize() == 0 and self.idle_work.qsize() == self.num_workers

    def has_work_to_return(self):
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
        :param work_tup: a tuple of the id of the work and the work to evaluate
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
        Checks to see if any work has completed. If so, updates the current_work,
        amount_idle and completed_work array and queues.

        Tune the speed you call this based on your application.
        :return: None.
        """
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
            if letter is not None:
                self.current_work[i] = None
                self.idle_work.put(i)
                work_id, cpu_cnt = self.current_work_ids[i]
                self.completed_work.put((work_id, letter))
                self.current_work_ids[i] = None


def main_loop():
    from mpi4py import MPI
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    assert rank != 0, "intra node dispatcher can not have rank of 0"

    intra_nd = IntraNodeDispatcherCore()
    comm.send(intra_nd.num_workers, dest=0, tag=SIZE_INFO)

    while True:
        intra_nd.check_work()  # check if there is new completed work.

        # handle current mode + exit messages
        if comm.Iprobe(source=0, tag=MODE_MSG):
            mode_id = comm.recv(source=0, tag=MODE_MSG)
            print("Node %d got mode id: %d " % (rank, mode_id))
            if mode_id == QUIT_MODE:
                exit(0)
            else:
                raise NotImplementedError("Unknown mode ID")

        # if we have work to return, return it
        if intra_nd.has_work_to_return():
            id, letter = intra_nd.get_completed_work()
            comm.send((id, letter), dest=0, tag=RETURN_WORK)  # send the id and letter of the completed work.

        # if we have been sent work, process it
        if comm.Iprobe(source=0, tag=GET_WORK):
            work = comm.recv(source=0, tag=GET_WORK)  # get the work
            intra_nd.insert_work(work)  # add the work to the queue


if __name__ == '__main__':
    main_loop()
