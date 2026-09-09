import importlib
import inspect
from nenv.Agent import AgentClass, AbstractAgent
from nenv.OpponentModel import OpponentModelClass, AbstractOpponentModel
from nenv.logger import LoggerClass, AbstractLogger


def _load_class(class_path, default_module, base_class):
    """Validate a short or dotted class name before returning a concrete class."""
    if not isinstance(class_path, str) or not class_path.strip():
        raise ValueError("Component paths must be nonempty strings.")
    module_path, separator, name = class_path.rpartition(".")
    if not separator:
        module_path, name = default_module, class_path
    value = getattr(importlib.import_module(module_path), name)
    if not inspect.isclass(value) or not issubclass(value, base_class) or inspect.isabstract(value):
        raise TypeError(f"{class_path} must be a concrete {base_class.__name__} subclass.")
    return value


def load_agent_class(class_path: str) -> AgentClass:
    """
        This method loads agent in runtime.

        Note that class must be a subclass of **AbstractAgent**

        :param class_path: Path to agent
        :return: The class of the agent
    """
    return _load_class(class_path, "agents", AbstractAgent)


def load_estimator_class(class_path: str) -> OpponentModelClass:
    """
        This method loads opponent model in runtime.

        Note that class must be a subclass of **AbstractOpponentModel**

        :param class_path: Path to opponent model
        :return: The class of the opponent model
    """
    return _load_class(class_path, "nenv.OpponentModel", AbstractOpponentModel)


def load_logger_class(class_path: str) -> LoggerClass:
    """
        This method loads logger in runtime.

        Note that class must be a subclass of **AbstractLogger**

        :param class_path: Path to logger
        :return: The class of the logger
    """
    return _load_class(class_path, "nenv.logger", AbstractLogger)
