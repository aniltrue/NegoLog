import datetime
import math
import time
from typing import Union


class TournamentProcessMonitor:
    """
        This method monitors the tournament process for web-based UI
    """

    current_session: str                        #: The last completed session
    start_time: float                           #: Start time of the tournament in terms of seconds
    start_datetime: datetime.datetime           #: Start time of the tournament in terms of datetime
    last_update_time: float                     #: Last update time of the process in terms of seconds
    last_update_datetime: datetime.datetime     #: Last update time of the process in terms of datetime
    total_number_of_sessions: int               #: The total number of negotiation sessions
    completed_number_of_sessions: int           #: The number of completed negotiation sessions
    is_completed: bool                          #: Whether all negotiation sessions is completed, or not
    is_active: bool                             #: Whether the tournament process is active, or not

    def __init__(self):
        self.current_session = ""
        self.start_time = 0.
        self.last_update_time = 0.
        self.total_number_of_sessions = 0
        self.completed_number_of_sessions = 0
        self.start_datetime = None
        self.last_update_datetime = None
        self.is_completed = False
        self.is_active = False

    def initiate(self, number_of_sessions: int):
        """
            This method is called when the tournament starts.

        :param number_of_sessions: The total number of negotiation sessions
        :return: Nothing
        """
        self.start_time = time.time()
        self.start_datetime = datetime.datetime.now()
        self.last_update_time = time.time()
        self.last_update_datetime = datetime.datetime.now()

        self.total_number_of_sessions = number_of_sessions
        self.completed_number_of_sessions = 0
        self.is_completed = False
        self.is_active = True

        self.current_session = "Started"

    def update(self, session: str, session_elapsed_time: float) -> str:
        """
            This method is called when a negotiation session ends.

        :param session: The information of the completed negotiation session as a string
        :param session_elapsed_time: The elapsed time of the completed negotiation session in terms of seconds
        :return: Nothing
        """
        self.current_session = session
        self.completed_number_of_sessions += 1
        self.last_update_time = time.time()
        self.last_update_datetime = datetime.datetime.now()

        session_elapsed_time = datetime.timedelta(seconds=math.ceil(session_elapsed_time))

        return f"{session} - Session Real Time: {str(session_elapsed_time)} - Process: {'%.2f' % (self.completed_percentage * 100.)} % - Estimated Remaining Time: {str(self.estimated_remaining_time)} - Elapsed Time: {str(self.elapsed_time)} - Last Update: {str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}"

    def end(self) -> datetime.timedelta:
        """
            This method is called when all negotiation sessions are completed.

        :return: Nothing
        """

        self.is_completed = True
        self.current_session = "Waiting for loggers."
        self.last_update_time = time.time()
        self.last_update_datetime = datetime.datetime.now()

        return datetime.timedelta(seconds=math.ceil(time.time() - self.start_time))

    def close(self) -> datetime.timedelta:
        """
            This method is called when the tournament process ends.

        :return: Nothing
        """
        self.is_completed = True
        self.is_active = False
        self.current_session = "-"
        self.last_update_time = time.time()
        self.last_update_datetime = datetime.datetime.now()

        return datetime.timedelta(seconds=math.ceil(time.time() - self.start_time))

    @property
    def completed_percentage(self) -> float:
        """
            This method provides the percentage of the completed negotiation sessions

        :return: Nothing
        """
        return self.completed_number_of_sessions / self.total_number_of_sessions

    @property
    def estimated_remaining_time(self) -> Union[datetime.timedelta, None]:
        """
            This method estimates the remaining time to complete the tournament process.

            **Note**: It returns *None* when no negotiation session ends to avoid zero-division errors.

        :return: The estimated remaining time to complete the tournament process
        """
        completed_percentage = self.completed_number_of_sessions / self.total_number_of_sessions

        if completed_percentage == 0.:
            return None

        elapsed_time = self.last_update_time - self.start_time

        if self.completed_number_of_sessions > 0:
            remaining_time = math.ceil((1 - completed_percentage) * elapsed_time / completed_percentage)
        else:
            remaining_time = elapsed_time

        return datetime.timedelta(seconds=remaining_time)

    @property
    def elapsed_time(self) -> datetime.timedelta:
        """
            This method provides the total elapsed time while the tournament process is active.

        :return: Total elapsed time during tournament process
        """
        if not self.is_active:
            elapsed_time = self.last_update_time - self.start_time
        else:
            elapsed_time = time.time() - self.start_time

        return datetime.timedelta(seconds=math.ceil(elapsed_time))
