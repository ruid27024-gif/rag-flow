1. 前端调用流程用户提交申请

await request.post('/knowledge/permission/apply', {
  kb_id: selectedKbId,
  permissions: ['preview', 'upload'],
  reason: '项目需要使用该知识库',
});

2.OA 审批页面查询

await request.get('/oa/workflow/pending');

3. OA 审批通过
await request.post('/oa/workflow/approve', {
  approval_id: approvalId,
  status: 'approved',
  comment: '同意',
});

await request.post('/oa/workflow/approve', {
  approval_id: approvalId,
  status: 'rejected',
  comment: '权限过大，驳回',
});