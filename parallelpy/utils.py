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
