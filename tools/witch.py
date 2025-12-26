from environment.environment import environment
from environment.settings import Role, GamePhase
from logs.logging_config import setup_logger

logger = setup_logger('witch')

async def cure(self_id: str) -> str:
    '''
    使用解药解救今晚被杀害的目标,你仅有一瓶解药，且每个晚上只能使用解药或毒药中的一个。
    注意：如果你今晚选择解救目标玩家，必须使用该工具。
    注意：该工具只能在晚上行动阶段使用，不能在发言和投票阶段使用。
    Args:
        self_id: 玩家id(系统自动注入，无需手动传入)
    Returns:
        str: 使用解药的结果
    '''

    phase = await environment.get_phase()
    if phase != GamePhase.NIGHT:
        logger.warning('女巫的使用解药工具只能在夜晚使用')
        return '女巫的使用解药工具只能在夜晚使用'

    target_id = await environment.get_player_killed_tonight()
    cure_status = await environment.get_cure_status()
    if cure_status == 'used':
        logger.error('解药已使用，无法再次使用。')
        return '解药已使用，无法再次使用。'
    if target_id is None:
        logger.error('今晚没有玩家被杀害，无法使用解药。')
        environment.add_player_memory(self_id, '今晚没有玩家被杀害，无法使用解药。')
        return '今晚没有玩家被杀害，无法使用解药。'
    
    await environment.use_cure()
    await environment.set_cure_tonight(True)
    await environment.set_player_killed_tonight(None)
    await environment.add_player_memory(self_id, f'你已使用了解药，解救了{target_id}。')
    return f'你使用解药解救了{target_id}，进入最终回答阶段。'

async def poison(self_id: str, target_id: str) -> str:
    '''
    使用毒药杀害指定目标,你仅有一瓶毒药，且每个晚上只能使用解药或毒药中的一个。
    注意：如果你今晚选择毒杀目标玩家，必须使用该工具。
    注意：该工具只能在晚上行动阶段使用，不能在发言和投票阶段使用。
    Args:
        self_id: 玩家id(系统自动注入，无需手动传入)
        target_id: 目标玩家id
    Returns:
        str: 使用毒药的结果
    '''

    phase = await environment.get_phase()
    if phase != GamePhase.NIGHT:
        logger.warning('女巫的使用毒药工具只能在夜晚使用')
        return '女巫的使用毒药工具只能在夜晚使用'

    if '=' in target_id:
        # 处理键值对格式：target_id="playerA" -> playerA
        target_id = target_id.split('=', 1)[1].strip().strip('"').strip("'")
    else:
        # 处理普通字符串，去除引号和空格
        target_id = target_id.strip().strip('"').strip("'")

    poison_status = await environment.get_poison_status()
    if poison_status == 'used':
        logger.error('毒药已使用，无法再次使用。')
        return '毒药已使用，无法再次使用。'
    await environment.use_poison(target_id)
    await environment.set_player_posioned_tonight(target_id)
    await environment.add_player_memory(self_id, f'你已使用了毒药，杀害了{target_id}。')
    return f'你使用毒药杀害了{target_id}，进入最终回答阶段。'