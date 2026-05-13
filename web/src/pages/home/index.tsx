import message from '@/components/ui/message';
import { useNavigateWithFromState } from '@/hooks/route-hook';
import { getAuthorization } from '@/utils/authorization-util';
import { useEffect, useRef, useState } from 'react';
import { Applications } from './applications';
import { NextBanner } from './banner';
import { Datasets } from './datasets';

const Home = () => {
  const navigate = useNavigateWithFromState();

  // --- 拖拽相关状态 ---
  const [isDragging, setIsDragging] = useState(false);
  // 初始位置对应原来的 right:100, bottom:100 (假设屏幕右下角)
  const [position, setPosition] = useState({
    left: 'auto',
    top: 'auto',
    right: '100px',
    bottom: '100px',
  });
  const dragRef = useRef(null);
  const offsetRef = useRef({ x: 0, y: 0 });

  // --- 拖拽逻辑 ---
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isDragging) return;

      // 计算新位置：鼠标当前位置 - 鼠标点击时相对于元素左上角的偏移量
      const newLeft = e.clientX - offsetRef.current.x;
      const newTop = e.clientY - offsetRef.current.y;

      // 切换为 left/top 定位模式，覆盖掉 right/bottom
      setPosition({
        left: `${newLeft}px`,
        top: `${newTop}px`,
        right: 'auto',
        bottom: 'auto',
      });
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      // 恢复鼠标样式，移除文本禁止选中样式（如果有）
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };

    if (isDragging) {
      // 防止拖动时选中文字
      document.body.style.userSelect = 'none';
      document.body.style.cursor = 'move';

      // 绑定全局事件，防止鼠标移动过快脱离元素导致拖动失效
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };
  }, [isDragging]);

  const handleMouseDown = (e) => {
    setIsDragging(true);
    // 计算鼠标点击点相对于按钮左上角的偏移
    // 注意：这里使用 dragRef 获取外层的 div
    const rect = dragRef.current.getBoundingClientRect();
    offsetRef.current = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  };

  // --- 原有业务逻辑 ---
  const handleSmartClick = async () => {
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

        {/* 1. Logo 容器 - 可拖动版 */}
        <div
          ref={dragRef} // 绑定 ref 用于计算坐标
          onMouseDown={handleMouseDown} // 绑定鼠标按下事件
          className="fixed pointer-events-auto scale-125 transition-transform duration-300 z-[50] cursor-move"
          style={{
            // 动态应用位置状态
            left: position.left,
            top: position.top,
            right: position.right,
            bottom: position.bottom,
            width: '100px',
            height: '100px',
            // 拖动时移除过渡效果，避免延迟感
            transition: isDragging ? 'none' : 'transform 0.3s duration-300',
          }}
        >
          <button
            onClick={handleSmartClick}
            className="absolute z-[100] rounded-full flex items-center justify-center group cursor-pointer"
            style={{
              right: '18%',
              bottom: '18%',
              width: '40px',
              height: '40px',
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
