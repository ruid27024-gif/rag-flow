import { useTranslate } from '@/hooks/common-hooks';
import { CheckOutlined, CopyOutlined } from '@ant-design/icons';
import { Tooltip } from 'antd';
import { useState } from 'react';
import { CopyToClipboard as Clipboard, Props } from 'react-copy-to-clipboard';

// const CopyToClipboard = ({ text, className }: Props) => {
//   const [copied, setCopied] = useState(false);
//   const { t } = useTranslate('common');
//   // 使用捕获组 () 来“记住”中间的内容
//   const filteredText = text
//     .replace(/<think>([\s\S]*?)<\/think>/gi, '$1')
//     .trim();

//   const handleCopy = () => {
//     setCopied(true);
//     setTimeout(() => {
//       setCopied(false);
//     }, 2000);
//   };

//   return (
//     <Tooltip title={copied ? t('copied') : t('copy')}>
//       <Clipboard text={filteredText} onCopy={handleCopy}>
//         {/* {copied ? <CheckOutlined /> : <CopyOutlined />} */}
//         <span className={className}>
//           {copied ? <CheckOutlined /> : <CopyOutlined />}
//         </span>
//       </Clipboard>
//     </Tooltip>
//   );
// };

const CopyToClipboard = ({ text, className }: Props) => {
  const [copied, setCopied] = useState(false);
  const { t } = useTranslate('common');

  const filteredText = text
    .replace(/<think>([\s\S]*?)<\/think>/gi, '$1')
    .trim();

  const handleCopy = () => {
    setCopied(true);
    setTimeout(() => {
      setCopied(false);
    }, 2000);
  };

  return (
    <Tooltip title={copied ? t('copied') : t('copy')}>
      <span className={className}>
        <Clipboard text={filteredText} onCopy={handleCopy}>
          <span className="copy-icon-inner">
            {copied ? <CheckOutlined /> : <CopyOutlined />}
          </span>
        </Clipboard>
      </span>
    </Tooltip>
  );
};

export default CopyToClipboard;

export function CopyToClipboardWithText({ text }: { text: string }) {
  return (
    <div className="bg-bg-card p-1 rounded-md flex gap-2">
      <span className="flex-1 truncate">{text}</span>
      <CopyToClipboard text={text}></CopyToClipboard>
    </div>
  );
}
