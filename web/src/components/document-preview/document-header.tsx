import { formatBytes } from '@/utils/file-util';

type Props = {
  size: number;
  name: string;
  create_date: string;
};

const formatDateToYMDHMS = (dateStr: string) => {
  if (!dateStr) return '-';

  const date = new Date(dateStr);

  if (Number.isNaN(date.getTime())) {
    return dateStr;
  }

  const pad = (num: number) => String(num).padStart(2, '0');

  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hour = pad(date.getHours());
  const minute = pad(date.getMinutes());
  const second = pad(date.getSeconds());

  return `${year}/${month}/${day} ${hour}:${minute}:${second}`;
};

export default ({ size, name, create_date }: Props) => {
  const sizeName = formatBytes(size);
  const dateStr = formatDateToYMDHMS(create_date);
  return (
    <div>
      <h2 className="text-[16px]">{name}</h2>
      <div className="text-text-secondary text-[12px] pt-[5px]">
        大小：{sizeName} 上传时间：{dateStr}
      </div>
    </div>
  );
};
