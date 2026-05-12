import React from 'react';

// 1. 定义 Props 接口，增加 children
interface HengfengLogoProps {
  isPaused?: boolean;
  children?: React.ReactNode;
}

const LOGO_WIDTH = 150;

export const HengfengLogo = ({
  isPaused = false,
  children,
}: HengfengLogoProps) => {
  const animationClass = isPaused ? 'paused' : '';

  // ... (path1 到 path8 以及 circlePath 的定义保持不变) ...
  const path1 = 'M 188 265 L 369 265 L 333 229 L 225 229 Z';
  const path2 = 'M 178 419 L 305 291 L 254 291 L 178 368 Z';
  const path3 = 'M 279 355 L 279 536 L 243 500 L 243 391 Z';
  const path4 = 'M 305 419 L 433 547 L 382 547 L 305 470 Z';
  const path5 = 'M 550 445 L 369 445 L 405 482 L 513 482 Z';
  const path6 = 'M 561 291 L 433 419 L 484 419 L 561 342 Z';
  const path7 = 'M 459 355 L 459 175 L 495 211 L 495 319 Z';
  const path8 = 'M 305 164 L 433 291 L 433 240 L 356 164 Z';

  const centerX = 369;
  const centerY = 355.24;
  const radius = 60;
  const circlePath = `M ${centerX + radius} ${centerY} a ${radius} ${radius} 0 1 0 ${-radius * 2} 0 a ${radius} ${radius} 0 1 0 ${radius * 2} 0 Z`;

  const def = (path: string, id: string, isCircle: boolean = false) => {
    return (
      <svg
        className="w-full h-full block"
        viewBox="0 0 1440 704"
        preserveAspectRatio="xMidYMid meet"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient
            id={`lightGreen${id}`}
            x1="0%"
            y1="0%"
            x2="100%"
            y2="100%"
          >
            <stop offset="0%" stopColor="#006227" />
            <stop offset="100%" stopColor="#00C853" />
          </linearGradient>
          <linearGradient
            id={`blueRing${id}`}
            x1="0%"
            y1="0%"
            x2="100%"
            y2="100%"
          >
            <stop offset="0%" stopColor="#0D47A1" />
            <stop offset="50%" stopColor="#2979FF" />
            <stop offset="100%" stopColor="#01579B" />
          </linearGradient>
          <linearGradient
            id={`flowingLight${id}`}
            x1="0%"
            y1="0%"
            x2="100%"
            y2="0%"
          >
            <stop offset="0%" stopColor="transparent" stopOpacity="0" />
            <stop offset="50%" stopColor="#FFFFFF" stopOpacity="1" />
            <stop offset="100%" stopColor="transparent" stopOpacity="0" />
          </linearGradient>
          <filter
            id={`glowFilter${id}`}
            x="-50%"
            y="-50%"
            width="200%"
            height="200%"
          >
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {isCircle ? (
          <>
            <path
              d={path}
              stroke={`url(#blueRing${id})`}
              strokeWidth="8"
              fill="none"
              strokeLinecap="round"
            />
            <path
              d={path}
              stroke={`url(#flowingLight${id})`}
              strokeWidth="3"
              fill="none"
              filter={`url(#glowFilter${id})`}
              className={`animate-flow ${animationClass}`}
              style={{ mixBlendMode: 'screen' }}
            />
          </>
        ) : (
          <path
            d={path}
            fill={`url(#lightGreen${id})`}
            fillOpacity="0.9"
            stroke="none"
          />
        )}
      </svg>
    );
  };

  return (
    <div
      className="absolute pointer-events-none z-50"
      style={{
        right: '20px',
        top: '50%',
        transform: 'translateY(-50%)',
        width: `${LOGO_WIDTH}px`,
        height: `${LOGO_WIDTH * (704 / 1440)}px`,
      }}
    >
      {/* 渲染所有 SVG 图形 */}
      <div className="absolute inset-0">{def(path1, '1')}</div>
      <div className="absolute inset-0">{def(path2, '2')}</div>
      <div className="absolute inset-0">{def(path3, '3')}</div>
      <div className="absolute inset-0">{def(path4, '4')}</div>
      <div className="absolute inset-0">{def(path5, '5')}</div>
      <div className="absolute inset-0">{def(path6, '6')}</div>
      <div className="absolute inset-0">{def(path7, '7')}</div>
      <div className="absolute inset-0">{def(path8, '8')}</div>
      <div className="absolute inset-0">{def(circlePath, 'center', true)}</div>

      {/* 
        2. 新增：渲染子元素 (按钮) 
        使用绝对定位将其放置在中心。
        注意：这里的坐标是基于 viewBox (1440x704) 的，所以需要根据 LOGO_WIDTH 进行缩放计算。
      */}
      {children && (
        <div
          className="absolute pointer-events-auto z-10"
          style={{
            // 基于 viewBox 的中心坐标 (369, 355.24) 计算
            left: `${(369 / 1440) * LOGO_WIDTH}px`,
            top: `${(355.24 / 704) * (LOGO_WIDTH * (704 / 1440))}px`,
            // 按钮自身的宽高，可以根据需要调整
            width: '30px',
            height: '30px',
            transform: 'translate(-50%, -50%)', // 确保按钮中心点对准圆心
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
};

// ... (样式注入代码保持不变) ...
const styles = `
  @keyframes flow {
    0% { stroke-dasharray: 0, 1000; stroke-dashoffset: 0; }
    50% { stroke-dasharray: 200, 1000; stroke-dashoffset: -200; }
    100% { stroke-dasharray: 0, 1000; stroke-dashoffset: -1000; }
  }
  .animate-flow { animation: flow 2s linear infinite; }
  .paused { animation-play-state: paused; }
`;

if (typeof document !== 'undefined') {
  let styleSheet = document.getElementById('hengfeng-logo-styles');
  if (!styleSheet) {
    const style = document.createElement('style');
    style.id = 'hengfeng-logo-styles';
    style.textContent = styles;
    document.head.appendChild(style);
  }
}

export default HengfengLogo;
