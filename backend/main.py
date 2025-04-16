from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional, Tuple
from fastapi.middleware.cors import CORSMiddleware
import random
import math

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（测试环境），生产环境请改为你的前端地址
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法（POST, GET 等）
    allow_headers=["*"],  # 允许所有请求头
)

# ----------------------------
# 定义输入/输出数据模型
# ----------------------------

class SimulationParameters(BaseModel):
    n: int                           # 总节点数
    m: int                           # 容错节点数（故障节点数量）
    topology: str                    # 拓扑结构，可选 "full", "ring", "star", "tree"
    n_value: Optional[int] = 2       # 针对树型拓扑的分支数（当 topology=="tree" 时有效）
    faulty_proposer: bool = False    # 是否由故障（恶意）提议者发起（对应 JS 中 maliciousOrigin）
    allow_tampering: bool = False     # 是否允许消息篡改（对应 JS 中 falsehoodMessage）
    message_delivery_prob: float = 1.0  # 消息到达的概率，默认为1.0（100%）
    probability_matrix: Optional[List[List[float]]] = None  
    # 若为空，则后端根据拓扑自动生成默认的概率矩阵（允许的连接概率为 1）

class MessagePath(BaseModel):
    nodes: List[int]  # 消息传递经过的节点路径
    success: bool     # 消息是否成功传递
    probabilities: List[float]  # 每个路径段的传递概率

class Message(BaseModel):
    src: int
    dst: Optional[int]  # 对于预准备阶段，proposer 给所有节点发消息时，dst 可为空（None）表示"自发"
    value: Optional[int]
    tampered: bool
    path: Optional[MessagePath] = None  # 消息传递的路径信息

class SimulationResult(BaseModel):
    pre_prepare: List[Message]
    prepare: List[List[Message]]       # 每个节点发出的准备消息列表
    commit: List[List[Message]]        # 每个节点收到的提交消息列表
    accepted_in_prepare: List[Optional[int]]  # 每个节点在准备阶段的"接受值"
    accepted_in_commit: List[Optional[int]]   # 每个节点在提交阶段的"接受值"
    consensus: str                     # 最终共识结果说明
    probability_matrix: List[List[float]]  # 模拟中使用的概率矩阵，可供前端显示或调试

# ----------------------------
# 工具函数
# ----------------------------

def is_connection_allowed(i: int, j: int, n: int, topology: str, n_value: int) -> bool:
    """
    根据拓扑类型判断节点 i 到节点 j 是否允许通信。
    i==j 的情况一律返回 False。
    """
    if i == j:
        return False
    
    if topology == "full":
        return True
    elif topology == "ring":
        # 在环形拓扑中，允许双向连接
        return j == (i + 1) % n or j == (i - 1) % n
    elif topology == "star":
        # 星型拓扑中，以 0 号为中心，其它节点与 0 相连
        # 允许中心节点与其他所有节点通信，但不允许非中心节点之间直接通信
        return i == 0 or j == 0
    elif topology == "tree":
        # 树型拓扑中，每个节点可以与其父节点和子节点通信
        # 父节点编号为 (i-1)//n_value
        # 子节点编号为 i*n_value+1 到 i*n_value+n_value
        parent = (i - 1) // n_value
        children = [i * n_value + k for k in range(1, n_value + 1) if i * n_value + k < n]
        return j == parent or j in children
    return False

