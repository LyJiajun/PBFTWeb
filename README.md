# 1. 构建前端项目
cd frontend
npm run build

# 2. 上传打包后的前端资源到服务器
scp -r dist/* root@47.108.222.71:/data/vue-app/


# 1. 上传后端代码到服务器
scp -r backend root@47.108.222.71:/data/

# 2. 登录服务器并重新构建后端镜像
ssh root@47.108.222.71

cd /data/backend
docker build -t python-backend .
docker rm -f backend-container || true
docker run -d --name backend-container -p 8000:8000 python-backend

sudo nginx -t
sudo systemctl restart nginx