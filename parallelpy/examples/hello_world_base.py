from parallelpy.parallel_evaluate import Work, Letter 
import uuid

ITERATION_COUNT = 10
class Hello_World(Work):
    def __init__(self, id):
        self.id = id
        self.name = uuid.uuid1()
        self.work = None

    def __repr__(self):
        return "Hello my id is: %d and my work is %s " %(self.id, str(self.work))

    def compute_work(self, work_directory=None):
        self.work = self.name

    def write_letter(self):
        return Letter(self.work, self.id)

    def open_letter(self, letter):
        self.work = letter.get_data()
