from typing import Dict, List, Set, TypeVar, Any, Union, Tuple, Optional
from nenv.utils.TypeCheck import TypeCheck

import pandas as pd

LogRow = TypeVar('LogRow', bound=Dict[str, Dict[str, Any]])
"""
    Type variable of log row
"""


def update(source: LogRow, target: LogRow):
    """
        This method updates the **`Source`** with given **`Target`**

        :param source: Source to be updated
        :param target: Target
        :return: Nothing
    """
    for sheet_name in target:
        if sheet_name not in source:
            source[sheet_name] = target[sheet_name]
        else:
            source[sheet_name].update(target[sheet_name])


class LogRowIterator:
    """
        This class helps to iterate over log rows index by index. You can iterate over ExcelLog object.

        :Example:
            Example for a loop in logs

            >>> for index, row : log:
            >>>     ...
    """

    def __init__(self, log_rows: Dict[str, List[Dict[str, Any]]]):
        self.log_rows = log_rows
        self.index = 0

    def __next__(self) -> (int, LogRow):
        if self.index < len(self.log_rows):

            row: LogRow = {}

            for sheet_name in self.log_rows:
                if len(self.log_rows[sheet_name]) <= self.index:
                    row[sheet_name] = {}
                else:
                    row[sheet_name] = self.log_rows[sheet_name][self.index]

            self.index += 1

            return self.index - 1, row

        raise StopIteration


class ExcelLog:
    """
        This class helps to logging into Excel file
    """
    log_rows: Dict[str, List[Dict[str, Any]]]  #: Log rows for each sheet
    sheet_names: Set[str]                      #: List of sheet names

    def __init__(self, sheet_names: Union[Set[str], List[str], None] = None, file_path: str = None):
        """
            Constructor

            :param sheet_names: Set of sheet names
            :param file_path: File path to read, default None
        """
        self.log_rows = {}

        self.sheet_names = set()

        if sheet_names is not None:
            self.sheet_names = set(sheet_names)
            self.log_rows = {sheet_name: [] for sheet_name in sheet_names}

        if file_path is not None:
            self.load(file_path)

    def load(self, file_path: str):
        """
            Load from file

            :param file_path: File path
            :return: Nothing
        """
        xlsx = pd.ExcelFile(file_path)

        self.sheet_names = set(xlsx.sheet_names)

        xlsx.close()

        for sheet_name in self.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            self.log_rows[sheet_name] = [row for _, row in df.to_dict('index').items()]

    def save(self, file_path: str):
        """
            Save to file

            :param file_path: File path
            :return: Nothing
        """
        with pd.ExcelWriter(file_path) as writer:
            for sheet_name in self.sheet_names:
                df = pd.DataFrame(self.log_rows[sheet_name])

                df.to_excel(writer, sheet_name=sheet_name, index=False)

    def to_data_frame(self, sheet_name: Optional[str] = None) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """
            Convert log rows to dictionary of data frames

            :return: Dictionary of data frames
        """

        if sheet_name is not None:
            return pd.DataFrame(self.log_rows[sheet_name])

        return {
            sheet_name: pd.DataFrame(self.log_rows[sheet_name]) for sheet_name in self.log_rows
        }

    def __update_sheet_names(self, row: LogRow):
        """
            Create sheets if not exists

            :param row: Log row
            :return: Nothing
        """
        for sheet_name in row:
            if sheet_name not in self.sheet_names:
                self.sheet_names.add(sheet_name)
                self.log_rows[sheet_name] = []

    def append(self, row: LogRow):
        """
            Append into logs

            :param row: Log row
            :return: Nothing
        """
        self.__update_sheet_names(row)

        for sheet_name in self.sheet_names:
            if sheet_name in row:
                self.log_rows[sheet_name].append(row[sheet_name])
            else:
                self.log_rows[sheet_name].append({})

    def update(self, row: LogRow, row_index: int = -1):
        """
            Update a log row

            :param row: New log row
            :param row_index: Index of row
            :return: Nothing
        """
        self.__update_sheet_names(row)

        if row_index == -1:
            for sheet_name in row:
                row_index = max(row_index, len(self.log_rows[sheet_name]) - 1)

        for sheet_name in row:
            if row_index < len(self.log_rows[sheet_name]):
                self.log_rows[sheet_name][row_index].update(row[sheet_name])
            else:
                while row_index >= len(self.log_rows[sheet_name]):
                    self.log_rows[sheet_name].append({})

                self.log_rows[sheet_name][row_index].update(row[sheet_name])

    def __iter__(self):
        """
            You can iterate over log rows index by index.

            :Example:
                Example for a loop in logs

                >>> for index, row : log:
                >>>     ...

            :return: LogRowIterator that will be called in for-loop.
        """
        return LogRowIterator(self.log_rows)

    def __getitem__(self, key: Union[int, Tuple[int, str]]) -> Union[LogRow, Dict[str, Any]]:
        if isinstance(key, int):
            row: LogRow = {}

            for sheet_name in self.log_rows:
                if len(self.log_rows[sheet_name]) <= key:
                    row[sheet_name] = {}
                else:
                    row[sheet_name] = self.log_rows[sheet_name][key]

            return row
        else:
            return self.log_rows[key[1]][key[0]]

    def __setitem__(self, key: Union[int, Tuple[int, str], Tuple[int, str, str]], value: Union[LogRow, Dict[str, Any], Any]):
        if isinstance(key, int):
            assert TypeCheck[LogRow]().check(value), "If `key` is Integer, `value` must be LogRow"

            for sheet_name in value:
                self.log_rows[sheet_name][key].update(value[sheet_name])
        elif TypeCheck[Tuple[int, str]]().check(key):
            assert TypeCheck[Dict[str, Any]]().check(key), "If `key` is (int, str), `value` must be Dict[str, Any]"

            self.log_rows[key[1]][key[0]].update(value)

        elif TypeCheck[Tuple[int, str, str]]().check(key):
            self.log_rows[key[1]][key[0]][key[2]] = value

        else:
            raise Exception("Unknown `key` Type.")

    def __len__(self):
        """
            This method provides the number of log rows.

            :return: The number of log rows
        """
        for key, values in self.log_rows.items():
            return len(values)

        return 0
