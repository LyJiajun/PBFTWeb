# 用官方 Python 镜像
FROM python:3.9-slim

# 切换工作目录
WORKDIR /app

# 复制依赖文件，安装依赖
COPY requirements.txt .
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制所有代码
COPY . .

# 启动服务（按你的框架定）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
