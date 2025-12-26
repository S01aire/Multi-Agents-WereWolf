import importlib
from typing import List, Callable

from environment.settings import Role


def load_tools(role: Role) -> List[Callable]:
    tools = []

    module_name = 'tools.common'
    module = importlib.import_module(module_name)
    check_alive_players = getattr(module, 'check_alive_players')
    tools.append(check_alive_players)
    get_history = getattr(module, 'get_history')
    tools.append(get_history)
    get_player_memory = getattr(module, 'get_player_memory')
    tools.append(get_player_memory)

    if role == Role.WOLF:
        module_name = 'tools.wolf'
        module = importlib.import_module(module_name)
        check_killed_player_tonight = getattr(module, 'check_killed_player_tonight')
        tools.append(check_killed_player_tonight)
        kill = getattr(module, 'kill')
        tools.append(kill)
    elif role == Role.SEER:
        module_name = 'tools.seer'
        module = importlib.import_module(module_name)
        check_identity = getattr(module, 'check_identity')
        tools.append(check_identity)
    elif role == Role.WITCH:
        module_name = 'tools.witch'
        module = importlib.import_module(module_name)
        cure = getattr(module, 'cure')
        tools.append(cure)
        poison = getattr(module, 'poison')
        tools.append(poison)

    return tools

