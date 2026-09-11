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
import asyncio
import datetime
import json
import re
import base64
import xxhash
from quart import request

from api.db.services.document_service import DocumentService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.llm_service import LLMBundle
from api.common.check_team_permission import check_kb_team_write_permission
from common.metadata_utils import apply_meta_data_filter
from api.db.services.search_service import SearchService
from api.db.services.user_service import UserTenantService
from api.utils.api_utils import get_data_error_result, get_json_result, server_error_response, validate_request, \
    get_request_json
from rag.app.qa import beAdoc, rmPrefix
from rag.app.tag import label_question
from rag.nlp import rag_tokenizer, search
from rag.prompts.generator import cross_languages, keyword_extraction
from common.string_utils import remove_redundant_spaces
from common.constants import RetCode, LLMType, ParserType, PAGERANK_FLD
from common import settings
from api.apps import login_required, current_user


@manager.route('/list', methods=['POST'])  # noqa: F821
@login_required
@validate_request("doc_id")
async def list_chunk():
    req = await get_request_json()
    doc_id = req["doc_id"]
    page = int(req.get("page", 1))
    size = int(req.get("size", 30))
    question = req.get("keywords", "")
    try:
        tenant_id = DocumentService.get_tenant_id(req["doc_id"])
        if not tenant_id:
            return get_data_error_result(message="Tenant not found!")
        e, doc = DocumentService.get_by_id(doc_id)
        if not e:
            return get_data_error_result(message="Document not found!")
        kb_ids = KnowledgebaseService.get_kb_ids(tenant_id)
        query = {
            "doc_ids": [doc_id], "page": page, "size": size, "question": question, "sort": True
        }
        if "available_int" in req:
            query["available_int"] = int(req["available_int"])
        sres = settings.retriever.search(query, search.index_name(tenant_id), kb_ids, highlight=["content_ltks"])
        res = {"total": sres.total, "chunks": [], "doc": doc.to_dict()}
        for id in sres.ids:
            d = {   
                "chunk_id": id,
                "content_with_weight": remove_redundant_spaces(sres.highlight[id]) if question and id in sres.highlight else sres.field[
                    id].get(
                    "content_with_weight", ""),
                "doc_id": sres.field[id]["doc_id"],
                "docnm_kwd": sres.field[id]["docnm_kwd"],
                "important_kwd": sres.field[id].get("important_kwd", []),
                "question_kwd": sres.field[id].get("question_kwd", []),
                "image_id": sres.field[id].get("img_id", ""),
                "available_int": int(sres.field[id].get("available_int", 1)),
                "positions": sres.field[id].get("position_int", []),
            }
            assert isinstance(d["positions"], list)
            assert len(d["positions"]) == 0 or (isinstance(d["positions"][0], list) and len(d["positions"][0]) == 5)
            res["chunks"].append(d)
        return get_json_result(data=res)
    except Exception as e:
        if str(e).find("not_found") > 0:
            return get_json_result(data=False, message='No chunk found!',
                                   code=RetCode.DATA_ERROR)
        return server_error_response(e)


@manager.route('/get', methods=['GET'])  # noqa: F821
@login_required
def get():
    chunk_id = request.args["chunk_id"]
    try:
        chunk = None
        tenants = UserTenantService.query(user_id=current_user.id)
        if not tenants:
            return get_data_error_result(message="Tenant not found!")
        for tenant in tenants:
            kb_ids = KnowledgebaseService.get_kb_ids(tenant.tenant_id)
            chunk = settings.docStoreConn.get(chunk_id, search.index_name(tenant.tenant_id), kb_ids)
            if chunk:
                break
        if chunk is None:
            return server_error_response(Exception("Chunk not found"))

        k = []
        for n in chunk.keys():
            if re.search(r"(_vec$|_sm_|_tks|_ltks)", n):
                k.append(n)
        for n in k:
            del chunk[n]

        return get_json_result(data=chunk)
    except Exception as e:
        if str(e).find("NotFoundError") >= 0:
            return get_json_result(data=False, message='Chunk not found!',
                                   code=RetCode.DATA_ERROR)
        return server_error_response(e)


@manager.route('/set', methods=['POST'])  # noqa: F821
@login_required
@validate_request("doc_id", "chunk_id", "content_with_weight")
async def set():
    req = await get_request_json()
    d = {
        "id": req["chunk_id"],
        "content_with_weight": req["content_with_weight"]}
    d["content_ltks"] = rag_tokenizer.tokenize(req["content_with_weight"])
    d["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(d["content_ltks"])
    if "important_kwd" in req:
        if not isinstance(req["important_kwd"], list):
            return get_data_error_result(message="`important_kwd` should be a list")
        d["important_kwd"] = req["important_kwd"]
        d["important_tks"] = rag_tokenizer.tokenize(" ".join(req["important_kwd"]))
    if "question_kwd" in req:
        if not isinstance(req["question_kwd"], list):
            return get_data_error_result(message="`question_kwd` should be a list")
        d["question_kwd"] = req["question_kwd"]
        d["question_tks"] = rag_tokenizer.tokenize("\n".join(req["question_kwd"]))
    if "tag_kwd" in req:
        d["tag_kwd"] = req["tag_kwd"]
    if "tag_feas" in req:
        d["tag_feas"] = req["tag_feas"]
    if "available_int" in req:
        d["available_int"] = req["available_int"]

    try:
        def _set_sync():
            tenant_id = DocumentService.get_tenant_id(req["doc_id"])
            if not tenant_id:
                return get_data_error_result(message="Tenant not found!")

            embd_id = DocumentService.get_embd_id(req["doc_id"])
            embd_mdl = LLMBundle(tenant_id, LLMType.EMBEDDING, embd_id)

            e, doc = DocumentService.get_by_id(req["doc_id"])
            if not e:
                return get_data_error_result(message="Document not found!")
            e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
            if not e:
                return get_data_error_result(message="Knowledgebase not found!")
            if not check_kb_team_write_permission(kb, current_user.id):
                return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

            _d = d
            if doc.parser_id == ParserType.QA:
                arr = [
                    t for t in re.split(
                        r"[\n\t]",
                        req["content_with_weight"]) if len(t) > 1]
                q, a = rmPrefix(arr[0]), rmPrefix("\n".join(arr[1:]))
                _d = beAdoc(d, q, a, not any(
                    [rag_tokenizer.is_chinese(t) for t in q + a]))

            v, c = embd_mdl.encode([doc.name, req["content_with_weight"] if not _d.get("question_kwd") else "\n".join(_d["question_kwd"])])
            v = 0.1 * v[0] + 0.9 * v[1] if doc.parser_id != ParserType.QA else v[1]
            _d["q_%d_vec" % len(v)] = v.tolist()
            settings.docStoreConn.update({"id": req["chunk_id"]}, _d, search.index_name(tenant_id), doc.kb_id)

            # update image
            image_id = req.get("img_id")
            bkt, name = image_id.split("-")
            image_base64 = req.get("image_base64", None)
            if image_base64:
                image_binary = base64.b64decode(image_base64)
                settings.STORAGE_IMPL.put(bkt, name, image_binary)
            return get_json_result(data=True)

        return await asyncio.to_thread(_set_sync)
    except Exception as e:
        return server_error_response(e)


@manager.route('/switch', methods=['POST'])  # noqa: F821
@login_required
@validate_request("chunk_ids", "available_int", "doc_id")
async def switch():
    req = await get_request_json()
    try:
        def _switch_sync():
            e, doc = DocumentService.get_by_id(req["doc_id"])
            if not e:
                return get_data_error_result(message="Document not found!")
            e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
            if not e:
                return get_data_error_result(message="Knowledgebase not found!")
            if not check_kb_team_write_permission(kb, current_user.id):
                return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)
            for cid in req["chunk_ids"]:
                if not settings.docStoreConn.update({"id": cid},
                                                    {"available_int": int(req["available_int"])},
                                                    search.index_name(DocumentService.get_tenant_id(req["doc_id"])),
                                                    doc.kb_id):
                    return get_data_error_result(message="Index updating failure")
            return get_json_result(data=True)

        return await asyncio.to_thread(_switch_sync)
    except Exception as e:
        return server_error_response(e)


