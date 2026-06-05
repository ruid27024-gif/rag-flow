import xgboost as xgb
import numpy as np

print(f"当前 XGBoost 版本: {xgb.__version__}")

# 准备测试数据
data = np.random.rand(100, 10)
label = np.random.randint(0, 2, 100)

try:
    # 创建数据矩阵
    dtrain = xgb.DMatrix(data, label=label)

    # 设置参数，关键是要指定 tree_method 为 gpu_hist
    params = {
        'tree_method': 'gpu_hist',  # 这是启用 GPU 的关键
        'device': 'cuda',
        'objective': 'binary:logistic',
        'eval_metric': 'logloss'
    }
    
    # 开始训练
    booster = xgb.train(params, dtrain, num_boost_round=10)

    print("✅ 成功！XGBoost 成功在 GPU 上执行了训练任务。")
    
except Exception as e:
    print(f"❌ 失败！XGBoost 无法使用 GPU，报错信息如下：\n{e}")