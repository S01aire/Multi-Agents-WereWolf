from environment.environment import environment
from environment.settings import Role, GamePhase
from logs.logging_config import setup_logger

logger = setup_logger('wolf')

async def check_killed_player_tonight() -> str:
    '''
    检查今晚队友选择杀害的目标，作为自己的行动参考。
    如果今晚没有玩家被杀，则返回空字符串。
    Args:
        None
    Returns:
        str: 今晚被杀的玩家
    '''
    phase = await environment.get_phase()
    if phase != GamePhase.NIGHT:
        logger.warning('狼人的检查今晚被杀的玩家工具只能在夜晚使用')
        return '狼人的检查今晚被杀的玩家工具只能在夜晚使用'

    target_id = await environment.get_player_killed_tonight()
    if target_id is None:
        return '你已经使用了check_killed_player_tonight工具，今晚没有玩家被杀害。'
    return f'你已经使用了check_killed_player_tonight工具，今晚队友选择杀害目标为{target_id}，作为自己的行动参考。'


async def kill(self_id: str, target_id: str) -> str:
    '''
    选择杀害目标。
    注意：如果你今晚选择杀害目标玩家，必须使用该工具。
    注意：该工具只能在晚上行动阶段使用，不能在发言和投票阶段使用。
    Args:
        self_id: 玩家id(系统自动注入，无需手动传入)
        target_id: 目标玩家id
    Returns:
        str: 杀害目标的结果
    '''
    phase = await environment.get_phase()
    if phase != GamePhase.NIGHT:
        logger.warning('狼人的杀害目标工具只能在夜晚使用')
        return '狼人的杀害目标工具只能在夜晚使用'

    if '=' in target_id:
        # 处理键值对格式：target_id="playerA" -> playerA
        target_id = target_id.split('=', 1)[1].strip().strip('"').strip("'")
    else:
        # 处理普通字符串，去除引号和空格
        target_id = target_id.strip().strip('"').strip("'")
    await environment.set_player_killed_tonight(target_id)
    await environment.add_player_memory(self_id, f'你将{target_id}作为杀害目标。')
    return f'你今晚选择杀害的目标为{target_id}，进入最终回答阶段。'