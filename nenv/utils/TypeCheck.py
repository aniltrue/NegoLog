from typing import TypeVar, Generic, Any

T = TypeVar('T')


class TypeCheck(Generic[T]):
    """
        This class checks the given type *T*.
    """
    def check(self, x: Any) -> bool:
        """
            Whether the given object *x* is an instance of the target class.

            :param x: Object that will be checked
            :return: Whether the given object *x* is an instance of the target class.
        """
        return isinstance(x, self.__orig_class__.__args__[0])  # type: ignore
