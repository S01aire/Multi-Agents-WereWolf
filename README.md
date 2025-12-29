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

启动agents/player.py脚本（以下两种方式二选一）：

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



### 快速了解

#### 相关链接

演示视频：[基于多智能体的狼人杀_哔哩哔哩_bilibili](https://www.bilibili.com/video/BV1PSvBBTEj8/)

#### 项目架构

本项目采用中心化多智能体系统，**god智能体**分别与其他**player智能体**通信，player智能体之间不能相互通信。god智能体控制游戏进度，并通过通信向player智能体发送指令。player智能体之间的交互通过**Environment**间接完成，智能体的行动会改变Environment中的信息，同时智能体可以通过**Tools**获取Environment中的信息。

![系统架构](assets/architecture.png)

**player.py**在运行后加载特定角色的提示词，成为狼人杀中的某个角色。

![玩家角色](assets\player.png)

#### 游戏逻辑

![游戏逻辑](assets/game_logic.png)