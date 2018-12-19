from __future__ import print_function
import multiprocessing
import pickle

from multiprocessing import Pool

import warnings
from abc import ABCMeta, abstractmethod

import numpy as np
from parallelpy.constants import *
try:
    from mpi4py import MPI
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    if size == 1:
        raise ImportError
except ImportError:
    comm = None
    rank = None
    size = None

pool = None
pool_count = None

# debug mode -- forces single threaded if using pool.
DEBUG = False

# MAX_THREADS
MAX_THREADS = None

class Letter(object):
    """
    A small packet of data to be sent to an object to update it following a computation on a different process
    This object will be pickled.
    """

    def __init__(self, data, dest):
        self.dest = dest
        self.data = data

    def get_data(self):
        return self.data

    def get_dest(self):
        return self.dest


class Work(object):
    """
    An abstract class to support minimizing the network traffic required to support using MPI to distribute computation
    of work across multiple computers
    """

    def complete_work(self, work_directory=None):
        """
        Completes the required work, and generates a letter to send back to the dispatcher.
        :return: A letter to be sent.
        """
        self.compute_work(work_directory=work_directory)
        return self.write_letter()

    def compute_work(self, work_directory=None):
        """
        Entry point to do the required computation.
        :return: none
        """
        raise NotImplementedError

    def write_letter(self):
        """
        Generates a small packet of data, a Letter, to send back to the dispatcher for it to update itself with the
        completed work
        :return: A Letter to send back to the dispatcher to update the object with the new data
        :rtype: Letter
        """
        raise NotImplementedError

    def open_letter(self, letter):
        """
        A message to send to the dispatcher to update the Work with the resulting computation data.
        :param letter: the letter to open
        :return: None
        """
        raise NotImplementedError


