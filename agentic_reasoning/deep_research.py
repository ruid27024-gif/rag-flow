#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import logging
import re
from functools import partial
from agentic_reasoning.prompts import BEGIN_SEARCH_QUERY, BEGIN_SEARCH_RESULT, END_SEARCH_RESULT, MAX_SEARCH_LIMIT, \
    END_SEARCH_QUERY, REASON_PROMPT, RELEVANT_EXTRACTION_PROMPT
from api.db.services.llm_service import LLMBundle
from rag.nlp import extract_between
from rag.prompts import kb_prompt
from rag.utils.tavily_conn import Tavily


# class DeepResearcher:
#     def __init__(self,
#                  chat_mdl: LLMBundle,
#                  prompt_config: dict,
#                  kb_retrieve: partial = None,
#                  kg_retrieve: partial = None
#                  ):
#         self.chat_mdl = chat_mdl
#         self.prompt_config = prompt_config
#         self._kb_retrieve = kb_retrieve
#         self._kg_retrieve = kg_retrieve

#     def _remove_tags(text: str, start_tag: str, end_tag: str) -> str:
#         """General Tag Removal Method"""
#         pattern = re.escape(start_tag) + r"(.*?)" + re.escape(end_tag)
#         return re.sub(pattern, "", text)

#     @staticmethod
#     def _remove_query_tags(text: str) -> str:
#         """Remove Query Tags"""
#         return DeepResearcher._remove_tags(text, BEGIN_SEARCH_QUERY, END_SEARCH_QUERY)

#     @staticmethod
#     def _remove_result_tags(text: str) -> str:
#         """Remove Result Tags"""
#         return DeepResearcher._remove_tags(text, BEGIN_SEARCH_RESULT, END_SEARCH_RESULT)

#     async def _generate_reasoning(self, msg_history):
#         """Generate reasoning steps"""
#         query_think = ""
#         if msg_history[-1]["role"] != "user":
#             msg_history.append({"role": "user", "content": "Continues reasoning with the new information.\n"})
#         else:
#             msg_history[-1]["content"] += "\n\nContinues reasoning with the new information.\n"
            
#         async for ans in self.chat_mdl.async_chat_streamly(REASON_PROMPT, msg_history, {"temperature": 0.7}):
#             ans = re.sub(r"^.*</think>", "", ans, flags=re.DOTALL)
#             if not ans:
#                 continue
#             query_think = ans
#             yield query_think
#             query_think = ""
#         yield query_think

#     def _extract_search_queries(self, query_think, question, step_index):
#         """Extract search queries from thinking"""
#         queries = extract_between(query_think, BEGIN_SEARCH_QUERY, END_SEARCH_QUERY)
#         if not queries and step_index == 0:
#             # If this is the first step and no queries are found, use the original question as the query
#             queries = [question]
#         return queries

#     def _truncate_previous_reasoning(self, all_reasoning_steps):
#         """Truncate previous reasoning steps to maintain a reasonable length"""
#         truncated_prev_reasoning = ""
#         for i, step in enumerate(all_reasoning_steps):
#             truncated_prev_reasoning += f"Step {i + 1}: {step}\n\n"

#         prev_steps = truncated_prev_reasoning.split('\n\n')
#         if len(prev_steps) <= 5:
#             truncated_prev_reasoning = '\n\n'.join(prev_steps)
#         else:
#             truncated_prev_reasoning = ''
#             for i, step in enumerate(prev_steps):
#                 if i == 0 or i >= len(prev_steps) - 4 or BEGIN_SEARCH_QUERY in step or BEGIN_SEARCH_RESULT in step:
#                     truncated_prev_reasoning += step + '\n\n'
#                 else:
#                     if truncated_prev_reasoning[-len('\n\n...\n\n'):] != '\n\n...\n\n':
#                         truncated_prev_reasoning += '...\n\n'
        
#         return truncated_prev_reasoning.strip('\n')

#     def _retrieve_information(self, search_query):
#         """Retrieve information from different sources"""
#         # 1. Knowledge base retrieval
#         kbinfos = []
#         try:
#             kbinfos = self._kb_retrieve(question=search_query) if self._kb_retrieve else {"chunks": [], "doc_aggs": []}
#         except Exception as e:
#             logging.error(f"Knowledge base retrieval error: {e}")

#         # 2. Web retrieval (if Tavily API is configured)
#         try:
#             if self.prompt_config.get("tavily_api_key"):
#                 tav = Tavily(self.prompt_config["tavily_api_key"])
#                 tav_res = tav.retrieve_chunks(search_query)
#                 kbinfos["chunks"].extend(tav_res["chunks"])
#                 kbinfos["doc_aggs"].extend(tav_res["doc_aggs"])
#         except Exception as e:
#             logging.error(f"Web retrieval error: {e}")

#         # 3. Knowledge graph retrieval (if configured)
#         try:
#             if self.prompt_config.get("use_kg") and self._kg_retrieve:
#                 ck = self._kg_retrieve(question=search_query)
#                 if ck["content_with_weight"]:
#                     kbinfos["chunks"].insert(0, ck)
#         except Exception as e:
#             logging.error(f"Knowledge graph retrieval error: {e}")

#         return kbinfos

#     def _update_chunk_info(self, chunk_info, kbinfos):
#         """Update chunk information for citations"""
#         if not chunk_info["chunks"]:
#             # If this is the first retrieval, use the retrieval results directly
#             for k in chunk_info.keys():
#                 chunk_info[k] = kbinfos[k]
#         else:
#             # Merge newly retrieved information, avoiding duplicates
#             cids = [c["chunk_id"] for c in chunk_info["chunks"]]
#             for c in kbinfos["chunks"]:
#                 if c["chunk_id"] not in cids:
#                     chunk_info["chunks"].append(c)
                    
#             dids = [d["doc_id"] for d in chunk_info["doc_aggs"]]
#             for d in kbinfos["doc_aggs"]:
#                 if d["doc_id"] not in dids:
#                     chunk_info["doc_aggs"].append(d)

