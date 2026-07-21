import CopyToClipboard from '@/components/copy-to-clipboard';
import { useSetModalState } from '@/hooks/common-hooks';
import { IRemoveMessageById } from '@/hooks/logic-hooks';
import {
  BranchesOutlined,
  DeleteOutlined,
  DislikeFilled,
  DislikeOutlined,
  LikeFilled,
  LikeOutlined,
  PauseCircleOutlined,
  SoundOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { Radio, Tooltip } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import FeedbackDialog from '../feedback-dialog';
import { PromptDialog } from '../prompt-dialog';
import { useRemoveMessage, useSendFeedback, useSpeech } from './hooks';
import styles from './index.less';

interface IProps {
  messageId: string;
  content: string;
  prompt?: string;
  showLikeButton: boolean;
  audioBinary?: string;
  showLoudspeaker?: boolean;
  onShareMessage?: () => void;
  onRebaseMessage?: () => void;
  thumbup?: boolean | null;
}

// export const AssistantGroupButton = ({
//   messageId,
//   content,
//   prompt,
//   audioBinary,
//   showLikeButton,
//   showLoudspeaker = true,
//   onShareMessage,
//   onRebaseMessage,
// }: IProps) => {
//   const { visible, hideModal, showModal, onFeedbackOk, loading } =
//     useSendFeedback(messageId);
//   const {
//     visible: promptVisible,
//     hideModal: hidePromptModal,
//     showModal: showPromptModal,
//   } = useSetModalState();
//   const { t } = useTranslation();
//   const { handleRead, ref, isPlaying } = useSpeech(content, audioBinary);

//   const handleLike = useCallback(() => {
//     onFeedbackOk({ thumbup: true });
//   }, [onFeedbackOk]);

//   return (
//     <>
//       <Radio.Group
//         size="small"
//         value={null}
//         className={styles.messageActionRadio}
//       >
//         <Radio.Button value="a">
//           <CopyToClipboard text={content} />
//         </Radio.Button>

//         {/* {onShareMessage && (
//           <Radio.Button value="share" onClick={onShareMessage}>
//             <Tooltip title="分享">
//               <ShareAltOutlined />
//             </Tooltip>
//           </Radio.Button>
//         )} */}

//         {onRebaseMessage && (
//           <Radio.Button value="rebase" onClick={onRebaseMessage}>
//             <Tooltip title="分支">
//               <BranchesOutlined />
//             </Tooltip>
//           </Radio.Button>
//         )}

//         {showLoudspeaker && (
//           <Radio.Button value="b" onClick={handleRead}>
//             <Tooltip title={t('chat.read')}>
//               {isPlaying ? <PauseCircleOutlined /> : <SoundOutlined />}
//             </Tooltip>
//             <audio src="" ref={ref}></audio>
//           </Radio.Button>
//         )}

//         {showLikeButton && (
//           <>
//             <Radio.Button value="c" onClick={handleLike}>
//               <Tooltip title="喜欢">
//                 <LikeOutlined />
//               </Tooltip>
//             </Radio.Button>

//             <Radio.Button value="d" onClick={showModal}>
//               <Tooltip title="不喜欢">
//                 <DislikeOutlined />
//               </Tooltip>
//             </Radio.Button>
//           </>
//         )}

//         {/* {prompt && (
//           <Radio.Button value="e" onClick={showPromptModal}>
//             <PromptIcon style={{ fontSize: '16px' }} />
//           </Radio.Button>
//         )} */}
//       </Radio.Group>

//       {visible && (
//         <FeedbackDialog
//           visible={visible}
//           hideModal={hideModal}
//           onOk={onFeedbackOk}
//           loading={loading}
//         />
//       )}

//       {promptVisible && (
//         <PromptDialog
//           visible={promptVisible}
//           hideModal={hidePromptModal}
//           prompt={prompt}
//         />
//       )}
//     </>
//   );

//   // return (
//   //   <>
//   //     <Radio.Group size="small">
//   //       <Radio.Button value="a">
//   //         <CopyToClipboard text={content}></CopyToClipboard>
//   //       </Radio.Button>
//   //       {showLoudspeaker && (
//   //         <Radio.Button value="b" onClick={handleRead}>
//   //           <Tooltip title={t('chat.read')}>
//   //             {isPlaying ? <PauseCircleOutlined /> : <SoundOutlined />}
//   //           </Tooltip>
//   //           <audio src="" ref={ref}></audio>
//   //         </Radio.Button>
//   //       )}
//   //       {showLikeButton && (
//   //         <>
//   //           <Radio.Button value="c" onClick={handleLike}>
//   //             <LikeOutlined />
//   //           </Radio.Button>
//   //           <Radio.Button value="d" onClick={showModal}>
//   //             <DislikeOutlined />
//   //           </Radio.Button>
//   //         </>
//   //       )}
//   //       {prompt && (
//   //         <Radio.Button value="e" onClick={showPromptModal}>
//   //           <PromptIcon style={{ fontSize: '16px' }} />
//   //         </Radio.Button>
//   //       )}
//   //     </Radio.Group>
//   //     {visible && (
//   //       <FeedbackDialog
//   //         visible={visible}
//   //         hideModal={hideModal}
//   //         onOk={onFeedbackOk}
//   //         loading={loading}
//   //       ></FeedbackDialog>
//   //     )}
//   //     {promptVisible && (
//   //       <PromptDialog
//   //         visible={promptVisible}
//   //         hideModal={hidePromptModal}
//   //         prompt={prompt}
//   //       ></PromptDialog>
//   //     )}
//   //   </>
//   // );
// };

export const AssistantGroupButton = ({
  messageId,
  content,
  prompt,
  audioBinary,
  showLikeButton,
  showLoudspeaker = true,
  onShareMessage,
  onRebaseMessage,
  thumbup,
}: IProps) => {
  const { visible, hideModal, showModal, onFeedbackOk, loading } =
    useSendFeedback(messageId);

  const {
    visible: promptVisible,
    hideModal: hidePromptModal,
    showModal: showPromptModal,
  } = useSetModalState();

  const { t } = useTranslation();
  const { handleRead, ref, isPlaying } = useSpeech(content, audioBinary);

  const [feedback, setFeedback] = useState<'like' | 'dislike' | null>(() => {
    if (thumbup === true) return 'like';
    if (thumbup === false) return 'dislike';
    return null;
  });

  /**
   * 根据后端返回的 thumbup 同步状态。
   *
   * 注意：
   * thumbup === undefined 时，说明父组件可能没传这个字段，
   * 这时不要强行 setFeedback(null)，否则点击后可能刚亮又灭。
   */
  useEffect(() => {
    if (thumbup === undefined) {
      return;
    }

    if (thumbup === true) {
      setFeedback('like');
    } else if (thumbup === false) {
      setFeedback('dislike');
    } else {
      setFeedback(null);
    }
  }, [thumbup, messageId]);

  /**
   * 点击喜欢：
   * - 当前已经是喜欢：取消
   * - 当前不是喜欢：切换为喜欢
   */
  const handleLike = useCallback(() => {
    if (feedback === 'like') {
      setFeedback(null);

      onFeedbackOk({
        thumbup: null,
      });

      return;
    }

    setFeedback('like');

    onFeedbackOk({
      thumbup: true,
    });
  }, [feedback, onFeedbackOk]);

  /**
   * 点击不喜欢：
   * - 当前已经是不喜欢：取消
   * - 当前不是不喜欢：打开反馈弹窗
   */
  const handleDislikeClick = useCallback(() => {
    if (feedback === 'dislike') {
      setFeedback(null);

      onFeedbackOk({
        thumbup: null,
      });

      return;
    }

    showModal();
  }, [feedback, onFeedbackOk, showModal]);

  /**
   * 不喜欢弹窗确认后：
   * 设置为不喜欢
   */
  const handleDislikeOk = useCallback(
    (params: any) => {
      setFeedback('dislike');

      onFeedbackOk({
        ...params,
        thumbup: false,
      });
    },
    [onFeedbackOk],
  );

  const likeActive = feedback === 'like';
  const dislikeActive = feedback === 'dislike';

  const activeButtonStyle = {
    color: '#1677ff',
    borderColor: '#1677ff',
    backgroundColor: '#e6f4ff',
  };

  const activeIconStyle = {
    color: '#1677ff',
  };

  return (
    <>
      <Radio.Group
        size="small"
        value={feedback}
        className={styles.messageActionRadio}
      >
        <Radio.Button value="copy">
          <CopyToClipboard text={content} />
        </Radio.Button>

        {onRebaseMessage && (
          <Radio.Button value="rebase" onClick={onRebaseMessage}>
            <Tooltip title="分支">
              <BranchesOutlined />
            </Tooltip>
          </Radio.Button>
        )}

        {showLoudspeaker && (
          <Radio.Button value="read" onClick={handleRead}>
            <Tooltip title={t('chat.read')}>
              {isPlaying ? <PauseCircleOutlined /> : <SoundOutlined />}
            </Tooltip>
            <audio src="" ref={ref}></audio>
          </Radio.Button>
        )}

        {showLikeButton && (
          <>
            <Radio.Button
              value="like"
              onClick={handleLike}
              style={likeActive ? activeButtonStyle : undefined}
            >
              <Tooltip title={likeActive ? '取消喜欢' : '喜欢'}>
                {likeActive ? (
                  <LikeFilled style={activeIconStyle} />
                ) : (
                  <LikeOutlined />
                )}
              </Tooltip>
            </Radio.Button>

            <Radio.Button
              value="dislike"
              onClick={handleDislikeClick}
              style={dislikeActive ? activeButtonStyle : undefined}
            >
              <Tooltip title={dislikeActive ? '取消不喜欢' : '不喜欢'}>
                {dislikeActive ? (
                  <DislikeFilled style={activeIconStyle} />
                ) : (
                  <DislikeOutlined />
                )}
              </Tooltip>
            </Radio.Button>
          </>
        )}

        {/* {prompt && (
          <Radio.Button value="prompt" onClick={showPromptModal}>
            <PromptIcon style={{ fontSize: '16px' }} />
          </Radio.Button>
        )} */}
      </Radio.Group>

      {visible && (
        <FeedbackDialog
          visible={visible}
          hideModal={hideModal}
          onOk={handleDislikeOk}
          loading={loading}
        />
      )}

      {promptVisible && (
        <PromptDialog
          visible={promptVisible}
          hideModal={hidePromptModal}
          prompt={prompt}
        />
      )}
    </>
  );
};

interface UserGroupButtonProps extends Partial<IRemoveMessageById> {
  messageId: string;
  content: string;
  regenerateMessage?: () => void;
  sendLoading: boolean;
}

export const UserGroupButton = ({
  content,
  messageId,
  sendLoading,
  removeMessageById,
  regenerateMessage,
}: UserGroupButtonProps) => {
  const { onRemoveMessage, loading } = useRemoveMessage(
    messageId,
    removeMessageById,
  );
  const { t } = useTranslation();

  return (
    <Radio.Group size="small">
      <Radio.Button value="a">
        <CopyToClipboard text={content}></CopyToClipboard>
      </Radio.Button>
      {regenerateMessage && (
        <Radio.Button
          value="b"
          onClick={regenerateMessage}
          disabled={sendLoading}
        >
          <Tooltip title={t('chat.regenerate')}>
            <SyncOutlined spin={sendLoading} />
          </Tooltip>
        </Radio.Button>
      )}
      {removeMessageById && (
        <Radio.Button value="c" onClick={onRemoveMessage} disabled={loading}>
          <Tooltip title={t('common.delete')}>
            <DeleteOutlined spin={loading} />
          </Tooltip>
        </Radio.Button>
      )}
    </Radio.Group>
  );
};
