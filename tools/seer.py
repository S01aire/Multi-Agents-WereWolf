from environment.environment import environment
from environment.settings import Role, GamePhase
from logs.logging_config import setup_logger

logger = setup_logger('seer_tool')

async def check_identity(self_id: str, target_id: str) -> str:
    '''
    预言家检查目标id是否为狼人，注意：每晚只能使用一次！
    注意：该工具只能在晚上行动阶段使用，不能在发言和投票阶段使用。
    
    Args:
        self_id: 玩家id(系统自动注入，无需手动传入)
        target_id: 目标id

    Returns:
        str: 目标id的身份
    '''

    if '=' in target_id:
        # 处理键值对格式：target_id="playerA" -> playerA
        target_id = target_id.split('=', 1)[1].strip().strip('"').strip("'")
    else:
        # 处理普通字符串，去除引号和空格
        target_id = target_id.strip().strip('"').strip("'")

    phase = await environment.get_phase()
    if phase != GamePhase.NIGHT:
        logger.warning('预言家的检查身份工具只能在夜晚使用')
        return '预言家的检查身份工具只能在夜晚使用'

    if target_id not in (await environment.get_alive_players()):
        logger.error(f"目标id {target_id} 不存在")
        return f"目标id {target_id} 不存在"

    is_wolf = (await environment.get_role(target_id)) == Role.WOLF
    if is_wolf:
        await environment.add_player_memory(self_id, f'你的预言结果是：{target_id}是狼人。')
        return f"目标id {target_id} 是狼人，你今晚已查看过身份，无法再次使用此工具，进入最终回答阶段。"
    else:
        await environment.add_player_memory(self_id, f'你的预言结果是：{target_id}不是狼人。')
        return f"目标id {target_id} 不是狼人，你今晚已查看过身份，无法再次使用此工具，进入最终回答阶段。"