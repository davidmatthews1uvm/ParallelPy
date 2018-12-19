from parallelpy.parallel_evaluate import batch_complete_work, clean_up_batch_tools
from hello_world_base import Hello_World, ITERATION_COUNT

if __name__ == '__main__':
    work = [Hello_World(i) for i in range(ITERATION_COUNT)]

    for w in work: print(w)

    batch_complete_work(work)

    for w in work: print(w)
    clean_up_batch_tools()

