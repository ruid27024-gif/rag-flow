import dashscope
import json

dashscope.api_key = 'sk-ws-H.EDIHPRL.RRr3.MEQCHybUX2NyotJScLSrKWV6lAA5niqfAv-I7n8GlL6NrSQCIQCFJieAnNLTw1yKk50U4PKdQ70Dr0qkNTczLQufruFwNQ'

resp = dashscope.TextEmbedding.call(
    model='text-embedding-v2',
    input='介绍一下石灰石'
)

# 打印原始响应，看 output 是否为 None
print(type(resp))       # 看看是什么类型
print(dir(resp))        # 看看有哪些方法
print(resp.output)      # 尝试用点号取值，而不是 resp['output']