@manager.route('/rm', methods=['POST'])  # noqa: F821
@login_required
@validate_request("chunk_ids", "doc_id")
async def rm():
    req = await get_request_json()
    try:
        def _rm_sync():
            e, doc = DocumentService.get_by_id(req["doc_id"])
            if not e:
                return get_data_error_result(message="Document not found!")
            e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
            if not e:
                return get_data_error_result(message="Knowledgebase not found!")
            if not check_kb_team_write_permission(kb, current_user.id):
                return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)
            if not settings.docStoreConn.delete({"id": req["chunk_ids"]},
                                                search.index_name(DocumentService.get_tenant_id(req["doc_id"])),
                                                doc.kb_id):
                return get_data_error_result(message="Chunk deleting failure")
            deleted_chunk_ids = req["chunk_ids"]
            chunk_number = len(deleted_chunk_ids)
            DocumentService.decrement_chunk_num(doc.id, doc.kb_id, 1, chunk_number, 0)
            for cid in deleted_chunk_ids:
                if settings.STORAGE_IMPL.obj_exist(doc.kb_id, cid):
                    settings.STORAGE_IMPL.rm(doc.kb_id, cid)
            return get_json_result(data=True)

        return await asyncio.to_thread(_rm_sync)
    except Exception as e:
        return server_error_response(e)


@manager.route('/create', methods=['POST'])  # noqa: F821
@login_required
@validate_request("doc_id", "content_with_weight")
async def create():
    req = await get_request_json()
    chunck_id = xxhash.xxh64((req["content_with_weight"] + req["doc_id"]).encode("utf-8")).hexdigest()
    d = {"id": chunck_id, "content_ltks": rag_tokenizer.tokenize(req["content_with_weight"]),
         "content_with_weight": req["content_with_weight"]}
    d["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(d["content_ltks"])
    d["important_kwd"] = req.get("important_kwd", [])
    if not isinstance(d["important_kwd"], list):
        return get_data_error_result(message="`important_kwd` is required to be a list")
    d["important_tks"] = rag_tokenizer.tokenize(" ".join(d["important_kwd"]))
    d["question_kwd"] = req.get("question_kwd", [])
    if not isinstance(d["question_kwd"], list):
        return get_data_error_result(message="`question_kwd` is required to be a list")
    d["question_tks"] = rag_tokenizer.tokenize("\n".join(d["question_kwd"]))
    d["create_time"] = str(datetime.datetime.now()).replace("T", " ")[:19]
    d["create_timestamp_flt"] = datetime.datetime.now().timestamp()
    if "tag_feas" in req:
        d["tag_feas"] = req["tag_feas"]
    if "tag_feas" in req:
        d["tag_feas"] = req["tag_feas"]

    try:
        def _create_sync():
            e, doc = DocumentService.get_by_id(req["doc_id"])
            if not e:
                return get_data_error_result(message="Document not found!")
            e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
            if not e:
                return get_data_error_result(message="Knowledgebase not found!")
            if not check_kb_team_write_permission(kb, current_user.id):
                return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)
            d["kb_id"] = [doc.kb_id]
            d["docnm_kwd"] = doc.name
            d["title_tks"] = rag_tokenizer.tokenize(doc.name)
            d["doc_id"] = doc.id

            tenant_id = DocumentService.get_tenant_id(req["doc_id"])
            if not tenant_id:
                return get_data_error_result(message="Tenant not found!")

            e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
            if not e:
                return get_data_error_result(message="Knowledgebase not found!")
            if kb.pagerank:
                d[PAGERANK_FLD] = kb.pagerank

            embd_id = DocumentService.get_embd_id(req["doc_id"])

            embd_mdl = LLMBundle(tenant_id, LLMType.EMBEDDING.value, embd_id)

            v, c = embd_mdl.encode([doc.name, req["content_with_weight"] if not d["question_kwd"] else "\n".join(d["question_kwd"])])
            v = 0.1 * v[0] + 0.9 * v[1]
            d["q_%d_vec" % len(v)] = v.tolist()
            settings.docStoreConn.insert([d], search.index_name(tenant_id), doc.kb_id)

            DocumentService.increment_chunk_num(
                doc.id, doc.kb_id, c, 1, 0)
            return get_json_result(data={"chunk_id": chunck_id})

        return await asyncio.to_thread(_create_sync)
    except Exception as e:
        return server_error_response(e)


# @manager.route('/retrieval_test', methods=['POST'])  # noqa: F821
# @login_required
# @validate_request("kb_id", "question")
# async def retrieval_test():
#     req = await get_request_json()
#     page = int(req.get("page", 1))
#     size = int(req.get("size", 30))
#     question = req["question"]
#     kb_ids = req["kb_id"]
#     tag = req["tag"]
#     # print(tag)
#     doc_ids = DocumentService.get_doc_ids_by_tags(kb_ids,tag)
#     print(doc_ids)
#     # print(len(doc_ids))
#     if isinstance(kb_ids, str):
#         kb_ids = [kb_ids]
#     if not kb_ids:
#         return get_json_result(data=False, message='Please specify dataset firstly.',
#                                code=RetCode.DATA_ERROR)

#     # doc_ids = req.get("doc_ids", [])
#     use_kg = req.get("use_kg", False)
#     top = int(req.get("top_k", 1024))
#     langs = req.get("cross_languages", [])
#     user_id = current_user.id

#     async def _retrieval():
#         local_doc_ids = list(doc_ids) if doc_ids else []
#         tenant_ids = []

