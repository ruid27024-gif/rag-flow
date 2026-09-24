// src/pages/chat/welcome-cloud-bg.tsx
import { cn } from '@/lib/utils';
import React, { useState } from 'react';

const random = (min: number, max: number) => Math.random() * (max - min) + min;

const makeBlueClouds = () => {
  const blueColors = [
    [72, 111, 178],
    [102, 138, 195],
    [128, 162, 210],
  ];

  const whiteColors = [
    [245, 249, 254],
    [235, 242, 252],
    [252, 253, 255],
  ];

  return Array.from({ length: 20 }).map((_, index) => {
    const isBaseCloud = index < 2;
    const isBlue = isBaseCloud ? true : Math.random() < 0.85;
    const palette = isBlue ? blueColors : whiteColors;
    const color = palette[Math.floor(Math.random() * palette.length)];

    const dir = Math.random() > 0.5 ? 'right' : 'left';
    const duration = random(28, 45);
    const delay = random(-duration, 0);
    const scaleMax = random(1.15, 1.45);
    const scaleMin = random(0.7, 0.9);

    return {
      top: isBaseCloud ? random(-10, 30) : random(-30, 90),
      width: isBaseCloud ? random(60, 85) : random(28, 60),
      height: isBaseCloud ? random(55, 75) : random(28, 60),
      opacity: 1,
      backgroundColor: `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${
        isBlue ? random(0.35, 0.6) : random(0.5, 0.8)
      })`,
      dir,
      duration,
      delay,
      scaleMax,
      scaleMin,
      isBaseCloud,
      isBlue,
    };
  });
};

const WelcomeCloudBg: React.FC<{ className?: string }> = ({ className }) => {
  const [blueClouds] = useState(makeBlueClouds);

  return (
    <>
      <div
        className={cn(
          // 👇 关键：fixed → absolute，-z-10 去掉
          'pointer-events-none absolute inset-0 overflow-hidden dark:hidden',
          className,
        )}
      >
        <div className="absolute inset-0 bg-[#EDF2FA]" />

        <div className="absolute inset-0 blur-[80px]">
          {/* 左上角专属蓝云 */}
          <div
            className="absolute rounded-full"
            style={{
              top: '-15%',
              left: '-10%',
              width: '48%',
              height: '48%',
              backgroundColor: 'rgba(37, 99, 235, 0.65)',
              animation: 'breatheA 15s ease-in-out infinite',
            }}
          />

          {blueClouds.map((cloud, index) => {
            if (cloud.isBaseCloud) {
              return (
                <div
                  key={index}
                  className="absolute rounded-full"
                  style={{
                    top: `${cloud.top}%`,
                    left: index === 0 ? '25%' : '55%',
                    width: `${cloud.width}%`,
                    height: `${cloud.height}%`,
                    opacity: cloud.opacity,
                    backgroundColor: cloud.backgroundColor,
                  }}
                />
              );
            }

            return (
              <div
                key={index}
                className="absolute rounded-full"
                style={
                  {
                    top: `${cloud.top}%`,
                    left: 0,
                    width: `${cloud.width}vw`,
                    height: `${cloud.height}vw`,
                    opacity: cloud.opacity,
                    backgroundColor: cloud.backgroundColor,
                    animation: `${
                      cloud.dir === 'right' ? 'blowRight' : 'blowLeft'
                    } ${cloud.duration}s linear infinite`,
                    animationDelay: `${cloud.delay}s`,
                    willChange: 'transform',
                    '--scaleMin': cloud.scaleMin,
                    '--scaleMax': cloud.scaleMax,
                  } as React.CSSProperties
                }
              />
            );
          })}

          <div
            className="absolute h-[65%] w-[55%] rounded-full bg-[#f3f8fe]/95 animate-[breatheA_14s_ease-in-out_infinite]"
            style={{ top: '18%', left: '18%' }}
          />
          <div
            className="absolute h-[45%] w-[42%] rounded-full bg-[#f5f9fe]/90 animate-[breatheB_18s_ease-in-out_infinite]"
            style={{ top: '-8%', left: '-6%' }}
          />
          <div
            className="absolute h-[50%] w-[50%] rounded-full bg-[#f5f9fe]/90 animate-[breatheA_16s_ease-in-out_infinite]"
            style={{ bottom: '2%', right: '-4%' }}
          />
        </div>

        <div
          className="absolute inset-0
            bg-[repeating-linear-gradient(to_right,transparent_0,transparent_98px,rgba(119,151,199,0.08)_99px,transparent_100px),repeating-linear-gradient(to_bottom,transparent_0,transparent_98px,rgba(119,151,199,0.06)_99px,transparent_100px)]"
        />
      </div>

      <style>{`
        @keyframes blowRight {
          0%   { transform: translateX(-100vw) scale(var(--scaleMin, 0.85)); }
          50%  { transform: translateX(50vw)   scale(var(--scaleMax, 1.25)); }
          100% { transform: translateX(200vw)  scale(var(--scaleMin, 0.85)); }
        }
        @keyframes blowLeft {
          0%   { transform: translateX(200vw)  scale(var(--scaleMin, 0.85)); }
          50%  { transform: translateX(50vw)   scale(var(--scaleMax, 1.25)); }
          100% { transform: translateX(-100vw) scale(var(--scaleMin, 0.85)); }
        }
        @keyframes breatheA {
          0%   { transform: scale(1.15); }
          50%  { transform: scale(0.9); }
          100% { transform: scale(1.15); }
        }
        @keyframes breatheB {
          0%   { transform: scale(0.92); }
          50%  { transform: scale(1.15); }
          100% { transform: scale(0.92); }
        }
      `}</style>
    </>
  );
};

export default WelcomeCloudBg;