#     async def _extract_relevant_info(self, truncated_prev_reasoning, search_query, kbinfos):
#         """Extract and summarize relevant information"""
#         summary_think = ""
#         async for ans in self.chat_mdl.async_chat_streamly(
#                 RELEVANT_EXTRACTION_PROMPT.format(
#                     prev_reasoning=truncated_prev_reasoning,
#                     search_query=search_query,
#                     document="\n".join(kb_prompt(kbinfos, 4096))
#                 ),
#                 [{"role": "user",
#                   "content": f'Now you should analyze each web page and find helpful information based on the current search query "{search_query}" and previous reasoning steps.'}],
#                 {"temperature": 0.7}):
#             ans = re.sub(r"^.*</think>", "", ans, flags=re.DOTALL)
#             if not ans:
#                 continue
#             summary_think = ans
#             yield summary_think
#             summary_think = ""
        
#         yield summary_think

#     async def thinking(self, chunk_info: dict, question: str):
#         executed_search_queries = []
#         msg_history = [{"role": "user", "content": f'Question:\"{question}\"\n'}]
#         all_reasoning_steps = []
#         think = "<think>"
        
#         for step_index in range(MAX_SEARCH_LIMIT + 1):
#             # Check if the maximum search limit has been reached
#             if step_index == MAX_SEARCH_LIMIT - 1:
#                 summary_think = f"\n{BEGIN_SEARCH_RESULT}\nThe maximum search limit is exceeded. You are not allowed to search.\n{END_SEARCH_RESULT}\n"
#                 yield {"answer": think + summary_think + "</think>", "reference": {}, "audio_binary": None}
#                 all_reasoning_steps.append(summary_think)
#                 msg_history.append({"role": "assistant", "content": summary_think})
#                 break

#             # Step 1: Generate reasoning
#             query_think = ""
#             async for ans in self._generate_reasoning(msg_history):
#                 query_think = ans
#                 yield {"answer": think + self._remove_query_tags(query_think) + "</think>", "reference": {}, "audio_binary": None}

#             think += self._remove_query_tags(query_think)
#             all_reasoning_steps.append(query_think)
            
#             # Step 2: Extract search queries
#             queries = self._extract_search_queries(query_think, question, step_index)
#             if not queries and step_index > 0:
#                 # If not the first step and no queries, end the search process
#                 break

#             # Process each search query
#             for search_query in queries:
#                 logging.info(f"[THINK]Query: {step_index}. {search_query}")
#                 msg_history.append({"role": "assistant", "content": search_query})
#                 think += f"\n\n> {step_index + 1}. {search_query}\n\n"
#                 yield {"answer": think + "</think>", "reference": {}, "audio_binary": None}

#                 # Check if the query has already been executed
#                 if search_query in executed_search_queries:
#                     summary_think = f"\n{BEGIN_SEARCH_RESULT}\nYou have searched this query. Please refer to previous results.\n{END_SEARCH_RESULT}\n"
#                     yield {"answer": think + summary_think + "</think>", "reference": {}, "audio_binary": None}
#                     all_reasoning_steps.append(summary_think)
#                     msg_history.append({"role": "user", "content": summary_think})
#                     think += summary_think
#                     continue
                
#                 executed_search_queries.append(search_query)
                
#                 # Step 3: Truncate previous reasoning steps
#                 truncated_prev_reasoning = self._truncate_previous_reasoning(all_reasoning_steps)
                
#                 # Step 4: Retrieve information
#                 kbinfos = self._retrieve_information(search_query)
                
#                 # Step 5: Update chunk information
#                 self._update_chunk_info(chunk_info, kbinfos)
                
#                 # Step 6: Extract relevant information
#                 think += "\n\n"
#                 summary_think = ""
#                 async for ans in self._extract_relevant_info(truncated_prev_reasoning, search_query, kbinfos):
#                     summary_think = ans
#                     yield {"answer": think + self._remove_result_tags(summary_think) + "</think>", "reference": {}, "audio_binary": None}

#                 all_reasoning_steps.append(summary_think)
#                 msg_history.append(
#                     {"role": "user", "content": f"\n\n{BEGIN_SEARCH_RESULT}{summary_think}{END_SEARCH_RESULT}\n\n"})
#                 think += self._remove_result_tags(summary_think)
#                 logging.info(f"[THINK]Summary: {step_index}. {summary_think}")

#         yield think + "</think>"

# class DeepResearcher:
#     def __init__(self,
#                  chat_mdl: LLMBundle,
#                  prompt_config: dict,
#                  kb_retrieve: partial = None,
#                  kg_retrieve: partial = None
#                  ):
#         self.chat_mdl = chat_mdl
#         self.prompt_config = prompt_config
#         self._kb_retrieve = kb_retrieve
#         self._kg_retrieve = kg_retrieve

#     def _pack_answer(self, answer: str, reference: dict = None):
#         """
#         快照模式输出。

#         注意：
#         这里 answer 是完整快照，不是增量。
#         适合前端每次替换 message.content 的场景。
#         """
#         return {
#             "answer": answer or "",
#             "reference": reference or {},
#             "audio_binary": None,
#         }

#     @staticmethod
#     def _remove_tag_block(text: str, start_tag: str, end_tag: str) -> str:
#         """
#         删除整个 tag block，包括里面内容。

#         用于 search query：
#         <query>xxx</query> -> ""

#         同时处理流式未闭合情况：
#         <query>xxx -> ""
#         """
#         if not text:
#             return text

#         # 删除完整 block
#         pattern = re.escape(start_tag) + r".*?" + re.escape(end_tag)
#         text = re.sub(pattern, "", text, flags=re.DOTALL)

#         # 删除未闭合 block，避免前端看到 <|begin_search_query|> 半截内容
#         dangling_pattern = re.escape(start_tag) + r".*$"
#         text = re.sub(dangling_pattern, "", text, flags=re.DOTALL)

#         return text

#     @staticmethod
#     def _remove_tag_markers(text: str, start_tag: str, end_tag: str) -> str:
#         """
#         只删除 tag 本身，保留里面内容。

#         用于 search result：
#         <result>abc</result> -> abc
#         """
#         if not text:
#             return text

#         return text.replace(start_tag, "").replace(end_tag, "")

#     @staticmethod
#     def _remove_query_tags(text: str) -> str:
#         """
#         search query 不直接展示。
#         因为后面会用：

#         > 1. query

#         单独展示。
#         """
#         return DeepResearcher._remove_tag_block(
#             text,
#             BEGIN_SEARCH_QUERY,
#             END_SEARCH_QUERY
#         )

