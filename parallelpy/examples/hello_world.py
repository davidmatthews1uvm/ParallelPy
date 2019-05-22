import sys
from time import sleep, time
import random
import uuid
import math
import time

from parallelpy.parallel_evaluate import PARALLEL_MODE_MPI_INTRA, PARALLEL_MODE_MPI_INTER, PARALLEL_MODE_POOL, Work, Letter, setup, batch_complete_work, cleanup

class Hello_World(Work):
    def __init__(self, id):
        self.id = id
        self.name = uuid.uuid1()
        self.work = None

    def __repr__(self):
        return "Hello my id is: %d and my work is %s " %(self.id, str(self.work))

    def compute_work(self, serial=False):
        self.work = self.name

    def write_letter(self):
        return Letter(self.work, self.id)

    def open_letter(self, letter):
        self.work = letter.get_data()

    def validate(self):
        assert self.name == self.work

if __name__ == '__main__':

    print("Testing: %s" % setup(PARALLEL_MODE_MPI_INTER))
    TEST_LENGTH = 1000
    for n in range(TEST_LENGTH):

        work = [Hello_World(i) for i in range(1000)]

        t0 = time.time()
        batch_complete_work(work)
        t1 = time.time()
        for w in work:
            w.validate()

        print("%10d took %.2f" %(n, t1-t0) )

    cleanup()



