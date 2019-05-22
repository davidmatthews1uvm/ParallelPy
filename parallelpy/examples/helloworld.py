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

import uuid
import time

from parallelpy.parallel_evaluate import PARALLEL_MODE_MPI_INTRA, PARALLEL_MODE_MPI_INTER, PARALLEL_MODE_POOL, setup, batch_complete_work, cleanup
from parallelpy.utils import Work, Letter


class HelloWorld(Work):
    def __init__(self, id):
        self.id = id
        self.name = uuid.uuid1()
        self.work = None

    def __repr__(self):
        return "Hello my id is: %d and my work is %s " % (self.id, str(self.work))

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
    TEST_LENGTH = 1000000
    for n in range(TEST_LENGTH):

        work = [HelloWorld(i) for i in range(1000)]

        t0 = time.time()
        batch_complete_work(work)
        t1 = time.time()
        for w in work:
            w.validate()

        print("%10d took %.2f" % (n, t1-t0))

    cleanup()