#     @staticmethod
#     def _remove_result_tags(text: str) -> str:
#         """
#         search result 的内容要展示，所以只删除标签本身。
#         """
#         return DeepResearcher._remove_tag_markers(
#             text,
#             BEGIN_SEARCH_RESULT,
#             END_SEARCH_RESULT
#         )

#     @staticmethod
#     def _strip_model_think(text: str) -> str:
#         """
#         去掉模型内部可能输出的 </think> 之前内容。
#         """
#         if not text:
#             return text

#         return re.sub(r"^.*?</think>", "", text, flags=re.DOTALL)

#     async def _generate_reasoning(self, msg_history):
#         """
#         Generate reasoning steps.

#         返回 full_text 快照。

#         兼容两种模型流式模式：
#         1. 模型每次返回 delta
#         2. 模型每次返回完整 snapshot
#         """
#         if msg_history[-1]["role"] != "user":
#             msg_history.append({
#                 "role": "user",
#                 "content": "Continues reasoning with the new information.\n"
#             })
#         else:
#             msg_history[-1]["content"] += "\n\nContinues reasoning with the new information.\n"

#         full_text = ""

#         async for ans in self.chat_mdl.async_chat_streamly(
#             REASON_PROMPT,
#             msg_history,
#             {"temperature": 0.7}
#         ):
#             ans = self._strip_model_think(ans or "")

#             if not ans:
#                 continue

#             # 模型返回 snapshot
#             if ans.startswith(full_text):
#                 full_text = ans
#             else:
#                 # 模型返回 delta
#                 full_text += ans

#             yield full_text

#     def _extract_search_queries(self, query_think, question, step_index):
#         """
#         Extract search queries from thinking.
#         """
#         queries = extract_between(
#             query_think,
#             BEGIN_SEARCH_QUERY,
#             END_SEARCH_QUERY
#         )

#         if not queries and step_index == 0:
#             queries = [question]

#         cleaned = []
#         seen = set()

#         for q in queries:
#             q = (q or "").strip()
#             if not q:
#                 continue

#             if q in seen:
#                 continue

#             seen.add(q)
#             cleaned.append(q)

#         return cleaned

#     def _truncate_previous_reasoning(self, all_reasoning_steps):
#         """
#         Truncate previous reasoning steps to maintain a reasonable length.
#         """
#         truncated_prev_reasoning = ""

#         for i, step in enumerate(all_reasoning_steps):
#             truncated_prev_reasoning += f"Step {i + 1}: {step}\n\n"

#         prev_steps = truncated_prev_reasoning.split('\n\n')

#         if len(prev_steps) <= 5:
#             truncated_prev_reasoning = '\n\n'.join(prev_steps)
#         else:
#             truncated_prev_reasoning = ''

#             for i, step in enumerate(prev_steps):
#                 if (
#                     i == 0
#                     or i >= len(prev_steps) - 4
#                     or BEGIN_SEARCH_QUERY in step
#                     or BEGIN_SEARCH_RESULT in step
#                 ):
#                     truncated_prev_reasoning += step + '\n\n'
#                 else:
#                     if not truncated_prev_reasoning.endswith('\n\n...\n\n'):
#                         truncated_prev_reasoning += '...\n\n'

#         truncated_prev_reasoning = truncated_prev_reasoning.strip('\n')

#         # 防止 Dashscope 输入过长
#         MAX_PREV_REASONING_CHARS = 12000
#         if len(truncated_prev_reasoning) > MAX_PREV_REASONING_CHARS:
#             truncated_prev_reasoning = truncated_prev_reasoning[-MAX_PREV_REASONING_CHARS:]

#         return truncated_prev_reasoning

#     def _normalize_kbinfos(self, kbinfos: dict) -> dict:
#         """
#         规范检索结果，避免缺少 doc_id / chunk_id 报错。
#         """
#         if not isinstance(kbinfos, dict):
#             kbinfos = {}

#         kbinfos.setdefault("chunks", [])
#         kbinfos.setdefault("doc_aggs", [])

#         existing_doc_ids = set()
#         normalized_doc_aggs = []

#         for d in kbinfos.get("doc_aggs", []):
#             if not isinstance(d, dict):
#                 continue

#             doc_id = d.get("doc_id") or d.get("document_id") or d.get("id")

#             if not doc_id:
#                 continue

#             d["doc_id"] = doc_id
#             d["document_id"] = doc_id

#             if "doc_name" not in d:
#                 d["doc_name"] = (
#                     d.get("name")
#                     or d.get("title")
#                     or d.get("url")
#                     or str(doc_id)
#                 )

#             if doc_id not in existing_doc_ids:
#                 normalized_doc_aggs.append(d)
#                 existing_doc_ids.add(doc_id)

#         kbinfos["doc_aggs"] = normalized_doc_aggs

#         normalized_chunks = []

#         for idx, c in enumerate(kbinfos.get("chunks", [])):
#             if not isinstance(c, dict):
#                 continue

#             chunk_id = (
#                 c.get("chunk_id")
#                 or c.get("id")
#                 or f"deep_research_chunk_{idx}_{abs(hash(str(c)))}"
#             )

#             c["chunk_id"] = chunk_id
#             c["id"] = c.get("id") or chunk_id

#             doc_id = (
#                 c.get("doc_id")
#                 or c.get("document_id")
#                 or c.get("docnm_kwd")
#                 or c.get("url")
#             )

#             if not doc_id:
#                 doc_id = f"deep_research_doc_{chunk_id}"

#             c["doc_id"] = doc_id
#             c["document_id"] = doc_id

#             if doc_id not in existing_doc_ids:
#                 kbinfos["doc_aggs"].append({
#                     "doc_id": doc_id,
#                     "document_id": doc_id,
#                     "doc_name": (
#                         c.get("doc_name")
#                         or c.get("title")
#                         or c.get("url")
#                         or "Deep Research"
#                     ),
#                     "url": c.get("url", "")
#                 })
#                 existing_doc_ids.add(doc_id)

#             normalized_chunks.append(c)

#         kbinfos["chunks"] = normalized_chunks

#         return kbinfos

#     def _retrieve_information(self, search_query):
#         """
#         Retrieve information from different sources.
#         """
#         kbinfos = {"chunks": [], "doc_aggs": []}

