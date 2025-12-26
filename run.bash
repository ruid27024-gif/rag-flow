conda activate rag-flow
source .venv/bin/activate
export PYTHONPATH=$(pwd)
pkill -f "ragflow_server.py|task_executor.py"
bash docker/launch_backend_service.sh