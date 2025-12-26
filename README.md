# Multi-Agents-WereWolf

### 环境配置

#### 多智能体框架

本项目使用 [OpenAgents][openagents] 作为多智能体框架。

[openagents]:https://github.com/openagents-org/openagents

使用Miniconda或者Anaconda创建一个新的虚拟环境：

```bash
#新建一个conda环境
conda create -n openagents python=3.12

#激活环境
conda activate openagents
```

安装项目所需的库：

```bash
#安装requirements.txt中的库
pip install -r requirements.txt 
```

#### 数据库

本项目使用 Redis 作为运行时存储游戏数据的数据库，使用 Redis Insight 作为数据库的可视化工具。

安装Redis：[Redis 安装 | 菜鸟教程](https://www.runoob.com/redis/redis-install.html)

安装Redis Insight：[Redis Insight](https://redis.io/insight/)

### 运行项目

首先运行openagents network：

```bash
openagents network start network.yaml
```

之后运行openagents studio：

```bash
openagents studio -s
```

启动agents/god.py脚本：

```bash
python -m agents.god
```

启动agents/player.py脚本：

```bash
#使用start_all_players.py快速启动
python -m start_all_players

#依次手动启动
python -m agents.player playerA
python -m agents.player playerB
python -m agents.player playerC
python -m agents.player playerD
python -m agents.player playerE
python -m agents.player playerF
```