#         # 1. Knowledge base retrieval
#         try:
#             if self._kb_retrieve:
#                 kb_res = self._kb_retrieve(question=search_query)

#                 if isinstance(kb_res, dict):
#                     kbinfos = kb_res
#         except Exception as e:
#             logging.error(f"Knowledge base retrieval error: {e}")

#         kbinfos = self._normalize_kbinfos(kbinfos)

#         # 2. Web retrieval Tavily
#         try:
#             if self.prompt_config.get("tavily_api_key"):
#                 tav = Tavily(self.prompt_config["tavily_api_key"])
#                 tav_res = tav.retrieve_chunks(search_query)

#                 tav_res = self._normalize_kbinfos(tav_res)

#                 kbinfos["chunks"].extend(tav_res.get("chunks", []))
#                 kbinfos["doc_aggs"].extend(tav_res.get("doc_aggs", []))

#                 kbinfos = self._normalize_kbinfos(kbinfos)
#         except Exception as e:
#             logging.error(f"Web retrieval error: {e}")

#         # 3. Knowledge graph retrieval
#         try:
#             if self.prompt_config.get("use_kg") and self._kg_retrieve:
#                 ck = self._kg_retrieve(question=search_query)

#                 if isinstance(ck, dict) and ck.get("content_with_weight"):
#                     kg_infos = {
#                         "chunks": [ck],
#                         "doc_aggs": []
#                     }

#                     kg_infos = self._normalize_kbinfos(kg_infos)

#                     kbinfos["chunks"] = (
#                         kg_infos.get("chunks", []) + kbinfos.get("chunks", [])
#                     )
#                     kbinfos["doc_aggs"].extend(kg_infos.get("doc_aggs", []))

#                     kbinfos = self._normalize_kbinfos(kbinfos)
#         except Exception as e:
#             logging.error(f"Knowledge graph retrieval error: {e}")

#         return self._normalize_kbinfos(kbinfos)

#     def _update_chunk_info(self, chunk_info, kbinfos):
#         """
#         Update chunk information for citations.
#         """
#         if not isinstance(chunk_info, dict):
#             return

#         chunk_info.setdefault("chunks", [])
#         chunk_info.setdefault("doc_aggs", [])

#         kbinfos = self._normalize_kbinfos(kbinfos)
#         chunk_info = self._normalize_kbinfos(chunk_info)

#         existing_chunk_ids = set()

#         for c in chunk_info.get("chunks", []):
#             cid = c.get("chunk_id") or c.get("id")
#             if cid:
#                 existing_chunk_ids.add(cid)

#         for c in kbinfos.get("chunks", []):
#             cid = c.get("chunk_id") or c.get("id")

#             if not cid:
#                 continue

#             if cid not in existing_chunk_ids:
#                 chunk_info["chunks"].append(c)
#                 existing_chunk_ids.add(cid)

#         existing_doc_ids = set()

#         for d in chunk_info.get("doc_aggs", []):
#             did = d.get("doc_id") or d.get("document_id") or d.get("id")

#             if did:
#                 d["doc_id"] = did
#                 d["document_id"] = did
#                 existing_doc_ids.add(did)

#         for d in kbinfos.get("doc_aggs", []):
#             did = d.get("doc_id") or d.get("document_id") or d.get("id")

#             if not did:
#                 continue

#             d["doc_id"] = did
#             d["document_id"] = did

#             if did not in existing_doc_ids:
#                 chunk_info["doc_aggs"].append(d)
#                 existing_doc_ids.add(did)

#     async def _extract_relevant_info(self, truncated_prev_reasoning, search_query, kbinfos):
#         """
#         Extract and summarize relevant information.

#         返回 full_text 快照。
#         """
#         kbinfos = self._normalize_kbinfos(kbinfos)

#         full_text = ""

#         async for ans in self.chat_mdl.async_chat_streamly(
#             RELEVANT_EXTRACTION_PROMPT.format(
#                 prev_reasoning=truncated_prev_reasoning,
#                 search_query=search_query,
#                 document="\n".join(kb_prompt(kbinfos, 4096))
#             ),
#             [{
#                 "role": "user",
#                 "content": (
#                     f'Now you should analyze each web page and find helpful information '
#                     f'based on the current search query "{search_query}" and previous reasoning steps.'
#                 )
#             }],
#             {"temperature": 0.7}
#         ):
#             ans = self._strip_model_think(ans or "")

#             if not ans:
#                 continue

#             # 模型返回 snapshot
#             if ans.startswith(full_text):
#                 full_text = ans
#             else:
#                 # 模型返回 delta
#                 full_text += ans

#             yield full_text

#     async def thinking(self, chunk_info: dict, question: str):
#         """
#         主流程。

#         注意：
#         这里是快照模式。

#         每次 yield 的 answer 都是：

#         <think>截至当前的完整思考过程</think>

#         适合前端每次替换 content 的情况。
#         """
#         executed_search_queries = []
#         msg_history = [{"role": "user", "content": f'Question:"{question}"\n'}]
#         all_reasoning_steps = []

#         if not isinstance(chunk_info, dict):
#             chunk_info = {"chunks": [], "doc_aggs": []}

#         chunk_info.setdefault("chunks", [])
#         chunk_info.setdefault("doc_aggs", [])

#         # 完整思考过程
#         think = "<think>"

#         # 先让前端出现思考框
#         yield self._pack_answer(think + "</think>")

#         for step_index in range(MAX_SEARCH_LIMIT + 1):

#             # 最大搜索次数
#             if step_index == MAX_SEARCH_LIMIT - 1:
#                 summary_raw = (
#                     f"\n{BEGIN_SEARCH_RESULT}\n"
#                     f"The maximum search limit is exceeded. You are not allowed to search.\n"
#                     f"{END_SEARCH_RESULT}\n"
#                 )

#                 summary_public = self._remove_result_tags(summary_raw)

#                 think += summary_public

#                 all_reasoning_steps.append(summary_raw)
#                 msg_history.append({
#                     "role": "assistant",
#                     "content": summary_raw
#                 })

#                 yield self._pack_answer(think + "</think>")
#                 break

#             # Step 1: Generate reasoning
#             query_think_raw = ""

#             async for full_text in self._generate_reasoning(msg_history):
#                 query_think_raw = full_text

#                 query_public = self._remove_query_tags(query_think_raw)

