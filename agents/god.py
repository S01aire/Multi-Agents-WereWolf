from argparse import Action
import asyncio
import random
from enum import Enum
from typing import Dict, Set, List
from collections import Counter

from openagents.agents.worker_agent import WorkerAgent, EventContext, ChannelMessageContext

from environment.settings import GamePhase, Role, all_roles, ROLE_INSTRUCTIONS, Action6
from environment.environment import environment
from logs.logging_config import setup_logger

logger = setup_logger('world')

class GodAgent(WorkerAgent):
    default_agent_id = 'god'

    def __init__(self):
        super().__init__()
        
        self.players: List[str] = []
        self.players_num: int = 0
        self.max_players_num: int = 6
        self.roles: Dict[str, Role] = {}
        self.actions: Dict[Role, List[str]] = {     #角色 -> 玩家id列表
            Role.WOLF: [],
            Role.SEER: [],
            Role.WITCH: [],
            Role.HUNTER: []
        }    
        self.action_turn: Action6 = Action6.WOLF1_KILL
        self.round: int = 0
        self.speech_list: List[str] = []
        self.speech_turn: int = 0
        self.vote_result: List[str] = []

    async def on_startup(self):
        ws = self.workspace()
        await ws.channel('general').post('请等待玩家加入...')
        await ws.agent('QuickHelper7781').send('test')
        logger.info('GodAgent started')
        
        await environment.clear_environment()
        await environment.set_phase(GamePhase.WAITING)
        await environment.init_witch_items()


    async def on_channel_post(self, context: ChannelMessageContext):
        message = context.incoming_event.payload.get('content', {}).get('text', '')
        source_id = context.source_id

        if message.endswith('加入游戏') and (await environment.get_phase()) == GamePhase.WAITING:
            await self._handle_join(source_id)
            logger.info('%s joined the game', source_id)
        elif message.endswith('离开游戏') and (await environment.get_phase()) == GamePhase.WAITING:
            await self._handle_leave(source_id)
            logger.info('%s left the game', source_id)
        elif message.startswith('Speech'):
            speech = message.split(':', 1)[1].strip()
            logger.info(f'获取{source_id}的Speech:%s', speech)
            await environment.add_history(self.round, source_id, f'玩家{source_id}发言：{speech}')
            await self._start_speech()
        elif message.startswith('Vote'):
            vote = message.split(':', 1)[1].strip()

            if '=' in vote:
                vote = vote.split('=', 1)[1].strip().strip('"').strip("'")
            else:
                vote = vote.strip().strip('"').strip("'")

            alive_players = await environment.get_alive_players()
            if vote not in alive_players:
                logger.error('不能投票给已出局玩家，当前玩家%s的vote为%s，当前玩家列表为%s', source_id, vote, alive_players)
                await self._re_vote()
                return
            if vote == source_id:
                logger.error('不能投票给自己，当前玩家%s的vote为%s', source_id, vote)
                await self._re_vote()
                return

            self.vote_result.append(vote)
            logger.info('获取%s的Vote:%s', source_id, vote)
            await environment.add_history(self.round, source_id, f'玩家{source_id}投给了：{vote}')
            await self._start_vote()

    async def on_direct(self, context: EventContext):
        message = context.incoming_event.payload.get('content', {}).get('text', '')
        source_id = context.source_id

        ws = self.workspace()

        if message.startswith('Action'):
            match self.action_turn:
                case Action6.WOLF1_KILL:
                    if source_id == self.actions[Role.WOLF][0]:
                        self.action_turn = Action6.WOLF2_KILL
                        logger.info('进入狼人2阶段')
                        await self._start_actions()
                    else:
                        await ws.channel('general').post(f'ERROR:游戏进度出错，当前action_turn为{self.action_turn}，当前玩家{source_id}的action为{message}')
                        logger.error('游戏进度出错，当前action_turn为%s，当前玩家%s的action为%s', self.action_turn, source_id, message)
                case Action6.WOLF2_KILL:
                    if source_id == self.actions[Role.WOLF][1]:
                        self.action_turn = Action6.SEER_SEE
                        logger.info('进入预言家阶段')
                        await self._start_actions()
                case Action6.SEER_SEE:
                    if source_id == self.actions[Role.SEER][0]:
                        self.action_turn = Action6.WITCH_CURE
                        logger.info('进入女巫使用解药阶段')
                        await self._start_actions()
                case Action6.WITCH_CURE:
                    if source_id == self.actions[Role.WITCH][0]:
                        self.action_turn = Action6.WITCH_POISON
                        logger.info('进入女巫使用毒药阶段')
                        await self._start_actions()
                case Action6.WITCH_POISON:
                    if source_id == self.actions[Role.WITCH][0]:
                        self.action_turn = Action6.END_NIGHT
                        logger.info('进入夜晚结束阶段')
                        await self._start_actions()

        


    async def _handle_join(self, source_id):
        ws = self.workspace()

        self.players_num += 1
        self.players.append(source_id)
        await ws.channel('general').post(f'玩家{source_id}加入了游戏，当前玩家数量：{self.players_num}')

        if self.players_num == self.max_players_num:
            await ws.channel('general').post('游戏人数已满！')
            logger.info('游戏人数已满，即将开始游戏')
            await self._start_game()

    async def _handle_leave(self, source_id):
        ws = self.workspace()
        self.players_num -= 1
        self.players.remove(source_id)
        await ws.channel('general').post(f'玩家{source_id}离开了游戏，当前玩家数量：{self.players_num}')

    async def _start_game(self):
        await environment.set_phase(GamePhase.PREPARING)
        await environment.set_alive_players(self.players.copy())
        
        ws = self.workspace()
        logger.info('开始分配角色...')
        await ws.channel('general').post('游戏开始！开始分配角色...')
        
        players_list = self.players.copy()
        if len(players_list) != self.max_players_num:
            await ws.channel('general').post('玩家数量不足，游戏无法开始！')
            await environment.set_phase(GamePhase.WAITING)
            return
        random.shuffle(players_list)

        for i in range(len(players_list)):
            await environment.set_role(players_list[i], all_roles[i])
            self.roles[players_list[i]] = all_roles[i]

        for pid, role in self.roles.items():
            if role == Role.WOLF:
                self.actions[Role.WOLF].append(pid)
            elif role == Role.SEER:
                self.actions[Role.SEER].append(pid)
            elif role == Role.WITCH:
                self.actions[Role.WITCH].append(pid)
            elif role == Role.HUNTER:
                self.actions[Role.HUNTER].append(pid)

        for pid, role in self.roles.items():
            await ws.agent(pid).send(f'Role:{role.value}')
            logger.info('%s is %s', pid, role.value)
        
        await environment.add_history(0, 'world', '本局游戏拥有的角色是：两个狼人，两个村民，一个预言家，一个女巫。')
        for wolf in self.actions[Role.WOLF]:
            peers = []
            for peer in self.actions[Role.WOLF]:
                if peer != wolf:
                    peers.append(peer)
            await environment.add_player_memory(wolf, f'你的狼人队友是{', '.join(peers)}')

        await ws.channel('general').post('角色分配完成！游戏正式开始...')
        logger.info('角色分配完成！游戏正式开始...')
        await self._start_night()

    async def _is_game_over(self) -> bool:
        ws = self.workspace()
        wolf_count = len(self.actions[Role.WOLF])
        alive_players = await environment.get_alive_players()
        alive_players_count = len(alive_players)
        match self.max_players_num:
            case 6:
                if wolf_count == 0:
                    await ws.channel('general').post('狼人全部死亡，好人阵营胜利，游戏结束！')
                    await environment.set_phase(GamePhase.ENDED)
                    return True
                elif wolf_count >= alive_players_count - wolf_count:
                    await ws.channel('general').post('狼人数量大于等于好人数量，狼人阵营胜利，游戏结束！')
                    await environment.set_phase(GamePhase.ENDED)
                    return True
                else:
                    return False
            case _:
                await ws.channel('general').post('游戏人数不支持，游戏结束！')
                return True


    async def _start_night(self):
        await environment.set_phase(GamePhase.NIGHT)
        self.round += 1
        await environment.increment_round()
        logger.info('第%d轮夜晚', self.round)
        ws = self.workspace()
        await ws.channel('general').post('天黑请闭眼...')
        await self._start_actions()

    async def _start_actions(self):
        ws = self.workspace()

        match self.action_turn:
            case Action6.WOLF1_KILL:
                await ws.channel('general').post('狼人请选择击杀目标...')
                if len(self.actions[Role.WOLF]) == 0:
                    logger.info('狼人已全部出局')
                    self.action_turn = Action6.SEER_SEE
                    await self._start_actions()
                    return
                wolf = self.actions[Role.WOLF][0]
                logger.info('向狼人1(%s)发送Action请求...', wolf)
                await ws.agent(wolf).send(
                'Action:请选择击杀目标，得到结果后进入最终回答阶段。\n'
                '如果本次输出为<final_answer>，输出内容请按照最终回复格式。\n'
                '最终回复格式：Action:目标玩家id\n'
                '例如：Action:playerA'
            )
            case Action6.WOLF2_KILL:
                if len(self.actions[Role.WOLF]) < 2:
                    logger.info('狼人2已出局')
                    self.action_turn = Action6.SEER_SEE
                    await self._start_actions()
                    return
                wolf = self.actions[Role.WOLF][1]
                logger.info('向狼人2(%s)发送Action请求...', wolf)
                await ws.agent(wolf).send(
                'Action:请选择击杀目标，得到结果后进入最终回答阶段。\n'
                '如果本次输出为<final_answer>，输出内容请按照最终回复格式。\n'
                '最终回复格式：Action:目标玩家id\n'
                '例如：Action:playerA'
            )
            case Action6.SEER_SEE:
                await ws.channel('general').post('预言家请选择查看目标...')
                if len(self.actions[Role.SEER]) == 0:
                    logger.info('预言家已出局')
                    self.action_turn = Action6.WITCH_CURE
                    await self._start_actions()
                    return
                seer = self.actions[Role.SEER][0]
                logger.info('向预言家(%s)发送Action请求...', seer)
                await ws.agent(seer).send(
                'Action:请选择预言目标，得到结果后进入最终回答阶段。\n'
                '如果本次输出为<final_answer>，输出内容请按照最终回复格式。\n'
                '最终回复格式:Action:目标玩家id\n'
                '例如:Action:playerA'
            )
            case Action6.WITCH_CURE:
                await ws.channel('general').post('女巫请选择是否使用解药...')
                if len(self.actions[Role.WITCH]) == 0:
                    logger.info('女巫已出局')
                    self.action_turn = Action6.END_NIGHT
                    await self._start_actions()
                    return
                witch = self.actions[Role.WITCH][0]
                cure_status = await environment.get_cure_status()
                if cure_status == 'used':
                    logger.info('解药已经使用过了')
                    self.action_turn = Action6.WITCH_POISON
                    await self._start_actions()
                    return
                killed_player = await environment.get_player_killed_tonight()
                if killed_player is None:
                    await ws.agent(witch).send(
                        'Action:今晚没有玩家被杀害，无法使用解药，进入最终回答阶段。\n'
                        '如果本次输出为<final_answer>，输出内容请按照最终回复格式。\n'
                        '最终回复格式：Action:目标玩家id\n'
                        '例如：Action:playerA'
                    )
                else:
                    await ws.agent(witch).send(
                    f'Action:今晚{killed_player}被杀了，请问需要使用解药吗。当你做出行动之后进入最终回答阶段。\n'
                    '注意：如果你今晚使用解药，你将无法使用毒药。如果你想在本晚使用毒药，请选择不使用解药。\n'
                    '注意：如果你今晚选择解救目标玩家，必须使用对应的解药工具。\n'
                    '如果本次输出为<final_answer>，输出内容请按照最终回复格式。\n'
                    '最终回复格式：Action:选择\n'
                    '例如：Action:使用、Action:不使用'
                    )
            
                logger.info('向女巫(%s)发送Action请求...', witch)
                
            case Action6.WITCH_POISON:
                await ws.channel('general').post('女巫请选择是否使用毒药...')
                witch = self.actions[Role.WITCH][0]
                poison_status = await environment.get_poison_status()
                if poison_status == 'used':
                    logger.info('毒药已经使用过了')
                    self.action_turn = Action6.END_NIGHT
                    await self._start_actions()
                    return
                cure_tonight_status = await environment.get_cure_tonight()
                if cure_tonight_status:
                    logger.info('今晚解药已经使用过了，无法使用毒药')
                    self.action_turn = Action6.END_NIGHT
                    await self._start_actions()
                    return
                logger.info('向女巫(%s)发送Action请求...', witch)
                await ws.agent(witch).send(
                'Action:请选择毒杀目标，选择完成后进入最终回答阶段。\n'
                '注意：如果你今晚选择毒杀目标玩家，必须使用对应的毒药工具。\n'
                '如果本次输出为<final_answer>，输出内容请按照最终回复格式。\n'
                '最终回复格式：Action:目标玩家id\n'
                '例如：Action:playerA'
            )
            case Action6.END_NIGHT:
                self.action_turn = Action6.WOLF1_KILL
                await self._start_day()

    async def _remove_action(self, agent_id):
        for role in [Role.WOLF, Role.SEER, Role.WITCH]:
            if agent_id in self.actions[role]:
                self.actions[role].remove(agent_id)
                logger.info('%s已出局', agent_id)

                
    async def _start_day(self):
        ws = self.workspace()

        await environment.set_phase(GamePhase.DAY)

        player_killed_tonight = await environment.get_player_killed_tonight()
        player_posioned_tonight = await environment.get_player_posioned_tonight()
        await environment.set_player_killed_tonight(None)
        await environment.set_player_posioned_tonight(None)
        await environment.set_cure_tonight(False)
        player_dead_tonight = []
        if player_killed_tonight is not None:
            player_dead_tonight.append(player_killed_tonight)
            await self._remove_action(player_killed_tonight)
            await environment.remove_alive_player(player_killed_tonight)
        if player_posioned_tonight is not None:
            player_dead_tonight.append(player_posioned_tonight)
            await self._remove_action(player_posioned_tonight)
            await environment.remove_alive_player(player_posioned_tonight)        

        is_game_over = await self._is_game_over()
        if is_game_over:
            return

        await ws.channel('general').post('天亮了，请睁眼...')
        if len(player_dead_tonight) == 0:
            await ws.channel('general').post('昨晚是个平安夜，没有玩家死亡')
            await environment.add_history(self.round, 'world', '昨晚是个平安夜，没有玩家死亡')
        else:
            await ws.channel('general').post('昨晚死亡玩家：' + ', '.join(player_dead_tonight))
            await environment.add_history(self.round, 'world', '昨晚死亡玩家：' + ', '.join(player_dead_tonight))

        alive_players = await environment.get_alive_players()
        self.speech_list = list(alive_players)
        random.shuffle(self.speech_list)
        await self._start_speech()


    async def _start_speech(self):
        ws = self.workspace()
        if self.speech_turn >= len(self.speech_list):
            self.speech_turn = 0
            logger.info('所有玩家发言结束')
            await ws.channel('general').post('所有玩家发言结束，进入投票阶段...')
            await self._start_vote()
            return
        speech_player = self.speech_list[self.speech_turn]
        self.speech_turn += 1
        await ws.channel('general').post(f'{speech_player}请发言...')
        await ws.agent(speech_player).send(f'Speech:请发言，发言结束后进入最终回答阶段。\n'
        '如果本次输出为<final_answer>，输出内容请按照最终回复格式。\n'
        '发言内容尽量简洁明了。\n'
        '最终回复格式：Speech:发言内容\n')

    async def _start_vote(self):
        ws = self.workspace()

        if self.speech_turn >= len(self.speech_list):
            self.speech_turn = 0
            logger.info('所有玩家投票结束')
            await ws.channel('general').post('所有玩家投票结束...')
            await self._end_vote()
            return

        vote_player = self.speech_list[self.speech_turn]
        self.speech_turn += 1
        await ws.channel('general').post(f'{vote_player}请投票...')
        await ws.agent(vote_player).send(f'Vote:请投票，选择完成后进入最终回答阶段。\n'
        '注意：你只能投票给一个玩家，不能投给自己和已经出局的玩家。\n'
        '如果你是好人，请投票给你觉得是狼人的玩家；如果你是狼人，请尽量保证自己和队友不被投出去。\n'
        '得票最高的玩家将出局，如果得票最高玩家有多个，则跳过此次投票。\n'
        '如果本次输出为<final_answer>，输出内容请按照最终回复格式。\n'
        '最终回复格式：Vote:目标玩家id\n'
        '例如：Vote:playerA'
        )

    async def _re_vote(self):
        ws = self.workspace()

        self.speech_turn -= 1
        vote_player = self.speech_list[self.speech_turn]
        self.speech_turn += 1

        await ws.channel('general').post(f'投票不符合要求，{vote_player}请重新投票...')
        await ws.agent(vote_player).send(f'Vote:你刚刚把票投给了自己或者已出局的玩家，请重新投票，选择完成后进入最终回答阶段。\n'
        '注意：你只能投票给一个玩家，不能投给自己和已经出局的玩家。\n'
        '如果你是好人，请投票给你觉得是狼人的玩家；如果你是狼人，请尽量保证自己和队友不被投出去。\n'
        '得票最高的玩家将出局，如果得票最高玩家有多个，则跳过此次投票。\n'
        '如果本次输出为<final_answer>，输出内容请按照最终回复格式。\n'
        '最终回复格式：Vote:目标玩家id\n'
        '例如：Vote:playerA'
        )

    async def _end_vote(self):
        ws = self.workspace()

        vote_counts = Counter(self.vote_result)
        # 显示投票详情
        vote_details = ', '.join([f'{player}({votes}票)' for player, votes in vote_counts.items()])
        await ws.channel('general').post(f'投票详情：{vote_details}')
        logger.info(f'投票详情：{vote_details}')
        
        # 找出最高票数
        max_votes = max(vote_counts.values())
        
        # 找出所有得票最高的玩家
        top_voted = [player for player, votes in vote_counts.items() if votes == max_votes]
        
        # 检查是否平票
        if len(top_voted) > 1:
            await ws.channel('general').post(f'平票！得票最高的玩家有：{", ".join(top_voted)}，每人得票{max_votes}票。本轮无人出局。')
            logger.info(f'平票：{top_voted}，每人{max_votes}票')
            await environment.add_history(self.round, 'world', f'平票：{", ".join(top_voted)}，每人{max_votes}票，无人出局')
        else:
            eliminated_player = top_voted[0]
            await ws.channel('general').post(f'投票结果：{eliminated_player}得票{max_votes}票，被投票出局。')
            logger.info(f'投票结果：{eliminated_player}得票{max_votes}票，被投票出局')
            await environment.add_history(self.round, 'world', f'投票结果：{eliminated_player}得票{max_votes}票，被投票出局')
            await self._remove_action(eliminated_player)
            await environment.remove_alive_player(eliminated_player)

        self.vote_result.clear()

        if await self._is_game_over():
            return

        await self._start_night()


        


if __name__ == "__main__":
    agent = GodAgent()
    agent.start(
        network_host='localhost',
        network_port=8700,
        network_id='default-network-1'
    )
    agent.wait_for_stop()

