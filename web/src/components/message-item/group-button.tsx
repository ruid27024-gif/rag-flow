import { PromptIcon } from '@/assets/icon/next-icon';
import CopyToClipboard from '@/components/copy-to-clipboard';
import { useSetModalState } from '@/hooks/common-hooks';
import { IRemoveMessageById } from '@/hooks/logic-hooks';
import {
  BranchesOutlined,
  DeleteOutlined,
  DislikeOutlined,
  LikeOutlined,
  PauseCircleOutlined,
  ShareAltOutlined,
  SoundOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { Radio, Tooltip } from 'antd';
import { useCallback } from 'react';
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
}

export const AssistantGroupButton = ({
  messageId,
  content,
  prompt,
  audioBinary,
  showLikeButton,
  showLoudspeaker = true,
  onShareMessage,
  onRebaseMessage,
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

  const handleLike = useCallback(() => {
    onFeedbackOk({ thumbup: true });
  }, [onFeedbackOk]);

  return (
    <>
      <Radio.Group
        size="small"
        value={null}
        className={styles.messageActionRadio}
      >
        <Radio.Button value="a">
          <CopyToClipboard text={content} />
        </Radio.Button>

        {onShareMessage && (
          <Radio.Button value="share" onClick={onShareMessage}>
            <Tooltip title="分享">
              <ShareAltOutlined />
            </Tooltip>
          </Radio.Button>
        )}

        {onRebaseMessage && (
          <Radio.Button value="rebase" onClick={onRebaseMessage}>
            <Tooltip title="分支">
              <BranchesOutlined />
            </Tooltip>
          </Radio.Button>
        )}

        {showLoudspeaker && (
          <Radio.Button value="b" onClick={handleRead}>
            <Tooltip title={t('chat.read')}>
              {isPlaying ? <PauseCircleOutlined /> : <SoundOutlined />}
            </Tooltip>
            <audio src="" ref={ref}></audio>
          </Radio.Button>
        )}

        {showLikeButton && (
          <>
            <Radio.Button value="c" onClick={handleLike}>
              <Tooltip title="喜欢">
                <LikeOutlined />
              </Tooltip>
            </Radio.Button>

            <Radio.Button value="d" onClick={showModal}>
              <Tooltip title="不喜欢">
                <DislikeOutlined />
              </Tooltip>
            </Radio.Button>
          </>
        )}

        {prompt && (
          <Radio.Button value="e" onClick={showPromptModal}>
            <PromptIcon style={{ fontSize: '16px' }} />
          </Radio.Button>
        )}
      </Radio.Group>

      {visible && (
        <FeedbackDialog
          visible={visible}
          hideModal={hideModal}
          onOk={onFeedbackOk}
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

  // return (
  //   <>
  //     <Radio.Group size="small">
  //       <Radio.Button value="a">
  //         <CopyToClipboard text={content}></CopyToClipboard>
  //       </Radio.Button>
  //       {showLoudspeaker && (
  //         <Radio.Button value="b" onClick={handleRead}>
  //           <Tooltip title={t('chat.read')}>
  //             {isPlaying ? <PauseCircleOutlined /> : <SoundOutlined />}
  //           </Tooltip>
  //           <audio src="" ref={ref}></audio>
  //         </Radio.Button>
  //       )}
  //       {showLikeButton && (
  //         <>
  //           <Radio.Button value="c" onClick={handleLike}>
  //             <LikeOutlined />
  //           </Radio.Button>
  //           <Radio.Button value="d" onClick={showModal}>
  //             <DislikeOutlined />
  //           </Radio.Button>
  //         </>
  //       )}
  //       {prompt && (
  //         <Radio.Button value="e" onClick={showPromptModal}>
  //           <PromptIcon style={{ fontSize: '16px' }} />
  //         </Radio.Button>
  //       )}
  //     </Radio.Group>
  //     {visible && (
  //       <FeedbackDialog
  //         visible={visible}
  //         hideModal={hideModal}
  //         onOk={onFeedbackOk}
  //         loading={loading}
  //       ></FeedbackDialog>
  //     )}
  //     {promptVisible && (
  //       <PromptDialog
  //         visible={promptVisible}
  //         hideModal={hidePromptModal}
  //         prompt={prompt}
  //       ></PromptDialog>
  //     )}
  //   </>
  // );
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