#                 # 快照输出：已有 think + 当前 reasoning 快照
#                 yield self._pack_answer(
#                     think + query_public + "</think>"
#                 )

#             query_public = self._remove_query_tags(query_think_raw)

#             think += query_public
#             all_reasoning_steps.append(query_think_raw)

#             # Step 2: Extract search queries
#             queries = self._extract_search_queries(
#                 query_think_raw,
#                 question,
#                 step_index
#             )

#             if not queries and step_index > 0:
#                 break

#             # Step 3: Process each search query
#             for search_query in queries:
#                 search_query = (search_query or "").strip()

#                 if not search_query:
#                     continue

#                 logging.info(f"[THINK]Query: {step_index}. {search_query}")

#                 msg_history.append({
#                     "role": "assistant",
#                     "content": search_query
#                 })

#                 search_title = f"\n\n> {step_index + 1}. {search_query}\n\n"
#                 think += search_title

#                 yield self._pack_answer(think + "</think>")

#                 # 重复搜索
#                 if search_query in executed_search_queries:
#                     summary_raw = (
#                         f"\n{BEGIN_SEARCH_RESULT}\n"
#                         f"You have searched this query. Please refer to previous results.\n"
#                         f"{END_SEARCH_RESULT}\n"
#                     )

#                     summary_public = self._remove_result_tags(summary_raw)

#                     think += summary_public

#                     all_reasoning_steps.append(summary_raw)
#                     msg_history.append({
#                         "role": "user",
#                         "content": summary_raw
#                     })

#                     yield self._pack_answer(think + "</think>")
#                     continue

#                 executed_search_queries.append(search_query)

#                 # Step 4: Truncate previous reasoning steps
#                 truncated_prev_reasoning = self._truncate_previous_reasoning(
#                     all_reasoning_steps
#                 )

#                 # Step 5: Retrieve information
#                 kbinfos = self._retrieve_information(search_query)

#                 # Step 6: Update chunk information
#                 self._update_chunk_info(chunk_info, kbinfos)

#                 # Step 7: Extract relevant information
#                 think += "\n\n"
#                 yield self._pack_answer(think + "</think>")

#                 summary_raw = ""

#                 async for full_text in self._extract_relevant_info(
#                     truncated_prev_reasoning,
#                     search_query,
#                     kbinfos
#                 ):
#                     summary_raw = full_text

#                     summary_public = self._remove_result_tags(summary_raw)

#                     # 快照输出：已有 think + 当前 summary 快照
#                     yield self._pack_answer(
#                         think + summary_public + "</think>"
#                     )

#                 summary_public = self._remove_result_tags(summary_raw)

#                 think += summary_public

#                 all_reasoning_steps.append(summary_raw)

#                 msg_history.append({
#                     "role": "user",
#                     "content": (
#                         f"\n\n{BEGIN_SEARCH_RESULT}"
#                         f"{summary_raw}"
#                         f"{END_SEARCH_RESULT}\n\n"
#                     )
#                 })

#                 logging.info(f"[THINK]Summary: {step_index}. {summary_raw}")

#         # 最终完整思考，带 reference
#         yield self._pack_answer(
#             think + "</think>",
#             reference=chunk_info
#         )

