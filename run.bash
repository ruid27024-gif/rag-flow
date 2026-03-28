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