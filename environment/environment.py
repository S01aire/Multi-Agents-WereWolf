from typing import Dict, Optional, Set, List
import redis.asyncio as aioredis
import redis.exceptions as redis_exceptions

from environment.settings import GamePhase, Role, Action6
from logs.logging_config import setup_logger

logger = setup_logger('environment')

class Environment:
    def __init__(self, redis_url: str = 'redis://localhost:6379'):
        self.redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None
        self.key_prefix = 'werewolf:'


    async def connect(self):
        """连接到 Redis，添加错误处理"""
        if self._redis is None:
            try:
                self._redis = await aioredis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    max_connections=10,
                    socket_connect_timeout=3  # 连接超时 3 秒
                )
                # 测试连接
                await self._redis.ping()
            except (redis_exceptions.ConnectionError, OSError, Exception) as e:
                logger.warning(f'Redis 连接失败 ({self.redis_url}): {e}')
                raise  # 重新抛出异常，让调用者处理
        return self._redis

    async def disconnect(self):
        if self._redis:
            try:
                await self._redis.close()
            except Exception as e:
                logger.warning(f'关闭 Redis 连接时出错: {e}')
            finally:
                self._redis = None

    async def get_phase(self) -> GamePhase:
        redis = await self.connect()
        phase_str = await redis.get(f'{self.key_prefix}phase')
        
        if phase_str is None:
            return GamePhase.WAITING
        try:
            return GamePhase(phase_str)
        except ValueError:
            logger.error(f'Invalid phase: {phase_str}')
            return GamePhase.WAITING
        
    async def set_phase(self, phase: GamePhase):
        redis = await self.connect()
        await redis.set(f'{self.key_prefix}phase', phase.value)

    async def get_alive_players(self) -> Set[str]:
        redis = await self.connect()
        players = await redis.smembers(f'{self.key_prefix}alive_players')
        if not players:
            logger.error('No alive players found')
            return set()
        return set(players)

    async def set_alive_players(self, players: Set[str]):
        redis = await self.connect()
        await redis.delete(f'{self.key_prefix}alive_players')
        await redis.sadd(f'{self.key_prefix}alive_players', *players)

    async def remove_alive_player(self, player_id: str):
        redis = await self.connect()
        await redis.srem(f'{self.key_prefix}alive_players', player_id)

    async def add_alive_player(self, player_id: str):
        redis = await self.connect()
        await redis.sadd(f'{self.key_prefix}alive_players', player_id)

    async def set_role(self, player_id: str, role: Role):
        redis = await self.connect()
        await redis.hset(f'{self.key_prefix}roles', player_id, role.value)
        
    async def get_role(self, player_id: str) -> Optional[Role]:
        redis = await self.connect()
        role_str = await redis.hget(f'{self.key_prefix}roles', player_id)
        if role_str is None:
            return None
        try:
            return Role(role_str)
        except ValueError:
            logger.error(f'Invalid role: {role_str}')
            return None

    async def get_round(self) -> int:
        redis = await self.connect()
        round_str = await redis.get(f'{self.key_prefix}round')
        if round_str is None:
            return 0
        try:
            return int(round_str)
        except ValueError:
            logger.error(f'Invalid round: {round_str}')
            return 0

    async def increment_round(self):
        redis = await self.connect()
        await redis.incr(f'{self.key_prefix}round')

    async def set_player_killed_tonight(self, player_id: str):
        redis = await self.connect()
        key = f'{self.key_prefix}player_killed_tonight'
        if player_id is None:
            await redis.delete(key)
        else:
            await redis.set(key, player_id)

    async def get_player_killed_tonight(self) -> str:
        redis = await self.connect()
        player_id = await redis.get(f'{self.key_prefix}player_killed_tonight')
        if player_id is None:
            return None
        return player_id

    async def init_witch_items(self):
        redis = await self.connect()
        key = f'{self.key_prefix}witch:'
        await redis.hset(key, mapping={
        'cure': 'unused',
        'poison': 'unused',
        'cure_tonight': 'False'
        })
        await redis.hdel(key, 'player_posioned_tonight')

    async def get_cure_status(self) -> str:
        redis = await self.connect()
        key = f'{self.key_prefix}witch:'
        cure_status = await redis.hget(key, 'cure')
        if cure_status is None:
            logger.error('Cure not found')
            return 'used'
        return cure_status

    async def use_cure(self):
        redis = await self.connect()
        key = f'{self.key_prefix}witch:'
        await redis.hset(key, 'cure', 'used')

    async def set_cure_tonight(self, status: bool):
        redis = await self.connect()
        key = f'{self.key_prefix}witch:'
        await redis.hset(key, 'cure_tonight', 'True' if status else 'False')
    
    async def get_cure_tonight(self) -> bool:
        redis = await self.connect()
        key = f'{self.key_prefix}witch:'
        cure_tonight = await redis.hget(key, 'cure_tonight')
        if cure_tonight is None:
            return False
        return cure_tonight == 'True'

    async def get_poison_status(self) -> str:
        redis = await self.connect()
        key = f'{self.key_prefix}witch:'
        poison_status = await redis.hget(key, 'poison')
        if poison_status is None:
            logger.error('Poison not found')
            return 'used'
        return poison_status

    async def use_poison(self, player_id: str):
        redis = await self.connect()
        key = f'{self.key_prefix}witch:'
        await redis.hset(key, 'poison', 'used')

    async def get_player_posioned_tonight(self) -> str:
        redis = await self.connect()
        player_id = await redis.hget(f'{self.key_prefix}witch:', 'player_posioned_tonight')
        if player_id is None:
            return None
        return player_id

    async def set_player_posioned_tonight(self, player_id: str):
        redis = await self.connect()
        key = f'{self.key_prefix}witch:'
        if player_id is None:
            await redis.hdel(key, 'player_posioned_tonight')
        else:
            await redis.hset(key, 'player_posioned_tonight', player_id)
    
        
    async def add_history(self, round: int, agent_id: str, record: str):
        redis = await self.connect()
        await redis.lpush(f'{self.key_prefix}history', f'round:{round},{agent_id},{record}')

    async def get_history(self) -> List[str]:
        redis = await self.connect()
        history = await redis.lrange(f'{self.key_prefix}history', 0, -1)
        if not history:
            return []
        return list(reversed(history))

    async def add_player_memory(self, player_id: str, memory: str):
        redis = await self.connect()
        await redis.lpush(f'{self.key_prefix}{player_id}_memory', memory)

    async def get_player_memory(self, player_id: str) -> str:
        redis = await self.connect()
        memory = await redis.lrange(f'{self.key_prefix}{player_id}_memory', 0, -1)
        if not memory:
            return []
        return list(reversed(memory))

    async def clear_environment(self):
        redis = await self.connect()
        deleted_count = 0
        async for key in redis.scan_iter(match=f'{self.key_prefix}*'):
            await redis.delete(key)
            deleted_count += 1
        if deleted_count > 0:
            logger.info(f'清空环境：删除了 {deleted_count} 个键')
        else:
            logger.info('环境已经是空的')

environment = Environment()

async def set_player_name(player_id: str, name: str):
    await environment.add_player_memory(player_id, f'你是{name}')

async def export_add_player_memory(player_id: str, memory: str):
    await environment.add_player_memory(player_id, memory)
