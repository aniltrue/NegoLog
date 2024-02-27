import sys
import threading


class KillableThread(threading.Thread):
    """
        This class is a subclass of built-in Thread class. It provides a kill function to terminate the thread.
    """
    __killed: bool    #: Killed flag

    def __init__(self, *args, **kwargs):
        """
            Constructor
        """
        threading.Thread.__init__(self, *args, **kwargs)
        self.__killed = False     # Set flag as false at the beginning

    def start(self):
        """
            Override the run method in the Thread class to replace with our one.

            :return: Nothing
        """
        self.__killed = False
        self.__run_backup = self.run
        self.run = self.__run
        threading.Thread.start(self)

    def __run(self):
        """
            Start tracing before calling the target method

            :return: Nothing
        """
        sys.settrace(self.globaltrace)
        self.__run_backup()
        self.run = self.__run_backup

    def globaltrace(self, frame, event, arg):
        """
            Global tracing
        """
        if event == 'call':
            return self.localtrace

        return None

    def localtrace(self, frame, event, arg):
        """
            Local tracing. Kill the thread when kill() method is called.
        """
        if self.__killed and event == 'line':
            raise SystemExit()

        return self.localtrace

    def kill(self):
        """
            This method terminates/kills the thread.

            Do not forget to call *join()* method after killing.

            :return: Nothing
        """
        self.__killed = True

    @property
    def killed(self) -> bool:
        """
            This method returns the killed state

            :return: Whether the thread is killed, or not
        """

        return self.__killed
