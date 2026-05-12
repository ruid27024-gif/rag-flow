import message from '@/components/ui/message';
import { useNavigateWithFromState } from '@/hooks/route-hook';
import { getAuthorization } from '@/utils/authorization-util';
import { HengfengLogo } from '../../HengfengLogo';
import { Applications } from './applications';
import { NextBanner } from './banner';
import { Datasets } from './datasets';

const Home = () => {
  const navigate = useNavigateWithFromState();
  // 假设你有获取 Token 的方法
  // const getAuthorization = () => localStorage.getItem('token');

  // 2. 封装点击处理函数
  const handleSmartClick = async () => {
    // 这里直接复用了你的逻辑，相当于触发了 'create-dialog-api' 选项
    const targetPath = 'create-dialog-api';

    try {
      const response = await fetch('/v1/debug/create_dialog_from_config', {
        method: 'POST',
        headers: {
          Authorization: getAuthorization() || '',
        },
      });

      const res = await response.json();

      if (res.retcode === 0 && res.data?.id) {
        // 假设 Routes.ChatDefault 是 '/chat' 之类的路径
        // 如果这里报错，请确保你有定义 Routes 或者直接用字符串路径
        navigate(`/next-chat-default/${res.data.id}`);
      } else {
        message.error(res.msg || '新建对话失败！');
      }
    } catch (error) {
      console.error(error);
      message.error('请求失败！');
    }
  };

  return (
    <section>
      <NextBanner></NextBanner>
      <section className="h-[calc(100dvh-260px)] overflow-auto px-10">
        <Datasets></Datasets>
        <Applications></Applications>
        {/* 1. Logo 容器 */}

        {/* 1. Logo 容器 - 修复版 */}
        <div
          className="fixed pointer-events-auto scale-125 transition-transform duration-300 z-[50]"
          style={{
            right: '100px',
            bottom: '-500px', // 建议改为正值，或者确保负值不会导致布局计算错误
            // 删除了 width: '100%' 和 height: '100%'
            // 让 div 自动适应内部 HengfengLogo 的大小
            width: '100px',
            height: '100px',
          }}
        >
          <HengfengLogo />

          <button
            onClick={handleSmartClick}
            className="absolute z-[100] rounded-full flex items-center justify-center group cursor-pointer"
            style={{
              // 这里的定位现在是相对于 HengfengLogo 或者父容器的大小
              // 如果按钮位置跑偏了，请微调这里的 right/bottom 值
              right: '82px',
              bottom: '582px',

              width: '30px',
              height: '30px',
              background: 'transparent',
              backdropFilter: 'none',
              border: '1px solid #40E0D0',
              boxShadow: '0 0 15px rgba(41, 121, 255, 0.6)',
              transition: 'all 0.3s ease',
            }}
          >
            <span
              className="font-bold drop-shadow-md group-hover:scale-110 transition-transform"
              style={{ color: '#2979FF' }}
            >
              恒
            </span>
          </button>
        </div>
      </section>
    </section>
  );
};

export default Home;
