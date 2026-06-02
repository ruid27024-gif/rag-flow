# conda activate rag-flow
# source .venv/bin/activate
# export PYTHONPATH=$(pwd)
# pkill -f "ragflow_server.py|task_executor.py"
# bash docker/launch_backend_service.sh

# deactivate
conda activate rag-flow
export PYTHONPATH=$(pwd)
python api/ragflow_server.py

cd /home/hit802/RAG1/ragflow/web
npm install
npm run dev


conda activate rag-flow
cd /home/hit802/RAG1/ragflow
export PYTHONPATH=$(pwd)
python rag/svr/task_executor.py


conda activate rag-flow
export PYTHONPATH=$(pwd)
cd admin/server
python admin_server.py 


# 注册ngrok后的token
# ngrok config add-authtoken 3EWAQ1p7AeXL7sGhVk0NS8GOunZ_VEZnEHM87QjWNeadoWMW
# 配置白名单
# https://dashboard.ngrok.com/ip-policies 
# 白名单id
# vim policy.yml
# 绑定
./ngrok http http://localhost:9222  --traffic-policy-file ./policy.yml
