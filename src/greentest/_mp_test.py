import sys
from time import sleep


def test_no_args():
    print(test_no_args.__name__)
    sleep(1)
    sys.exit(10)


def test_queues(r_q, w_q):
    sleep(1)
    print(r_q.get(timeout=5))
    sleep(1)
    w_q.put(test_queues.__name__, timeout=5)
    sleep(1)
    sys.exit(10)
