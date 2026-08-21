import { getAuthorization } from '@/utils/authorization-util';
import { Button, Modal, Space, Table, Tag, message } from 'antd';
import React, { useEffect, useState } from 'react';
import './index.less';

interface OaApplyItem {
  id: number;
  business_id: string;
  business_type: string;
  applicant_user_id: string;
  applicant_name: string;
  approver_user_id: string;
  approver_name: string;
  role_id: number;
  role_name: string;
  dept_codes: string[];
  reason: string;
  status: number; // 0-待审批,1-已通过,2-已拒绝
  created_time: number;
  updated_time: number | null;
  payload: string;
}

const OaApplyList: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<OaApplyItem[]>([]);
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const authHeaders = {
    Authorization: getAuthorization() || '',
    'Content-Type': 'application/json',
  };

  const fetchList = async () => {
    try {
      setLoading(true);
      const res = await fetch(
        '/v1/role/oa/list?business_type=role_permission',
        {
          method: 'GET',
          headers: authHeaders,
          credentials: 'include',
        },
      );
      const result = await res.json();
      if (result.code === 0 || result.code === 200) {
        setData(result.data || []);
      } else {
        message.error(result.message || '获取申请列表失败');
      }
    } catch (e) {
      console.error(e);
      message.error('请求失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchList();
  }, []);

  const handleApprove = (record: OaApplyItem, action: 'agree' | 'reject') => {
    Modal.confirm({
      title: action === 'agree' ? '确认同意' : '确认拒绝',
      content: `确定要${action === 'agree' ? '同意' : '拒绝'}用户【${record.applicant_name}】的【${record.role_name}】权限申请吗？`,
      okText: action === 'agree' ? '同意' : '拒绝',
      cancelText: '取消',
      onOk: async () => {
        setActionLoading(record.id);
        try {
          const res = await fetch('/v1/role/oa/approve', {
            method: 'POST',
            headers: authHeaders,
            credentials: 'include',
            body: JSON.stringify({
              business_id: record.business_id,
              action: action,
            }),
          });
          const result = await res.json();
          if (
            result.code === 0 ||
            result.code === 200 ||
            result.data === true
          ) {
            message.success(`已${action === 'agree' ? '同意' : '拒绝'}该申请`);
            fetchList(); // 刷新列表
          } else {
            message.error(result.message || '操作失败');
          }
        } catch (e) {
          console.error(e);
          message.error('请求失败');
        } finally {
          setActionLoading(null);
        }
      },
    });
  };

  const columns = [
    {
      title: '申请人',
      dataIndex: 'applicant_name',
      key: 'applicant_name',
    },
    {
      title: '角色名称',
      dataIndex: 'role_name',
      key: 'role_name',
    },
    {
      title: '部门',
      dataIndex: 'dept_codes',
      key: 'dept_codes',
      render: (val: string[]) => {
        return val?.join('、') || '-';
      },
    },
    {
      title: '申请理由',
      dataIndex: 'reason',
      key: 'reason',
      ellipsis: true,
    },
    {
      title: '申请时间',
      dataIndex: 'created_time',
      key: 'created_time',
      render: (ts: number) => {
        if (!ts) return '-';
        return new Date(ts * 1000).toLocaleString();
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: number) => {
        if (status === 0) return <Tag color="orange">待审批</Tag>;
        if (status === 1) return <Tag color="green">已通过</Tag>;
        if (status === 2) return <Tag color="red">已拒绝</Tag>;
        return <Tag>未知</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: OaApplyItem) => {
        if (record.status !== 0) return <span>已处理</span>;
        const isActionLoading = actionLoading === record.id;
        return (
          <Space>
            <Button
              type="primary"
              size="small"
              style={{ background: '#00A870', borderColor: '#00A870' }}
              loading={isActionLoading}
              onClick={() => handleApprove(record, 'agree')}
            >
              同意
            </Button>
            <Button
              danger
              size="small"
              loading={isActionLoading}
              onClick={() => handleApprove(record, 'reject')}
            >
              拒绝
            </Button>
          </Space>
        );
      },
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div
        style={{
          fontSize: 20,
          fontWeight: 600,
          marginBottom: 16,
          display: 'flex',
          alignItems: 'center',
        }}
      >
        <span
          style={{
            width: 4,
            height: 20,
            background: '#00A870',
            display: 'inline-block',
            marginRight: 8,
            borderRadius: 2,
          }}
        />
        OA审批管理
      </div>
      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={data}
        pagination={{ pageSize: 10 }}
      />
    </div>
  );
};

export default OaApplyList;