#         meta_data_filter = {}
#         chat_mdl = None
#         if req.get("search_id", ""):
#             search_config = SearchService.get_detail(req.get("search_id", "")).get("search_config", {})
#             meta_data_filter = search_config.get("meta_data_filter", {})
#             if meta_data_filter.get("method") in ["auto", "semi_auto"]:
#                 chat_mdl = LLMBundle(user_id, LLMType.CHAT, llm_name=search_config.get("chat_id", ""))
#         else:
#             meta_data_filter = req.get("meta_data_filter") or {}
#             if meta_data_filter.get("method") in ["auto", "semi_auto"]:
#                 chat_mdl = LLMBundle(user_id, LLMType.CHAT)

#         if meta_data_filter:
#             metas = DocumentService.get_meta_by_kbs(kb_ids)
#             local_doc_ids = await apply_meta_data_filter(meta_data_filter, metas, question, chat_mdl, local_doc_ids)

#         for kb_id in kb_ids:
#             if not KnowledgebaseService.accessible(kb_id, user_id):
#                 return get_json_result(
#                     data=False, message='Only owner of dataset authorized for this operation.',
#                     code=RetCode.OPERATING_ERROR)
#             e, _kb = KnowledgebaseService.get_by_id(kb_id)
#             if not e:
#                 return get_data_error_result(message="Knowledgebase not found!")
#             tenant_ids.append(_kb.tenant_id)

#         e, kb = KnowledgebaseService.get_by_id(kb_ids[0])
#         if not e:
#             return get_data_error_result(message="Knowledgebase not found!")

#         _question = question
#         if langs:
#             _question = await cross_languages(kb.tenant_id, None, _question, langs)

        
#         from api.db.services.tenant_llm_service import TenantLLMService
#         config = TenantLLMService.get_model_config(kb.tenant_id, LLMType.EMBEDDING.value, kb.embd_id)
#         print("===== DEBUG =====")
#         print(f"tenant_id: {kb.tenant_id}")
#         print(f"embd_id: {kb.embd_id}")
#         print(f"api_key from DB: {config.get('api_key', 'N/A')[:10]}...")
#         embd_mdl = LLMBundle(kb.tenant_id, LLMType.EMBEDDING.value, llm_name=kb.embd_id)

#         rerank_mdl = None
#         if req.get("rerank_id"):
#             rerank_mdl = LLMBundle(kb.tenant_id, LLMType.RERANK.value, llm_name=req["rerank_id"])

#         if req.get("keyword", False):
#             chat_mdl = LLMBundle(kb.tenant_id, LLMType.CHAT)
#             _question += await keyword_extraction(chat_mdl, _question)

#         labels = label_question(_question, [kb])
#         ranks = settings.retriever.retrieval(_question, embd_mdl, tenant_ids, kb_ids, page, size,
#                                float(req.get("similarity_threshold", 0.0)),
#                                float(req.get("vector_similarity_weight", 0.3)),
#                                top,
#                                local_doc_ids, rerank_mdl=rerank_mdl,
#                                              highlight=req.get("highlight", False),
#                                rank_feature=labels
#                                )
#         if use_kg:
#             ck = settings.kg_retriever.retrieval(_question,
#                                                    tenant_ids,
#                                                    kb_ids,
#                                                    embd_mdl,
#                                                    LLMBundle(kb.tenant_id, LLMType.CHAT))
#             if ck["content_with_weight"]:
#                 ranks["chunks"].insert(0, ck)
#         ranks["chunks"] = settings.retriever.retrieval_by_children(ranks["chunks"], tenant_ids)

#         for c in ranks["chunks"]:
#             c.pop("vector", None)
#             print("召回的chunk")
#             print(c["kb_id"])
#             KnowledgebaseService.get_detail(c["kb_id"])
#             kb_detail = KnowledgebaseService.get_detail(c["kb_id"])

#             # 2. 先判断一下详情是否存在（防止 c.kb_id 无效导致返回 None）
#             if kb_detail:
#                 # 3. 通过键 'name' 获取知识库名称
#                 kb_name = kb_detail.get('name')
#                 c['kb_name'] = kb_name

#             else:
#                 c['kb_name'] = "未知知识库"


#         ranks["labels"] = labels

#         return get_json_result(data=ranks)

#     try:
#         return await _retrieval()
#     except Exception as e:
#         if str(e).find("not_found") > 0:
#             return get_json_result(data=False, message='No chunk found! Check the chunk status please!',
#                                    code=RetCode.DATA_ERROR)
#         return server_error_response(e)

# @manager.route('/retrieval_test', methods=['POST'])  # noqa: F821
# @login_required
# @validate_request("kb_id", "question")
# async def retrieval_test():
#     req = await get_request_json()
#     page = int(req.get("page", 1))
#     size = int(req.get("size", 30))
#     question = req["question"].strip()
#     kb_ids = req["kb_id"]
#     tag = req.get("tag")
#     use_kg = req.get("use_kg", False)
#     top = int(req.get("top_k", 1024))
#     langs = req.get("cross_languages", [])
#     user_id = current_user.id
#     mode = req.get("mode")
#     print(mode)

#     if isinstance(kb_ids, str):
#         kb_ids = [kb_ids]

#     if not kb_ids:
#         return get_json_result(
#             data=False,
#             message='Please specify dataset firstly.',
#             code=RetCode.DATA_ERROR
#         )

#     async def _retrieval():
#         tenant_ids = []

#         # 1. 权限校验 + 获取 tenant_ids
#         for kb_id in kb_ids:
#             if not KnowledgebaseService.accessible(kb_id, user_id):
#                 return get_json_result(
#                     data=False,
#                     message='Only owner of dataset authorized for this operation.',
#                     code=RetCode.OPERATING_ERROR
#                 )

#             e, _kb = KnowledgebaseService.get_by_id(kb_id)
#             if not e:
#                 return get_data_error_result(message="Knowledgebase not found!")

#             tenant_ids.append(_kb.tenant_id)

#         e, kb = KnowledgebaseService.get_by_id(kb_ids[0])
#         if not e:
#             return get_data_error_result(message="Knowledgebase not found!")

#         tenant_id = kb.tenant_id

#         # 2. 先把 question 当“文件名关键词”去模糊匹配 doc_ids
#         file_doc_ids = DocumentService.get_doc_ids_by_file_name(question) or []
#         # file_doc_ids = ["27ea1fc68b0c11f1b77b28952976d72a"]
#         print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
#         print(file_doc_ids)

#         # 如果还有 tag 过滤，和 tag 的结果取交集
#         if tag:
#             tag_doc_ids = DocumentService.get_doc_ids_by_tags(kb_ids, tag) or []
#             if tag_doc_ids:
#                 if file_doc_ids:
#                     import builtins

#                     file_doc_ids = list(builtins.set(file_doc_ids) & builtins.set(tag_doc_ids))

#                 else:
#                     file_doc_ids = []
#             else:
#                 file_doc_ids = file_doc_ids