class ParallelRobot(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_simulator_instances(self): raise NotImplementedError

    @abstractmethod
    def get_num_evaluations(self): raise NotImplementedError

    @abstractmethod
    def evaluate_via_sim_data(self, sims_dat): raise NotImplementedError


def clean_up_batch_tools():
    """
    If we used MPI, informs the workers that they can exit.
    :return: None
    """
    if not (comm is None):
        for i in range(1, size):
            comm.send(-1, dest=i, tag=101)

def clean_up_batch_tools_multi_node():
    """
    If we used MPI, informs the workers that they can exit.
    :return: None
    """
    if not (comm is None):
        for i in range(1, size):
            comm.send(QUIT_MODE, dest=i, tag=MODE_MSG)

global node_sizes
global total_cores

node_sizes = None
total_cores = None
def batch_complete_work_multi_node(work_to_complete, over_commit_level = 1.0):
    """
    Uses MPI to complete work across multiple nodes. Recieves letters from the completed distributed coNmputation and has the local work to open the letters/
    :param work_to_complete: A derived class from the Work class.
    :param over_commit_level: A number between 1.0 and 2.0. When nearing the end of the work to compute, this determines how many parcels of work should be running per core.
                                If a number outside of the range is given, the number will be set to the closest value in the range.
    :return: None
    """

    from time import time
    assert comm != None, "Need MPI to do multi_node dispatching"
    if work_to_complete is []:
        return
    else:
        assert isinstance(work_to_complete[0], Work), \
            "Can only complete work which is a subclass of Work"
    global node_sizes
    global total_cores
    if node_sizes is None:
        node_sizes = [0] * (size)
        for i in range(1, size):
            node_sizes[i] = comm.recv(source=i, tag=SIZE_MSG)
        total_cores = np.sum(np.array(node_sizes))
        print(node_sizes)

    # threshold over_commit_level
    if over_commit_level < 1.0:
        over_commit_level = 1.0
    elif over_commit_level > 2.0:
        over_commit_level = 2.0
    elif np.isnan(over_commit_level):
        over_commit_level = 1.0

    total_work_count = len(work_to_complete)

    # Calculate when to start over commiting
    if (total_work_count < total_cores):
        begin_over_commit = 0
    else:
        begin_over_commit = int(total_cores*over_commit_level)

    # calculate over commit quantities
    if (begin_over_commit != 0):
        over_commit_quantities = list([int((over_commit_level- 1.0)*core_cnt) for core_cnt in node_sizes])
    else:
        over_commit_quantities = [0]* len(node_sizes)
    over_committed = False

    completed_work = [None] * total_work_count
    work_index = 0  # the simulation we are currently working on

    while work_index < total_work_count:

        # check all intra node dispatchers for newly completed work
        t0 = time()
        newly_finished_work = 0
        for i in range(1, size):
            if comm.Iprobe(source=i, tag=RETURN_WORK):
                batch_of_completed_work = comm.recv(source=i, tag=RETURN_WORK)

                for completed_work_index, letter  in batch_of_completed_work:
                    # print(completed_work_index, letter)
                    # letter = comm.recv(source=i, tag=RETURN_WORK)
                    completed_work[completed_work_index] = letter
                newly_finished_work += len(batch_of_completed_work)
                node_sizes[i] += len(batch_of_completed_work)

        # check if it is time to begin overcommiting
        if ( over_committed is False and total_work_count - work_index <= begin_over_commit):
            over_committed = True
            for i in range(len(node_sizes)):
                node_sizes[i] += over_commit_quantities[i]

        # check all intra node dispatchers to see if they need new work and if we have more work, give it to them.
        for i in range(1, size):
            if node_sizes[i] > 0:
                target_work_size = node_sizes[i]
                work_to_send = []
                for _ in range(target_work_size):
                    if work_index >= total_work_count:
                        break

                    work = work_to_complete[work_index]
                    completed_work[work_index] = (work_index, i)
                    work_to_send.append((work_index, work))
                    work_index += 1

                if work_to_send != []:
                    comm.send(work_to_send, dest=i, tag=GET_WORK)
                node_sizes[i] -= len(work_to_send)

    # collect which simulations are still running, wait for them to finish.
    work_not_done = [n for n in completed_work if isinstance(n, tuple)]
    work_left = len(work_not_done)
    while work_left > 0:
        for node in [w[1] for w in work_not_done]:
            # print(node)
            if comm.Iprobe(source=node, tag=RETURN_WORK):
                batch_of_completed_work = comm.recv(source=node, tag=RETURN_WORK)
                for completed_work_index, letter in batch_of_completed_work:
                    completed_work[completed_work_index] = letter
                work_left -= len(batch_of_completed_work)
                node_sizes[node] += len(batch_of_completed_work)

    # remove over commit quantites from each node, if needed.
    if (over_committed):
        for i in range(len(node_sizes)):
            node_sizes[i] -= over_commit_quantities[i]

    # open the letters
    for work, letter in zip(work_to_complete, completed_work):
        work.open_letter(letter)


def batch_complete_work(work_to_complete, force_fork=False, force_mpi=False):
    """
    Does a given set of work in parallel using MPI or fork
    Prior to exiting from  your program, please call clean_up_batch_simulate() to clean up the other MPI processes.

    :param work_to_complete: An iterable of work to complete
    :param max_processes: If not using MPI, forces the maximum number of processes that can run at a given time.
    :param force_fork: Forces the use of multiprocessing instead of MPI
    :param force_mpi: Forces the use of MPI.
    :return: None
    """
    assert not (force_fork and force_mpi), "Can not force both MPI and fork at the same time!"
    assert isinstance(work_to_complete[0], Work)

    if comm is None or force_fork:
        assert force_mpi is False, "Failed to use MPI as requested"
        # run as pool

        if DEBUG:
            process_cnt = 1
        else:
            try:
                process_cnt = multiprocessing.cpu_count()
            except NotImplementedError:
                warnings.warn("Unable to determine how many CPU's are avaiable, using 1 process.")
                process_cnt = 1
        if MAX_THREADS is None:
            letters = _batch_complete_work_via_pool(work_to_complete, process_cnt)
        else:
            letters = _batch_complete_work_via_pool(work_to_complete, min(MAX_THREADS, process_cnt))

    else:
        # run as MPI
        letters = _batch_complete_work_via_MPI(work_to_complete)

    # open the letters
    for work, letter in zip(work_to_complete, letters):
        work.open_letter(letter)


def _batch_complete_work_via_pool(work_to_complete, process_count):
    """
    Uses python's multiprocessing package to compute the work across a single compute node.
    Used as a fallback instead of MPI.
    :param work_to_complete: Array of work to complete
    :param process_count: Number of processes to include in the pool
    :return: Array of Letter objects
    """

    global pool
    global pool_count
    if pool_count != process_count:
        if pool is not None:
            pool.close()
        pool = Pool(processes=process_count)
        pool_count = process_count

    res = [pool.apply_async(w.complete_work) for w in work_to_complete]
    letters = [r.get() for r in res]

    return letters


def _batch_complete_work_via_MPI(work_to_complete):
    """
     Helper method for batch_evaluate_robots(). Uses MPI to evaluate a given set of simulation instances in parallel.
     :param work_to_complete: An iterable containing work to evaluate.
     :return: an array of letters
     """
    if work_to_complete is []:
        return
    else:
        assert isinstance(work_to_complete[0], Work), \
            "Can only complete work which is a subclass of Work"
    completed_work = [None] * len(work_to_complete)

    global comm, rank, size

    work_index = 0  # the simulation we are currently working on
    total_work_count = len(work_to_complete)
    while work_index < total_work_count:
        if work_index < size - 1:  # prime the workers processes with work to start.
            i = work_index + 1
            # store which worker doing the job, and which work is being run
            completed_work[work_index] = (work_index, i)

            # send a new work to the worker
            work = work_to_complete[work_index]
            comm.send(work_index, dest=i, tag=101)
            comm.send(work, dest=i, tag=1)

            # update the work index.
            work_index += 1
            # print("priming the engines")
        else:
            for i in range(1, size):
                if work_index >= total_work_count:
                    break
                if comm.Iprobe(source=i, tag=101):
                    # get and save work data ( a letter)
                    completed_work_index = comm.recv(source=i, tag=101)
                    letter = comm.recv(source=i, tag=102)
                    completed_work[completed_work_index] = letter

                    # store which worker is doing the job, and what work is being run
                    completed_work[work_index] = (work_index, i)

                    # send a new work to the worker
                    work = work_to_complete[work_index]
                    comm.send(work_index, dest=i, tag=101)
                    comm.send(work, dest=i, tag=1)

                    # update the simulation index.
                    work_index += 1

    # collect which simulations are still running, wait for them to finish.
    work_not_done = [n for n in completed_work if isinstance(n, tuple)]

    for sim_index, compute_node in work_not_done:
        completed_work_index = comm.recv(source=compute_node, tag=101)
        letter = comm.recv(source=compute_node, tag=102)
        completed_work[completed_work_index] = letter

    return completed_work
