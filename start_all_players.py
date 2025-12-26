# start_all_players.py
import subprocess
import sys
import time
import os

def start_players():
    """启动所有玩家实例"""
    players = ['playerA', 'playerB', 'playerC', 'playerD', 'playerE', 'playerF']
    
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    player_script = os.path.join(script_dir, 'agents', 'player.py')
    
    print("正在启动6个玩家实例...")
    
    for player_id in players:
        print(f"启动 {player_id}...")
        # 在新窗口中启动每个玩家
        if sys.platform == 'win32':
            # Windows: 使用start命令在新窗口运行
            cmd = f'start "Player {player_id}" cmd /k python "{player_script}" {player_id}'
            subprocess.Popen(cmd, shell=True)
        else:
            # Linux/Mac: 使用xterm或gnome-terminal
            subprocess.Popen(['xterm', '-e', f'python {player_script} {player_id}'])
        
        time.sleep(0.5)  # 短暂延迟，避免同时启动造成冲突
    
    print("\n所有玩家实例已启动！")
    print("每个玩家都在独立的窗口中运行。")

if __name__ == "__main__":
    start_players()