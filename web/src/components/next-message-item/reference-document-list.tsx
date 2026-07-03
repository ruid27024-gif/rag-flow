import FileIcon from '../file-icon';

// export function ReferenceDocumentList({ list }: { list: Docagg[] }) {
//   // 在组件外部或顶部定义颜色映射
//   const getNumberColor = (num: number) => {
//     const colors = [
//       'bg-blue-500', // 1: 蓝色
//       'bg-green-500', // 2: 绿色
//       'bg-yellow-500', // 3: 黄色
//       'bg-purple-500', // 4: 紫色
//       'bg-pink-500', // 5: 粉色
//       'bg-orange-500', // 6: 橙色
//       'bg-teal-500', // 7: 青色
//       'bg-red-500', // 8: 红色
//       'bg-indigo-500', // 9: 靛蓝
//       'bg-cyan-500', // 10: 青色
//     ];
//     return colors[(num - 1) % colors.length];
//   };

//   return (
//     <section className="flex flex-col gap-3 w-full max-w-full">
//       {list.map((item, i) => (
//         <Card key={item.doc_id} className="w-full max-w-[600px]">
//           <CardContent className="p-1.5">
//             <div className="flex items-center gap-2 w-full min-w-0">
//               <span
//                 className={`
//               flex-shrink-0
//               inline-flex items-center justify-center
//               w-5 h-5
//               text-xs font-medium text-white
//               rounded-full
//               bg-[#018B8D]
//             `}
//               >
//                 {i + 1}
//               </span>

//               <FileIcon id={item.doc_id} name={item.doc_name} />

//               <NewDocumentLink
//                 documentId={item.doc_id}
//                 documentName={item.doc_name}
//                 prefix="document"
//                 link={item.url}
//                 className="text-text-sub-title-invert"
//               >
//                 {item.doc_name}
//               </NewDocumentLink>
//             </div>
//           </CardContent>
//         </Card>
//       ))}
//     </section>
//   );
// }

// const PANEL_WIDTH = 330; // 右侧实际面板宽度
// const MAIN_RIGHT_SPACE = 330; // 主内容只让出 200px

// export function ReferenceDocumentList({
//   list,
// }: {
//   list: Array<{
//     doc_id: string;
//     doc_name: string;
//     url?: string;
//   }>;
// }) {
//   const [open, setOpen] = useState(false);

//   useEffect(() => {
//     const el = document.getElementById('chat-main-content');

//     if (!el) return;

//     if (open) {
//       // 主内容只移动/让出 200px
//       el.style.marginRight = `${MAIN_RIGHT_SPACE}px`;
//     } else {
//       el.style.marginRight = '';
//     }

//     return () => {
//       el.style.marginRight = '';
//     };
//   }, [open]);

//   if (!list || list.length === 0) {
//     return null;
//   }

//   return (
//     <>
//       {/* 底部来源按钮 */}
//       <section className="mt-3 flex w-full max-w-full">
//         <button
//           type="button"
//           onClick={() => setOpen(true)}
//           className="
//             inline-flex
//             items-center
//             gap-2
//             rounded-md
//             px-2
//             py-1.5
//             text-sm
//             text-gray-500
//             transition-colors
//             hover:bg-gray-100
//             hover:text-gray-900
//             dark:text-gray-400
//             dark:hover:bg-gray-800
//             dark:hover:text-gray-100
//           "
//         >
//           <span className="flex items-center -space-x-2">
//             {list.slice(0, 3).map((item, index) => (
//               <span
//                 key={item.doc_id || index}
//                 className="
//                   flex
//                   h-6
//                   w-6
//                   items-center
//                   justify-center
//                   rounded-full
//                   border
//                   border-white
//                   bg-gray-100
//                   shadow-sm
//                   dark:border-gray-900
//                   dark:bg-gray-800
//                 "
//               >
//                 <span className="scale-75">
//                   <FileIcon id={item.doc_id} name={item.doc_name} />
//                 </span>
//               </span>
//             ))}

//             {list.length > 3 && (
//               <span
//                 className="
//                   flex
//                   h-6
//                   min-w-6
//                   items-center
//                   justify-center
//                   rounded-full
//                   border
//                   border-white
//                   bg-gray-200
//                   px-1.5
//                   text-[10px]
//                   font-medium
//                   text-gray-600
//                   shadow-sm
//                   dark:border-gray-900
//                   dark:bg-gray-700
//                   dark:text-gray-200
//                 "
//               >
//                 +{list.length - 3}
//               </span>
//             )}
//           </span>

//           <span>{list.length}篇来源</span>
//         </button>
//       </section>

//       {/* 右侧来源面板 */}
//       {open && (
//         <aside
//           onWheel={(e) => e.stopPropagation()}
//           className="
//             fixed
//             right-0
//             top-0
//             z-50
//             flex
//             h-[100dvh]
//             w-[320px]
//             max-w-[85vw]
//             flex-col
//             overflow-hidden
//             border-l
//             border-gray-200
//             bg-transparent
//             shadow-none
//             dark:border-gray-800
//           "
//           style={{
//             width: PANEL_WIDTH,
//           }}
//         >
//           {/* 面板头部 */}
//           <div
//             className="
//               flex
//               shrink-0
//               items-center
//               justify-between
//               border-b
//               border-gray-100
//               px-4
//               py-3
//               dark:border-gray-800
//             "
//           >
//             <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
//               参考来源 ({list.length})
//             </div>

