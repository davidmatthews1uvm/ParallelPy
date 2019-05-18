from __future__ import print_function
import multiprocessing

from multiprocessing import Pool

import warnings
from abc import ABCMeta, abstractmethod

import numpy as np
from ParallelPy.parallelpy.constants import *
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

    def cpus_requested(self):
        return 1

    def complete_work(self, serial=False):
        """
        Completes the required work, and generates a letter to send back to the dispatcher.
        :return: A letter to be sent.
        """
        self.compute_work(serial=serial)
        return self.write_letter()

    def compute_work(self, serial=False):
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

def batch_complete_work_multi_node(work_to_complete):
    """
    Uses MPI to complete work across multiple nodes. Recieves letters from the completed distributed coNmputation and has the local work to open the letters/
    :param work_to_complete: A derived class from the Work class.
    :return: None
    """
    if (comm is None):
        return batch_complete_work(work_to_complete)
    if work_to_complete is []:
        return
    else:
        assert isinstance(work_to_complete[0], Work), \
            "Can only complete work which is a subclass of Work"

    completed_work = [None] * len(work_to_complete)

    work_to_complete_new = sorted([(n,c,w) for n, (c,w) in enumerate([(w.cpus_requested(), w) for w in work_to_complete])], key=lambda x: x[1])

    work_index = 0  # the simulation we are currently working on
    total_work_count = len(work_to_complete)

    # inform all workers to start requesting work
    for i in range(1, size):
        comm.send(EXIT_IDLE_MODE, dest=i, tag=MODE_MSG)
        # print("sent exit idle mode msg to %d" % i)

    while work_index < total_work_count:
        # check all intra node dispatchers for newly completed work
        # print("Checking each node for newly completed work")
        for i in range(1, size):
            if comm.Iprobe(source=i, tag=RETURN_WORK):
                completed_work_index, letter  = comm.recv(source=i, tag=RETURN_WORK)
                # letter = comm.recv(source=i, tag=RETURN_WORK)
                completed_work[completed_work_index] = letter

        # check all intra node dispatchers to see if they need new work and if we have more work, give it to them.
        # print("Checking if any node needs more work")
        for i in range(1, size):
            if comm.Iprobe(source=i, tag=NEED_WORK):

                # recieve the request
                work_quant_requested = comm.recv(source=i, tag=NEED_WORK)
                while (work_quant_requested > 0):
                    if work_index >= total_work_count:
                        # print("Sent all work, waiting for all responses to return")
                        break
                    # print("Node %d has requested more work, sending work %d" % (i, work_index), flush=True)
                    # send the work

                    work_index_real, work_cpu_cnt, work = work_to_complete_new[work_index]
                    if (work_quant_requested >= work_cpu_cnt):
                        comm.send((work_index, work), dest=i, tag=GET_WORK)

                        # store which worker is doing the job, and what work is being run
                        completed_work[work_index_real] = (work_index_real, i)

                        # update the work index
                        work_index += 1
                        work_quant_requested -= work_cpu_cnt
                    else:
                        comm.send(None, dest=i, tag=GET_WORK)

    # inform all workers to stop asking for work
    for i in range(1, size):
        comm.send(ENTER_IDLE_MODE, dest=i, tag=MODE_MSG)

    # collect which simulations are still running, wait for them to finish.
    work_not_done = [n for n in completed_work if isinstance(n, tuple)]

    for sim_index, compute_node in work_not_done:
        # print("Waiting for work %d from node %d" % (sim_index, compute_node ))
        completed_work_index, letter = comm.recv(source=compute_node, tag=RETURN_WORK)
        # letter = comm.recv(source=compute_node, tag=RETURN_WORK)
        completed_work[completed_work_index] = letter
    # print("Recieved all completed work!")

    # open the letters
    for work, letter in zip(work_to_complete, completed_work):
        work.open_letter(letter)
    import time
    time.sleep(1)
    return


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

    res = [pool.apply_async(w.complete_work, (True,)) for w in work_to_complete]
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
