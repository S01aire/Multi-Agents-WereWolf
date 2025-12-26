import importlib
import asyncio

from environment.settings import Role

def load_prompts(role: Role) -> str:
    match role:
        case Role.WOLF:
            module_name = 'prompts.prompt_wolf'
            module = importlib.import_module(module_name)
            role_prompt = getattr(module, 'react_system_prompt_template')
        case Role.SEER:
            module_name = 'prompts.prompt_seer'
            module = importlib.import_module(module_name)
            role_prompt = getattr(module, 'react_system_prompt_template')
        case Role.WITCH:
            module_name = 'prompts.prompt_witch'
            module = importlib.import_module(module_name)
            role_prompt = getattr(module, 'react_system_prompt_template')
        case Role.VILLAGER:
            module_name = 'prompts.prompt_villager'
            module = importlib.import_module(module_name)
            role_prompt = getattr(module, 'react_system_prompt_template')
        
        case _:
            raise ValueError(f'Unknown role: {role}')

    return role_prompt