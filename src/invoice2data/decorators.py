import time
import functools
import logging

logger = logging.getLogger(__name__)

def timeit(func):
    """
    Measures time taken by the given function.
    :param func: a function
    :return:
    """

    @functools.wraps(func)
    def inner(*args, **kwargs):
        CRED = '\033[91m'
        CEND = '\033[0m'
        func_name = func.__name__ + '()'
        t1 = time.time()

        result = func(*args, **kwargs)
        t2 = time.time()
        total_time_taken = t2-t1
        logger.error(CRED + f'****************** time_taken -- {func_name: <30}-- {total_time_taken:.2f}s **********************' + CEND)
        #print(CRED + f'****************** time_taken -- {func_name: <30}-- {total_time_taken:.2f}s **********************' + CEND)
        return result

    return inner