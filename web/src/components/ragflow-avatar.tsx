import { cn } from '@/lib/utils';
import * as AvatarPrimitive from '@radix-ui/react-avatar';
import { forwardRef, memo, useEffect, useRef, useState } from 'react';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';

const PREDEFINED_COLORS = [
  { from: '#4F6DEE', to: '#67BDF9' },
  { from: '#633897', to: '#CBA1FF' },
  { from: '#38A04D', to: '#93DCA2' },

  { from: '#C35F2B', to: '#EDB395' },
  { from: '#FF6B6B', to: '#FF8E53' }, // 5. 珊瑚红 (活力/醒目)
  // { from: '#F093FB', to: '#F5576C' }, // 7. 樱花粉 (柔和/年轻)
  { from: '#43E97B', to: '#38F9D7' }, // 8. 薄荷绿 (清爽/现代)
  { from: '#FA709A', to: '#FEE140' }, // 9. 落日黄 (温暖/渐变)
  // { from: '#30CFD0', to: '#330867' }, // 10. 赛博朋克 (深色/酷炫)
];

const getStringHash = (str: string): number => {
  if (typeof str !== 'string') return 0;

  const normalized = str.trim().toLowerCase();
  let hash = 104729;
  const seed = 0x9747b28c;

  for (let i = 0; i < normalized.length; i++) {
    hash ^= seed ^ normalized.charCodeAt(i);
    hash = (hash << 13) | (hash >>> 19);
    hash = (hash * 5 + 0x52dce72d) | 0;
  }

  return Math.abs(hash);
};

const getColorForName = (name: string): { from: string; to: string } => {
  const hash = getStringHash(name);
  const slicedColors = PREDEFINED_COLORS.slice(3);
  const index = hash % slicedColors.length;
  return slicedColors[index];
};

export const RAGFlowAvatar = memo(
  forwardRef<
    React.ElementRef<typeof AvatarPrimitive.Root>,
    React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Root> & {
      name?: string;
      avatar?: string;
      isPerson?: boolean;
      color?: number; // 👈 在这里添加这一行
    }
  >(({ name, avatar, isPerson = false, color, className, ...props }, ref) => {
    // Generate initial letter logic
    const isGreenSvgIcon = color === 6;
    const getInitials = (name?: string) => {
      if (color === 3) {
        return '参';
      }
      if (color === 6) {
        return '';
      }
      if (typeof name !== 'string' || !name) return '';
      const parts = name?.trim().split(/\s+/);
      if (parts.length === 1) {
        return parts[0][0].toUpperCase();
      }
      return parts[0][0].toUpperCase();
    };

    const initials = getInitials(name);
    // const { from, to } = name
    //   ? getColorForName(name)
    //   : { from: 'hsl(0, 0%, 30%)', to: 'hsla(0, 60%, 57%, 0.88)' };

    // 2. 颜色逻辑修改
    let from, to;

    // 判断 color 是否为数字 (1, 2, 3...)
    if (color === 6) {
      from = '#064E3B';
      to = '#047857';
    } else if (typeof color === 'number') {
      // 获取对应的颜色配置
      // 注意：数组索引是从 0 开始的，所以用 color - 1
      console.log(color);
      const colorConfig = PREDEFINED_COLORS[color - 1];

      if (colorConfig) {
        from = colorConfig.from;
        to = colorConfig.to;
      } else {
        // 如果数字超出了数组范围（比如传了 99），给个默认兜底色
        from = 'hsl(0, 0%, 30%)';
        to = 'hsl(0, 0%, 80%)';
      }
    }
    // 如果没有 color 数字，但有 name，走原来的随机颜色逻辑
    else if (name) {
      const colors = getColorForName(name);
      from = colors.from;
      to = colors.to;
    }
    // 都没有，走默认灰色
    else {
      from = 'hsl(0, 0%, 30%)';
      to = 'hsl(0, 0%, 80%)';
    }

    const fallbackRef = useRef<HTMLElement>(null);
    const [fontSize, setFontSize] = useState('0.875rem');

    // Calculate font size
    const calculateFontSize = () => {
      if (fallbackRef.current) {
        const containerWidth = fallbackRef.current.offsetWidth;
        const newSize = containerWidth * 0.6;
        setFontSize(`${newSize}px`);
      }
    };

    useEffect(() => {
      calculateFontSize();

      if (fallbackRef.current) {
        const resizeObserver = new ResizeObserver(() => {
          calculateFontSize();
        });

        resizeObserver.observe(fallbackRef.current);

        return () => {
          if (fallbackRef.current) {
            resizeObserver.unobserve(fallbackRef.current);
          }
          resizeObserver.disconnect();
        };
      }
    }, []);

    return (
      <Avatar
        ref={ref}
        {...props}
        className={cn(className, { 'rounded-md': !isPerson })}
      >
        <AvatarImage src={avatar} />
        {/* <AvatarFallback
          ref={(node) => {
            fallbackRef.current = node;
            calculateFontSize();
          }}
          className={cn(
            'bg-gradient-to-b',
            `from-[${from}] to-[${to}]`,
            'flex items-center justify-center',
            'text-white ',
            { 'rounded-md': !isPerson },
          )}
          style={{
            backgroundImage: `linear-gradient(to bottom, ${from}, ${to})`,
            fontSize: fontSize,
          }}
        >
          {initials}
        </AvatarFallback> */}
        <AvatarFallback
          ref={(node) => {
            fallbackRef.current = node;
            calculateFontSize();
          }}
          className={cn(
            'flex items-center justify-center overflow-hidden',
            isGreenSvgIcon
              ? 'bg-emerald-50 text-emerald-900 border border-emerald-100'
              : 'bg-gradient-to-b text-white',
            { 'rounded-md': !isPerson },
          )}
          style={{
            backgroundImage: isGreenSvgIcon
              ? 'none'
              : `linear-gradient(to bottom, ${from}, ${to})`,
            fontSize: isGreenSvgIcon ? undefined : fontSize,
          }}
        >
          {isGreenSvgIcon ? (
            <img
              src="/hf-remove-bg-io.png"
              alt="恒丰纸业"
              className="h-[72%] w-[72%] object-contain"
            />
          ) : (
            initials
          )}
        </AvatarFallback>
      </Avatar>
    );
  }),
);

RAGFlowAvatar.displayName = 'RAGFlowAvatar';
