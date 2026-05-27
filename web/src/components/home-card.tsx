import { RAGFlowAvatar } from '@/components/ragflow-avatar';
import { Card, CardContent } from '@/components/ui/card';
// import { formatDate } from '@/utils/date';
import { ReactNode } from 'react';

interface IProps {
  data: {
    name: string;
    description?: string;
    avatar?: string;
    update_time?: string | number;
  };
  onClick?: () => void;
  moreDropdown: React.ReactNode;
  sharedBadge?: ReactNode;
  icon?: React.ReactNode;
}
export function HomeCard({
  data,
  onClick,
  moreDropdown,
  sharedBadge,
  icon,
}: IProps) {
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');

    // 新增：获取时、分、秒并补零
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');

    // 拼接成你想要的格式，这里以 YYYY/MM/DD HH:mm:ss 为例
    return `${year}/${month}/${day} ${hours}:${minutes}:${seconds}`;
  };
  return (
    <Card
      onClick={() => {
        // navigateToSearch(data?.id);
        onClick?.();
      }}
    >
      <CardContent className="p-4 flex gap-2 items-start group h-full w-full hover:shadow-md">
        <div className="flex justify-between mb-4">
          <RAGFlowAvatar
            className="w-[32px] h-[32px]"
            avatar={data.avatar}
            name={data.name}
            color={data.color}
          />
        </div>
        <div className="flex flex-col justify-between gap-1 flex-1 h-full w-[calc(100%-50px)]">
          <section className="flex justify-between">
            <section className="flex flex-1 min-w-0 gap-1 items-center">
              <div className="text-base font-bold leading-snug truncate">
                {data.name}
              </div>
              {icon}
            </section>
            {moreDropdown}
          </section>

          <section className="flex flex-col gap-1 mt-1">
            <div className="whitespace-nowrap overflow-hidden text-ellipsis">
              {data.description}
            </div>
            <div className="flex justify-between items-center">
              <p className="text-sm opacity-80 whitespace-nowrap">
                {formatDate(data.update_time)}
              </p>
              {sharedBadge}
            </div>
          </section>
        </div>
      </CardContent>
    </Card>
  );
}
