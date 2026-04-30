import { useFetchUserInfo } from '@/hooks/use-user-setting-request';
import { PropsWithChildren } from 'react';

export function SharedBadge({ children }: PropsWithChildren) {
  const { data: userInfo } = useFetchUserInfo();

  if (typeof children === 'string' && userInfo.nickname === children) {
    return null;
  }

  // return <span className="bg-bg-card rounded-sm px-1 text-xs">{children}</span>;

  return (
    <span
      className="inline-block max-w-[100px] truncate align-middle bg-bg-card rounded-sm px-1 text-xs"
      title={typeof children === 'string' ? children : ''} // 加上 title 属性，鼠标悬停看全名
    >
      {children}
    </span>
  );
}