#         print(file_doc_ids)
#         # 3. 先查文件名命中的 doc 下的所有 chunk
#         file_chunks = []
#         if file_doc_ids:
#             query = {
#                 "doc_ids": file_doc_ids,
#                 "page": 1,
#                 "size": 100,   # 想要“所有片段”就调大一点
#                 "question": "",
#                 "sort": True
#             }

#             if "available_int" in req:
#                 query["available_int"] = int(req["available_int"])

#             sres = settings.retriever.search(
#                 query,
#                 search.index_name(tenant_id),
#                 kb_ids,
#                 highlight=["content_ltks"]
#             )
#             print(sres)

#             for cid in sres.ids:
#                 field = sres.field[cid]
#                 d = {
#                     "chunk_id": cid,
#                     "content_with_weight": (
#                         remove_redundant_spaces(sres.highlight[cid])
#                         if cid in sres.highlight else field.get("content_with_weight", "")
#                     ),
#                     "doc_id": field["doc_id"],
#                     "docnm_kwd": field["docnm_kwd"],
#                     "important_kwd": field.get("important_kwd", []),
#                     "question_kwd": field.get("question_kwd", []),
#                     "image_id": field.get("img_id", ""),
#                     "available_int": int(field.get("available_int", 1)),
#                     "positions": field.get("position_int", []),
#                     "kb_id": kb_ids[0] if len(kb_ids) == 1 else field.get("kb_id", "")
#                 }
#                 file_chunks.append(d)

#         print("=== 按文件名召回的 chunks ===")
#         print(len(file_chunks))
#         # 4. 再把 question 当“文本问题”做语义召回
#         meta_data_filter = {}
#         chat_mdl = None
#         if req.get("search_id", ""):
#             search_config = SearchService.get_detail(req.get("search_id", "")).get("search_config", {})
#             meta_data_filter = search_config.get("meta_data_filter", {})
#             if meta_data_filter.get("method") in ["auto", "semi_auto"]:
#                 chat_mdl = LLMBundle(user_id, LLMType.CHAT, llm_name=search_config.get("chat_id", ""))
#         else:
#             meta_data_filter = req.get("meta_data_filter") or {}
#             if meta_data_filter.get("method") in ["auto", "semi_auto"]:
#                 chat_mdl = LLMBundle(user_id, LLMType.CHAT)

#         doc_ids = DocumentService.get_doc_ids_by_tags(kb_ids,tag)
#         local_doc_ids = list(doc_ids) if doc_ids else []
#         # local_doc_ids = []
#         if meta_data_filter:
#             metas = DocumentService.get_meta_by_kbs(kb_ids)
#             local_doc_ids = await apply_meta_data_filter(meta_data_filter, metas, question, chat_mdl, local_doc_ids)

#         _question = question
#         if langs:
#             _question = await cross_languages(kb.tenant_id, None, _question, langs)

#         embd_mdl = LLMBundle(kb.tenant_id, LLMType.EMBEDDING.value, llm_name=kb.embd_id)

#         rerank_mdl = None
#         if req.get("rerank_id"):
#             rerank_mdl = LLMBundle(kb.tenant_id, LLMType.RERANK.value, llm_name=req["rerank_id"])

#         if req.get("keyword", False):
#             chat_mdl = LLMBundle(kb.tenant_id, LLMType.CHAT)
#             _question += await keyword_extraction(chat_mdl, _question)

#         labels = label_question(_question, [kb])

#         ranks = settings.retriever.retrieval(
#             _question,
#             embd_mdl,
#             tenant_ids,
#             kb_ids,
#             page,
#             size,
#             float(req.get("similarity_threshold", 0.0)),
#             float(req.get("vector_similarity_weight", 0.3)),
#             top,
#             local_doc_ids,
#             rerank_mdl=rerank_mdl,
#             highlight=req.get("highlight", False),
#             rank_feature=labels
#         )
#         print("=== 语义相似召回的 chunks ===")
#         print(len(ranks["chunks"]))


#         # 5. 可选 KG 召回
#         if use_kg:
#             ck = settings.kg_retriever.retrieval(
#                 _question,
#                 tenant_ids,
#                 kb_ids,
#                 embd_mdl,
#                 LLMBundle(kb.tenant_id, LLMType.CHAT)
#             )
#             if ck["content_with_weight"]:
#                 ranks["chunks"].insert(0, ck)

#         # 6. 合并两路结果，按 chunk_id 去重
#         merged_chunks = []
#         import builtins

#         seen = builtins.set()

#         def _append_chunk(c):
#             cid = c.get("chunk_id") or c.get("id")
#             if not cid or cid in seen:
#                 return
#             seen.add(cid)
#             merged_chunks.append(c)

#         for c in file_chunks:
#             _append_chunk(c)

#         for c in ranks["chunks"]:
#             _append_chunk(c)

#         # 7. child chunk 展开
#         merged_chunks = settings.retriever.retrieval_by_children(merged_chunks, tenant_ids)

#         # 8. 去掉 vector，补 kb_name
#         for c in merged_chunks:
#             c.pop("vector", None)
#             kb_detail = KnowledgebaseService.get_detail(c["kb_id"])
#             if kb_detail:
#                 c["kb_name"] = kb_detail.get("name", "未知知识库")
#             else:
#                 c["kb_name"] = "未知知识库"

#         ranks["chunks"] = merged_chunks
#         ranks["labels"] = labels
#         ranks["file_doc_ids"] = file_doc_ids

#         return get_json_result(data=ranks)

#     try:
#         return await _retrieval()
#     except Exception as e:
#         if str(e).find("not_found") > 0:
#             return get_json_result(
#                 data=False,
#                 message='No chunk found! Check the chunk status please!',
#                 code=RetCode.DATA_ERROR
#             )
#         return server_error_response(e)

# @manager.route('/retrieval_test', methods=['POST'])  # noqa: F821
# @login_required
# @validate_request("kb_id", "question")
# async def retrieval_test():
#     req = await get_request_json()

#     page = int(req.get("page", 1))
#     size = int(req.get("size", 30))
#     question = req["question"].strip()
#     kb_ids = req["kb_id"]
#     tag = req.get("tag")
#     use_kg = req.get("use_kg", False)
#     top = int(req.get("top_k", 1024))
#     langs = req.get("cross_languages", [])
#     user_id = current_user.id
#     mode = str(req.get("mode", "3"))

#     if isinstance(kb_ids, str):
#         kb_ids = [kb_ids]

#     if not kb_ids:
#         return get_json_result(
#             data=False,
#             message='Please specify dataset firstly.',
#             code=RetCode.DATA_ERROR
#         )

#     async def _prepare_context():
#         """
#         公共逻辑：
#         1. 校验知识库权限
#         2. 获取 tenant_ids
#         3. 获取当前 kb
#         """
#         tenant_ids = []

