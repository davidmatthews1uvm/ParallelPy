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


def main_loop():

    from mpi4py import MPI
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    assert rank != 0, "delegate can not have a rank of 0"

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


if __name__ == "__main__":
    main_loop()