def generate_probability_matrix(n: int, topology: str, n_value: int, message_delivery_prob: float = 1.0) -> List[List[float]]:
    """
    生成一个 n×n 的概率矩阵，对允许通信的边赋指定的概率（默认为1.0）。
    对于星型拓扑，中心节点（0号）到其他节点的概率可能更高。
    对于树型拓扑，父子节点之间的概率可能更高。
    """
    matrix = [[0.0 for _ in range(n)] for _ in range(n)]
    
    if topology == "star":
        # 星型拓扑中，中心节点到其他节点的概率可能更高
        for i in range(n):
            if i == 0:  # 中心节点
                for j in range(1, n):
                    matrix[i][j] = message_delivery_prob
            else:  # 其他节点只能与中心节点通信
                matrix[i][0] = message_delivery_prob
    elif topology == "tree":
        # 树型拓扑中，父子节点之间的概率可能更高
        for i in range(n):
            parent = (i - 1) // n_value
            children = [i * n_value + k for k in range(1, n_value + 1) if i * n_value + k < n]
            if parent >= 0:
                matrix[i][parent] = message_delivery_prob
                matrix[parent][i] = message_delivery_prob
            for child in children:
                matrix[i][child] = message_delivery_prob
                matrix[child][i] = message_delivery_prob
    else:
        # 其他拓扑结构（全连接、环形）使用统一的概率
        for i in range(n):
            for j in range(n):
                if is_connection_allowed(i, j, n, topology, n_value):
                    matrix[i][j] = message_delivery_prob
    
    return matrix

def is_message_delivered(prob_matrix: List[List[float]], src: int, dst: int, topology: str, n_value: int) -> Tuple[bool, List[int], List[float]]:
    """
    判断从 src 到 dst 的消息是否能成功传输，并返回传递路径和概率。
    支持消息转发，即消息可以通过中间节点传递。
    """
    if src == dst:
        return True, [src], [1.0]
    
    n = len(prob_matrix)
    visited = [False] * n
    # (当前节点, 路径, 累积概率, 路径概率列表)
    queue = [(src, [src], 1.0, [])]
    
    while queue:
        node, path, current_prob, probs = queue.pop(0)
        if node == dst:
            # 如果找到目标节点，根据累积概率判断是否成功传递
            success = random.random() <= current_prob
            return success, path, probs
        
        visited[node] = True
        for i in range(n):
            if not visited[i] and is_connection_allowed(node, i, n, topology, n_value):
                # 计算新的累积概率
                new_prob = current_prob * prob_matrix[node][i]
                # 如果累积概率太小，可以提前终止
                if new_prob > 0.01:  # 设置一个阈值，避免概率太小的情况
                    new_path = path + [i]
                    new_probs = probs + [prob_matrix[node][i]]
                    queue.append((i, new_path, new_prob, new_probs))
    
    return False, [], []

def is_honest(i: int, n: int, m: int, faulty_proposer: bool) -> bool:
    if m == 0:
        return True
    if faulty_proposer:
        if i == 0:
            return False
        return i <= n - m
    else:
        if i == 0:
            return True
        return i < n - m

# ----------------------------
# 模拟主逻辑（各阶段计算）
# ----------------------------

