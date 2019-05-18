import sys
from time import sleep, time
import random
import uuid
import math
import time

from ParallelPy.parallelpy.parallel_evaluate import Work, Letter, batch_complete_work_multi_node, clean_up_batch_tools_multi_node

class Hello_World(Work):
    def __init__(self, id):
        self.id = id
        self.name = uuid.uuid1()
        self.work = None

    def __repr__(self):
        return "Hello my id is: %d and my work is %s " %(self.id, str(self.work))

    def compute_work(self):
        self.work = self.name

    def write_letter(self):
        return Letter(self.work, self.id)

    def open_letter(self, letter):
        self.work = letter.get_data()

if __name__ == '__main__':
    for i in range(10):
        work = [Hello_World(i) for i in range(2000)]
        t0 = time.time()

        batch_complete_work_multi_node(work)
        print("Took %.2f" % (time.time() - t0))

    clean_up_batch_tools_multi_node()



