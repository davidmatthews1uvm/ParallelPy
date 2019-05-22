from __future__ import print_function
import multiprocessing
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

from multiprocessing import Pool

import warnings

from parallelpy.constants import *
from parallelpy.intra_node_dispatcher import main_loop as intra_loop
from parallelpy.mpi_deligate import main_loop as inter_loop
from parallelpy.utils import Work


"""
Global Variables
"""
# determines which type of parallelism we are using
PARALLEL_MODE = None
PARALLEL_MODE_MPI_INTRA = "INTRA"
PARALLEL_MODE_MPI_INTER = "INTER"
PARALLEL_MODE_POOL = "POOL"


"""
Variables specific to using a multiprocessing pool
"""
# the pool
pool = None

# keeps track of the number of processes in the pool
pool_count = None

# debug mode -- forces single threaded if using pool.
DEBUG = False

# if using a pool, limits the number of processes that the pool will use.
MAX_THREADS = None

"""
Variables specific to MPI Intra Node
"""
PROCS_PER_NODE = None

"""
Begin Public Methods
"""

comm = None
rank = None
size = None


def setup(target_mode=PARALLEL_MODE_POOL):
    global PARALLEL_MODE
    global comm, rank, size
    PARALLEL_MODE = target_mode

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

    # if we can't use MPI change to Pool
    if comm is None:
        PARALLEL_MODE = PARALLEL_MODE_POOL

    # if we are usign MPI, determine if we need to enter the service loop
    if PARALLEL_MODE == PARALLEL_MODE_MPI_INTRA:
        if rank > 0:
            intra_loop()
        else:
            _setup_intra_node()
    elif PARALLEL_MODE == PARALLEL_MODE_MPI_INTER and rank > 0:
        inter_loop()

    # return which mode we are using.
    return PARALLEL_MODE


def batch_complete_work(work_to_compute):
    if PARALLEL_MODE == PARALLEL_MODE_POOL:
        _batch_complete_work(work_to_compute, force_pool=True)

    elif PARALLEL_MODE == PARALLEL_MODE_MPI_INTER:
        _batch_complete_work(work_to_compute)

    elif PARALLEL_MODE == PARALLEL_MODE_MPI_INTRA:
        _batch_complete_work_multi_node(work_to_compute)


def cleanup():
    """
    Cleans up the batch tools that we used.
    :return: None
    """
    global PARALLEL_MODE
    if PARALLEL_MODE == PARALLEL_MODE_MPI_INTRA:
        _cleanup_batch_tools_multi_node()
    elif PARALLEL_MODE == PARALLEL_MODE_MPI_INTER:
        _cleanup_batch_tools()
    return


"""
Begin private helper methods.
"""


def _setup_intra_node():
    assert PARALLEL_MODE == PARALLEL_MODE_MPI_INTRA, "Cannot run _setup_intra_node() unless in PARALLEL_MODE_MPI_INTRA"
    assert isinstance(size, int)
    global PROCS_PER_NODE
    PROCS_PER_NODE = [None]*size
    PROCS_PER_NODE[0] = 0
    for i in range(1, size):
        PROCS_PER_NODE[i] = comm.recv(source=i, tag=SIZE_INFO)


def _cleanup_batch_tools():
    """
    If we used MPI, informs the workers that they can exit.
    :return: None
    """
    assert isinstance(size, int)
    if not (comm is None):
        for i in range(1, size):
            comm.send(-1, dest=i, tag=101)


def _cleanup_batch_tools_multi_node():
    """
    If we used MPI, informs the workers that they can exit.
    :return: None
    """
    if not (comm is None):
        assert isinstance(size, int)
        for i in range(1, size):
            comm.send(QUIT_MODE, dest=i, tag=MODE_MSG)


def _batch_complete_work_multi_node(work_to_complete):
    """
    Uses MPI to complete work across multiple nodes. Recieves letters from the completed distributed computation
     and has the local work open the letters,
    :param work_to_complete: A derived class from the Work class.
    :return: None
    """
    if comm is None:
        return _batch_complete_work(work_to_complete)
    if work_to_complete is []:
        return
    else:
        assert isinstance(work_to_complete[0], Work), \
            "Can only complete work which is a subclass of Work"
    global PROCS_PER_NODE
    # print(PROCS_PER_NODE)
    completed_work = [None] * len(work_to_complete)

    work_to_complete_new = sorted([(n, c, w) for n, (c, w) in enumerate([(w.cpus_requested(), w) for w in work_to_complete])], key=lambda x: x[1])

    work_index = 0  # the simulation we are currently working on
    total_work_count = len(work_to_complete)

    while work_index < total_work_count:
        # check all intra node dispatchers for newly completed work
        # print("Checking each node for newly completed work")
        for i in range(1, size):
            if comm.Iprobe(source=i, tag=RETURN_WORK):
                completed_work_index, letter = comm.recv(source=i, tag=RETURN_WORK)
                # letter = comm.recv(source=i, tag=RETURN_WORK)
                completed_work[completed_work_index] = letter
                PROCS_PER_NODE[i] += work_to_complete_new[completed_work_index][1]

        # check all intra node dispatchers to see if they need new work and if we have more work, give it to them.
        # print("Checking if any node needs more work")
        for i in range(1, size):
            if PROCS_PER_NODE[i] > 0:
                work_quant_requested = PROCS_PER_NODE[i]
                while work_quant_requested > 0:
                    if work_index >= total_work_count:
                        # print("Sent all work, waiting for all responses to return")
                        break
                    # print("Node %d has requested more work, sending work %d" % (i, work_index), flush=True)
                    # send the work

                    work_index_real, work_cpu_cnt, work = work_to_complete_new[work_index]
                    if work_quant_requested >= work_cpu_cnt:
                        comm.send((work_index, work), dest=i, tag=GET_WORK)

                        # store which worker is doing the job, and what work is being run
                        completed_work[work_index_real] = (work_index_real, i)

                        # update the work index
                        work_index += 1
                        work_quant_requested -= work_cpu_cnt
                PROCS_PER_NODE[i] = work_quant_requested

    # collect which simulations are still running, wait for them to finish.
    work_not_done = [n for n in completed_work if isinstance(n, tuple)]

    for work_index, i in work_not_done:
        # print("Waiting for work: %s" % str([n for n in completed_work if isinstance(n, tuple)]))
        completed_work_index, letter = comm.recv(source=i, tag=RETURN_WORK)
        # print("got work %d" % completed_work_index)
        # letter = comm.recv(source=compute_node, tag=RETURN_WORK)
        completed_work[completed_work_index] = letter
        PROCS_PER_NODE[i] += work_to_complete_new[completed_work_index][1]
    # print("Recieved all completed work!")

    # open the letters
    for work, letter in zip(work_to_complete, completed_work):
        work.open_letter(letter)
    # import time
    # time.sleep(1)
    return


def _batch_complete_work(work_to_complete, force_pool=False, force_mpi=False):
    """
    Does a given set of work in parallel using MPI or fork
    Prior to exiting from  your program, please call clean_up_batch_simulate() to clean up the other MPI processes.

    :param work_to_complete: An iterable of work to complete
    :param force_pool: Forces the use of multiprocessing instead of MPI
    :param force_mpi: Forces the use of MPI.
    :return: None
    """
    assert not (force_pool and force_mpi), "Can not force both MPI and fork at the same time!"
    assert isinstance(work_to_complete[0], Work)

    if force_pool:
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
