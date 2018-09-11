from __future__ import print_function
import multiprocessing

from multiprocessing import Pool

import warnings
from abc import ABCMeta, abstractmethod

import numpy as np

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

    def complete_work(self):
        """
        Completes the required work, and generates a letter to send back to the dispatcher.
        :return: A letter to be sent.
        """
        self.compute_work()
        return self.write_letter()

    def compute_work(self):
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


def batch_complete_work(work_to_complete, max_processes=None, force_fork=False, force_mpi=False):
    """
    Does a given set of work in parallel using MPI or fork
    Prior to exiting from  your program, please call clean_up_batch_simulate() to clean up the other MPI processes.

    :param work_to_complete: An iterable of work to complete
    :param max_processes: If not using MPI, forces the maximum number of processes that can run at a given time.
    :param force_fork: Forces the use of multiprocessing instead of MPI
    :param force_mpi: Forces the use of MPI.
    :return: An array of the given work
    """
    assert not (force_fork and force_mpi), "Can not force both MPI and fork at the same time!"
    assert isinstance(work_to_complete[0], Work)

    if comm is None or force_fork:
        assert force_mpi is False, "Failed to use MPI as requested"
        # run as pool
        if max_processes is None:
            try:
                max_processes = multiprocessing.cpu_count()
            except NotImplementedError:
                warnings.warn("Unable to determine how many CPU's are avaiable, using 1 process.")
                max_processes = 1
        letters = _batch_complete_work_via_pool(work_to_complete, max_processes)

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
    print (res[0].get())
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
