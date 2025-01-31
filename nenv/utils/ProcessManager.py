from nenv.utils.KillableThread import KillableThread
from typing import Callable, Union, Any


class ProcessManager:
    """
        This class helps us to set time-out for a process.
    """
    return_val: Any             #: Return value of the process
    timeout: float              #: Timeout in terms of seconds
    timed_out: bool             #: The process is timed-out or not
    exception: Exception        #: Exception if it occurs
    has_exception: bool         #: If any exception is occurred, or not
    process: Callable           #: Process will be called
    thread: KillableThread      #: Thread object

    def __init__(self):
        """
            Constructor
        """

        # Default values
        self.return_val = None
        self.timeout = 0.
        self.time_outed = False
        self.process = lambda args: {}
        self.exception = None
        self.has_exception = False

    def _run(self, args: Union[list, dict, None], return_dict: dict):
        """
            This method is a wrapper to run the process with given arguments. It also handles the exception if it
            occurs.

            :param args: Given arguments as a list, dictionary or none
            :param return_dict: Return dictionary
            :return: None
        """

        # Handle different kind of arguments.
        if not args:
                return_dict["return_val"] = self.process()
        elif isinstance(args, list):
                return_dict["return_val"] = self.process(*args)
        else:
                return_dict["return_val"] = self.process(**args)
        """
        except Exception as e:  # Keep the exception
            return_dict["exception"] = e
            return_dict["has_exception"] = True
        """

    def run(self, process: Callable, timeout: float, args: Union[list, dict, None] = None) -> object:
        """
            This method calls the process with given arguments by setting a timeout. It returns the output of the
            process. If the process is killed due to the timeout, timed_out variable becomes true.

            It also handles any exception occurred. The occurred exception is also kept in this object.

            :param process: The process will be called
            :param timeout: Timeout in terms of seconds
            :param args: Given arguments as a list, dictionary or none
            :return: Return value of the process
        """
        # Initial values
        self.return_val = None
        self.timeout = timeout
        self.process = process
        self.time_outed = False
        self.has_exception = False

        # Return dictionary of the process
        return_dict = {}
        return_dict["return_val"] = None
        return_dict["exception"] = None
        return_dict["has_exception"] = False

        # Start the process with a timeout
        self.thread = KillableThread(target=self._run, args=(args, return_dict))
        self.thread.daemon = True

        self.thread.start()

        self.thread.join(timeout=self.timeout)

        # If timed-out
        if self.thread.is_alive():
            self.thread.kill()
            self.thread.join()
            self.time_outed = True

        # Get variables from the return dictionary
        self.return_val = return_dict["return_val"]
        self.exception = return_dict["exception"]
        self.has_exception = return_dict["has_exception"]

        return self.return_val  # Return value of the given process
