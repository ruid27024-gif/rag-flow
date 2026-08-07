import { getAuthorization } from '@/utils/authorization-util';
import {
  CloseOutlined,
  CopyOutlined,
  DownOutlined,
  DownloadOutlined,
  FileTextOutlined,
  FolderOpenOutlined,
  FolderOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { Button, Empty, Spin, Tooltip, message, theme } from 'antd';
import React, { useEffect, useMemo, useState } from 'react';

import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import {
  oneDark,
  oneLight,
} from 'react-syntax-highlighter/dist/esm/styles/prism';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import DOMPurify from 'dompurify';
import mammoth from 'mammoth';
import './index.less';

interface FileTreeNode {
  name: string;
  path: string;
  type: 'directory' | 'file';
  children?: FileTreeNode[];

  /**
   * 前端展示用名称
   * name 仍然保留后端原始 ID 或文件名
   */
  displayName?: string;
}

interface FileInfo {
  name?: string;
  path?: string;
  suffix?: string;
  content?: string;
}

interface FileTreePreviewProps {
  open: boolean;
  onClose: () => void;
}
type PreviewType =
  | 'text'
  | 'markdown'
  | 'pdf'
  | 'image'
  | 'docx'
  | 'unsupported';

const FileTreePreview: React.FC<FileTreePreviewProps> = ({ open, onClose }) => {
  const { token } = theme.useToken();

  const [tree, setTree] = useState<FileTreeNode[]>([]);
  const [loading, setLoading] = useState(false);

  const [expandedPaths, setExpandedPaths] = useState<string[]>([]);
  const [selectedFile, setSelectedFile] = useState<FileTreeNode | null>(null);

  const [fileInfo, setFileInfo] = useState<FileInfo | null>(null);
  const [fileContent, setFileContent] = useState('');
  const [fileLoading, setFileLoading] = useState(false);
  const [docxHtml, setDocxHtml] = useState('');

  /**
   * pdf / image 这种二进制预览地址
   */
  const [previewUrl, setPreviewUrl] = useState('');
  const [previewType, setPreviewType] = useState<PreviewType>('text');

  const isDark = token.colorBgContainer === '#141414';
  const codeTheme = isDark ? oneDark : oneLight;

  const authHeaders = useMemo(
    () => ({
      Authorization: getAuthorization() || '',
      'Content-Type': 'application/json',
    }),
    [],
  );

  const getFileSuffix = (nameOrPath?: string) => {
    if (!nameOrPath) {
      return '';
    }

    const index = nameOrPath.lastIndexOf('.');

    if (index === -1) {
      return '';
    }

    return nameOrPath.slice(index).toLowerCase();
  };

  const getLanguageBySuffix = (nameOrSuffix?: string) => {
    const ext = nameOrSuffix?.startsWith('.')
      ? nameOrSuffix.toLowerCase()
      : getFileSuffix(nameOrSuffix);

    const map: Record<string, string> = {
      '.py': 'python',
      '.js': 'javascript',
      '.jsx': 'jsx',
      '.ts': 'typescript',
      '.tsx': 'tsx',
      '.json': 'json',
      '.md': 'markdown',
      '.html': 'html',
      '.css': 'css',
      '.less': 'less',
      '.yml': 'yaml',
      '.yaml': 'yaml',
      '.xml': 'xml',
      '.sh': 'bash',
      '.sql': 'sql',
      '.txt': 'text',
      '.log': 'text',
      '.csv': 'csv',
    };

    return map[ext || ''] || 'text';
  };

  const isTextPreviewFile = (file?: FileTreeNode | null) => {
    const suffix = getFileSuffix(file?.name || file?.path);

    return [
      '.txt',
      '.json',
      '.csv',
      '.log',
      '.py',
      '.js',
      '.ts',
      '.tsx',
      '.jsx',
      '.html',
      '.css',
      '.less',
      '.yaml',
      '.yml',
      '.xml',
      '.sh',
      '.sql',
    ].includes(suffix);
  };

  const isMarkdownFile = (file?: FileTreeNode | null) => {
    return getFileSuffix(file?.name || file?.path) === '.md';
  };

  const isPdfFile = (file?: FileTreeNode | null) => {
    return getFileSuffix(file?.name || file?.path) === '.pdf';
  };

  const isImageFile = (file?: FileTreeNode | null) => {
    return ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'].includes(
      getFileSuffix(file?.name || file?.path),
    );
  };

  const isDocxFile = (file?: FileTreeNode | null) => {
    return getFileSuffix(file?.name || file?.path) === '.docx';
  };

  const isDocFile = (file?: FileTreeNode | null) => {
    return getFileSuffix(file?.name || file?.path) === '.doc';
  };

  const isOfficeFile = (file?: FileTreeNode | null) => {
    return ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'].includes(
      getFileSuffix(file?.name || file?.path),
    );
  };

  const clearPreviewUrl = () => {
    setPreviewUrl((oldUrl) => {
      if (oldUrl) {
        URL.revokeObjectURL(oldUrl);
      }

      return '';
    });
  };

  const findFirstFile = (nodes: FileTreeNode[]): FileTreeNode | null => {
    for (const node of nodes) {
      if (node.type === 'file') {
        return node;
      }

      if (node.children?.length) {
        const file = findFirstFile(node.children);

        if (file) {
          return file;
        }
      }
    }

    return null;
  };

  const collectKbIds = (nodes: FileTreeNode[]) => {
    return [
      ...new Set(
        nodes
          .filter((node) => node.type === 'directory')
          .map((node) => node.name)
          .filter(Boolean),
      ),
    ];
  };

  const collectUserIds = (nodes: FileTreeNode[]) => {
    const userIds: string[] = [];

    nodes.forEach((kbNode) => {
      if (kbNode.type !== 'directory') {
        return;
      }

      kbNode.children?.forEach((userNode) => {
        if (userNode.type === 'directory') {
          userIds.push(userNode.name);
        }
      });
    });

    return [...new Set(userIds.filter(Boolean))];
  };

  const applyDisplayNameToTree = (
    nodes: FileTreeNode[],
    kbNameMap: Record<string, string>,
    userNameMap: Record<string, string>,
    level = 0,
  ): FileTreeNode[] => {
    return nodes.map((node) => {
      let displayName = node.name;

      /**
       * 第一层：kb_id -> 知识库名称
       */
      if (level === 0 && node.type === 'directory') {
        displayName = kbNameMap[node.name] || node.name;
      }

      /**
       * 第二层：user_id -> 用户昵称
       */
      if (level === 1 && node.type === 'directory') {
        displayName = userNameMap[node.name] || node.name;
      }

      return {
        ...node,
        displayName,
        children: node.children?.length
          ? applyDisplayNameToTree(
              node.children,
              kbNameMap,
              userNameMap,
              level + 1,
            )
          : node.children,
      };
    });
  };
  const loadTreeNameMap = async (): Promise<{
    kb: Record<string, string>;
    user: Record<string, string>;
  }> => {
    const res = await fetch('/v1/file/tree/name_map', {
      method: 'POST',
      credentials: 'include',
      headers: authHeaders,
      body: JSON.stringify({}),
    });

    const result = await res.json();

    if (!res.ok || result.code !== 0) {
      throw new Error(result.message || '获取名称映射失败');
    }

    return {
      kb: result.data?.kb || {},
      user: result.data?.user || {},
    };
  };

  const loadTree = async () => {
    try {
      setLoading(true);

      const res = await fetch('/v1/file/tree1', {
        method: 'GET',
        credentials: 'include',
        headers: authHeaders,
      });

      const result = await res.json();

      if (!res.ok || result.code !== 0) {
        throw new Error(result.message || '获取目录失败');
      }

      const data: FileTreeNode[] = result.data || [];

      const kbIds = collectKbIds(data);
      const userIds = collectUserIds(data);

      let kbNameMap: Record<string, string> = {};
      let userNameMap: Record<string, string> = {};

      try {
        const nameMap = await loadTreeNameMap(kbIds, userIds);
        kbNameMap = nameMap.kb;
        userNameMap = nameMap.user;
      } catch (e: any) {
        message.warning(e.message || '获取名称映射失败，将展示 ID');
      }

      const displayTree = applyDisplayNameToTree(data, kbNameMap, userNameMap);

      setTree(displayTree);

      /**
       * 默认展开第一层目录
       */
      const firstLevelDirs = displayTree
        .filter((item: FileTreeNode) => item.type === 'directory')
        .map((item: FileTreeNode) => item.path);

      setExpandedPaths(firstLevelDirs);

      /**
       * 默认选中第一个文件
       */
      const firstFile = findFirstFile(displayTree);

      if (firstFile) {
        handleSelectFile(firstFile);
      }
    } catch (e: any) {
      message.error(e.message || '获取目录失败');
    } finally {
      setLoading(false);
    }
  };

  /**
   * 加载文本/代码/Markdown内容
   */
  const loadFileContent = async (file: FileTreeNode) => {
    try {
      setFileLoading(true);
      setFileContent('');
      setFileInfo(null);

      const res = await fetch('/v1/file/content', {
        method: 'POST',
        credentials: 'include',
        headers: authHeaders,
        body: JSON.stringify({
          path: file.path,
        }),
      });

      const result = await res.json();

      if (!res.ok || result.code !== 0) {
        throw new Error(result.message || '获取文件内容失败');
      }

      setFileInfo(result.data || null);
      setFileContent(result.data?.content || '');
    } catch (e: any) {
      setFileInfo(null);
      setFileContent('');
      message.error(e.message || '获取文件内容失败');
    } finally {
      setFileLoading(false);
    }
  };

  /**
   * 加载 PDF / 图片 Blob 预览
   */
  const loadBinaryPreview = async (file: FileTreeNode) => {
    try {
      setFileLoading(true);
      clearPreviewUrl();

      const res = await fetch('/v1/file/download', {
        method: 'POST',
        credentials: 'include',
        headers: authHeaders,
        body: JSON.stringify({
          path: file.path,
          preview: true,
        }),
      });

      /**
       * 如果后端返回 JSON 错误，避免拿 JSON 当 blob 渲染
       */
      const contentType = res.headers.get('content-type') || '';

      if (contentType.includes('application/json')) {
        const result = await res.json();
        throw new Error(result.message || '获取文件预览失败');
      }

      if (!res.ok) {
        throw new Error('获取文件预览失败');
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);

      setPreviewUrl(url);
    } catch (e: any) {
      clearPreviewUrl();
      message.error(e.message || '获取文件预览失败');
    } finally {
      setFileLoading(false);
    }
  };

  const loadDocxPreview = async (file: FileTreeNode) => {
    try {
      setFileLoading(true);
      setDocxHtml('');

      const res = await fetch('/v1/file/download', {
        method: 'POST',
        credentials: 'include',
        headers: authHeaders,
        body: JSON.stringify({
          path: file.path,
          preview: true,
        }),
      });

      const contentType = res.headers.get('content-type') || '';

      if (contentType.includes('application/json')) {
        const result = await res.json();
        throw new Error(result.message || '获取 Word 预览失败');
      }

      if (!res.ok) {
        throw new Error('获取 Word 预览失败');
      }

      const arrayBuffer = await res.arrayBuffer();

      const result = await mammoth.convertToHtml({
        arrayBuffer,
      });

      const safeHtml = DOMPurify.sanitize(result.value || '');

      setDocxHtml(safeHtml || '<p>暂无内容</p>');
    } catch (e: any) {
      setDocxHtml('');
      message.error(e.message || '获取 Word 预览失败');
    } finally {
      setFileLoading(false);
    }
  };

  const toggleExpand = (path: string) => {
    setExpandedPaths((list) =>
      list.includes(path)
        ? list.filter((item) => item !== path)
        : [...list, path],
    );
  };

  const handleSelectFile = async (node: FileTreeNode) => {
    setSelectedFile(node);
    setFileInfo(null);
    setFileContent('');
    setDocxHtml('');
    clearPreviewUrl();

    if (isMarkdownFile(node)) {
      setPreviewType('markdown');
      await loadFileContent(node);
      return;
    }

    if (isTextPreviewFile(node)) {
      setPreviewType('text');
      await loadFileContent(node);
      return;
    }

    if (isPdfFile(node)) {
      setPreviewType('pdf');
      await loadBinaryPreview(node);
      return;
    }

    if (isImageFile(node)) {
      setPreviewType('image');
      await loadBinaryPreview(node);
      return;
    }

    if (isDocxFile(node)) {
      setPreviewType('docx');
      await loadDocxPreview(node);
      return;
    }

    /**
     * .doc 老格式，纯前端不建议直接预览
     */
    if (isDocFile(node)) {
      setPreviewType('unsupported');
      return;
    }

    if (isOfficeFile(node)) {
      setPreviewType('unsupported');
      return;
    }

    setPreviewType('unsupported');
  };
  /**
   * 复制只对文本/Markdown/代码可用
   */
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(fileContent || '');
      message.success('已复制');
    } catch (e) {
      message.error('复制失败');
    }
  };

  /**
   * 下载所有类型文件：直接走后端 /download
   */
  const handleDownload = async () => {
    if (!selectedFile) {
      return;
    }

    try {
      const res = await fetch('/v1/file/download', {
        method: 'POST',
        credentials: 'include',
        headers: authHeaders,
        body: JSON.stringify({
          path: selectedFile.path,
        }),
      });

      const contentType = res.headers.get('content-type') || '';

      if (contentType.includes('application/json')) {
        const result = await res.json();
        throw new Error(result.message || '下载失败');
      }

      if (!res.ok) {
        throw new Error('下载失败');
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);

      const a = document.createElement('a');
      a.href = url;
      a.download = selectedFile.name;

      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);

      URL.revokeObjectURL(url);
    } catch (e: any) {
      message.error(e.message || '下载失败');
    }
  };

  useEffect(() => {
    if (open) {
      loadTree();
    }

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  /**
   * 组件卸载时释放 blob url
   */
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  if (!open) {
    return null;
  }

  const renderTreeNode = (node: FileTreeNode, level = 0) => {
    const isDirectory = node.type === 'directory';
    const isExpanded = expandedPaths.includes(node.path);
    const isSelected = selectedFile?.path === node.path;

    return (
      <div key={node.path}>
        <div
          onClick={() => {
            if (isDirectory) {
              toggleExpand(node.path);
            } else {
              handleSelectFile(node);
            }
          }}
          style={{
            height: 34,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            paddingLeft: 12 + level * 16,
            paddingRight: 10,
            cursor: 'pointer',
            borderRadius: 8,
            color: isSelected ? '#00A870' : token.colorText,
            background: isSelected ? 'rgba(0, 168, 112, 0.1)' : 'transparent',
            fontSize: 14,
            userSelect: 'none',
          }}
        >
          <span
            style={{
              width: 14,
              display: 'inline-flex',
              justifyContent: 'center',
              color: token.colorTextTertiary,
              flexShrink: 0,
            }}
          >
            {isDirectory ? (
              isExpanded ? (
                <DownOutlined style={{ fontSize: 10 }} />
              ) : (
                <RightOutlined style={{ fontSize: 10 }} />
              )
            ) : null}
          </span>

          <span
            style={{
              width: 16,
              display: 'inline-flex',
              color: isDirectory ? '#D99700' : token.colorTextSecondary,
              flexShrink: 0,
            }}
          >
            {isDirectory ? (
              isExpanded ? (
                <FolderOpenOutlined />
              ) : (
                <FolderOutlined />
              )
            ) : (
              <FileTextOutlined />
            )}
          </span>

          <Tooltip title={node.displayName || node.name}>
            <span
              style={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                flex: 1,
              }}
            >
              {node.displayName || node.name}
            </span>
          </Tooltip>
        </div>

        {isDirectory && isExpanded && node.children?.length ? (
          <div>
            {node.children.map((child) => renderTreeNode(child, level + 1))}
          </div>
        ) : null}
      </div>
    );
  };

  const renderPreviewContent = () => {
    if (fileLoading) {
      return (
        <div
          style={{
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Spin />
        </div>
      );
    }

    if (!selectedFile) {
      return <Empty description="请选择左侧文件" />;
    }

    if (previewType === 'pdf') {
      return previewUrl ? (
        <iframe
          src={previewUrl}
          title={selectedFile.name}
          style={{
            width: '100%',
            height: '100%',
            border: 'none',
            display: 'block',
            background: '#fff',
          }}
        />
      ) : (
        <div
          style={{
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Empty description="PDF 预览地址为空" />
        </div>
      );
    }

    if (previewType === 'image') {
      return previewUrl ? (
        <div
          style={{
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'auto',
            padding: 16,
          }}
        >
          <img
            src={previewUrl}
            alt={selectedFile.name}
            style={{
              maxWidth: '100%',
              maxHeight: '100%',
              objectFit: 'contain',
            }}
          />
        </div>
      ) : (
        <Empty description="图片预览地址为空" />
      );
    }

    if (previewType === 'docx') {
      return docxHtml ? (
        <div
          className="file-docx-preview"
          style={{
            color: token.colorText,
            background: token.colorBgContainer,
            padding: 24,
            borderRadius: 8,
            lineHeight: '26px',
            fontSize: 14,
          }}
          dangerouslySetInnerHTML={{
            __html: docxHtml,
          }}
        />
      ) : (
        <Empty description="Word 内容为空" />
      );
    }

    if (previewType === 'markdown') {
      return (
        <div
          className="file-markdown-preview"
          style={{
            color: token.colorText,
            fontSize: 14,
            lineHeight: '24px',
          }}
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ inline, className, children, ...props }: any) {
                const match = /language-(\w+)/.exec(className || '');

                return !inline && match ? (
                  <SyntaxHighlighter
                    style={codeTheme}
                    language={match[1]}
                    PreTag="div"
                    customStyle={{
                      margin: '12px 0',
                      borderRadius: 8,
                      fontSize: 13,
                      lineHeight: '22px',
                    }}
                    {...props}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <code
                    style={{
                      background: isDark
                        ? 'rgba(255, 255, 255, 0.12)'
                        : 'rgba(0, 0, 0, 0.06)',
                      padding: '2px 5px',
                      borderRadius: 4,
                      fontSize: 13,
                    }}
                    {...props}
                  >
                    {children}
                  </code>
                );
              },
            }}
          >
            {fileContent || '暂无内容'}
          </ReactMarkdown>
        </div>
      );
    }

    if (previewType === 'text') {
      return (
        <SyntaxHighlighter
          language={getLanguageBySuffix(fileInfo?.suffix || selectedFile.name)}
          style={codeTheme}
          showLineNumbers
          wrapLongLines
          customStyle={{
            margin: 0,
            borderRadius: 8,
            fontSize: 13,
            lineHeight: '22px',
            background: token.colorFillQuaternary,
            minHeight: '100%',
          }}
        >
          {fileContent || '暂无内容'}
        </SyntaxHighlighter>
      );
    }

    return (
      <Empty
        description={<span>该文件暂不支持在线预览，可点击右上角下载</span>}
      />
    );
  };

  const canCopy = ['text', 'markdown'].includes(previewType) && !!fileContent;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.48)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <div
        style={{
          width: 980,
          height: 720,
          background: token.colorBgContainer,
          borderRadius: 16,
          overflow: 'hidden',
          boxShadow: '0 24px 80px rgba(0, 0, 0, 0.28)',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* 顶部 */}
        <div
          style={{
            height: 64,
            padding: '0 22px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontSize: 16,
              fontWeight: 600,
              color: token.colorText,
            }}
          >
            <span>上传待审批文件</span>

            {/* <span
              style={{
                fontSize: 12,
                color: token.colorTextSecondary,
                background: token.colorFillSecondary,
                padding: '2px 6px',
                borderRadius: 6,
              }}
            >
              tree
            </span> */}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {/* <Button size="small" onClick={() => message.info('去使用')}>
              去使用
            </Button>

            <Tooltip title="下载">
              <Button
                size="small"
                type="text"
                icon={<DownloadOutlined />}
                onClick={handleDownload}
                disabled={!selectedFile}
              />
            </Tooltip> */}

            <Tooltip title="关闭">
              <Button
                size="small"
                type="text"
                icon={<CloseOutlined />}
                onClick={onClose}
              />
            </Tooltip>
          </div>
        </div>

        {/* 主体 */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            minHeight: 0,
          }}
        >
          {/* 左侧 */}
          <div
            style={{
              width: 240,
              borderRight: `1px solid ${token.colorBorderSecondary}`,
              padding: 14,
              overflowY: 'auto',
              background: token.colorFillQuaternary,
            }}
          >
            <div
              style={{
                fontSize: 13,
                fontWeight: 600,
                marginBottom: 10,
                color: token.colorTextSecondary,
              }}
            >
              文件
            </div>

            {loading ? (
              <div
                style={{
                  padding: 24,
                  textAlign: 'center',
                }}
              >
                <Spin size="small" />
              </div>
            ) : tree.length ? (
              tree.map((node) => renderTreeNode(node))
            ) : (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="暂无文件"
              />
            )}
          </div>

          {/* 右侧 */}
          <div
            style={{
              flex: 1,
              minWidth: 0,
              display: 'flex',
              flexDirection: 'column',
              background: token.colorBgContainer,
            }}
          >
            <div
              style={{
                height: 44,
                padding: '0 16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderBottom: `1px solid ${token.colorBorderSecondary}`,
              }}
            >
              <div
                style={{
                  fontWeight: 500,
                  color: token.colorText,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {selectedFile?.name || '请选择文件'}
              </div>

              <div style={{ display: 'flex', gap: 4 }}>
                <Tooltip title="复制内容">
                  <Button
                    size="small"
                    type="text"
                    icon={<CopyOutlined />}
                    disabled={!canCopy}
                    onClick={handleCopy}
                  />
                </Tooltip>

                <Tooltip title="下载">
                  <Button
                    size="small"
                    type="text"
                    icon={<DownloadOutlined />}
                    disabled={!selectedFile}
                    onClick={handleDownload}
                  />
                </Tooltip>
              </div>
            </div>

            <div
              style={{
                flex: 1,
                minHeight: 0,
                overflow: 'auto',
                padding: 16,
              }}
            >
              {renderPreviewContent()}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
export default FileTreePreview;
