import { Card, CardContent } from '@/components/ui/card';
import { Docagg } from '@/interfaces/database/chat';
import FileIcon from '../file-icon';
import NewDocumentLink from '../new-document-link';

export function ReferenceDocumentList({ list }: { list: Docagg[] }) {
  // 在组件外部或顶部定义颜色映射
  const getNumberColor = (num: number) => {
    const colors = [
      'bg-blue-500', // 1: 蓝色
      'bg-green-500', // 2: 绿色
      'bg-yellow-500', // 3: 黄色
      'bg-purple-500', // 4: 紫色
      'bg-pink-500', // 5: 粉色
      'bg-orange-500', // 6: 橙色
      'bg-teal-500', // 7: 青色
      'bg-red-500', // 8: 红色
      'bg-indigo-500', // 9: 靛蓝
      'bg-cyan-500', // 10: 青色
    ];
    return colors[(num - 1) % colors.length];
  };

  return (
    // <section className="flex gap-3 flex-wrap">
    //   {list.map((item) => (

    //     <Card key={item.doc_id} className="flex-1 min-w-[400px] max-w-[500px]">
    //       <CardContent className="p-1.5">
    //         <div className="flex items-center gap-2">
    //           <FileIcon id={item.doc_id} name={item.doc_name}></FileIcon>
    //           <NewDocumentLink
    //             documentId={item.doc_id}
    //             documentName={item.doc_name}
    //             prefix="document"
    //             link={item.url}
    //             className="flex-1 truncate text-text-sub-title-invert"
    //           >
    //             {item.doc_name}
    //           </NewDocumentLink>
    //         </div>
    //       </CardContent>
    //     </Card>
    //   ))}
    // </section>

    //   <section className="flex flex-col gap-3">
    //   {list.map((item) => (
    //     // 修改点：去掉 w-full，加上 w-[500px] (或者你想要的宽度)
    //     <Card key={item.doc_id} className="w-[500px]">
    //       <CardContent className="p-1.5">
    //         {/* 内容保持不变 */}
    //         <div className="flex items-center gap-2">
    //           <FileIcon id={item.doc_id} name={item.doc_name}></FileIcon>
    //           <NewDocumentLink
    //             documentId={item.doc_id}
    //             documentName={item.doc_name}
    //             prefix="document"
    //             link={item.url}
    //             className="flex-1 truncate text-text-sub-title-invert"
    //           >
    //             {item.doc_name}
    //           </NewDocumentLink>
    //         </div>
    //       </CardContent>
    //     </Card>
    //   ))}
    // </section>

    <section className="flex flex-col gap-3 w-full max-w-full">
      {list.map((item, i) => (
        <Card key={item.doc_id} className="w-[600px]">
          <CardContent className="p-1.5">
            <div className="flex items-center gap-2">
              <span
                className={`
                flex-shrink-0                 /* 关键：禁止压缩 */
                inline-flex items-center justify-center 
                w-5 h-5 
                text-xs font-medium text-white 
                rounded-full 
                ${getNumberColor(i + 1)}
              `}
              >
                {i + 1}
              </span>

              <FileIcon id={item.doc_id} name={item.doc_name}></FileIcon>
              {/* 核心修改区域 */}
              <NewDocumentLink
                documentId={item.doc_id}
                documentName={item.doc_name}
                prefix="document"
                link={item.url}
                // 关键类名：min-w-0 配合 flex-1
                // min-w-0 允许 flex 项目在内容过长时收缩到 0 宽度
                // flex-1 让它填满剩余空间
                className="flex-1 overflow-hidden truncate text-text-sub-title-invert"
              >
                {item.doc_name}
              </NewDocumentLink>
            </div>
          </CardContent>
        </Card>
      ))}
    </section>
  );
}
