import {
  ArrowLeftOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  TeamOutlined,
  UserSwitchOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { Button, ConfigProvider, Menu, theme } from 'antd';
import React, { useState } from 'react';
import { history } from 'umi';

import PersonRolePage from '@/pages/person-role';
import RolePage from '@/pages/role';

type ActiveKey = 'role' | 'person-role';

const RolePersonManagePage: React.FC = () => {
  const { token } = theme.useToken();

  const [activeKey, setActiveKey] = useState<ActiveKey>('role');
  const [collapsed, setCollapsed] = useState(false);

  const siderWidth = collapsed ? 64 : 220;

  const menuItems: MenuProps['items'] = [
    {
      key: 'role',
      icon: <TeamOutlined />,
      label: '角色人员',
    },

    {
      key: 'person-role',
      icon: <UserSwitchOutlined />,
      label: '人员角色',
    },
  ];

  const renderContent = () => {
    if (activeKey === 'person-role') {
      return <PersonRolePage />;
    }

    if (activeKey === 'role') {
      return <RolePage />;
    }

    return null;
  };

  return (
    <div
      style={{
        display: 'flex',
        height: 'calc(100vh - 64px)',
        background: token.colorBgContainer,
        overflow: 'hidden',
      }}
    >
      <aside
        style={{
          width: siderWidth,
          minWidth: siderWidth,
          height: '100%',
          background: token.colorBgContainer,
          transition: 'width 0.2s ease, min-width 0.2s ease',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div
          style={{
            height: 48,
            flexShrink: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'space-between',
            padding: collapsed ? 0 : '0 12px 0 28px',
            boxSizing: 'border-box',
          }}
        >
          {!collapsed && (
            <span
              style={{
                fontWeight: 600,
                color: token.colorText,
                whiteSpace: 'nowrap',
              }}
            >
              角色人员管理
            </span>
          )}

          <Button
            type="text"
            size="small"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed((value) => !value)}
            style={{
              width: 40,
              height: 40,
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 0,
            }}
          />
        </div>

        <ConfigProvider
          theme={{
            components: {
              Menu: {
                itemSelectedBg: 'rgba(0, 168, 112, 0.12)',
                itemSelectedColor: '#00A870',
                itemHoverColor: '#00A870',
              },
            },
          }}
        >
          <Menu
            mode="inline"
            inlineCollapsed={collapsed}
            selectedKeys={[activeKey]}
            items={menuItems}
            onClick={({ key }) => {
              setActiveKey(key as ActiveKey);
            }}
            style={{
              borderInlineEnd: 'none',
              background: token.colorBgContainer,
              flex: 1,
            }}
          />
        </ConfigProvider>

        <div
          style={{
            flexShrink: 0,
            padding: collapsed ? '12px' : '12px 16px',
            borderTop: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <Button
            block={!collapsed}
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={() => history.push('/admin-files')}
            style={{
              height: 36,
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: collapsed ? 'center' : 'flex-start',
              paddingInline: collapsed ? 0 : 12,
              color: token.colorTextSecondary,
            }}
          >
            {collapsed ? null : '返回系统设置'}
          </Button>
        </div>
      </aside>

      <div
        style={{
          flex: 1,
          minWidth: 0,
          height: '100%',
          overflow: 'hidden',
          padding: 0,
          boxSizing: 'border-box',
          background: token.colorBgContainer,
        }}
      >
        {renderContent()}
      </div>
    </div>
  );
};

export default RolePersonManagePage;
