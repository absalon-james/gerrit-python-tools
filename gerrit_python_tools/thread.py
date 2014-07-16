import log
import Queue
import sys
import threading
import time

_stopped = threading.Event()
logger = log.get_logger()


class StoppableThread(threading.Thread):
    """
    Adds an threading.Event object to the thread object
    to signal that the thread should stop. Subclassed objects
    should check the event in each cycle.

    """

    def __init__(self):
        """
        Class constructor.
        Adds the event object as the _stop attribute.

        """
        super(StoppableThread, self).__init__()
        self._stop = threading.Event()

    def stop(self):
        """
        Sets the stop event.

        """
        self._stop.set()


class Worker(StoppableThread):
    """
    StoppableThread worker that is to be used with a WorkerPool.
    All Workers share the same queue in the same WorkerPool.

    """
    def __init__(self, queue):
        """
        Inits the worker queue

        @param queue - queue to pull tasks froms

        """
        super(Worker, self).__init__()
        self.queue = queue
        logger.debug("Worker thread started.")
        self.start()

    def run(self):
        """
        Run loop of the worker thread.
        Checks to see if the thread should stop.
        Tries to pull a tuple from the queue.
        The tuple should be in the form (function, args, kwargs)
        Sleeps if the queue is empty.

        """
        while True:
            # Check to see if we should stop
            if self._stop.isSet():
                logger.debug("Worker thread stopping.")
                break

            # Try to pull from the queue
            try:
                func, args, kwargs = self.queue.get_nowait()
                func(*args, **kwargs)
            except Queue.Empty:
                time.sleep(5)
                continue
            except Exception as e:
                logger.exception(e)


class WorkerPool(object):
    """
    Worker thread pool. Initializes the indicated number of worker threads
    with a shared queue. Very dumb pool that can't be changed after initting
    aside from adding tasks.

    """
    def __init__(self, numthreads):
        """
        Inits the WorkerPool

        @param numthreads - Integer number of worker threads.

        """
        self.queue = Queue.Queue()
        for _ in range(numthreads):
            Worker(self.queue)
        logger.debug("Event worker pool started with %s threads." % numthreads)

    def add_task(self, func, *args, **kwargs):
        """
        Adds a task in the form of a tuple to the queue.

        @param func - Function to run with args and kwargs
        @param *args - Args to send to function
        @param **kwargs - Kwargs to send to function

        """
        self.queue.put((func, args, kwargs))


def stop_threads(signal, frame):
    """
    Handles sig int. Iterates over stoppable threads and instructs
    them to stop in order to gracefully stop.

    """
    # Set _stopped flag to prevent multiple stoppings
    if _stopped.isSet():
        return

    logger.info("Stop Requested.")
    _stopped.set()

    # Get currently running stoppable threads
    threads = [t for t in threading.enumerate()
               if isinstance(t, StoppableThread)]
    logger.info("Stopping %s thread(s)." % len(threads))

    # Instruct threads they should stop
    for t in threads:
        t.stop()

    # Wait for threads to stop
    for t in threads:
        t.join()

    logger.info("Stopped all threads. Exiting.")

    # Exit successfully
    sys.exit(0)
