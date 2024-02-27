from nenv.Agent import AbstractAgent


# Process Name and corresponding agent methods. All methods should take agent object (AbstractAgent) and **kwargs.
AGENT_OPERATIONS = {
    "Initiate": lambda agent, **kwargs: agent.initiate(**kwargs),
    "Act": lambda agent, **kwargs: agent.act(**kwargs),
    "Receive Bid": lambda agent, **kwargs: agent.receive_bid(**kwargs),
    "Terminate": lambda agent, **kwargs: agent.terminate(**kwargs)
}
"""
    Lambda functions for agent operations.
"""


def session_operation(agent: AbstractAgent, process_name: str, **kwargs) -> dict:
    """
        This method helps to wrap the agent method to use them with process manager.

        :param agent: Agent
        :param process_name: Name of the agent's process
        :param kwargs: Additional arguments
        :return: A dictionary which contains the returned value and the agent object.
    """
    return AGENT_OPERATIONS[process_name](agent, **kwargs)
