from enum import Enum

class GamePhase(Enum):
    WAITING = "waiting"   # 等待玩家加入/准备
    PREPARING = "preparing"   # 准备阶段
    NIGHT = "night"       # 夜晚行动
    DAY = "day"           # 白天公布结果 + 讨论
    VOTING = "voting"     # 投票阶段
    ENDED = "ended"       # 游戏结束

class Role(Enum):
    WOLF = "wolf"   # 狼人
    VILLAGER = "villager"   # 村民
    SEER = "seer"   # 预言家
    WITCH = "witch"   # 女巫
    HUNTER = "hunter"   # 猎人

all_roles = [Role.WOLF, Role.WOLF, Role.VILLAGER, Role.VILLAGER, Role.SEER, Role.WITCH, Role.HUNTER]

ROLE_INSTRUCTIONS = {
    Role.WOLF: '''你是狼人！你的目标是：
1. 夜晚与其他狼人讨论并选择击杀目标
2. 白天伪装成好人，避免被投票出局
3. 通过私聊 God 来击杀玩家
4. 记住：不要暴露身份，要表现得像好人
胜利条件：当狼人的数量大于好人的数量时，你获胜
失败条件：当场上狼人数量为0时，你失败
    ''',
    Role.VILLAGER: '''你是村民！你的目标是：
1. 白天分析场上形势，找出你认为可能是狼人的玩家，并进行投票
2. 分析每个玩家的发言，找出其中可疑的地方，在自己发言时和大家分享
胜利条件：当场上狼人数量为0时，你获胜
失败条件：当场上狼人数量大于好人的数量时，你失败
    ''',
    Role.SEER: '''你是预言家！你的目标是：
1. 夜晚通过私聊 God 来查看玩家身份
2. 白天时可以选择是否公开自己的身份，并告知预言结果
3. 白天分析场上形势，找出你认为可能是狼人的玩家，并进行投票
4. 分析每个玩家的发言，找出其中可疑的地方，在自己发言时和大家分享
5. 尽量保护自己的安全
胜利条件：当场上狼人数量为0时，你获胜
失败条件：当场上狼人数量大于好人的数量时，你失败
    ''',
    Role.WITCH: '''你是女巫！你的目标是：
1. 你有一瓶毒药和一瓶解药，毒药可以杀死你指定的玩家，如果当晚有玩家被杀，
你可以选择使用解药解救，但每晚只能使用一瓶药水，夜晚通过私聊 God 来使用药水
2. 白天分析场上形势，找出你认为可能是狼人的玩家，并进行投票
3. 分析每个玩家的发言，找出其中可疑的地方，在自己发言时和大家分享
胜利条件：当场上狼人数量为0时，你获胜
失败条件：当场上狼人数量大于好人的数量时，你失败
    '''
}

class Action6(Enum):
    WOLF1_KILL = 'wolf1_kill'
    WOLF2_KILL = 'wolf2_kill'
    SEER_SEE = 'seer_see'
    WITCH_POISON = 'witch_poison'
    WITCH_CURE = 'witch_cure'
    END_NIGHT = 'end_night'
    
