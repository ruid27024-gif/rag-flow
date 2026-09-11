import React, { useCallback, useEffect, useState } from 'react';

import {
  Button,
  Descriptions,
  Drawer,
  Input,
  Modal,
  Space,
  Table,
  Tag,
  message,
} from 'antd';

import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';

import { getAuthorization } from '@/utils/authorization-util';

const { TextArea } = Input;

/**
 * 申请人
 */
interface Applicant {
  user_id?: string;
  user_name?: string;
}

/**
 * 部门
 */
interface Department {
  dept_code?: string;
  dept_name?: string;
}

/**
 * 公共知识库
 */
interface PublicKb {
  kb_id?: string;
  kb_name?: string;
}

/**
 * OA 中 data 字段内容
 */
interface CreateKbData {
  kb_name?: string;
  applicant_dept?: Department;
  public_kb?: PublicKb | null;
  [key: string]: any;
}

/**
 * 后端返回的 OA 待办记录。
 *
 * 当前后端返回的是扁平结构，例如：
 *
 * {
 *   task_id: 1,
 *   kb_name: "测试",
 *   applicant_user_name: "邬宪娜",
 *   applicant_dept: {
 *     dept_code: "100146",
 *     dept_name: "工艺研究一室"
 *   },
 *   level: 1
 * }
 */
interface OaApplyItem {
  task_id: number | string;

  oa_request_id: string;
  business_id: string;
  business_type: string;

  kb_name?: string;
  reason?: string;

  applicant_user_id?: string;
  applicant_user_name?: string;

  approver_user_id?: string;
  approver_user_name?: string;

  applicant_dept?: Department;

  level?: number;
  task_level?: number;

  task_status?: string;
  application_status?: string;

  task_created_time?: number;
  task_updated_time?: number;

  created_time?: number;
  updated_time?: number;

  public_kb?: PublicKb | null;

  /**
   * 兼容嵌套格式
   */
  applicant?: Applicant;
  approver?: Applicant;
  data?: CreateKbData;
  business_data?: CreateKbData;

  [key: string]: any;
}

/**
 * 待办分页数据
 */
interface OaTodoData {
  items?: OaApplyItem[];
  total?: number;
  page?: number;
  page_size?: number;
  has_more?: boolean;
}

/**
 * 接口返回格式
 */
interface ApiResponse<T = any> {
  code: number | string;
  message?: string;
  data?: T;
}

type ApproveAction = 'approve' | 'reject';

