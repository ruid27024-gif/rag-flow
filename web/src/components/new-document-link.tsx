import {
  getExtension,
  isSupportedPreviewDocumentType,
} from '@/utils/document-util';
import React from 'react';

interface IProps extends React.PropsWithChildren {
  link?: string;
  preventDefault?: boolean;
  color?: string;
  documentName: string;
  documentId?: string;
  prefix?: string;
  className?: string;
}

const NewDocumentLink = ({
  children,
  link,
  preventDefault = false,
  color = 'rgb(15, 79, 170)',
  documentId,
  documentName,
  prefix = 'file',
  className,
}: IProps) => {
  let nextLink = link;
  // 获取后缀
  const extension = getExtension(documentName);
  if (!link) {
    nextLink = `/document/${documentId}?ext=${extension}&prefix=${prefix}`;
  }
  console.log(nextLink);
  // 2. 处理下载的函数
  const handleDownload = (e: React.MouseEvent) => {
    e.stopPropagation(); // 阻止事件冒泡，避免触发父元素的点击事件
    const downloadLink = document.createElement('a');
    downloadLink.href = `/v1/document/get/${documentId}?ext=pdf`;
    // download 属性会提示浏览器下载资源，而不是导航到该资源
    // 其值可以作为下载文件的默认文件名
    downloadLink.download = documentName || 'download';
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
  };

  // return (
  //   <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
  //   <a
  //     target="_blank"
  //     onClick={
  //       !preventDefault || isSupportedPreviewDocumentType(extension)
  //         ? undefined
  //         : (e) => e.preventDefault()
  //     }
  //     href={nextLink}
  //     rel="noreferrer"
  //     style={{ color: className ? '' : color, wordBreak: 'break-all' }}
  //     className={className}
  //   >
  //     {children}
  //   </a>

  //   {isSupportedPreviewDocumentType(extension) && (
  //       <button
  //         onClick={handleDownload}
  //         style={{
  //           cursor: 'pointer',
  //           padding: '2px 6px',
  //           fontSize: '12px',
  //           border: '1px solid #ccc',
  //           borderRadius: '4px',
  //           backgroundColor: '#f0f0f0'
  //         }}
  //       >
  //         下载
  //       </button>
  //     )}
  //     </span>
  // );

  // NewDocumentLink 组件内部
  //   return (
  //     // 修改点：
  //     // 1. 移除 style 中的 wordBreak: 'break-all' (这会强制换行，与截断冲突)
  //     // 2. 确保 className 被正确应用
  //     <div
  //       style={{
  //         display: 'inline-flex',
  //         alignItems: 'center',
  //         gap: '8px',
  //         width: '100%',
  //         justifyContent: 'space-between',
  //       }}
  //     >
  //       <div
  //         style={{
  //           width: '90%',
  //           overflow: 'hidden',
  //           textOverflow: 'ellipsis',
  //         }}
  //       >
  //         <a
  //           target="_blank"
  //           onClick={
  //             !preventDefault || isSupportedPreviewDocumentType(extension)
  //               ? undefined
  //               : (e) => e.preventDefault()
  //           }
  //           href={nextLink}
  //           rel="noreferrer"
  //           style={{ color: className ? '' : color }} // 移除了 wordBreak
  //           className={className} // 确保这里的 className 接收到了父组件传来的 'flex-1 truncate'
  //         >
  //           {children}
  //         </a>
  //       </div>

  //       {isSupportedPreviewDocumentType(extension) && (
  //         <button
  //           onClick={handleDownload}
  //           className="
  //                     cursor-pointer
  //                     px-2 py-1 text-xs border rounded-md
  //                     bg-gray-100 text-gray-700 border-gray-300
  //                     hover:bg-gray-200
  //                     dark:bg-slate-800 dark:text-gray-200 dark:border-slate-600 dark:hover:bg-slate-700
  //                     flex-shrink-0
  //                 "
  //         >
  //           下载
  //         </button>
  //       )}
  //     </div>
  //   );
  // };
  return (
    <div className="flex items-center gap-2 min-w-0 flex-1 w-full max-w-[550px]">
      <div className="min-w-0 flex-1 overflow-hidden">
        <a
          target="_blank"
          onClick={
            !preventDefault || isSupportedPreviewDocumentType(extension)
              ? undefined
              : (e) => e.preventDefault()
          }
          href={nextLink}
          rel="noreferrer"
          title={documentName}
          style={{ color: className ? '' : color }}
          className={`block w-full overflow-hidden text-ellipsis whitespace-nowrap ${className || ''}`}
        >
          {children}
        </a>
      </div>

      {isSupportedPreviewDocumentType(extension) && (
        <button
          type="button"
          onClick={handleDownload}
          className="
            flex-shrink-0
            cursor-pointer
            px-2 py-1 text-xs border rounded-md
            bg-gray-100 text-gray-700 border-gray-300
            hover:bg-gray-200
            dark:bg-slate-800 dark:text-gray-200 dark:border-slate-600 dark:hover:bg-slate-700
          "
        >
          下载
        </button>
      )}
    </div>
  );
};

export default NewDocumentLink;
