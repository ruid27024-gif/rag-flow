import React, { useRef, useState } from 'react';

declare global {
  interface Window {
    DocsAPI?: any;
  }
}

const OnlyOfficeTestPage: React.FC = () => {
  const editorRef = useRef<any>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const host = window.location.hostname;

  // 浏览器访问 OnlyOffice（必须用绝对地址）
  const onlyOfficeBaseUrl = `http://${host}:8080`;

  // 后端 API 相对路径（由代理转发）
  const apiBaseUrl = '/v1/api';

  const loadOnlyOfficeScript = (): Promise<void> => {
    return new Promise((resolve, reject) => {
      if (window.DocsAPI) {
        resolve();
        return;
      }

      const scriptUrl = `${onlyOfficeBaseUrl}/web-apps/apps/api/documents/api.js`;
      const existingScript = document.querySelector(
        `script[src="${scriptUrl}"]`,
      );

      if (existingScript) {
        existingScript.addEventListener('load', () => resolve());
        existingScript.addEventListener('error', () =>
          reject(new Error('OnlyOffice API 脚本加载失败')),
        );
        setTimeout(() => {
          if (window.DocsAPI) {
            resolve();
          }
        }, 300);
        return;
      }

      const script = document.createElement('script');
      script.src = scriptUrl;
      script.onload = () => {
        if (window.DocsAPI) {
          resolve();
        } else {
          reject(new Error('OnlyOffice DocsAPI 不存在'));
        }
      };
      script.onerror = () => {
        reject(new Error(`无法加载 OnlyOffice 脚本：${script.src}`));
      };
      document.body.appendChild(script);
    });
  };

  const destroyEditor = () => {
    if (
      editorRef.current &&
      typeof editorRef.current.destroyEditor === 'function'
    ) {
      try {
        editorRef.current.destroyEditor();
      } catch (e) {
        console.warn('销毁 OnlyOffice 编辑器失败', e);
      }
    }
    editorRef.current = null;
  };

  const openEditor = async () => {
    try {
      setLoading(true);
      setMessage('正在加载 OnlyOffice...');

      await loadOnlyOfficeScript();

      setMessage('正在获取编辑器配置...');

      const response = await fetch(
        `${apiBaseUrl}/onlyoffice/editor-config/test`,
        {
          method: 'GET',
          credentials: 'include',
        },
      );

      const result = await response.json();

      console.log('OnlyOffice config result:', result);

      if (!response.ok) {
        throw new Error(result?.message || '获取 OnlyOffice 配置失败');
      }

      const config = result.data;

      if (!config) {
        throw new Error('后端没有返回 OnlyOffice config');
      }

      destroyEditor();

      setMessage('正在打开编辑器...');

      editorRef.current = new window.DocsAPI.DocEditor(
        'onlyoffice-editor',
        config,
      );

      setMessage('✅ 编辑器已打开');
    } catch (error: any) {
      console.error(error);
      setMessage(`❌ ${error?.message || '打开 OnlyOffice 失败'}`);
    } finally {
      setLoading(false);
    }
  };

  const downloadDocx = () => {
    window.open(`${apiBaseUrl}/onlyoffice/download/test`, '_blank');
  };

  return (
    // 整个页面占满视口，无内边距
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        width: '100vw',
        margin: 0,
        padding: 0,
        overflow: 'hidden',
      }}
    >
      {/* 极简顶部栏 - 只有一行，高度自适应 */}
      <div
        style={{
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '8px 16px',
          background: '#f5f5f5',
          borderBottom: '1px solid #ddd',
          flexWrap: 'wrap',
        }}
      >
        <span style={{ fontWeight: 'bold', fontSize: 16, marginRight: 8 }}>
          📄 OnlyOffice
        </span>
        <button
          onClick={openEditor}
          disabled={loading}
          style={{
            padding: '6px 16px',
            cursor: loading ? 'not-allowed' : 'pointer',
            background: '#1890ff',
            color: '#fff',
            border: 'none',
            borderRadius: 4,
            fontSize: 14,
          }}
        >
          {loading ? '处理中...' : '打开 test.docx'}
        </button>
        <button
          onClick={downloadDocx}
          style={{
            padding: '6px 16px',
            cursor: 'pointer',
            background: '#52c41a',
            color: '#fff',
            border: 'none',
            borderRadius: 4,
            fontSize: 14,
          }}
        >
          📥 下载
        </button>
        {message && (
          <span
            style={{
              marginLeft: 'auto',
              fontSize: 14,
              color: message.includes('✅') ? '#52c41a' : '#ff4d4f',
              background: '#fff',
              padding: '2px 12px',
              borderRadius: 12,
              border: '1px solid #ddd',
            }}
          >
            {message}
          </span>
        )}
      </div>

      {/* 编辑器占满剩余所有空间 */}
      <div
        id="onlyoffice-editor"
        style={{
          flex: 1,
          border: 'none',
          minHeight: 0,
          width: '100%',
          background: '#fff',
        }}
      />
    </div>
  );
};

export default OnlyOfficeTestPage;
