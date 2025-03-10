from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
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
    probability_matrix: Optional[List[List[float]]] = None  
    # 若为空，则后端根据拓扑自动生成默认的概率矩阵（允许的连接概率为 1）

class Message(BaseModel):
    src: int
    dst: Optional[int]  # 对于预准备阶段，proposer 给所有节点发消息时，dst 可为空（None）表示“自发”
    value: Optional[int]
    tampered: bool

class SimulationResult(BaseModel):
    pre_prepare: List[Message]
    prepare: List[List[Message]]       # 每个节点发出的准备消息列表
    commit: List[List[Message]]        # 每个节点收到的提交消息列表
    accepted_in_prepare: List[Optional[int]]  # 每个节点在准备阶段的“接受值”
    accepted_in_commit: List[Optional[int]]   # 每个节点在提交阶段的“接受值”
    consensus: str                     # 最终共识结果说明
    probability_matrix: List[List[float]]  # 模拟中使用的概率矩阵，可供前端显示或调试

# ----------------------------
# 工具函数
# ----------------------------

def is_connection_allowed(i: int, j: int, n: int, topology: str, n_value: int) -> bool:
    if i == j:
        return False
    if topology == "full":
        return True
    elif topology == "ring":
        return j == (i + 1) % n or j == (i - 1) % n  # 现在严格按环状连接
    elif topology == "star":
        return i == 0 or j == 0
    elif topology == "tree":
        parent = (j - 1) // n_value  # 计算 j 的父节点
        return i == parent and j < n  # 现在严格保证树状拓扑
    return False

def generate_probability_matrix(n: int, topology: str, n_value: int) -> List[List[float]]:
    matrix = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if is_connection_allowed(i, j, n, topology, n_value):
                matrix[i][j] = 1.0
    return matrix

def is_message_delivered(prob_matrix: List[List[float]], src: int, dst: int, topology: str, n_value: int) -> bool:
    """ 判断从 src 到 dst 的消息是否能成功传输 """
    if not is_connection_allowed(src, dst, len(prob_matrix), topology, n_value):
        return False  # 如果拓扑结构不允许，则直接返回 False

    transmission_probability = prob_matrix[src][dst]  # 获取传输概率
    return random.random() <= transmission_probability  # 按概率决定是否传输成功

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
    print("Received parameters:", params.model_dump())
    n = params.n
    m = params.m
    topology = params.topology
    n_value = params.n_value if params.n_value is not None else 2
    faulty_proposer = params.faulty_proposer
    allow_tampering = params.allow_tampering



    if params.probability_matrix is not None:
        prob_matrix = params.probability_matrix
    else:
        prob_matrix = generate_probability_matrix(n, topology, n_value)

    # ----------- 预准备阶段（Pre-Prepare）-----------
    pre_prepare = []
    for i in range(n):
        if i == 0 or is_message_delivered(prob_matrix, 0, i, topology, n_value):
            if is_honest(0, n, m, faulty_proposer):
                value = 0
            else:
                value = random.choice([0, 1])
            tampered = not is_honest(0, n, m, faulty_proposer)
            dst = None if i == 0 else i
        else:
            value = None
            tampered = False
            dst = i
        
        msg = Message(src=0, dst=dst, value=value, tampered=tampered)
        pre_prepare.append(msg)

    # ----------- 准备阶段（Prepare）-----------
    prepare = []
    for src in range(n):
        # 修改部分：如果发送者是主节点（节点 0），则不发送准备消息
        if src == 0:
            prepare.append([])
            continue
        msgs = []
        for dst in range(n):
            if src == dst:
                continue
            if is_message_delivered(prob_matrix, src, dst, topology, n_value):
                if is_honest(src, n, m, faulty_proposer):
                    value = pre_prepare[src].value
                else:
                    value = random.choice([0, 1]) if allow_tampering else None
                tampered = (value != pre_prepare[src].value) if pre_prepare[src].value is not None else False
                msg = Message(src=src, dst=dst, value=value, tampered=tampered)
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
            if is_message_delivered(prob_matrix, src, dst, topology, n_value):
                if is_honest(src, n, m, faulty_proposer) or not allow_tampering:
                    value = accepted_in_prepare[src]
                else:
                    value = random.choice([0, 1])
                tampered = not is_honest(src, n, m, faulty_proposer)
                msg = Message(src=src, dst=dst, value=value, tampered=tampered)
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