#         for kb_id in kb_ids:
#             if not KnowledgebaseService.accessible(kb_id, user_id):
#                 return None, None, get_json_result(
#                     data=False,
#                     message='Only owner of dataset authorized for this operation.',
#                     code=RetCode.OPERATING_ERROR
#                 )

#             e, _kb = KnowledgebaseService.get_by_id(kb_id)
#             if not e:
#                 return None, None, get_data_error_result(message="Knowledgebase not found!")

#             tenant_ids.append(_kb.tenant_id)

#         e, kb = KnowledgebaseService.get_by_id(kb_ids[0])
#         if not e:
#             return None, None, get_data_error_result(message="Knowledgebase not found!")

#         return tenant_ids, kb, None

#     def _get_title_doc_ids():
#         """
#         标题 / 文件名查询 doc_id。
#         如果传了 tag，则和 tag 查询出来的 doc_id 取交集。
#         """
#         file_doc_ids = DocumentService.get_doc_ids_by_file_name(question) or []

#         if tag:
#             tag_doc_ids = DocumentService.get_doc_ids_by_tags(kb_ids, tag)

#             # 注意：如果 tag 没查到，那么应该返回空，而不是保留 file_doc_ids
#             if tag_doc_ids is None:
#                 return file_doc_ids

#             elif tag_doc_ids == []:
#                 return []

#             else:
#                 import builtins
#                 file_doc_ids = list(builtins.set(file_doc_ids) & builtins.set(tag_doc_ids))

#         return file_doc_ids

#     def _search_chunks_by_doc_ids(doc_ids, tenant_id):
#         """
#         根据 doc_ids 查询 chunk。
#         用于 mode1 以及 mode3 中的标题召回部分。
#         """
#         if not doc_ids:
#             return []

#         query = {
#             "doc_ids": doc_ids,
#             "page": page,
#             "size": int(req.get("title_size", 50)),
#             "question": "",
#             "sort": True
#         }

#         if "available_int" in req:
#             query["available_int"] = int(req["available_int"])

#         sres = settings.retriever.search(
#             query,
#             search.index_name(tenant_id),
#             kb_ids,
#             highlight=["content_ltks"]
#         )

#         chunks = []

#         for cid in sres.ids:
#             field = sres.field[cid]
#             chunks.append({
#                 "chunk_id": cid,
#                 "content_with_weight": (
#                     remove_redundant_spaces(sres.highlight[cid])
#                     if cid in sres.highlight else field.get("content_with_weight", "")
#                 ),
#                 "doc_id": field["doc_id"],
#                 "docnm_kwd": field["docnm_kwd"],
#                 "important_kwd": field.get("important_kwd", []),
#                 "question_kwd": field.get("question_kwd", []),
#                 "image_id": field.get("img_id", ""),
#                 "available_int": int(field.get("available_int", 1)),
#                 "positions": field.get("position_int", []),
#                 "kb_id": kb_ids[0] if len(kb_ids) == 1 else field.get("kb_id", "")
#             })

#         return chunks

#     async def _semantic_retrieval(tenant_ids, kb, local_doc_ids=None):
#         """
#         语义相似度查询。
#         mode2 和 mode3 都会用到。
#         """
#         meta_data_filter = {}
#         chat_mdl = None

#         if req.get("search_id", ""):
#             search_config = SearchService.get_detail(req.get("search_id", "")).get("search_config", {})
#             meta_data_filter = search_config.get("meta_data_filter", {})

#             if meta_data_filter.get("method") in ["auto", "semi_auto"]:
#                 chat_mdl = LLMBundle(
#                     user_id,
#                     LLMType.CHAT,
#                     llm_name=search_config.get("chat_id", "")
#                 )
#         else:
#             meta_data_filter = req.get("meta_data_filter") or {}

#             if meta_data_filter.get("method") in ["auto", "semi_auto"]:
#                 chat_mdl = LLMBundle(user_id, LLMType.CHAT)

#         if local_doc_ids is None:
#             local_doc_ids = []

#         if meta_data_filter:
#             metas = DocumentService.get_meta_by_kbs(kb_ids)
#             local_doc_ids = await apply_meta_data_filter(
#                 meta_data_filter,
#                 metas,
#                 question,
#                 chat_mdl,
#                 local_doc_ids
#             )

#         _question = question

#         if langs:
#             _question = await cross_languages(kb.tenant_id, None, _question, langs)

#         embd_mdl = LLMBundle(
#             kb.tenant_id,
#             LLMType.EMBEDDING.value,
#             llm_name=kb.embd_id
#         )

#         rerank_mdl = None
#         if req.get("rerank_id"):
#             rerank_mdl = LLMBundle(
#                 kb.tenant_id,
#                 LLMType.RERANK.value,
#                 llm_name=req["rerank_id"]
#             )

#         if req.get("keyword", False):
#             chat_mdl = LLMBundle(kb.tenant_id, LLMType.CHAT)
#             _question += await keyword_extraction(chat_mdl, _question)

#         labels = label_question(_question, [kb])

#         ranks = settings.retriever.retrieval(
#             _question,
#             embd_mdl,
#             tenant_ids,
#             kb_ids,
#             page,
#             size,
#             float(req.get("similarity_threshold", 0.0)),
#             float(req.get("vector_similarity_weight", 0.3)),
#             top,
#             local_doc_ids,
#             rerank_mdl=rerank_mdl,
#             highlight=req.get("highlight", False),
#             rank_feature=labels
#         )

#         return ranks, labels, embd_mdl, _question

#     def _merge_chunks(file_chunks, semantic_chunks):
#         """
#         chunk 合并去重。
#         """
#         merged_chunks = []

#         import builtins
#         seen = builtins.set()

#         def _append_chunk(c):
#             cid = c.get("chunk_id") or c.get("id")
#             if not cid or cid in seen:
#                 return
#             seen.add(cid)
#             merged_chunks.append(c)

#         for c in file_chunks:
#             _append_chunk(c)

#         for c in semantic_chunks:
#             _append_chunk(c)

#         return merged_chunks

#     def _fill_kb_name(chunks):
#         """
#         去掉 vector，补充 kb_name。
#         """
#         for c in chunks:
#             c.pop("vector", None)

#             kb_detail = KnowledgebaseService.get_detail(c["kb_id"])
#             if kb_detail:
#                 c["kb_name"] = kb_detail.get("name", "未知知识库")
#             else:
#                 c["kb_name"] = "未知知识库"

#         return chunks

#     async def _retrieval_by_title():
#         """
#         mode1：
#         只按照标题 / 文件名查询。
#         """
#         tenant_ids, kb, error = await _prepare_context()
#         if error:
#             return error

#         tenant_id = kb.tenant_id

#         file_doc_ids = _get_title_doc_ids()
#         print(file_doc_ids)

#         file_chunks = _search_chunks_by_doc_ids(file_doc_ids, tenant_id)

#         file_chunks = settings.retriever.retrieval_by_children(file_chunks, tenant_ids)
#         file_chunks = _fill_kb_name(file_chunks)

