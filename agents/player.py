import sys
import asyncio
import re
from typing import List, Tuple, Callable
import ast
import inspect
import os
from string import Template
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

from openai import OpenAI
from openai import AsyncOpenAI

from openagents.agents.worker_agent import WorkerAgent, EventContext, ChannelMessageContext
from openagents.models.agent_config import AgentConfig

project_root = Path(__file__).parent.parent  # 从 agents/test.py 向上到 werewolf/
sys.path.insert(0, str(project_root))

from environment.settings import Role
from environment.environment import set_player_name
from tools.tools_loader import load_tools
from prompts.prompts_loader import load_prompts
from prompts.prompt_seer import react_system_prompt_template
from logs.logging_config import setup_logger

load_dotenv(find_dotenv())
provider = os.getenv('PROVIDER')
api_key = os.getenv('OPENAI_API_KEY')
base_url = os.getenv('BASE_URL')
model_name = os.getenv('MODEL_NAME')

class PlayerAgent(WorkerAgent):
    default_agent_id = 'test'

    def __init__(self, agent_config: AgentConfig):
        super().__init__(agent_config=agent_config)

        self._agent_config = agent_config

        self._client = AsyncOpenAI(
            api_key=agent_config.api_key,
            base_url=agent_config.api_base
        )
        self.model = 'deepseek-chat'

        self.role = Role.SEER
        self.role_instructions = None   #系统提示词
        self.action_instructions = None    #用户提示词
        self._tools = None

    async def on_startup(self):
        ws = self.workspace()
        await ws.channel('general').post(f'玩家{self.default_agent_id}加入游戏')

    async def on_shutdown(self):
        ws = self.workspace()
        await ws.channel('general').post(f'玩家{self.default_agent_id}离开游戏')

    async def on_direct(self, context: EventContext):
        ws = self.workspace()
        message = context.incoming_event.payload.get('content', {}).get('text', '')
        source_id = context.source_id

        #if source_id != 'god':
        #    return

        if message.startswith('Role'):  #获取角色
            role_str = message.split(':')[1].strip()
            self.role = Role(role_str)
            print(f'########Role: {self.role}')
            tools = load_tools(self.role)
            self._tools = {func.__name__: func for func in tools}
            role_prompt = self.render_system_prompt(load_prompts(self.role))
            await ws.agent('QuickHelper7781').send(f'RolePrompt:{role_prompt}')
            self.role_instructions = role_prompt
            self._agent_config.instruction = self.role_instructions
            
        elif message.startswith('Action'):    #获取执行动作
            instructions = message.split(':', 1)[1].strip()
            logger.info('获取Action:%s', instructions)
            messages = [
                {'role': 'system', 'content': self.role_instructions},
                {'role': 'user', 'content': instructions},
            ]
            await self._run(messages)
            await ws.agent('god').send(f'Action')

        elif message.startswith('Speech'):    #获取发言
            instructions = message.split(':', 1)[1].strip()
            logger.info('获取Speech:%s', instructions)
            messages = [
                {'role': 'system', 'content': self.role_instructions},
                {'role': 'user', 'content': instructions},
            ]
            logger.info('%s开始发言。', self.default_agent_id)
            result = await self._run(messages)
            if result.startswith('Speech'):
                speech = result.split(':', 1)[1].strip()
                await ws.channel('general').post(f'Speech:{speech}')
            else:
                await ws.channel('general').post(f'Speech:{result}')

        elif message.startswith('Vote'):
            instructions = message.split(':', 1)[1].strip()
            logger.info('获取Vote:%s', instructions)
            messages = [
                {'role': 'system', 'content': self.role_instructions},
                {'role': 'user', 'content': instructions},
            ]
            logger.info('%s开始投票。', self.default_agent_id)
            result = await self._run(messages)

            if result.startswith('Vote'):
                vote = result.split(':', 1)[1].strip()
                await ws.channel('general').post(f'Vote:{vote}')
            else:
                await ws.channel('general').post(f'Vote:{result}')


    

    def get_tool_list(self) -> str:
        """生成工具列表字符串，包含函数签名和简要说明"""
        tool_descriptions = []
        for func in self._tools.values():
            name = func.__name__
            signature = str(inspect.signature(func))
            doc = inspect.getdoc(func)
            tool_descriptions.append(f"- {name}{signature}: {doc}")
        return "\n".join(tool_descriptions)

    def render_system_prompt(self, system_prompt_template: str) -> str:
        """渲染系统提示模板，替换变量"""
        tool_list = self.get_tool_list()
        return Template(system_prompt_template).substitute(
            player_name=self.default_agent_id,
            tool_list=tool_list
        )

    async def _run(self, messages):
        ws = self.workspace()

        while True:
            #1.请求模型
            logger.info('请求模型')
            max_retries = 3
            retry_count = 0
            raw_response = None
            
            while retry_count < max_retries:
                try:
                    raw_response = await self._client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        stream=False,
                        timeout=30.0  # 添加超时设置
                    )
                    break  # 成功则跳出重试循环
                except Exception as e:
                    retry_count += 1
                    error_msg = str(e)
                    logger.warning('API 请求失败 (尝试 %d/%d): %s', retry_count, max_retries, error_msg)
                    
                    if retry_count >= max_retries:
                        # 重试次数用尽，返回错误信息
                        logger.error('API 请求失败，已重试 %d 次: %s', max_retries, error_msg)
                        return f'错误：无法连接到 AI 服务 ({error_msg})，请稍后重试。'
                    
                    # 等待后重试（指数退避）
                    wait_time = min(2 ** retry_count, 10)  # 最多等待10秒
                    logger.info('等待 %d 秒后重试...', wait_time)
                    await asyncio.sleep(wait_time)
            
            if raw_response is None:
                return '错误：无法连接到 AI 服务，请稍后重试。'

            response = raw_response.choices[0].message.content

            #2.检测Thought
            logger.info('检查Thought')
            thought_match = re.search(r'<thought>(.*?)</thought>', response, re.DOTALL)
            if thought_match:
                thought = thought_match.group(1)
                logger.info('Thought: %s', thought)

            #3.检测Final Answer
            logger.info('检测Final Answer')
            if '<final_answer>' in response:
                final_answer = re.search(r'<final_answer>(.*?)</final_answer>', response, re.DOTALL)
                if final_answer:
                    logger.info('Final Answer: %s', final_answer.group(1))
                    return final_answer.group(1)

            #4.检测Action
            logger.info('检测Action')
            action_match = re.search(r'<action>(.*?)</action>', response, re.DOTALL)
            if not action_match:
                raise RuntimeError('模型未输出<action>')
            action = action_match.group(1)
            tool_name, args = self._parse_action(action)
            logger.info('Action: %s:%s', tool_name, args)

            try:
                tool_func = self._tools.get(tool_name)
                if tool_func is None:
                    observation = f'工具 {tool_name} 不存在'
                else:
                    # ✅ 通用方法：检查并注入 self_id
                    sig = inspect.signature(tool_func)
                    param_names = list(sig.parameters.keys())
                    
                    if 'self_id' in param_names:
                        # 需要 self_id
                        param_index = param_names.index('self_id')
                        args_list = list(args)
                        
                        if len(args_list) == 0:
                            args_list.append(self.default_agent_id)
                        elif len(args_list) < len(sig.parameters):
                            args_list.insert(param_index, self.default_agent_id)
                        else:
                            args_list[param_index] = self.default_agent_id
                        
                        args = tuple(args_list)
                    
                    if asyncio.iscoroutinefunction(tool_func):
                        observation = await tool_func(*args)
                    else:
                        observation = tool_func(*args)
            except Exception as e:
                observation = f'工具执行错误: {str(e)}'
            logger.info('Observation: %s', observation)
            obs_msg = f"<observation>{observation}</observation>"
            messages.append({"role": "user", "content": obs_msg})


    def _parse_action(self, code_str: str) -> Tuple[str, List[str]]:
        """
        解析函数调用字符串，例如：check_alive_players() 或 check_identity("player1")
        
        Args:
            code_str: 函数调用字符串，例如 "check_alive_players()" 或 'check_identity("player1")'
        
        Returns:
            Tuple[str, List]: (函数名, 参数列表)
        """
        code_str = code_str.strip()
        
        logger.debug('解析 action 字符串: %s', repr(code_str))
        
       
        if not code_str:
            raise ValueError("Action 字符串为空")
        
        match = re.match(r'(\w+)\s*\((.*)\)\s*$', code_str, re.DOTALL)
        
        if not match:
            match_no_args = re.match(r'(\w+)\s*\(\s*\)\s*$', code_str)
            if match_no_args:
                func_name = match_no_args.group(1)
                return func_name, []

            # 处理只有函数名没有括号的情况（例如：get_player_memory）
            match_func_name_only = re.match(r'^(\w+)\s*$', code_str)
            if match_func_name_only:
                func_name = match_func_name_only.group(1)
                logger.warning('Action 字符串缺少括号，自动添加：%s()', func_name)
                return func_name, []
            
            logger.error('无法解析 action 字符串: %s', repr(code_str))
            raise ValueError(
                f"Invalid function call syntax: '{code_str}'. "
                f"期望格式: function_name() 或 function_name(arg1, arg2, ...)"
            )
        
        func_name = match.group(1).strip()
        args_str = match.group(2).strip()
        
        if not args_str:
            return func_name, []
        
        # 手动解析参数，特别处理包含多行内容的字符串
        args = []
        current_arg = ""
        in_string = False
        string_char = None
        i = 0
        paren_depth = 0
        
        while i < len(args_str):
            char = args_str[i]
            
            if not in_string:
                if char in ['"', "'"]:
                    in_string = True
                    string_char = char
                    current_arg += char
                elif char == '(':
                    paren_depth += 1
                    current_arg += char
                elif char == ')':
                    paren_depth -= 1
                    current_arg += char
                elif char == ',' and paren_depth == 0:
                    # 遇到顶层逗号，结束当前参数
                    args.append(self._parse_single_arg(current_arg.strip()))
                    current_arg = ""
                else:
                    current_arg += char
            else:
                current_arg += char
                if char == string_char and (i == 0 or args_str[i-1] != '\\'):
                    in_string = False
                    string_char = None
            
            i += 1
        
        if current_arg.strip():
            args.append(self._parse_single_arg(current_arg.strip()))
        
        return func_name, args

    def _parse_single_arg(self, arg_str: str):
        """解析单个参数"""
        arg_str = arg_str.strip()
        
        # 如果是字符串字面量
        if (arg_str.startswith('"') and arg_str.endswith('"')) or \
           (arg_str.startswith("'") and arg_str.endswith("'")):
            # 移除外层引号并处理转义字符
            inner_str = arg_str[1:-1]
            # 处理常见的转义字符
            inner_str = inner_str.replace('\\"', '"').replace("\\'", "'")
            inner_str = inner_str.replace('\\n', '\n').replace('\\t', '\t')
            inner_str = inner_str.replace('\\r', '\r').replace('\\\\', '\\')
            return inner_str
        
        # 尝试使用 ast.literal_eval 解析其他类型
        try:
            return ast.literal_eval(arg_str)
        except (SyntaxError, ValueError):
            # 如果解析失败，返回原始字符串
            return arg_str







if __name__ == "__main__":
    agent_id = sys.argv[1] if len(sys.argv) > 1 else 'player'
    PlayerAgent.default_agent_id = agent_id
    logger = setup_logger(agent_id)
    agent_config = AgentConfig(
        model_name=model_name,
        instruction='你是一个狼人杀玩家，请根据角色和游戏规则进行游戏。',
        provider=provider,
        api_base=base_url,
        api_key=api_key
    )
    agent = PlayerAgent(agent_config)
    agent.start(
        network_host='localhost',
        network_port=8700,
        network_id='default-network-1'
    )
    logger.info('Agent %s started', agent_id)
    agent.wait_for_stop()
