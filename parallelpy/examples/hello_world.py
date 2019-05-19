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
        #t0 = time.time()
        #while (time.time() < t0+.0001):
        #    pass

    def write_letter(self):
        return Letter(self.work, self.id)

    def open_letter(self, letter):
        self.work = letter.get_data()

if __name__ == '__main__':
    setup(PARALLEL_MODE_MPI_INTER)

    i = 0
    while True:gi
        i += 1
        print(str(i))
        work = [Hello_World(i) for i in range(200)]
        t0 = time.time()

        batch_complete_work(work)
        print("Took %.2f" % (time.time() - t0))

    cleanup()



