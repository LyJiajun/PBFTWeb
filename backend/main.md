from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import random
import math

app = FastAPI()


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
    """
    根据拓扑类型判断节点 i 到节点 j 是否允许通信（前端中用于生成输入矩阵）。
    i==j 的情况一律返回 False。
    """
    if i == j:
        return False
    if topology == "full":
        return True
    elif topology == "ring":
        # 在环形拓扑中，假设仅允许从 i 到 (i+1 mod n) 的连接
        return j == (i + 1) % n
    elif topology == "star":
        # 星型拓扑中，以 0 号为中心，其它节点与 0 相连
        return i == 0 or j == 0
    elif topology == "tree":
        # 假设节点 i 的子节点编号为：i*n_value+1 到 i*n_value+n_value（不超过 n）
        return j >= (i * n_value + 1) and j <= (i * n_value + n_value) and j < n
    return False


def generate_probability_matrix(n: int, topology: str, n_value: int) -> List[List[float]]:
    """
    生成一个 n×n 的概率矩阵，对允许通信的边赋默认概率 1（其余 0）。
    """
    matrix = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if is_connection_allowed(i, j, n, topology, n_value):
                matrix[i][j] = 1.0  # 默认100%传输成功
    return matrix


def is_message_delivered(prob_matrix: List[List[float]], src: int, dst: int) -> bool:
    """
    模拟消息传输：采用广度优先搜索（BFS），沿着概率矩阵中大于 0 的边进行随机传输。
    对于每条边：若 random.random() <= p 则认为消息“传递成功”。
    注意：由于每次调用都重新随机，所以在整个模拟中相同的
    is_message_delivered 调用可能得到不同结果（与前端逻辑一致）。
    """
    if src == dst:
        return True
    n = len(prob_matrix)
    visited = [False] * n
    queue = [src]
    while queue:
        node = queue.pop(0)
        if node == dst:
            return True
        visited[node] = True
        for i in range(n):
            if not visited[i] and prob_matrix[node][i] > 0:
                if random.random() <= prob_matrix[node][i]:
                    queue.append(i)
    return False


def is_honest(i: int, n: int, m: int, faulty_proposer: bool) -> bool:
    """
    根据参数判断节点 i 是否诚实。
    若 m==0，则所有节点都诚实。
    当 faulty_proposer 为 True 时，认为提议者（节点 0）故障，其它节点中前 n-m 个诚实。
    当 faulty_proposer 为 False 时，则节点 0 诚实，其它节点中编号小于 n-m 的诚实。
    """
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

    # 若前端未传入概率矩阵，则自动根据拓扑生成默认矩阵
    if params.probability_matrix is not None:
        prob_matrix = params.probability_matrix
    else:
        prob_matrix = generate_probability_matrix(n, topology, n_value)

    # ----------- 预准备阶段（Pre-Prepare）-----------
    # 节点 0 发出预准备消息；其它节点仅在“消息传递成功”时接收到消息
    pre_prepare = []
    for i in range(n):
        if i == 0 or is_message_delivered(prob_matrix, 0, i):
            if is_honest(0, n, m, faulty_proposer):
                value = 0
            else:
                value = random.choice([0, 1])
            tampered = not is_honest(0, n, m, faulty_proposer)
            # 对于 proposer 自身，dst 置为 None
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
        msgs = []
        for dst in range(n):
            if src == dst:
                continue
            if is_message_delivered(prob_matrix, src, dst):
                if is_honest(src, n, m, faulty_proposer):
                    value = pre_prepare[src].value
                else:
                    # 当允许篡改时，恶意节点可能随机发送 0 或 1
                    value = random.choice([0, 1]) if allow_tampering else None
                # 若发送的值与其预准备消息不同，则视为篡改
                tampered = (value != pre_prepare[src].value) if pre_prepare[src].value is not None else False
                msg = Message(src=src, dst=dst, value=value, tampered=tampered)
                msgs.append(msg)
        prepare.append(msgs)

    def accepted_value_in_prepare(i: int) -> Optional[int]:
        """
        对于节点 i：
          - 若不诚实，返回 None；
          - 否则统计其收到的准备消息中与预准备消息一致的比例（包括预准备消息本身），
            若达到 2/3 则“接受”该值，否则返回 -1 表示拒绝。
        """
        if not is_honest(i, n, m, faulty_proposer):
            return None
        valid = 0
        total = len(prepare[i])
        # 遍历准备消息
        for msg in prepare[i]:
            # 此处判断可以加入额外条件，例如：仅计算 msg.dst != i 的消息
            if is_message_delivered(prob_matrix, msg.src, msg.dst):
                if msg.value == pre_prepare[i].value:
                    valid += 1
        # 将预准备消息也纳入统计，相当于 valid+1 和 total+1
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
            if is_message_delivered(prob_matrix, src, dst):
                if is_honest(src, n, m, faulty_proposer) or not allow_tampering:
                    value = accepted_in_prepare[src]
                else:
                    value = random.choice([0, 1])
                tampered = not is_honest(src, n, m, faulty_proposer)
                msg = Message(src=src, dst=dst, value=value, tampered=tampered)
                commit[dst].append(msg)

    def accepted_value_in_commit(i: int) -> Optional[int]:
        """
        对于节点 i：
          - 若不诚实，返回 None；
          - 否则结合其收到的所有提交消息和自己准备阶段的接受值，
            若某一值（0 或 1）的比例达到 2/3，则返回该值，否则返回 -1 表示拒绝。
        """
        if not is_honest(i, n, m, faulty_proposer):
            return None
        values = []
        for msg in commit[i]:
            if msg.value is not None and msg.value >= 0:
                values.append(msg.value)
        # 加入自身准备阶段的接受值
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

    # ----------- 判断最终共识结果 -----------
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


# ----------------------------
# 运行 FastAPI 应用（调试时可直接运行）
# ----------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
