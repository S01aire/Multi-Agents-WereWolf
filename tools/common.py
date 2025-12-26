from environment.environment import environment
from environment.settings import Role
from typing import List

async def check_alive_players() -> str:
    '''
    检查当前存活玩家，请不要多次使用该工具。

    Args:
        None

    Returns:
        str: 当前存活玩家
    '''
    alive_players = await environment.get_alive_players()
    if not alive_players:
        return '你已经使用了check_alive_players工具，当前没有存活玩家'

    return '你已经使用了check_alive_players工具，当前存活玩家：' + ', '.join(alive_players)


async def get_history() -> str:
    '''
    获取游戏历史记录，包括各个玩家的发言和行动

    Args:
        None

    Returns:
        str: 历史记录
    '''
    history = await environment.get_history()
    if not history:
        return '你已经使用了get_history工具，当前没有历史记录'
    return f'你已经使用了get_history工具，游戏历史记录：\n' + '\n'.join(history)

async def get_player_memory(self_id: str) -> str:
    '''
    获取本局游戏中自己的记忆，包括自己私有的信息和行动。

    Args:
        self_id: 玩家id(系统自动注入，无需手动传入)

    Returns:
        str: 玩家记忆
    '''
    
    memory = await environment.get_player_memory(self_id)
    if not memory:
        return '你已经使用了get_player_memory工具，当前没有记忆'
    
    return f'你已经使用了get_player_memory工具，玩家记忆：\n' + '\n'.join(memory)