//             <button
//               type="button"
//               onClick={() => setOpen(false)}
//               className="
//                 flex
//                 h-7
//                 w-7
//                 items-center
//                 justify-center
//                 rounded-md
//                 text-lg
//                 text-gray-400
//                 hover:bg-gray-100
//                 hover:text-gray-700
//                 dark:hover:bg-gray-800
//                 dark:hover:text-gray-200
//               "
//             >
//               ×
//             </button>
//           </div>

//           {/* 来源列表：自己滚动，不影响主页 */}
//           <div
//             onWheel={(e) => e.stopPropagation()}
//             className="
//               flex-1
//               overflow-y-auto
//               overscroll-contain
//               px-4
//               py-4
//             "
//           >
//             <div className="space-y-4">
//               {list.map((item, i) => (
//                 <div key={item.doc_id || i} className="flex gap-3">
//                   {/* 序号 */}
//                   <span
//                     className="
//                       mt-0.5
//                       flex
//                       h-5
//                       w-5
//                       shrink-0
//                       items-center
//                       justify-center
//                       rounded-full
//                       bg-[#018B8D]
//                       text-[11px]
//                       font-medium
//                       text-white
//                     "
//                   >
//                     {i + 1}
//                   </span>

//                   <div className="min-w-0 flex-1">
//                     {/* 文档标题 */}
//                     <div className="flex min-w-0 items-start gap-2">
//                       <div className="mt-0.5 shrink-0">
//                         <FileIcon id={item.doc_id} name={item.doc_name} />
//                       </div>

//                       <NewDocumentLink
//                         documentId={item.doc_id}
//                         documentName={item.doc_name}
//                         prefix="document"
//                         link={item.url}
//                         className="
//                           line-clamp-2
//                           text-sm
//                           font-semibold
//                           leading-5
//                           text-gray-900
//                           hover:text-[#018B8D]
//                           dark:text-gray-100
//                           dark:hover:text-[#018B8D]
//                         "
//                       >
//                         {item.doc_name}
//                       </NewDocumentLink>
//                     </div>

//                     {/* 来源地址 / 类型 */}
//                     <div
//                       className="
//                         mt-1
//                         truncate
//                         pl-7
//                         text-xs
//                         text-gray-400
//                         dark:text-gray-500
//                       "
//                     >
//                       {item.url || '本地文档'}
//                     </div>
//                   </div>
//                 </div>
//               ))}
//             </div>
//           </div>
//         </aside>
//       )}
//     </>
//   );
// }

// import { useEffect, useState } from 'react';

const PANEL_WIDTH = 320;
const MAIN_RIGHT_SPACE = 200;

type ReferenceDocumentItem = {
  // doc_aggs 字段
  doc_id?: string;
  doc_name?: string;
  count?: number;
  url?: string | null;

  // chunk 字段
  id?: string;
  content?: string;
  dataset_id?: string;
  document_id?: string;
  document_name?: string;
  docnm_kwd?: string;
  positions?: any[];
  image_id?: string;
  doc_type?: string;

  // 合并后的 chunks
  chunks?: any[];
};

export function ReferenceDocumentList({
  list,
  onOpenReferencePanel,
}: {
  list: ReferenceDocumentItem[];
  onOpenReferencePanel?: (list: ReferenceDocumentItem[]) => void;
}) {
  if (!list || list.length === 0) {
    return null;
  }

  const getDocumentId = (item: ReferenceDocumentItem) => {
    return item.document_id || item.doc_id || '';
  };

  const getDocumentName = (item: ReferenceDocumentItem) => {
    return item.document_name || item.doc_name || item.docnm_kwd || '';
  };

  return (
    <section className="mt-3 flex w-full max-w-full">
      <button
        type="button"
        onClick={() => onOpenReferencePanel?.(list)}
        className="
          inline-flex items-center gap-2 rounded-md px-2 py-1.5
          text-sm text-gray-500 transition-colors
          hover:bg-gray-100 hover:text-gray-900
          dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100
        "
      >
        <span className="flex items-center -space-x-2">
          {list.slice(0, 3).map((item, index) => {
            const docId = getDocumentId(item);
            const docName = getDocumentName(item);

            return (
              <span
                key={item.id || docId || index}
                className="
                  flex h-6 w-6 items-center justify-center rounded-full
                  border border-white bg-gray-100 shadow-sm
                  dark:border-gray-900 dark:bg-gray-800
                "
              >
                <span className="scale-75">
                  <FileIcon id={docId} name={docName} />
                </span>
              </span>
            );
          })}

          {list.length > 3 && (
            <span
              className="
                flex h-6 min-w-6 items-center justify-center rounded-full
                border border-white bg-gray-200 px-1.5
                text-[10px] font-medium text-gray-600 shadow-sm
                dark:border-gray-900 dark:bg-gray-700 dark:text-gray-200
              "
            >
              +{list.length - 3}
            </span>
          )}
        </span>

        <span>{list.length}篇来源</span>
      </button>
    </section>
  );
}