#         return get_json_result(data={
#             "chunks": file_chunks,
#             # "total": len(file_chunks),
#             "total": 100,
#             "file_doc_ids": file_doc_ids,
#             "mode": "1"
#         })

#     async def _retrieval_by_tag_similarity():
#         """
#         mode2：
#         tag 过滤后的相似度查询。
#         """
#         tenant_ids, kb, error = await _prepare_context()
#         if error:
#             return error

#         if not tag:
#             return get_json_result(
#                 data=False,
#                 message="mode2 requires tag.",
#                 code=RetCode.DATA_ERROR
#             )

#         doc_ids = DocumentService.get_doc_ids_by_tags(kb_ids, tag)

#         # 如果 tag 下没有文档，直接返回空
#         if doc_ids == []:
#             return get_json_result(data={
#             "chunks": [],
#             "total": 0,
#             "doc_ids": [],
#             "tag_doc_ids": [],
#             "mode": "2"
#             })

#         local_doc_ids = doc_ids

#         ranks, labels, embd_mdl, _question = await _semantic_retrieval(
#             tenant_ids,
#             kb,
#             local_doc_ids
#         )

#         chunks = ranks.get("chunks", [])

#         chunks = settings.retriever.retrieval_by_children(chunks, tenant_ids)
#         chunks = _fill_kb_name(chunks)

#         ranks["chunks"] = chunks
#         ranks["labels"] = labels
#         ranks["tag_doc_ids"] = local_doc_ids
#         ranks["mode"] = "2"

#         return get_json_result(data=ranks)

#     async def _retrieval():
#         """
#         mode3：
#         当前完整 retrieval：
#         标题召回 + 语义召回 + KG + 合并。
#         """
#         tenant_ids, kb, error = await _prepare_context()
#         if error:
#             return error

#         tenant_id = kb.tenant_id

#         # 1. 标题 / 文件名召回
#         file_doc_ids = _get_title_doc_ids()
#         file_chunks = _search_chunks_by_doc_ids(file_doc_ids, tenant_id)

#         # 2. tag 过滤后的语义召回
#         doc_ids = DocumentService.get_doc_ids_by_tags(kb_ids, tag) if tag else []
#         # 如果 tag 下没有文档，直接返回空
#         if doc_ids == []:
#             return get_json_result(data={
#             "chunks": [],
#             "total": 0,
#             "doc_ids": [],
#             "tag_doc_ids": [],
#             "mode": "2"
#             })

#         local_doc_ids = doc_ids

#         ranks, labels, embd_mdl, _question = await _semantic_retrieval(
#             tenant_ids,
#             kb,
#             local_doc_ids
#         )

#         # 3. KG 召回
#         if use_kg:
#             ck = settings.kg_retriever.retrieval(
#                 _question,
#                 tenant_ids,
#                 kb_ids,
#                 embd_mdl,
#                 LLMBundle(kb.tenant_id, LLMType.CHAT)
#             )

#             if ck["content_with_weight"]:
#                 ranks["chunks"].insert(0, ck)

#         # 4. 合并标题召回和语义召回
#         merged_chunks = _merge_chunks(file_chunks, ranks.get("chunks", []))

#         # 5. child chunk 展开
#         merged_chunks = settings.retriever.retrieval_by_children(
#             merged_chunks,
#             tenant_ids
#         )

#         # 6. 去掉 vector，补 kb_name
#         merged_chunks = _fill_kb_name(merged_chunks)

#         ranks["chunks"] = merged_chunks
#         ranks["labels"] = labels
#         ranks["file_doc_ids"] = file_doc_ids
#         ranks["mode"] = "3"

#         return get_json_result(data=ranks)

#     try:
#         if mode == "mode1":
#             return await _retrieval_by_title()

#         elif mode == "mode2":
#             return await _retrieval_by_tag_similarity()

#         elif mode == "mode3":
#             return await _retrieval()

#         else:
#             return get_json_result(
#                 data=False,
#                 message="Invalid mode, mode must be 1, 2 or 3.",
#                 code=RetCode.DATA_ERROR
#             )

#     except Exception as e:
#         if str(e).find("not_found") > 0:
#             return get_json_result(
#                 data=False,
#                 message='No chunk found! Check the chunk status please!',
#                 code=RetCode.DATA_ERROR
#             )

#         return server_error_response(e)

