from parallelpy.parallel_evaluate import Work, Letter, batch_complete_work, clean_up_batch_tools
import uuid

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
    work = [Hello_World(i) for i in range(10)]

    for w in work: print(w)

    batch_complete_work(work)

    for w in work: print(w)
    clean_up_batch_tools()

