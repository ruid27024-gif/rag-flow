import React, { useId } from 'react';

interface HengfengLogoProps {
  /** 是否暂停流光动画 */
  isPaused?: boolean;

  /** Logo 中心位置的自定义内容 */
  children?: React.ReactNode;

  /** 外层容器类名 */
  className?: string;

  /** 外层容器样式，可以覆盖默认宽高 */
  style?: React.CSSProperties;

  /** Logo 尺寸，默认 48px */
  size?: number | string;
}

/**
 * 图形实际坐标大致范围：
 *
 * x: 178 ~ 561
 * y: 164 ~ 547
 *
 * 因此不应该继续使用：
 * viewBox="0 0 1440 704"
 *
 * 这里在图形四周保留少量空间，并裁剪成正方形。
 */
const LOGO_VIEW_BOX = {
  x: 150,
  y: 136,
  width: 440,
  height: 440,
};

export const HengfengLogo = ({
  isPaused = false,
  children,
  className = '',
  style = {},
  size = 48,
}: HengfengLogoProps) => {
  /*
   * 防止页面同时渲染多个 Logo 时，SVG defs 中的 id 发生冲突。
   *
   * React useId() 可能生成包含冒号的字符串，
   * 这里替换成普通字符，避免 url(#id) 在部分环境下出现兼容问题。
   */
  const reactId = useId();
  const uniqueId = reactId.replace(/:/g, '');

  const lightGreenId = `hengfeng-light-green-${uniqueId}`;
  const blueRingId = `hengfeng-blue-ring-${uniqueId}`;
  const flowingLightId = `hengfeng-flowing-light-${uniqueId}`;
  const glowFilterId = `hengfeng-glow-filter-${uniqueId}`;

  // 八个外部图形路径
  const paths = [
    'M 188 265 L 369 265 L 333 229 L 225 229 Z',
    'M 178 419 L 305 291 L 254 291 L 178 368 Z',
    'M 279 355 L 279 536 L 243 500 L 243 391 Z',
    'M 305 419 L 433 547 L 382 547 L 305 470 Z',
    'M 550 445 L 369 445 L 405 482 L 513 482 Z',
    'M 561 291 L 433 419 L 484 419 L 561 342 Z',
    'M 459 355 L 459 175 L 495 211 L 495 319 Z',
    'M 305 164 L 433 291 L 433 240 L 356 164 Z',
  ];

  // 中间圆环
  const centerX = 369;
  const centerY = 355.24;
  const radius = 60;

  const circlePath = [
    `M ${centerX + radius} ${centerY}`,
    `a ${radius} ${radius} 0 1 0 ${-radius * 2} 0`,
    `a ${radius} ${radius} 0 1 0 ${radius * 2} 0`,
    'Z',
  ].join(' ');

  const normalizedSize = typeof size === 'number' ? `${size}px` : size;

  return (
    <div
      className={[
        'relative inline-block shrink-0 align-middle pointer-events-none',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      style={{
        width: normalizedSize,
        height: normalizedSize,
        ...style,
      }}
    >
      <svg
        className="block h-full w-full"
        viewBox={`${LOGO_VIEW_BOX.x} ${LOGO_VIEW_BOX.y} ${LOGO_VIEW_BOX.width} ${LOGO_VIEW_BOX.height}`}
        preserveAspectRatio="xMidYMid meet"
        xmlns="http://www.w3.org/2000/svg"
        role="img"
        aria-label="恒丰纸业 Logo"
      >
        <defs>
          {/* 外部绿色图形渐变 */}
          <linearGradient id={lightGreenId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#006227" />
            <stop offset="100%" stopColor="#00C853" />
          </linearGradient>

          {/* 中间圆环蓝色渐变 */}
          <linearGradient id={blueRingId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0D47A1" />
            <stop offset="50%" stopColor="#2979FF" />
            <stop offset="100%" stopColor="#01579B" />
          </linearGradient>

          {/* 圆环流光渐变 */}
          <linearGradient id={flowingLightId} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0" />
            <stop offset="50%" stopColor="#FFFFFF" stopOpacity="1" />
            <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0" />
          </linearGradient>

          {/* 流光发光效果 */}
          <filter
            id={glowFilterId}
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

        {/* 八个绿色图形 */}
        <g fill={`url(#${lightGreenId})`} fillOpacity="0.9" stroke="none">
          {paths.map((path, index) => (
            <path key={index} d={path} />
          ))}
        </g>

        {/* 中间蓝色圆环 */}
        <path
          d={circlePath}
          stroke={`url(#${blueRingId})`}
          strokeWidth="8"
          fill="none"
          strokeLinecap="round"
        />

        {/* 圆环流光 */}
        <path
          d={circlePath}
          stroke={`url(#${flowingLightId})`}
          strokeWidth="3"
          fill="none"
          strokeLinecap="round"
          filter={`url(#${glowFilterId})`}
          className="hengfeng-logo-flow"
          style={{
            mixBlendMode: 'screen',
            animationPlayState: isPaused ? 'paused' : 'running',
          }}
        />
      </svg>

      {/* Logo 中心自定义内容 */}
      {children && (
        <div
          className="pointer-events-auto absolute z-10"
          style={{
            /*
             * 中心坐标基本处于裁剪后 viewBox 的正中心，
             * 因此直接使用 50% 定位即可。
             */
            left: '50%',
            top: '50%',
            width: '30%',
            height: '30%',
            transform: 'translate(-50%, -50%)',
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
};

// 全局动画样式
const styles = `
  @keyframes hengfeng-logo-flow {
    0% {
      stroke-dasharray: 0, 1000;
      stroke-dashoffset: 0;
    }

    50% {
      stroke-dasharray: 200, 1000;
      stroke-dashoffset: -200;
    }

    100% {
      stroke-dasharray: 0, 1000;
      stroke-dashoffset: -1000;
    }
  }

  .hengfeng-logo-flow {
    animation: hengfeng-logo-flow 2s linear infinite;
  }
`;

if (typeof document !== 'undefined') {
  const styleId = 'hengfeng-logo-styles';
  const existingStyle = document.getElementById(styleId);

  if (!existingStyle) {
    const styleElement = document.createElement('style');

    styleElement.id = styleId;
    styleElement.textContent = styles;

    document.head.appendChild(styleElement);
  }
}

export default HengfengLogo;