@manager.route('/retrieval_test', methods=['POST'])  # noqa: F821
@login_required
@validate_request("kb_id", "question")
async def retrieval_test():
    req = await get_request_json()

    page = int(req.get("page", 1))
    size = int(req.get("size", 30))
    question = req["question"].strip()
    kb_ids = req["kb_id"]
    tag = req.get("tag")
    use_kg = req.get("use_kg", False)
    top = int(req.get("top_k", 1024))
    langs = req.get("cross_languages", [])
    user_id = current_user.id
    mode = str(req.get("mode", "mode3"))

    if isinstance(kb_ids, str):
        kb_ids = [kb_ids]

    if not kb_ids:
        return get_json_result(
            data=False,
            message='Please specify dataset firstly.',
            code=RetCode.DATA_ERROR
        )

    async def _prepare_context():
        """
        公共逻辑：
        1. 校验知识库权限
        2. 获取 tenant_ids
        3. 获取当前 kb
        """
        tenant_ids = []

        for kb_id in kb_ids:
            if not KnowledgebaseService.accessible(kb_id, user_id):
                return None, None, get_json_result(
                    data=False,
                    message='Only owner of dataset authorized for this operation.',
                    code=RetCode.OPERATING_ERROR
                )

            e, _kb = KnowledgebaseService.get_by_id(kb_id)
            if not e:
                return None, None, get_data_error_result(message="Knowledgebase not found!")

            tenant_ids.append(_kb.tenant_id)

        e, kb = KnowledgebaseService.get_by_id(kb_ids[0])
        if not e:
            return None, None, get_data_error_result(message="Knowledgebase not found!")

        return tenant_ids, kb, None

    def _empty_result(mode_value, file_doc_ids=None, tag_doc_ids=None, labels=None):
        """
        统一空返回结构。
        """
        return {
            "chunks": [],
            "total": 0,
            "returned": 0,
            "page": page,
            "size": size,
            "doc_aggs": [],
            "labels": labels or {},
            "file_doc_ids": file_doc_ids or [],
            "tag_doc_ids": tag_doc_ids,
            "mode": mode_value
        }

    def _get_title_doc_ids():
        """
        标题 / 文件名查询 doc_id。
        如果传了 tag，则和 tag 查询出来的 doc_id 取交集。

        get_doc_ids_by_tags 返回：
        None：没选标签
        []：选了标签但没命中
        list：命中文档 id
        """
        file_doc_ids = DocumentService.get_doc_ids_by_file_name(question) or []

        tag_doc_ids = DocumentService.get_doc_ids_by_tags(kb_ids, tag)

        # 没选标签：标题结果不做 tag 过滤
        if tag_doc_ids is None:
            return file_doc_ids

        # 选了标签但没命中：标题结果为空
        if tag_doc_ids == []:
            return []

        # 选了标签且命中：标题命中文档和 tag 命中文档取交集
        import builtins
        return list(builtins.set(file_doc_ids) & builtins.set(tag_doc_ids))

    def _search_chunks_by_doc_ids(doc_ids, tenant_id):
        """
        根据 doc_ids 分页查询 chunk。
        用于 mode1 以及 mode3 中的标题召回部分。

        返回：
        chunks, total
        """
        if not doc_ids:
            return [], 0

        query = {
            "doc_ids": doc_ids,
            "page": page,
            "size": size,
            "question": "",
            "sort": True
        }

        if "available_int" in req:
            query["available_int"] = int(req["available_int"])

        sres = settings.retriever.search(
            query,
            search.index_name(tenant_id),
            kb_ids,
            highlight=["content_ltks"]
        )

        chunks = []

        for cid in sres.ids:
            field = sres.field[cid]
            chunks.append({
                "chunk_id": cid,
                "content_with_weight": (
                    remove_redundant_spaces(sres.highlight[cid])
                    if cid in sres.highlight else field.get("content_with_weight", "")
                ),
                "doc_id": field["doc_id"],
                "docnm_kwd": field["docnm_kwd"],
                "important_kwd": field.get("important_kwd", []),
                "question_kwd": field.get("question_kwd", []),
                "image_id": field.get("img_id", ""),
                "available_int": int(field.get("available_int", 1)),
                "positions": field.get("position_int", []),
                "kb_id": kb_ids[0] if len(kb_ids) == 1 else field.get("kb_id", "")
            })

        total = getattr(sres, "total", None)
        if total is None:
            total = getattr(sres, "total_count", None)
        if total is None:
            total = len(chunks)

        return chunks, total

    async def _semantic_retrieval(tenant_ids, kb, local_doc_ids=None):
        """
        语义相似度查询。
        mode2 和 mode3 都会用到。

        local_doc_ids:
        None：不限制 doc_id，也就是全量检索
        []：空限制，一般不应该传进来，外层会提前返回空
        list：只在这些 doc_id 中检索
        """
        meta_data_filter = {}
        chat_mdl = None

        if req.get("search_id", ""):
            search_config = SearchService.get_detail(req.get("search_id", "")).get("search_config", {})
            meta_data_filter = search_config.get("meta_data_filter", {})

            if meta_data_filter.get("method") in ["auto", "semi_auto"]:
                chat_mdl = LLMBundle(
                    user_id,
                    LLMType.CHAT,
                    llm_name=search_config.get("chat_id", "")
                )
        else:
            meta_data_filter = req.get("meta_data_filter") or {}

            if meta_data_filter.get("method") in ["auto", "semi_auto"]:
                chat_mdl = LLMBundle(user_id, LLMType.CHAT)

        # 注意：
        # 这里不要把 None 改成 []
        # None 表示不限制文档，[] 表示空文档集合
        if meta_data_filter:
            metas = DocumentService.get_meta_by_kbs(kb_ids)
            local_doc_ids = await apply_meta_data_filter(
                meta_data_filter,
                metas,
                question,
                chat_mdl,
                local_doc_ids
            )

            # 如果 meta filter 后没有文档，直接给空结果
            if local_doc_ids == []:
                return {
                    "chunks": [],
                    "total": 0,
                    "doc_aggs": []
                }, {}, None, question

        _question = question

        if langs:
            _question = await cross_languages(kb.tenant_id, None, _question, langs)

        embd_mdl = LLMBundle(
            kb.tenant_id,
            LLMType.EMBEDDING.value,
            llm_name=kb.embd_id
        )

        rerank_mdl = None
        if req.get("rerank_id"):
            rerank_mdl = LLMBundle(
                kb.tenant_id,
                LLMType.RERANK.value,
                llm_name=req["rerank_id"]
            )

        if req.get("keyword", False):
            chat_mdl = LLMBundle(kb.tenant_id, LLMType.CHAT)
            _question += await keyword_extraction(chat_mdl, _question)

        labels = label_question(_question, [kb])

        ranks = settings.retriever.retrieval(
            _question,
            embd_mdl,
            tenant_ids,
            kb_ids,
            page,
            size,
            float(req.get("similarity_threshold", 0.0)),
            float(req.get("vector_similarity_weight", 0.3)),
            top,
            local_doc_ids,
            rerank_mdl=rerank_mdl,
            highlight=req.get("highlight", False),
            rank_feature=labels
        )

        return ranks, labels, embd_mdl, _question

    def _merge_chunks(file_chunks, semantic_chunks):
        """
        chunk 合并去重。
        """
        merged_chunks = []

        import builtins
        seen = builtins.set()

        def _append_chunk(c):
            cid = c.get("chunk_id") or c.get("id")
            if not cid or cid in seen:
                return
            seen.add(cid)
            merged_chunks.append(c)

        for c in file_chunks:
            _append_chunk(c)

        for c in semantic_chunks:
            _append_chunk(c)

        return merged_chunks

    def _fill_kb_name(chunks):
        """
        去掉 vector，补充 kb_name。
        """
        for c in chunks:
            c.pop("vector", None)

            kb_id = c.get("kb_id")
            if not kb_id:
                c["kb_name"] = "未知知识库"
                continue

            kb_detail = KnowledgebaseService.get_detail(kb_id)
            if kb_detail:
                c["kb_name"] = kb_detail.get("name", "未知知识库")
            else:
                c["kb_name"] = "未知知识库"

        return chunks

    def _normalize_result(ranks, mode_value, file_doc_ids=None, tag_doc_ids=None, labels=None):
        chunks = ranks.get("chunks", [])

        ranks["chunks"] = chunks
        ranks["total"] = ranks.get("total", len(chunks))
        ranks["returned"] = len(chunks)
        ranks["page"] = page
        ranks["size"] = size
        ranks["doc_aggs"] = ranks.get("doc_aggs", [])
        ranks["labels"] = labels or ranks.get("labels", {})
        ranks["file_doc_ids"] = file_doc_ids or []
        ranks["tag_doc_ids"] = tag_doc_ids
        ranks["mode"] = mode_value

        return ranks

    def _build_doc_aggs(chunks):
        doc_map = {}

        for c in chunks:
            doc_id = c.get("doc_id")
            if not doc_id:
                continue

            doc_name = c.get("docnm_kwd", "")
            if isinstance(doc_name, list):
                doc_name = doc_name[0] if doc_name else ""

            if doc_id not in doc_map:
                doc_map[doc_id] = {
                    "doc_id": doc_id,
                    "doc_name": doc_name,
                    "kb_id": c.get("kb_id", ""),
                    "count": 0
                }

            doc_map[doc_id]["count"] += 1

        return list(doc_map.values())

    async def _retrieval_by_title():
        """
        mode1：
        只按照标题 / 文件名查询。
        """
        tenant_ids, kb, error = await _prepare_context()
        if error:
            return error

        tenant_id = kb.tenant_id

        file_doc_ids = _get_title_doc_ids()

        file_chunks, total = _search_chunks_by_doc_ids(file_doc_ids, tenant_id)

        file_chunks = settings.retriever.retrieval_by_children(file_chunks, tenant_ids)
        file_chunks = _fill_kb_name(file_chunks)

        doc_aggs = _build_doc_aggs(file_chunks)

        ranks = {
            "chunks": file_chunks,
            "total": total,
            "doc_aggs": doc_aggs
        }

        data = _normalize_result(
            ranks,
            mode_value="1",
            file_doc_ids=file_doc_ids,
            tag_doc_ids=DocumentService.get_doc_ids_by_tags(kb_ids, tag),
            labels={}
        )

        return get_json_result(data=data)

    async def _retrieval_by_tag_similarity():
        """
        mode2：
        tag 过滤后的相似度查询。

        没选标签：
            tag_doc_ids is None
            local_doc_ids = None
            表示全量相似度检索

        选了标签但没命中：
            tag_doc_ids == []
            直接返回空

        选了标签且命中：
            local_doc_ids = tag_doc_ids
        """
        tenant_ids, kb, error = await _prepare_context()
        if error:
            return error

        tag_doc_ids = DocumentService.get_doc_ids_by_tags(kb_ids, tag)

        if tag_doc_ids == []:
            return get_json_result(
                data=_empty_result(
                    mode_value="2",
                    file_doc_ids=[],
                    tag_doc_ids=[]
                )
            )

        local_doc_ids = tag_doc_ids

        ranks, labels, embd_mdl, _question = await _semantic_retrieval(
            tenant_ids,
            kb,
            local_doc_ids
        )

        chunks = ranks.get("chunks", [])
        chunks = settings.retriever.retrieval_by_children(chunks, tenant_ids)
        chunks = _fill_kb_name(chunks)

        ranks["chunks"] = chunks
        ranks["labels"] = labels

        data = _normalize_result(
            ranks,
            mode_value="2",
            file_doc_ids=[],
            tag_doc_ids=tag_doc_ids,
            labels=labels
        )

        return get_json_result(data=data)

    async def _retrieval():
        """
        mode3：
        标题召回第 N 页 + 语义召回第 N 页 + KG + 合并。
        """
        tenant_ids, kb, error = await _prepare_context()
        if error:
            return error

        tenant_id = kb.tenant_id

        # 1. 标题 / 文件名召回：第 N 页
        file_doc_ids = _get_title_doc_ids()
        file_chunks, title_total = _search_chunks_by_doc_ids(file_doc_ids, tenant_id)

        # 2. tag 过滤后的语义召回：第 N 页
        tag_doc_ids = DocumentService.get_doc_ids_by_tags(kb_ids, tag)

        # 选了 tag 但没命中，直接空结果
        if tag_doc_ids == []:
            return get_json_result(
                data=_empty_result(
                    mode_value="3",
                    file_doc_ids=file_doc_ids,
                    tag_doc_ids=[]
                )
            )

        # 没选标签：tag_doc_ids is None，直接查全量
        local_doc_ids = tag_doc_ids

        ranks, labels, embd_mdl, _question = await _semantic_retrieval(
            tenant_ids,
            kb,
            local_doc_ids
        )

        semantic_total = ranks.get("total", 0)

        # 3. KG 召回
        if use_kg and embd_mdl:
            ck = settings.kg_retriever.retrieval(
                _question,
                tenant_ids,
                kb_ids,
                embd_mdl,
                LLMBundle(kb.tenant_id, LLMType.CHAT)
            )

            if ck.get("content_with_weight"):
                ranks.setdefault("chunks", []).insert(0, ck)

        # 4. 合并标题召回和语义召回
        merged_chunks = _merge_chunks(file_chunks, ranks.get("chunks", []))

        # 5. child chunk 展开
        merged_chunks = settings.retriever.retrieval_by_children(
            merged_chunks,
            tenant_ids
        )

        # 6. 补 kb_name
        merged_chunks = _fill_kb_name(merged_chunks)

        # 7. 构造 doc_aggs
        doc_aggs = _build_doc_aggs(merged_chunks)

        # 8. 统一返回
        ranks["chunks"] = merged_chunks
        ranks["labels"] = labels
        ranks["doc_aggs"] = doc_aggs
        ranks["title_total"] = title_total
        ranks["semantic_total"] = semantic_total

        data = _normalize_result(
            ranks,
            mode_value="3",
            file_doc_ids=file_doc_ids,
            tag_doc_ids=tag_doc_ids,
            labels=labels
        )

        return get_json_result(data=data)

    try:
        if mode in ("1", "mode1"):
            return await _retrieval_by_title()

        elif mode in ("2", "mode2"):
            return await _retrieval_by_tag_similarity()

        elif mode in ("3", "mode3"):
            return await _retrieval()

        else:
            return get_json_result(
                data=False,
                message="Invalid mode, mode must be 1, 2 or 3.",
                code=RetCode.DATA_ERROR
            )

    except Exception as e:
        if str(e).find("not_found") > 0:
            return get_json_result(
                data=False,
                message='No chunk found! Check the chunk status please!',
                code=RetCode.DATA_ERROR
            )

        return server_error_response(e)


