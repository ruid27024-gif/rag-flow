import os
os.environ["RAGAS_DO_NOT_TRACK"] = "true"
os.environ["OPENAI_API_KEY"] = "sk-031cbd771af24c07937602182ffe7993"
os.environ["OPENAI_API_BASE"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall
from openai import OpenAI
from ragas.llms import llm_factory
import inspect

client = None
model_name = "qwen3-max"
client = OpenAI(
    api_key="sk-031cbd771af24c07937602182ffe7993",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

from langchain_openai import ChatOpenAI
# from ragas.llms.base import LangchainLLM # Not found

try:
    openai_model = ChatOpenAI(
        model_name=model_name,
        openai_api_key="sk-031cbd771af24c07937602182ffe7993",
        openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    # ragas_llm = LangchainLLM(openai_model)
    ragas_llm = openai_model # Try passing directly
except Exception as e:
    print(f"Error initializing LLM: {e}")
    ragas_llm = None

base_url = getattr(client, "base_url", None)

def run_evaluation(dataset):
    # In ragas 0.1.x, we pass llm to evaluate
    metrics = [Faithfulness, ContextPrecision, ContextRecall,AnswerRelevancy]
    # try:
    #     if base_url is None:
    #         metrics.insert(1, AnswerRelevancy)
    # except Exception:
    #     pass
        
    # Note: In 0.1.x, metrics list usually contains classes or instances?
    # Usually instances: [Faithfulness(), ...]
    # But if we want to rely on evaluate injection, instances are fine.
    
    metrics_instances = [m() for m in metrics]
    
    results = evaluate(dataset=dataset, metrics=metrics_instances, llm=ragas_llm)
    with open("success.txt", "w") as f:
        f.write("Evaluation completed successfully!")
    return results

def prepare_eval_data():
    """
    Load data from eval/final_answer.json and prepare for Ragas evaluation.
    """
    import json
    
    # Use absolute path or relative to the script
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "final_answer.json")
    print(f"[DEBUG-HY] Loading dataset from: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    dataset_list = []
    for item in data:
        # Extract contexts from model_references
        # model_references contains a list of dicts with 'content'
        contexts = [ref["content"] for ref in item.get("model_references", [])]
        
        dataset_list.append({
            "question": item.get("question", ""),
            "answer": item.get("model_answer", ""),
            "contexts": contexts,
            "ground_truth": item.get("answer", ""), 
        })
    dataset_list = dataset_list[:1]
    print(f"[DEBUG-HY] Loaded {len(dataset_list)} samples.")
    eval_dataset = Dataset.from_list(dataset_list)
    return eval_dataset


if __name__ == "__main__":
    # 1. 准备数据
    eval_dataset = prepare_eval_data()
    
    # 2. 运行评估
    eval_results = run_evaluation(eval_dataset)
    
    # 3. 输出结果
    print("\n====== 评估总分 ======")
    print(eval_results)
    
    
    # 4. 导出详细结果到 Excel (方便人工复查)
    try:
        df = eval_results.to_pandas()
        df.to_excel("ragflow_eval_report.xlsx", index=False)
        print("\n详细报告已保存为 ragflow_eval_report.xlsx")
    except PermissionError:
        print("\n[错误] 无法保存 Excel 文件，请关闭 'ragflow_eval_report.xlsx' 后重试。")
        # 尝试保存为带时间戳的副本
        import time
        ts = int(time.time())
        backup_name = f"ragflow_eval_report_{ts}.xlsx"
        df.to_excel(backup_name, index=False)
        print(f"已保存副本为: {backup_name}")