const OaApplyList: React.FC = () => {
  const [loading, setLoading] = useState(false);

  const [data, setData] = useState<OaApplyItem[]>([]);

  const [total, setTotal] = useState(0);

  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
  });

  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const [detailOpen, setDetailOpen] = useState(false);

  const [currentRecord, setCurrentRecord] = useState<OaApplyItem | null>(null);

  const [actionModalOpen, setActionModalOpen] = useState(false);

  const [actionType, setActionType] = useState<ApproveAction | null>(null);

  const [actionRecord, setActionRecord] = useState<OaApplyItem | null>(null);

  const [comment, setComment] = useState('');

  /**
   * 判断接口是否成功。
   *
   * 兼容：
   * code = 0
   * code = "0"
   * code = 200
   * code = "200"
   */
  const isSuccess = useCallback((code: number | string | undefined) => {
    return String(code) === '0' || String(code) === '200';
  }, []);

  /**
   * 格式化时间。
   *
   * 后端当前返回的是秒级时间戳，例如：
   *
   * 1789030120
   *
   * 如果后端返回毫秒级，也兼容。
   */
  const formatTime = useCallback((timestamp?: number | string | null) => {
    if (timestamp === undefined || timestamp === null || timestamp === '') {
      return '-';
    }

    const numericTimestamp = Number(timestamp);

    if (Number.isNaN(numericTimestamp) || numericTimestamp <= 0) {
      return '-';
    }

    const milliseconds =
      numericTimestamp < 10000000000
        ? numericTimestamp * 1000
        : numericTimestamp;

    return new Date(milliseconds).toLocaleString();
  }, []);

  /**
   * 将后端返回的扁平结构统一转换成前端使用的结构。
   *
   * 后端当前返回：
   *
   * {
   *   kb_name: "测试",
   *   applicant_user_name: "邬宪娜",
   *   applicant_dept: {...},
   *   level: 1
   * }
   *
   * 前端统一后可同时使用：
   *
   * record.kb_name
   * record.applicant_user_name
   * record.task_level
   * record.data
   */
  const normalizeItem = useCallback((item: OaApplyItem): OaApplyItem => {
    const rawData = item.data || item.business_data || {};

    const applicantDept = item.applicant_dept || rawData.applicant_dept || {};

    const publicKb = item.public_kb || rawData.public_kb || null;

    const applicantUserId = item.applicant_user_id || item.applicant?.user_id;

    const applicantUserName =
      item.applicant_user_name || item.applicant?.user_name;

    const approverUserId = item.approver_user_id || item.approver?.user_id;

    const approverUserName =
      item.approver_user_name || item.approver?.user_name;

    const kbName = item.kb_name || rawData.kb_name || rawData.name || '';

    const taskLevel = item.task_level || item.level || 1;

    const taskStatus = item.task_status || item.application_status || 'pending';

    return {
      ...item,

      kb_name: kbName,

      applicant_user_id: applicantUserId,
      applicant_user_name: applicantUserName,

      approver_user_id: approverUserId,
      approver_user_name: approverUserName,

      applicant_dept: applicantDept,

      public_kb: publicKb,

      task_level: taskLevel,
      task_status: taskStatus,

      data: {
        ...rawData,
        kb_name: kbName,
        applicant_dept: applicantDept,
        public_kb: publicKb,
      },

      business_data: {
        ...rawData,
        kb_name: kbName,
        applicant_dept: applicantDept,
        public_kb: publicKb,
      },

      applicant: {
        user_id: applicantUserId,
        user_name: applicantUserName,
      },

      approver: {
        user_id: approverUserId,
        user_name: approverUserName,
      },
    };
  }, []);

  /**
   * 获取知识库名称。
   */
  const getKbName = useCallback((record: OaApplyItem) => {
    return (
      record.kb_name ||
      record.data?.kb_name ||
      record.business_data?.kb_name ||
      '-'
    );
  }, []);

  /**
   * 获取申请人姓名。
   */
  const getApplicantName = useCallback((record: OaApplyItem) => {
    return (
      record.applicant_user_name ||
      record.applicant?.user_name ||
      record.applicant_user_id ||
      record.applicant?.user_id ||
      '-'
    );
  }, []);

  /**
   * 获取审批人姓名。
   */
  const getApproverName = useCallback((record: OaApplyItem) => {
    return (
      record.approver_user_name ||
      record.approver?.user_name ||
      record.approver_user_id ||
      record.approver?.user_id ||
      '-'
    );
  }, []);

  /**
   * 获取部门。
   */
  const getDepartment = useCallback((record: OaApplyItem): Department => {
    return (
      record.applicant_dept ||
      record.data?.applicant_dept ||
      record.business_data?.applicant_dept ||
      {}
    );
  }, []);

  /**
   * 获取审批级别。
   */
  const getTaskLevel = useCallback((record: OaApplyItem) => {
    return record.task_level || record.level || 1;
  }, []);

  /**
   * 获取待办列表。
   */
  const fetchList = useCallback(
    async (page: number, pageSize: number) => {
      try {
        setLoading(true);

        const params = new URLSearchParams({
          page: String(page),
          page_size: String(pageSize),
        });

        const response = await fetch(
          `/v1/kb/oa/approval/tasks/todo?${params.toString()}`,
          {
            method: 'GET',
            headers: {
              Authorization: getAuthorization() || '',
              'Content-Type': 'application/json',
            },
            credentials: 'include',
          },
        );

        const result: ApiResponse<OaTodoData | OaApplyItem[]> =
          await response.json();

        console.log('[OA TODO] response:', result);

        if (!response.ok) {
          message.error(result.message || `请求失败：${response.status}`);
          return;
        }

        if (!isSuccess(result.code)) {
          message.error(result.message || '获取待办任务失败');
          return;
        }

        let list: OaApplyItem[] = [];
        let totalCount = 0;

        /**
         * 兼容：
         *
         * data: []
         *
         * 或：
         *
         * data: {
         *   items: [],
         *   total: 1
         * }
         */
        if (Array.isArray(result.data)) {
          list = result.data;
          totalCount = result.data.length;
        } else if (result.data && typeof result.data === 'object') {
          list = result.data.items || [];
          totalCount = result.data.total ?? list.length;
        }

        const normalizedList = list.map(normalizeItem);

        console.log('[OA TODO] normalized list:', normalizedList);

        setData(normalizedList);
        setTotal(totalCount);

        setPagination({
          current: page,
          pageSize,
        });
      } catch (error) {
        console.error('[OA TODO] 获取待办任务失败:', error);

        message.error('获取待办任务失败，请稍后重试');
      } finally {
        setLoading(false);
      }
    },
    [isSuccess, normalizeItem],
  );

  /**
   * 页面首次加载。
   */
  useEffect(() => {
    fetchList(1, 20);
  }, [fetchList]);

  /**
   * 打开申请详情。
   */
  const handleViewDetail = (record: OaApplyItem) => {
    const normalizedRecord = normalizeItem(record);

    setCurrentRecord(normalizedRecord);
    setDetailOpen(true);
  };

  /**
   * 打开审批弹窗。
   */
  const handleOpenAction = (record: OaApplyItem, action: ApproveAction) => {
    const normalizedRecord = normalizeItem(record);

    setActionRecord(normalizedRecord);
    setActionType(action);
    setComment('');
    setActionModalOpen(true);
  };

  /**
   * 提交审批。
   */
  const handleSubmitAction = async () => {
    if (!actionRecord || !actionType) {
      return;
    }

    const oaRequestId = actionRecord.oa_request_id;

    if (!oaRequestId) {
      message.error('OA 申请单 ID 不存在');
      return;
    }

    if (actionType === 'reject' && !comment.trim()) {
      message.warning('请输入拒绝原因');
      return;
    }

    const loadingKey = `${actionType}-${oaRequestId}`;

    try {
      setActionLoading(loadingKey);

      const response = await fetch(
        `/v1/kb/oa/approval/${encodeURIComponent(oaRequestId)}/${actionType}`,
        {
          method: 'POST',
          headers: {
            Authorization: getAuthorization() || '',
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({
            comment: comment.trim(),
          }),
        },
      );

      const result: ApiResponse = await response.json();

      console.log('[OA APPROVAL] response:', result);

      if (!response.ok) {
        message.error(result.message || `请求失败：${response.status}`);
        return;
      }

      if (!isSuccess(result.code)) {
        message.error(
          result.message ||
            (actionType === 'approve' ? '审批通过失败' : '拒绝申请失败'),
        );
        return;
      }

      message.success(actionType === 'approve' ? '审批通过' : '已拒绝申请');

      setActionModalOpen(false);
      setActionRecord(null);
      setActionType(null);
      setComment('');

      await fetchList(pagination.current, pagination.pageSize);
    } catch (error) {
      console.error('[OA APPROVAL] 审批操作失败:', error);

      message.error('审批请求失败，请稍后重试');
    } finally {
      setActionLoading(null);
    }
  };

  /**
   * 表格分页变化。
   */
  const handleTableChange = (tablePagination: TablePaginationConfig) => {
    const current = tablePagination.current || 1;

    const pageSize = tablePagination.pageSize || 20;

    fetchList(current, pageSize);
  };

  /**
   * 表格列。
   */
  const columns: ColumnsType<OaApplyItem> = [
    {
      title: '申请单号',
      dataIndex: 'business_id',
      key: 'business_id',
      width: 240,
      ellipsis: true,
    },

    {
      title: 'OA 审批单号',
      dataIndex: 'oa_request_id',
      key: 'oa_request_id',
      width: 220,
      ellipsis: true,
    },

    {
      title: '申请类型',
      dataIndex: 'business_type',
      key: 'business_type',
      width: 140,
      render: (value: string) => {
        if (value === 'kb_create') {
          return <Tag color="blue">创建知识库</Tag>;
        }

        return <Tag>{value || '-'}</Tag>;
      },
    },

    {
      title: '知识库名称',
      key: 'kb_name',
      width: 180,
      ellipsis: true,
      render: (_, record) => {
        return getKbName(record);
      },
    },

    {
      title: '申请人',
      key: 'applicant',
      width: 140,
      ellipsis: true,
      render: (_, record) => {
        return getApplicantName(record);
      },
    },

    {
      title: '申请部门',
      key: 'applicant_dept',
      width: 180,
      ellipsis: true,
      render: (_, record) => {
        const department = getDepartment(record);

        return (
          <span>{department.dept_name || department.dept_code || '-'}</span>
        );
      },
    },

    {
      title: '审批人',
      key: 'approver',
      width: 140,
      ellipsis: true,
      render: (_, record) => {
        return getApproverName(record);
      },
    },

    {
      title: '申请原因',
      dataIndex: 'reason',
      key: 'reason',
      width: 220,
      ellipsis: true,
      render: (value: string) => {
        return value || '-';
      },
    },

    {
      title: '审批级别',
      key: 'task_level',
      width: 100,
      render: (_, record) => {
        return `第 ${getTaskLevel(record)} 级`;
      },
    },

    {
      title: '提交时间',
      key: 'created_time',
      width: 180,
      render: (_, record) => {
        return formatTime(record.task_created_time || record.created_time);
      },
    },

    {
      title: '状态',
      key: 'task_status',
      width: 100,
      render: (_, record) => {
        const status =
          record.task_status || record.application_status || 'pending';

        if (status === 'pending') {
          return <Tag color="orange">待审批</Tag>;
        }

        if (status === 'approved') {
          return <Tag color="green">已通过</Tag>;
        }

        if (status === 'rejected') {
          return <Tag color="red">已拒绝</Tag>;
        }

        return <Tag>{status}</Tag>;
      },
    },

    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 240,
      render: (_, record) => {
        const approveLoading =
          actionLoading === `approve-${record.oa_request_id}`;

        const rejectLoading =
          actionLoading === `reject-${record.oa_request_id}`;

        const isPending =
          (record.task_status || record.application_status || 'pending') ===
          'pending';

        return (
          <Space>
            <Button size="small" onClick={() => handleViewDetail(record)}>
              查看
            </Button>

            <Button
              size="small"
              type="primary"
              loading={approveLoading}
              disabled={!!actionLoading || !isPending}
              onClick={() => handleOpenAction(record, 'approve')}
            >
              同意
            </Button>

            <Button
              size="small"
              danger
              loading={rejectLoading}
              disabled={!!actionLoading || !isPending}
              onClick={() => handleOpenAction(record, 'reject')}
            >
              拒绝
            </Button>
          </Space>
        );
      },
    },
  ];

  /**
   * 渲染公共知识库。
   */
  const renderPublicKb = (publicKb?: PublicKb | null) => {
    if (!publicKb || !publicKb.kb_id) {
      return '-';
    }

    return `${publicKb.kb_name || '-'}` + `（${publicKb.kb_id}）`;
  };

  /**
   * 当前详情数据。
   */
  const detailRecord = currentRecord ? normalizeItem(currentRecord) : null;

  const detailData: CreateKbData = detailRecord?.data || {};

  const detailDepartment = detailRecord ? getDepartment(detailRecord) : {};

  return (
    <div
      style={{
        padding: 24,
        // background: '#fff',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}
      >
        <div>
          <h2
            style={{
              margin: 0,
              fontSize: 20,
            }}
          >
            OA 待办审批
          </h2>

          <div
            style={{
              marginTop: 8,
              color: '#999',
            }}
          >
            当前登录用户的知识库创建审批任务
          </div>
        </div>

        <Button
          onClick={() => fetchList(pagination.current, pagination.pageSize)}
          loading={loading}
        >
          刷新
        </Button>
      </div>

      <Table<OaApplyItem>
        rowKey={(record) =>
          String(record.task_id || record.oa_request_id || record.business_id)
        }
        loading={loading}
        columns={columns}
        dataSource={data}
        scroll={{ x: 1900 }}
        pagination={{
          current: pagination.current,
          pageSize: pagination.pageSize,
          total,
          showSizeChanger: true,
          showTotal: (value) => `共 ${value} 条待办`,
          pageSizeOptions: ['10', '20', '50', '100'],
        }}
        onChange={handleTableChange}
      />

      {/* 申请详情 */}
      <Drawer
        title="建库申请详情"
        width={640}
        open={detailOpen}
        onClose={() => {
          setDetailOpen(false);
          setCurrentRecord(null);
        }}
      >
        {detailRecord && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="OA 申请单号">
              {detailRecord.oa_request_id || '-'}
            </Descriptions.Item>

            <Descriptions.Item label="知识库侧申请单号">
              {detailRecord.business_id || '-'}
            </Descriptions.Item>

            <Descriptions.Item label="业务类型">
              {detailRecord.business_type || '-'}
            </Descriptions.Item>

            <Descriptions.Item label="知识库名称">
              {getKbName(detailRecord)}
            </Descriptions.Item>

            <Descriptions.Item label="申请人">
              {getApplicantName(detailRecord)}
              {detailRecord.applicant_user_id
                ? `（${detailRecord.applicant_user_id}）`
                : ''}
            </Descriptions.Item>

            <Descriptions.Item label="申请人部门">
              {detailDepartment.dept_name || detailDepartment.dept_code || '-'}
              {detailDepartment.dept_code
                ? `（${detailDepartment.dept_code}）`
                : ''}
            </Descriptions.Item>

            <Descriptions.Item label="审批人">
              {getApproverName(detailRecord)}
              {detailRecord.approver_user_id
                ? `（${detailRecord.approver_user_id}）`
                : ''}
            </Descriptions.Item>

            <Descriptions.Item label="审批级别">
              第 {getTaskLevel(detailRecord)} 级
            </Descriptions.Item>

            <Descriptions.Item label="关联公共知识库">
              {renderPublicKb(detailData.public_kb)}
            </Descriptions.Item>

            <Descriptions.Item label="申请原因">
              {detailRecord.reason || '-'}
            </Descriptions.Item>

            <Descriptions.Item label="任务状态">
              {detailRecord.task_status || '-'}
            </Descriptions.Item>

            <Descriptions.Item label="申请状态">
              {detailRecord.application_status ||
                detailRecord.task_status ||
                '-'}
            </Descriptions.Item>

            <Descriptions.Item label="提交时间">
              {formatTime(
                detailRecord.task_created_time || detailRecord.created_time,
              )}
            </Descriptions.Item>

            <Descriptions.Item label="更新时间">
              {formatTime(
                detailRecord.task_updated_time || detailRecord.updated_time,
              )}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>

      {/* 同意/拒绝弹窗 */}
      <Modal
        title={actionType === 'approve' ? '同意建库申请' : '拒绝建库申请'}
        open={actionModalOpen}
        confirmLoading={!!actionLoading}
        okText={actionType === 'approve' ? '确认同意' : '确认拒绝'}
        cancelText="取消"
        okButtonProps={{
          danger: actionType === 'reject',
        }}
        onCancel={() => {
          if (actionLoading) {
            return;
          }

          setActionModalOpen(false);
          setActionRecord(null);
          setActionType(null);
          setComment('');
        }}
        onOk={handleSubmitAction}
      >
        <div
          style={{
            marginBottom: 12,
          }}
        >
          <div>
            <strong>知识库名称：</strong>

            {actionRecord ? getKbName(actionRecord) : '-'}
          </div>

          <div
            style={{
              marginTop: 8,
            }}
          >
            <strong>申请人：</strong>

            {actionRecord ? getApplicantName(actionRecord) : '-'}
          </div>

          <div
            style={{
              marginTop: 8,
            }}
          >
            <strong>申请部门：</strong>

            {actionRecord
              ? getDepartment(actionRecord).dept_name ||
                getDepartment(actionRecord).dept_code ||
                '-'
              : '-'}
          </div>
        </div>

        <TextArea
          rows={4}
          value={comment}
          placeholder={
            actionType === 'approve'
              ? '请输入审批意见，可选'
              : '请输入拒绝原因，必填'
          }
          onChange={(event) => setComment(event.target.value)}
        />
      </Modal>
    </div>
  );
};

export default OaApplyList;
