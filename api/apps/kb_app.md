# RAGFlow Knowledge Base API (kb_app.py) 分析报告

该文件定义了 RAGFlow 中与 **知识库 (Knowledge Base, KB)** 相关的后端 API 接口。所有接口均要求用户登录 (`@login_required`)。

## 1. 核心管理接口

### **创建知识库**
- **路径**: `/create`
- **方法**: `POST`
- **功能**: 创建一个新的知识库。
- **关键参数**: `name` (必填), `parser_id` (可选), `description` (可选)。
- **逻辑**: 调用 `KnowledgebaseService.create_with_name` 初始化数据，并保存到数据库。

### **更新知识库**
- **路径**: `/update`
- **方法**: `POST`
- **功能**: 修改知识库的配置（如名称、描述、解析器、权限等）。
- **关键参数**: `kb_id`, `name`, `description`, `parser_id`。
- **权限**: 仅允许知识库所有者操作。

### **删除知识库**
- **路径**: `/rm`
- **方法**: `POST`
- **功能**: 彻底删除知识库及其关联的所有文档、文件、索引数据和存储桶。
- **逻辑**: 同步清理数据库记录、Elasticsearch/Milvus 索引以及底层存储。

### **获取详情**
- **路径**: `/detail`
- **方法**: `GET`
- **功能**: 获取特定知识库的详细信息，包括文档总大小、关联的连接器等。
- **参数**: `kb_id`。

### **知识库列表**
- **路径**: `/list`
- **方法**: `POST`
- **功能**: 分页获取当前用户有权访问的知识库列表。
- **支持过滤**: `keywords` (名称搜索), `parser_id`, `owner_ids`。

---

## 2. 标签 (Tags) 管理接口

### **获取标签列表**
- **路径**: `/<kb_id>/tags` (GET) 或 `/tags` (GET)
- **功能**: 从指定的知识库中提取所有已定义的标签（通过检索器从索引中获取）。

### **删除/重命名标签**
- **路径**: `/<kb_id>/rm_tags` (POST) 和 `/<kb_id>/rename_tag` (POST)
- **功能**: 批量删除标签或修改现有标签名称。该操作会直接更新搜索引擎中的 `tag_kwd` 字段。

---

## 3. 知识图谱 (Knowledge Graph) 接口

### **获取知识图谱**
- **路径**: `/<kb_id>/knowledge_graph`
- **方法**: `GET`
- **功能**: 获取知识库生成的知识图谱数据（节点和边），支持按 PageRank 排序和过滤。

### **删除知识图谱**
- **路径**: `/<kb_id>/knowledge_graph`
- **方法**: `DELETE`
- **功能**: 清除该知识库下所有的知识图谱相关索引数据。

---

## 4. 统计与元数据接口

### **获取元数据**
- **路径**: `/get_meta`
- **方法**: `GET`
- **功能**: 获取指定知识库下所有文档的元数据（如文件名等）。

### **基础统计信息**
- **路径**: `/basic_info`
- **方法**: `GET`
- **功能**: 获取知识库的统计概览（如文档数量、解析状态统计等）。

---

## 5. 流水线日志 (Pipeline Logs) 接口

### **查看流水线日志**
- **路径**: `/list_pipeline_logs` (POST) 和 `/list_pipeline_dataset_logs` (POST)
- **功能**: 分页查看文件解析、处理的流水线日志。
- **过滤条件**: 状态 (`operation_status`), 文件类型 (`types`), 后缀 (`suffix`), 时间范围等。

### **删除流水线日志**
- **路径**: `/delete_pipeline_logs`
- **方法**: `POST`
- **功能**: 根据 ID 批量删除流水线记录。

---

## 技术细节说明
- **异步处理**: 大部分写操作（如 `/rm`）使用 `asyncio.to_thread` 运行，以避免阻塞 Quart 的异步主循环。
- **安全性**: 接口广泛使用 `KnowledgebaseService.accessible` 或 `accessible4deletion` 校验当前用户是否有权操作目标知识库。
- **数据一致性**: 知识库的删除和更新不仅涉及关系型数据库 (MySQL)，还同步操作搜索引擎 (Elasticsearch/Infinity) 和文件存储 (MinIO/S3)。