class DeepResearcher:
    def __init__(self,
                 chat_mdl: LLMBundle,
                 prompt_config: dict,
                 kb_retrieve: partial = None,
                 kg_retrieve: partial = None
                 ):
        self.chat_mdl = chat_mdl
        self.prompt_config = prompt_config
        self._kb_retrieve = kb_retrieve
        self._kg_retrieve = kg_retrieve

    # ----------------------------------------------------------------------
    # 基础输出
    # ----------------------------------------------------------------------
    def _pack_answer(self, answer: str, reference: dict = None):
        return {
            "answer": answer or "",
            "reference": reference or {},
            "audio_binary": None,
        }

    def _pack_think_snapshot(self, raw_think: str, reference: dict = None):
        """
        快照模式专用。

        raw_think 内部可以包含原始 token：
        - <|begin_search_result|>
        - <|end_search_result|>
        - Final Information
        - Final Answer
        - > 1. xxx

        输出前统一转换为用户可读格式。
        """
        raw_think = raw_think or ""

        inner = raw_think

        # 去掉外层 think，避免重复包裹
        inner = re.sub(r"^<think\b[^>]*>", "", inner, flags=re.I)
        inner = re.sub(r"</think>$", "", inner, flags=re.I)

        public_inner = self._format_public_think(inner)

        return self._pack_answer(
            f"<think>{public_inner}</think>",
            reference=reference
        )

    # ----------------------------------------------------------------------
    # 展示格式化
    # ----------------------------------------------------------------------
    @staticmethod
    def _normalize_display_tags(text: str) -> str:
        """
        兼容原始 token 和 HTML 转义后的 token。
        """
        if not text:
            return ""

        replacements = {
            "&lt;|begin_search_result|&gt;": BEGIN_SEARCH_RESULT,
            "&lt;|end_search_result|&gt;": END_SEARCH_RESULT,
            "&lt;|begin_search_query|&gt;": BEGIN_SEARCH_QUERY,
            "&lt;|end_search_query|&gt;": END_SEARCH_QUERY,
            "&gt;": ">",
        }

        for k, v in replacements.items():
            text = text.replace(k, v)

        return text

    @staticmethod
    def _format_public_think(text: str) -> str:
        """
        把内部推理 token 转成用户可读的展示文本。

        规则：
        1. <|begin_search_result|> -> 知识库召回
        2. <|end_search_result|> -> 删除
        3. Final Information -> 检索总结
        4. Final Answer -> 阶段总结
        5. > 1. xxx -> 泛化检索问题
        """
        if not text:
            return ""

        text = DeepResearcher._normalize_display_tags(text)

        # 去掉可能残留的 think 外壳
        text = re.sub(r"^<think\b[^>]*>", "", text, flags=re.I)
        text = re.sub(r"</think>$", "", text, flags=re.I)

        # --------------------------------------------------------------
        # search query block 不直接展示
        # 因为 query 会通过 > 1. xxx 转成“泛化检索问题”
        # --------------------------------------------------------------
        query_pattern = (
            re.escape(BEGIN_SEARCH_QUERY)
            + r".*?"
            + re.escape(END_SEARCH_QUERY)
        )
        text = re.sub(query_pattern, "", text, flags=re.DOTALL)

        # 流式过程中可能有未闭合 query，删掉
        dangling_query_pattern = re.escape(BEGIN_SEARCH_QUERY) + r".*$"
        text = re.sub(dangling_query_pattern, "", text, flags=re.DOTALL)

        # --------------------------------------------------------------
        # search result：第一次显示“知识库召回”，后续用分隔线
        # --------------------------------------------------------------
        parts = text.split(BEGIN_SEARCH_RESULT)

        if len(parts) > 1:
            rebuilt = [parts[0]]

            for idx, part in enumerate(parts[1:], start=1):
                if idx == 1:
                    rebuilt.append("\n\n━━━━━━━━━━━━━━━━━━━━\n知识库召回\n━━━━━━━━━━━━━━━━━━━━\n\n")
                else:
                    rebuilt.append("\n\n---\n\n")

                rebuilt.append(part)

            text = "".join(rebuilt)

        # end_search_result 删除
        text = text.replace(END_SEARCH_RESULT, "")

        # --------------------------------------------------------------
        # Final Information -> 检索总结
        # --------------------------------------------------------------
        text = re.sub(
            r"^\s*Final Information\s*[:：]?\s*",
            "\n\n━━━━━━━━━━━━━━━━━━━━\n检索总结\n━━━━━━━━━━━━━━━━━━━━\n\n",
            text,
            flags=re.I
        )

        text = re.sub(
            r"\n\s*Final Information\s*[:：]?\s*",
            "\n\n━━━━━━━━━━━━━━━━━━━━\n检索总结\n━━━━━━━━━━━━━━━━━━━━\n\n",
            text,
            flags=re.I
        )

        # --------------------------------------------------------------
        # Final Answer -> 阶段总结
        # --------------------------------------------------------------
        text = re.sub(
            r"^\s*Final Answer\s*[:：]?\s*",
            "\n\n━━━━━━━━━━━━━━━━━━━━\n阶段总结\n━━━━━━━━━━━━━━━━━━━━\n\n",
            text,
            flags=re.I
        )

        text = re.sub(
            r"\n\s*Final Answer\s*[:：]?\s*",
            "\n\n━━━━━━━━━━━━━━━━━━━━\n阶段总结\n━━━━━━━━━━━━━━━━━━━━\n\n",
            text,
            flags=re.I
        )

        # --------------------------------------------------------------
        # > 1. xxx -> 泛化检索问题
        # --------------------------------------------------------------
        text = re.sub(
            r"(?:^|\n)>\s*\d+\.\s*(.+)",
            lambda m: (
                f"\n\n━━━━━━━━━━━━━━━━━━━━\n"
                f"泛化检索问题\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"- {m.group(1).strip()}"
            )                                       ,
            text
        )

        # 无结果提示中文化
        text = text.replace(
            "No helpful information found.",
            "未检索到直接相关的信息。"
        )

        # 清理残留内部 token
        text = text.replace("<|begin_search|>", "")
        text = text.replace("<|end_search|>", "")
        text = text.replace("<|begin_search", "")
        text = text.replace("<|end", "")

        # 多余空行
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    # ----------------------------------------------------------------------
    # 原始 tag 清理工具，内部逻辑使用
    # ----------------------------------------------------------------------
    @staticmethod
    def _remove_tag_block(text: str, start_tag: str, end_tag: str) -> str:
        """
        删除整个 tag block，包括里面内容。
        """
        if not text:
            return text

        pattern = re.escape(start_tag) + r".*?" + re.escape(end_tag)
        text = re.sub(pattern, "", text, flags=re.DOTALL)

        dangling_pattern = re.escape(start_tag) + r".*$"
        text = re.sub(dangling_pattern, "", text, flags=re.DOTALL)

        return text

    @staticmethod
    def _remove_tag_markers(text: str, start_tag: str, end_tag: str) -> str:
        """
        只删除 tag 本身，保留里面内容。
        """
        if not text:
            return text

        return text.replace(start_tag, "").replace(end_tag, "")

    @staticmethod
    def _remove_query_tags(text: str) -> str:
        return DeepResearcher._remove_tag_block(
            text,
            BEGIN_SEARCH_QUERY,
            END_SEARCH_QUERY
        )

    @staticmethod
    def _remove_result_tags(text: str) -> str:
        return DeepResearcher._remove_tag_markers(
            text,
            BEGIN_SEARCH_RESULT,
            END_SEARCH_RESULT
        )

    @staticmethod
    def _strip_model_think(text: str) -> str:
        """
        去掉模型内部可能输出的 </think> 之前内容。
        """
        if not text:
            return text

        return re.sub(r"^.*?</think>", "", text, flags=re.DOTALL)

    # ----------------------------------------------------------------------
    # LLM reasoning
    # ----------------------------------------------------------------------
    async def _generate_reasoning(self, msg_history):
        """
        Generate reasoning steps.

        返回 full_text 快照。

        兼容：
        1. 模型每次返回 delta
        2. 模型每次返回完整 snapshot
        """
        if msg_history[-1]["role"] != "user":
            msg_history.append({
                "role": "user",
                "content": "Continues reasoning with the new information.\n"
            })
        else:
            msg_history[-1]["content"] += "\n\nContinues reasoning with the new information.\n"

        full_text = ""

        async for ans in self.chat_mdl.async_chat_streamly(
            REASON_PROMPT,
            msg_history,
            {"temperature": 0.7}
        ):
            ans = self._strip_model_think(ans or "")

            if not ans:
                continue

            if ans.startswith(full_text):
                full_text = ans
            else:
                full_text += ans

            yield full_text

    def _extract_search_queries(self, query_think, question, step_index):
        """
        Extract search queries from thinking.
        """
        queries = extract_between(
            query_think,
            BEGIN_SEARCH_QUERY,
            END_SEARCH_QUERY
        )

        if not queries and step_index == 0:
            queries = [question]

        cleaned = []
        seen = set()

        for q in queries:
            q = (q or "").strip()

            if not q:
                continue

            if q in seen:
                continue

            seen.add(q)
            cleaned.append(q)

        return cleaned

    def _truncate_previous_reasoning(self, all_reasoning_steps):
        """
        Truncate previous reasoning steps to maintain a reasonable length.
        """
        truncated_prev_reasoning = ""

        for i, step in enumerate(all_reasoning_steps):
            truncated_prev_reasoning += f"Step {i + 1}: {step}\n\n"

        prev_steps = truncated_prev_reasoning.split('\n\n')

        if len(prev_steps) <= 5:
            truncated_prev_reasoning = '\n\n'.join(prev_steps)
        else:
            truncated_prev_reasoning = ''

            for i, step in enumerate(prev_steps):
                if (
                    i == 0
                    or i >= len(prev_steps) - 4
                    or BEGIN_SEARCH_QUERY in step
                    or BEGIN_SEARCH_RESULT in step
                ):
                    truncated_prev_reasoning += step + '\n\n'
                else:
                    if not truncated_prev_reasoning.endswith('\n\n...\n\n'):
                        truncated_prev_reasoning += '...\n\n'

        truncated_prev_reasoning = truncated_prev_reasoning.strip('\n')

        MAX_PREV_REASONING_CHARS = 12000
        if len(truncated_prev_reasoning) > MAX_PREV_REASONING_CHARS:
            truncated_prev_reasoning = truncated_prev_reasoning[-MAX_PREV_REASONING_CHARS:]

        return truncated_prev_reasoning

    # ----------------------------------------------------------------------
    # kbinfos normalize
    # ----------------------------------------------------------------------
    def _normalize_kbinfos(self, kbinfos: dict) -> dict:
        """
        规范检索结果，避免缺少 doc_id / chunk_id 报错。
        """
        if not isinstance(kbinfos, dict):
            kbinfos = {}

        kbinfos.setdefault("chunks", [])
        kbinfos.setdefault("doc_aggs", [])

        existing_doc_ids = set()
        normalized_doc_aggs = []

        for d in kbinfos.get("doc_aggs", []):
            if not isinstance(d, dict):
                continue

            doc_id = d.get("doc_id") or d.get("document_id") or d.get("id")

            if not doc_id:
                continue

            d["doc_id"] = doc_id
            d["document_id"] = doc_id

            if "doc_name" not in d:
                d["doc_name"] = (
                    d.get("name")
                    or d.get("title")
                    or d.get("url")
                    or str(doc_id)
                )

            if doc_id not in existing_doc_ids:
                normalized_doc_aggs.append(d)
                existing_doc_ids.add(doc_id)

        kbinfos["doc_aggs"] = normalized_doc_aggs

        normalized_chunks = []

        for idx, c in enumerate(kbinfos.get("chunks", [])):
            if not isinstance(c, dict):
                continue

            chunk_id = (
                c.get("chunk_id")
                or c.get("id")
                or f"deep_research_chunk_{idx}_{abs(hash(str(c)))}"
            )

            c["chunk_id"] = chunk_id
            c["id"] = c.get("id") or chunk_id

            doc_id = (
                c.get("doc_id")
                or c.get("document_id")
                or c.get("docnm_kwd")
                or c.get("url")
            )

            if not doc_id:
                doc_id = f"deep_research_doc_{chunk_id}"

            c["doc_id"] = doc_id
            c["document_id"] = doc_id

            if doc_id not in existing_doc_ids:
                kbinfos["doc_aggs"].append({
                    "doc_id": doc_id,
                    "document_id": doc_id,
                    "doc_name": (
                        c.get("doc_name")
                        or c.get("title")
                        or c.get("url")
                        or "Deep Research"
                    ),
                    "url": c.get("url", "")
                })
                existing_doc_ids.add(doc_id)

            normalized_chunks.append(c)

        kbinfos["chunks"] = normalized_chunks

        return kbinfos

    def _retrieve_information(self, search_query):
        """
        Retrieve information from different sources.
        """
        kbinfos = {"chunks": [], "doc_aggs": []}

        # 1. Knowledge base retrieval
        try:
            if self._kb_retrieve:
                kb_res = self._kb_retrieve(question=search_query)

                if isinstance(kb_res, dict):
                    kbinfos = kb_res
        except Exception as e:
            logging.error(f"Knowledge base retrieval error: {e}")

        kbinfos = self._normalize_kbinfos(kbinfos)

        # 2. Web retrieval Tavily
        try:
            if self.prompt_config.get("tavily_api_key"):
                tav = Tavily(self.prompt_config["tavily_api_key"])
                tav_res = tav.retrieve_chunks(search_query)

                tav_res = self._normalize_kbinfos(tav_res)

                kbinfos["chunks"].extend(tav_res.get("chunks", []))
                kbinfos["doc_aggs"].extend(tav_res.get("doc_aggs", []))

                kbinfos = self._normalize_kbinfos(kbinfos)
        except Exception as e:
            logging.error(f"Web retrieval error: {e}")

        # 3. Knowledge graph retrieval
        try:
            if self.prompt_config.get("use_kg") and self._kg_retrieve:
                ck = self._kg_retrieve(question=search_query)

                if isinstance(ck, dict) and ck.get("content_with_weight"):
                    kg_infos = {
                        "chunks": [ck],
                        "doc_aggs": []
                    }

                    kg_infos = self._normalize_kbinfos(kg_infos)

                    kbinfos["chunks"] = (
                        kg_infos.get("chunks", []) + kbinfos.get("chunks", [])
                    )
                    kbinfos["doc_aggs"].extend(kg_infos.get("doc_aggs", []))

                    kbinfos = self._normalize_kbinfos(kbinfos)
        except Exception as e:
            logging.error(f"Knowledge graph retrieval error: {e}")

        return self._normalize_kbinfos(kbinfos)

    def _update_chunk_info(self, chunk_info, kbinfos):
        """
        Update chunk information for citations.
        """
        if not isinstance(chunk_info, dict):
            return

        chunk_info.setdefault("chunks", [])
        chunk_info.setdefault("doc_aggs", [])

        kbinfos = self._normalize_kbinfos(kbinfos)
        chunk_info = self._normalize_kbinfos(chunk_info)

        existing_chunk_ids = set()

        for c in chunk_info.get("chunks", []):
            cid = c.get("chunk_id") or c.get("id")
            if cid:
                existing_chunk_ids.add(cid)

        for c in kbinfos.get("chunks", []):
            cid = c.get("chunk_id") or c.get("id")

            if not cid:
                continue

            if cid not in existing_chunk_ids:
                chunk_info["chunks"].append(c)
                existing_chunk_ids.add(cid)

        existing_doc_ids = set()

        for d in chunk_info.get("doc_aggs", []):
            did = d.get("doc_id") or d.get("document_id") or d.get("id")

            if did:
                d["doc_id"] = did
                d["document_id"] = did
                existing_doc_ids.add(did)

        for d in kbinfos.get("doc_aggs", []):
            did = d.get("doc_id") or d.get("document_id") or d.get("id")

            if not did:
                continue

            d["doc_id"] = did
            d["document_id"] = did

            if did not in existing_doc_ids:
                chunk_info["doc_aggs"].append(d)
                existing_doc_ids.add(did)

    # ----------------------------------------------------------------------
    # relevant extraction
    # ----------------------------------------------------------------------
    async def _extract_relevant_info(self, truncated_prev_reasoning, search_query, kbinfos):
        """
        Extract and summarize relevant information.

        返回 full_text 快照。
        """
        kbinfos = self._normalize_kbinfos(kbinfos)

        full_text = ""

        async for ans in self.chat_mdl.async_chat_streamly(
            RELEVANT_EXTRACTION_PROMPT.format(
                prev_reasoning=truncated_prev_reasoning,
                search_query=search_query,
                document="\n".join(kb_prompt(kbinfos, 4096))
            ),
            [{
                "role": "user",
                "content": (
                    f'Now you should analyze each web page and find helpful information '
                    f'based on the current search query "{search_query}" and previous reasoning steps.'
                )
            }],
            {"temperature": 0.7}
        ):
            ans = self._strip_model_think(ans or "")

            if not ans:
                continue

            if ans.startswith(full_text):
                full_text = ans
            else:
                full_text += ans

            yield full_text

    # ----------------------------------------------------------------------
    # main thinking
    # ----------------------------------------------------------------------
    async def thinking(self, chunk_info: dict, question: str):
        """
        主流程。

        快照模式：
        每次 yield 给前端的都是完整 <think>...</think>。
        """
        executed_search_queries = []
        msg_history = [{"role": "user", "content": f'Question:"{question}"\n'}]
        all_reasoning_steps = []

        if not isinstance(chunk_info, dict):
            chunk_info = {"chunks": [], "doc_aggs": []}

        chunk_info.setdefault("chunks", [])
        chunk_info.setdefault("doc_aggs", [])

        # 内部保存 raw think，输出时通过 _pack_think_snapshot 格式化
        think = "<think>"
        think += (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "原始问题\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{question}\n"
        )

        yield self._pack_think_snapshot(think)

        for step_index in range(MAX_SEARCH_LIMIT + 1):

            # 达到最大搜索次数
            if step_index == MAX_SEARCH_LIMIT - 1:
                summary_raw = (
                    f"\n{BEGIN_SEARCH_RESULT}\n"
                    f"The maximum search limit is exceeded. You are not allowed to search.\n"
                    f"{END_SEARCH_RESULT}\n"
                )

                think += "\n\nFinal Information\n已达到最大检索次数，本轮不再继续检索。\n"

                all_reasoning_steps.append(summary_raw)
                msg_history.append({
                    "role": "assistant",
                    "content": summary_raw
                })

                yield self._pack_think_snapshot(think)
                break

            # ----------------------------------------------------------
            # Step 1: 生成 reasoning
            # ----------------------------------------------------------
            query_think_raw = ""

            async for full_text in self._generate_reasoning(msg_history):
                query_think_raw = full_text

                # query tag 不展示，但 raw 仍用于提取 query
                query_public = self._remove_query_tags(query_think_raw)

                yield self._pack_think_snapshot(
                    think + query_public
                )

            query_public = self._remove_query_tags(query_think_raw)

            if query_public:
                think += query_public

            all_reasoning_steps.append(query_think_raw)

            # ----------------------------------------------------------
            # Step 2: 提取检索 query
            # ----------------------------------------------------------
            queries = self._extract_search_queries(
                query_think_raw,
                question,
                step_index
            )

            if not queries and step_index > 0:
                break

            if not queries and step_index == 0:
                queries = [question]

            # ----------------------------------------------------------
            # Step 3: 逐个执行检索
            # ----------------------------------------------------------
            for search_query in queries:
                search_query = (search_query or "").strip()

                if not search_query:
                    continue

                logging.info(f"[THINK]Query: {step_index}. {search_query}")

                msg_history.append({
                    "role": "assistant",
                    "content": search_query
                })

                # 保留原始格式，输出时会被替换成 “泛化检索问题”
                think += f"\n\n> {step_index + 1}. {search_query}\n\n"

                yield self._pack_think_snapshot(think)

                # 重复检索
                if search_query in executed_search_queries:
                    summary_raw = (
                        f"\n{BEGIN_SEARCH_RESULT}\n"
                        f"You have searched this query. Please refer to previous results.\n"
                        f"{END_SEARCH_RESULT}\n"
                    )

                    think += summary_raw

                    all_reasoning_steps.append(summary_raw)
                    msg_history.append({
                        "role": "user",
                        "content": summary_raw
                    })

                    yield self._pack_think_snapshot(think)
                    continue

                executed_search_queries.append(search_query)

                # ------------------------------------------------------
                # Step 4: 检索
                # ------------------------------------------------------
                truncated_prev_reasoning = self._truncate_previous_reasoning(
                    all_reasoning_steps
                )

                kbinfos = self._retrieve_information(search_query)

                self._update_chunk_info(chunk_info, kbinfos)

                # ------------------------------------------------------
                # Step 5: 提取相关信息
                # ------------------------------------------------------
                summary_raw = ""

                async for full_text in self._extract_relevant_info(
                    truncated_prev_reasoning,
                    search_query,
                    kbinfos
                ):
                    summary_raw = full_text

                    yield self._pack_think_snapshot(
                        think + summary_raw
                    )

                if summary_raw:
                    think += summary_raw

                all_reasoning_steps.append(summary_raw)

                msg_history.append({
                    "role": "user",
                    "content": (
                        f"\n\n{BEGIN_SEARCH_RESULT}"
                        f"{summary_raw}"
                        f"{END_SEARCH_RESULT}\n\n"
                    )
                })

                logging.info(f"[THINK]Summary: {step_index}. {summary_raw}")

        yield self._pack_think_snapshot(
            think,
            reference=chunk_info
        )