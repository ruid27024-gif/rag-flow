import { useFetchUserInfo } from '@/hooks/use-user-setting-request';
import { useCallback, useEffect, useMemo, useState } from 'react';

const API_BASE = 'http://127.0.0.1:9380';
// const API_PREFIX = `${API_BASE}/v1/document`;
const API_PREFIX = '/v1/document';

const STATUS_TEXT = {
  pending: '待审批',
  pending_level_1: '待一级审批',
  approved: '已同意',
  rejected: '已拒绝',
  callback_success: '回调成功',
  callback_failed: '回调失败',
  importing: '入库中',
  imported: '已入库',
  import_failed: '入库失败',
  partial_imported: '部分入库',
};

export default function Level1ApprovalPage() {
  const { data: userInfo, loading: userLoading } = useFetchUserInfo();

  // 根据当前项目用户对象的实际字段取值
  const currentUserId = useMemo(() => {
    return String(
      userInfo?.id || userInfo?.user_id || userInfo?.userId || '',
    ).trim();
  }, [userInfo]);

  const currentUserName = useMemo(() => {
    return (
      userInfo?.nickname ||
      userInfo?.name ||
      userInfo?.username ||
      userInfo?.user_name ||
      currentUserId
    );
  }, [userInfo, currentUserId]);

  const [tasks, setTasks] = useState([]);
  const [detail, setDetail] = useState(null);
  const [comment, setComment] = useState('');

  const [loadingTasks, setLoadingTasks] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  /**
   * 统一请求方法。
   * response.text() 可以避免后端返回 HTML 时直接出现 JSON 解析错误。
   */
  const requestJson = useCallback(async (url, options = {}) => {
    const response = await fetch(url, {
      credentials: 'include',
      ...options,
      headers: {
        Accept: 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(options.headers || {}),
      },
    });

    const text = await response.text();

    let result;

    try {
      result = text ? JSON.parse(text) : {};
    } catch {
      throw new Error(
        `接口未返回 JSON，HTTP ${response.status}：${text.slice(0, 200)}`,
      );
    }

    const failed =
      !response.ok ||
      (result.code !== undefined && result.code !== 0 && result.code !== '0');

    if (failed) {
      throw new Error(
        result.message || result.msg || `请求失败，HTTP ${response.status}`,
      );
    }

    return result.data !== undefined ? result.data : result;
  }, []);

  /**
   * 查询当前登录用户的一级待审批任务。
   */
  const loadTasks = useCallback(async () => {
    if (!currentUserId) {
      setTasks([]);
      return;
    }

    setLoadingTasks(true);
    setErrorMessage('');

    try {
      const url =
        `${API_PREFIX}/oa/approval/level1/tasks` +
        `?approver_user_id=${encodeURIComponent(currentUserId)}` +
        `&status=pending`;

      const data = await requestJson(url);

      setTasks(Array.isArray(data) ? data : []);
    } catch (error) {
      setErrorMessage(error.message || '加载审批列表失败');
    } finally {
      setLoadingTasks(false);
    }
  }, [currentUserId, requestJson]);

  /**
   * 查询审批详情。
   */
  const loadDetail = useCallback(
    async (approvalId) => {
      if (!approvalId) {
        return;
      }

      setLoadingDetail(true);
      setErrorMessage('');

      try {
        const data = await requestJson(
          `${API_PREFIX}/oa/approval/detail?approval_id=${encodeURIComponent(
            approvalId,
          )}`,
        );

        setDetail(data);
        setComment('');
      } catch (error) {
        setErrorMessage(error.message || '加载审批详情失败');
      } finally {
        setLoadingDetail(false);
      }
    },
    [requestJson],
  );

  /**
   * 同意或拒绝审批。
   */
  const submitDecision = useCallback(
    async (result) => {
      if (!detail || submitting) {
        return;
      }

      if (!currentUserId) {
        setErrorMessage('无法获取当前登录用户 ID');
        return;
      }

      if (result === 'rejected' && !comment.trim()) {
        setErrorMessage('拒绝审批时必须填写审批意见');
        return;
      }

      const confirmMessage =
        result === 'approved' ? '确认同意该审批吗？' : '确认拒绝该审批吗？';

      if (!window.confirm(confirmMessage)) {
        return;
      }

      setSubmitting(true);
      setErrorMessage('');

      try {
        await requestJson(`${API_PREFIX}/oa/approval/decision`, {
          method: 'POST',
          body: JSON.stringify({
            approval_id: detail.approval_id,

            // 这里传系统用户 ID，不是 MDM 用户 ID
            approver_user_id: currentUserId,
            approver_user_name: currentUserName,

            result,
            comment: comment.trim(),
          }),
        });

        window.alert(result === 'approved' ? '审批已同意' : '审批已拒绝');

        setDetail(null);
        setComment('');

        await loadTasks();
      } catch (error) {
        setErrorMessage(error.message || '审批操作失败');
      } finally {
        setSubmitting(false);
      }
    },
    [
      comment,
      currentUserId,
      currentUserName,
      detail,
      loadTasks,
      requestJson,
      submitting,
    ],
  );

  useEffect(() => {
    if (!userLoading && currentUserId) {
      loadTasks();
    }
  }, [userLoading, currentUserId, loadTasks]);

  if (userLoading) {
    return (
      <div style={styles.centerPage}>
        <div style={styles.loadingText}>正在加载当前用户信息...</div>
      </div>
    );
  }

  if (!currentUserId) {
    return (
      <div style={styles.centerPage}>
        <div style={styles.errorBox}>
          无法获取当前登录用户 ID，请重新登录后重试。
        </div>
      </div>
    );
  }

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div>
          <h1 style={styles.title}>一级审批</h1>
          <div style={styles.subtitle}>
            当前审批人：{currentUserName}
            <span style={styles.userId}>系统 ID：{currentUserId}</span>
          </div>
        </div>

        <button
          type="button"
          style={styles.secondaryButton}
          onClick={loadTasks}
          disabled={loadingTasks}
        >
          {loadingTasks ? '刷新中...' : '刷新'}
        </button>
      </header>

      {errorMessage && (
        <div style={styles.errorBox}>
          <span>{errorMessage}</span>
          <button
            type="button"
            style={styles.closeErrorButton}
            onClick={() => setErrorMessage('')}
          >
            关闭
          </button>
        </div>
      )}

      <main style={styles.layout}>
        <section style={styles.panel}>
          <div style={styles.panelHeader}>
            <div>
              <h2 style={styles.panelTitle}>待审批列表</h2>
              <div style={styles.panelHint}>只显示当前用户的一级待审批任务</div>
            </div>

            <span style={styles.countBadge}>{tasks.length}</span>
          </div>

          <div style={styles.tableWrapper}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>审批单号</th>
                  <th style={styles.th}>上传人</th>
                  <th style={styles.th}>文件数</th>
                  <th style={styles.th}>状态</th>
                  <th style={styles.th}>提交时间</th>
                  <th style={styles.th}>操作</th>
                </tr>
              </thead>

              <tbody>
                {loadingTasks && (
                  <tr>
                    <td colSpan={6} style={styles.emptyCell}>
                      正在加载...
                    </td>
                  </tr>
                )}

                {!loadingTasks && tasks.length === 0 && (
                  <tr>
                    <td colSpan={6} style={styles.emptyCell}>
                      暂无待审批任务
                    </td>
                  </tr>
                )}

                {!loadingTasks &&
                  tasks.map((item) => (
                    <tr
                      key={item.task_id || item.approval_id}
                      style={
                        detail?.approval_id === item.approval_id
                          ? styles.selectedRow
                          : undefined
                      }
                    >
                      <td style={styles.td}>
                        <div style={styles.primaryText}>
                          {item.approval_id || '-'}
                        </div>
                        <div style={styles.secondaryText}>
                          批次：{item.batch_id || '-'}
                        </div>
                      </td>

                      <td style={styles.td}>{item.uploader_user_id || '-'}</td>

                      <td style={styles.td}>{item.file_count ?? 0}</td>

                      <td style={styles.td}>
                        <StatusTag status={item.approval_status} />
                      </td>

                      <td style={styles.td}>{item.created_at || '-'}</td>

                      <td style={styles.td}>
                        <button
                          type="button"
                          style={styles.linkButton}
                          onClick={() => loadDetail(item.approval_id)}
                        >
                          查看详情
                        </button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </section>

        <section style={styles.panel}>
          <div style={styles.panelHeader}>
            <div>
              <h2 style={styles.panelTitle}>审批详情</h2>
              <div style={styles.panelHint}>查看文件后进行审批操作</div>
            </div>
          </div>

          {!detail && !loadingDetail && (
            <div style={styles.emptyDetail}>
              <div style={styles.emptyDetailTitle}>请选择审批记录</div>
              <div style={styles.emptyDetailText}>
                从左侧列表选择一条待审批记录
              </div>
            </div>
          )}

          {loadingDetail && (
            <div style={styles.emptyDetail}>
              <div style={styles.emptyDetailTitle}>正在加载详情...</div>
            </div>
          )}

          {detail && !loadingDetail && (
            <ApprovalDetail
              detail={detail}
              comment={comment}
              setComment={setComment}
              submitting={submitting}
              onDecision={submitDecision}
            />
          )}
        </section>
      </main>
    </div>
  );
}

function ApprovalDetail({
  detail,
  comment,
  setComment,
  submitting,
  onDecision,
}) {
  const files = Array.isArray(detail.files) ? detail.files : [];

  const tasks = Array.isArray(detail.tasks) ? detail.tasks : [];

  return (
    <div>
      <div style={styles.metaGrid}>
        <Info label="审批单号" value={detail.approval_id} />
        <Info label="批次号" value={detail.batch_id} />
        <Info label="知识库 ID" value={detail.kb_id} />
        <Info label="上传人" value={detail.uploader_user_id} />
        <Info label="审批状态" value={<StatusTag status={detail.status} />} />
        <Info label="当前级别" value={detail.current_level} />
        <Info label="创建时间" value={detail.created_at} />
        <Info label="更新时间" value={detail.updated_at} />
      </div>

      <section style={styles.detailSection}>
        <h3 style={styles.blockTitle}>文件列表</h3>

        <div style={styles.tableWrapper}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>文件名</th>
                <th style={styles.th}>大小</th>
                <th style={styles.th}>预览</th>
              </tr>
            </thead>

            <tbody>
              {files.length === 0 && (
                <tr>
                  <td colSpan={3} style={styles.emptyCell}>
                    没有文件信息
                  </td>
                </tr>
              )}

              {files.map((file, index) => (
                <tr
                  key={
                    file.id ||
                    file.object_name ||
                    `${file.filename || 'file'}-${index}`
                  }
                >
                  <td style={styles.td}>{file.filename || file.name || '-'}</td>

                  <td style={styles.td}>{formatSize(file.size)}</td>

                  <td style={styles.td}>
                    {file.url ? (
                      <a
                        href={file.url}
                        target="_blank"
                        rel="noreferrer"
                        style={styles.previewLink}
                      >
                        查看文件
                      </a>
                    ) : (
                      <span style={styles.mutedText}>暂无链接</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section style={styles.detailSection}>
        <h3 style={styles.blockTitle}>一级审批人</h3>

        <div style={styles.tableWrapper}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>审批人</th>
                <th style={styles.th}>系统用户 ID</th>
                <th style={styles.th}>状态</th>
                <th style={styles.th}>意见</th>
              </tr>
            </thead>

            <tbody>
              {tasks.length === 0 && (
                <tr>
                  <td colSpan={4} style={styles.emptyCell}>
                    暂无审批任务
                  </td>
                </tr>
              )}

              {tasks.map((task, index) => (
                <tr
                  key={task.task_id || task.approver_user_id || `task-${index}`}
                >
                  <td style={styles.td}>{task.approver_name || '-'}</td>

                  <td style={styles.td}>{task.approver_user_id || '-'}</td>

                  <td style={styles.td}>
                    <StatusTag status={task.status} />
                  </td>

                  <td style={styles.td}>{task.comment || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section style={styles.detailSection}>
        <h3 style={styles.blockTitle}>审批意见</h3>

        <textarea
          value={comment}
          disabled={submitting}
          onChange={(event) => setComment(event.target.value)}
          placeholder="请输入审批意见。拒绝时必须填写。"
          style={styles.textarea}
        />

        <div style={styles.actions}>
          <button
            type="button"
            style={styles.rejectButton}
            disabled={submitting}
            onClick={() => onDecision('rejected')}
          >
            {submitting ? '处理中...' : '拒绝'}
          </button>

          <button
            type="button"
            style={styles.approveButton}
            disabled={submitting}
            onClick={() => onDecision('approved')}
          >
            {submitting ? '处理中...' : '同意'}
          </button>
        </div>
      </section>
    </div>
  );
}

function Info({ label, value }) {
  return (
    <div style={styles.infoItem}>
      <div style={styles.infoLabel}>{label}</div>
      <div style={styles.infoValue}>{value || '-'}</div>
    </div>
  );
}

function StatusTag({ status }) {
  const text = STATUS_TEXT[status] || status || '未知';

  let color = '#6b7280';
  let background = '#f3f4f6';

  if (['pending', 'pending_level_1'].includes(status)) {
    color = '#b45309';
    background = '#fef3c7';
  }

  if (['approved', 'callback_success', 'imported'].includes(status)) {
    color = '#047857';
    background = '#d1fae5';
  }

  if (['rejected', 'callback_failed', 'import_failed'].includes(status)) {
    color = '#b91c1c';
    background = '#fee2e2';
  }

  if (['importing', 'partial_imported'].includes(status)) {
    color = '#1d4ed8';
    background = '#dbeafe';
  }

  return (
    <span
      style={{
        ...styles.statusTag,
        color,
        background,
      }}
    >
      {text}
    </span>
  );
}

function formatSize(size) {
  const value = Number(size || 0);

  if (value < 1024) {
    return `${value} B`;
  }

  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }

  if (value < 1024 * 1024 * 1024) {
    return `${(value / 1024 / 1024).toFixed(1)} MB`;
  }

  return `${(value / 1024 / 1024 / 1024).toFixed(1)} GB`;
}

const styles = {
  page: {
    minHeight: '100vh',
    padding: 24,
    boxSizing: 'border-box',
    background: 'transparent',
    color: 'hsl(var(--foreground))',
  },

  centerPage: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'transparent',
    color: 'hsl(var(--foreground))',
  },

  loadingText: {
    color: 'hsl(var(--muted-foreground))',
    fontSize: 14,
  },

  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 16,
    marginBottom: 18,
  },

  title: {
    margin: 0,
    fontSize: 24,
    fontWeight: 600,
    color: 'hsl(var(--foreground))',
  },

  subtitle: {
    marginTop: 7,
    color: 'hsl(var(--muted-foreground))',
    fontSize: 13,
  },

  userId: {
    marginLeft: 14,
    color: 'hsl(var(--muted-foreground))',
  },

  layout: {
    display: 'grid',
    gridTemplateColumns: 'minmax(560px, 1.1fr) minmax(440px, 0.9fr)',
    gap: 16,
    alignItems: 'start',
  },

  // 原布局不变，只去掉面板背景
  panel: {
    minWidth: 0,
    background: 'transparent',
    border: '1px solid hsl(var(--border))',
    borderRadius: 8,
    padding: 16,
  },

  panelHeader: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    marginBottom: 14,
  },

  panelTitle: {
    margin: 0,
    fontSize: 16,
    fontWeight: 600,
    color: 'hsl(var(--foreground))',
  },

  panelHint: {
    marginTop: 4,
    color: 'hsl(var(--muted-foreground))',
    fontSize: 12,
  },

  countBadge: {
    minWidth: 24,
    height: 24,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '0 7px',
    borderRadius: 12,
    background: 'transparent',
    border: '1px solid hsl(var(--border))',
    color: 'hsl(var(--primary))',
    fontSize: 12,
    fontWeight: 600,
  },

  tableWrapper: {
    width: '100%',
    overflowX: 'auto',
  },

  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 13,
  },

  th: {
    padding: '10px 9px',
    textAlign: 'left',
    whiteSpace: 'nowrap',
    color: 'hsl(var(--muted-foreground))',
    fontWeight: 600,
    borderBottom: '1px solid hsl(var(--border))',
  },

  td: {
    padding: '11px 9px',
    verticalAlign: 'top',
    borderBottom: '1px solid hsl(var(--border))',
    color: 'hsl(var(--foreground))',
    wordBreak: 'break-word',
  },

  // 选中行不再使用浅色背景
  selectedRow: {
    background: 'transparent',
  },

  primaryText: {
    color: 'hsl(var(--foreground))',
    fontWeight: 500,
  },

  secondaryText: {
    marginTop: 4,
    color: 'hsl(var(--muted-foreground))',
    fontSize: 12,
  },

  emptyCell: {
    padding: 32,
    textAlign: 'center',
    color: 'hsl(var(--muted-foreground))',
    borderBottom: '1px solid hsl(var(--border))',
  },

  emptyDetail: {
    padding: 48,
    textAlign: 'center',
    border: '1px dashed hsl(var(--border))',
    borderRadius: 8,
    background: 'transparent',
  },

  emptyDetailTitle: {
    color: 'hsl(var(--foreground))',
    fontSize: 14,
    fontWeight: 500,
  },

  emptyDetailText: {
    marginTop: 8,
    color: 'hsl(var(--muted-foreground))',
    fontSize: 13,
  },

  metaGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 10,
  },

  // 信息块保留边框和布局，去掉背景
  infoItem: {
    padding: 10,
    border: '1px solid hsl(var(--border))',
    borderRadius: 6,
    background: 'transparent',
  },

  infoLabel: {
    marginBottom: 4,
    color: 'hsl(var(--muted-foreground))',
    fontSize: 12,
  },

  infoValue: {
    color: 'hsl(var(--foreground))',
    fontSize: 13,
    wordBreak: 'break-word',
  },

  detailSection: {
    marginTop: 20,
  },

  blockTitle: {
    margin: '0 0 10px',
    color: 'hsl(var(--foreground))',
    fontSize: 14,
    fontWeight: 600,
  },

  statusTag: {
    display: 'inline-block',
    padding: '3px 8px',
    borderRadius: 4,
    fontSize: 12,
    lineHeight: 1.4,
  },

  textarea: {
    width: '100%',
    minHeight: 90,
    padding: 10,
    boxSizing: 'border-box',
    resize: 'vertical',
    border: '1px solid hsl(var(--border))',
    borderRadius: 6,
    outline: 'none',
    background: 'transparent',
    color: 'hsl(var(--foreground))',
    fontSize: 14,
  },

  actions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 10,
    marginTop: 14,
  },

  approveButton: {
    minWidth: 84,
    border: '1px solid #1677ff',
    borderRadius: 6,
    padding: '9px 18px',
    background: 'transparent',
    color: '#1677ff',
    cursor: 'pointer',
  },

  rejectButton: {
    minWidth: 84,
    border: '1px solid #dc2626',
    borderRadius: 6,
    padding: '9px 18px',
    background: 'transparent',
    color: '#dc2626',
    cursor: 'pointer',
  },

  secondaryButton: {
    border: '1px solid hsl(var(--border))',
    borderRadius: 6,
    padding: '8px 14px',
    background: 'transparent',
    color: 'hsl(var(--foreground))',
    cursor: 'pointer',
  },

  linkButton: {
    border: 0,
    padding: 0,
    background: 'transparent',
    color: '#1677ff',
    cursor: 'pointer',
  },

  previewLink: {
    color: '#1677ff',
    textDecoration: 'none',
  },

  mutedText: {
    color: 'hsl(var(--muted-foreground))',
  },

  errorBox: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
    marginBottom: 16,
    padding: '10px 12px',
    border: '1px solid #fecaca',
    borderRadius: 6,
    background: 'transparent',
    color: '#b91c1c',
    fontSize: 13,
  },

  closeErrorButton: {
    border: 0,
    background: 'transparent',
    color: '#b91c1c',
    cursor: 'pointer',
  },
};