@manager.route('/knowledge_graph', methods=['GET'])  # noqa: F821
@login_required
def knowledge_graph():
    doc_id = request.args["doc_id"]
    tenant_id = DocumentService.get_tenant_id(doc_id)
    kb_ids = KnowledgebaseService.get_kb_ids(tenant_id)
    req = {
        "doc_ids": [doc_id],
        "knowledge_graph_kwd": ["graph", "mind_map"]
    }
    sres = settings.retriever.search(req, search.index_name(tenant_id), kb_ids)
    obj = {"graph": {}, "mind_map": {}}
    for id in sres.ids[:2]:
        ty = sres.field[id]["knowledge_graph_kwd"]
        try:
            content_json = json.loads(sres.field[id]["content_with_weight"])
        except Exception:
            continue

        if ty == 'mind_map':
            node_dict = {}

            def repeat_deal(content_json, node_dict):
                if 'id' in content_json:
                    if content_json['id'] in node_dict:
                        node_name = content_json['id']
                        content_json['id'] += f"({node_dict[content_json['id']]})"
                        node_dict[node_name] += 1
                    else:
                        node_dict[content_json['id']] = 1
                if 'children' in content_json and content_json['children']:
                    for item in content_json['children']:
                        repeat_deal(item, node_dict)

            repeat_deal(content_json, node_dict)

        obj[ty] = content_json

    return get_json_result(data=obj)
