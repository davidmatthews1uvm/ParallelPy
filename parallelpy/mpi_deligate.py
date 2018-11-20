from __future__ import print_function
import sys

from mpi4py import MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()
assert rank != 0, "delegate can not have a rank of 0"

from examples.hello_world import Hello_World

while True:
    work_id = comm.recv(source=0, tag=101)
    if work_id == -1:
        exit()

    # get the work that needs to be completed
    work = comm.recv(source=0, tag=1)

    # do the work, and get the letter to send.
    letter = work.complete_work()

    # send the results.
    comm.send(work_id, dest=0, tag=101)
    comm.send(letter, dest=0, tag=102)

    # delete the variables
    del work_id
    del work
    del letter