@app.post("/simulate", response_model=SimulationResult)
def simulate(params: SimulationParameters):
    n = params.n
    m = params.m
    topology = params.topology
    n_value = params.n_value if params.n_value is not None else 2
    faulty_proposer = params.faulty_proposer
    allow_tampering = params.allow_tampering
    message_delivery_prob = params.message_delivery_prob

    # 若前端未传入概率矩阵，则自动根据拓扑生成默认矩阵
    if params.probability_matrix is not None:
        prob_matrix = params.probability_matrix
    else:
        prob_matrix = generate_probability_matrix(n, topology, n_value, message_delivery_prob)

    # ----------- 预准备阶段（Pre-Prepare）-----------
    pre_prepare = []
    for i in range(n):
        if i == 0:
            # 对于提议者自身
            msg = Message(
                src=0,
                dst=None,
                value=0 if is_honest(0, n, m, faulty_proposer) else random.choice([0, 1]),
                tampered=not is_honest(0, n, m, faulty_proposer),
                path=MessagePath(nodes=[0], success=True, probabilities=[1.0])
            )
        else:
            # 对于其他节点
            success, path, probs = is_message_delivered(prob_matrix, 0, i, topology, n_value)
            msg = Message(
                src=0,
                dst=i,
                value=0 if is_honest(0, n, m, faulty_proposer) else random.choice([0, 1]),
                tampered=not is_honest(0, n, m, faulty_proposer),
                path=MessagePath(nodes=path, success=success, probabilities=probs)
            )
        pre_prepare.append(msg)

    # ----------- 准备阶段（Prepare）-----------
    prepare = []
    for src in range(n):
        msgs = []
        for dst in range(n):
            if src == dst:
                continue
            success, path, probs = is_message_delivered(prob_matrix, src, dst, topology, n_value)
            if success:
                if is_honest(src, n, m, faulty_proposer):
                    value = pre_prepare[src].value
                else:
                    value = random.choice([0, 1]) if allow_tampering else None
                tampered = (value != pre_prepare[src].value) if pre_prepare[src].value is not None else False
                msg = Message(
                    src=src,
                    dst=dst,
                    value=value,
                    tampered=tampered,
                    path=MessagePath(nodes=path, success=success, probabilities=probs)
                )
                msgs.append(msg)
        prepare.append(msgs)

    def accepted_value_in_prepare(i: int) -> Optional[int]:
        if not is_honest(i, n, m, faulty_proposer):
            return None
        valid = 0
        total = len(prepare[i])
        for msg in prepare[i]:
            if is_message_delivered(prob_matrix, msg.src, msg.dst, topology, n_value):
                if msg.value == pre_prepare[i].value:
                    valid += 1
        if (valid + 1) / (total + 1) >= 2/3:
            return pre_prepare[i].value
        else:
            return -1

    accepted_in_prepare = []
    for i in range(n):
        accepted = accepted_value_in_prepare(i)
        accepted_in_prepare.append(accepted)

    # ----------- 提交阶段（Commit）-----------
    commit = [[] for _ in range(n)]
    for dst in range(n):
        for src in range(n):
            if src == dst:
                continue
            success, path, probs = is_message_delivered(prob_matrix, src, dst, topology, n_value)
            if success:
                if is_honest(src, n, m, faulty_proposer) or not allow_tampering:
                    value = accepted_in_prepare[src]
                else:
                    value = random.choice([0, 1])
                tampered = not is_honest(src, n, m, faulty_proposer)
                msg = Message(
                    src=src,
                    dst=dst,
                    value=value,
                    tampered=tampered,
                    path=MessagePath(nodes=path, success=success, probabilities=probs)
                )
                commit[dst].append(msg)

    def accepted_value_in_commit(i: int) -> Optional[int]:
        if not is_honest(i, n, m, faulty_proposer):
            return None
        values = []
        for msg in commit[i]:
            if msg.value is not None and msg.value >= 0:
                values.append(msg.value)
        if accepted_in_prepare[i] is not None:
            values.append(accepted_in_prepare[i])
        count0 = values.count(0)
        count1 = values.count(1)
        if count0 / n >= 2/3:
            return 0
        if count1 / n >= 2/3:
            return 1
        return -1

    accepted_in_commit = []
    for i in range(n):
        accepted = accepted_value_in_commit(i)
        accepted_in_commit.append(accepted)

    truth = 0
    falsehood = 0
    rejected = 0
    for i in range(n):
        if is_honest(i, n, m, faulty_proposer):
            val = accepted_in_commit[i]
            if val == 0:
                truth += 1
            elif val == 1:
                falsehood += 1
            elif val == -1:
                rejected += 1

    if truth + falsehood + rejected == 0:
        consensus = "No non-faulty process"
    elif truth + falsehood == 0:
        consensus = "Agreed to reject the proposal"
    elif rejected == 0 and ((truth > 0 and falsehood == 0) or (truth == 0 and falsehood > 0)):
        decided_value = 0 if truth > 0 else 1
        consensus = f"Agreed to {decided_value}"
    else:
        consensus = "Contradiction, consensus failed"

    return SimulationResult(
        pre_prepare=pre_prepare,
        prepare=prepare,
        commit=commit,
        accepted_in_prepare=accepted_in_prepare,
        accepted_in_commit=accepted_in_commit,
        consensus=consensus,
        probability_matrix=prob_matrix
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
