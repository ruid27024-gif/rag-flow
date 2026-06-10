import { api_host } from '@/utils/api';
import classNames from 'classnames';

interface IImage {
  id: string;
  className?: string;
  onClick?(): void;
}

const Image = ({ id, className, ...props }: IImage) => {
  return (
    <img
      {...props}
      src={`${api_host}/document/image/${id}`}
      alt=""
      className={classNames('max-w-[45vw] max-h-[40wh] block', className)}
    />
  );
};

export default Image;

// export const ImageWithPopover = ({ id }: { id: string }) => {
//   return (
//     <Popover>
//       <PopoverTrigger>
//         <Image id={id} className="max-h-[100px] inline-block"></Image>
//       </PopoverTrigger>
//       {/* <PopoverContent> */}
//       <PopoverContent
//         side="right"
//         align="start"
//         sideOffset={750}
//         className="p-0"
//       >
//         <Image id={id} className="max-w-[100px] object-contain"></Image>
//       </PopoverContent>
//     </Popover>
//   );
// };
// import { useState } from 'react';
// import { createPortal } from 'react-dom';
// import { X } from 'lucide-react';

// export const ImageWithPopover = ({ id }: { id?: string }) => {
//   const [open, setOpen] = useState(false);

//   if (!id) return null;

//   return (
//     <>
//       <button
//         type="button"
//         className="inline-block"
//         onClick={() => setOpen(true)}
//       >
//         <Image
//           id={id}
//           className="max-h-[100px] max-w-[160px] rounded-md object-contain"
//         />
//       </button>

//       {open &&
//         createPortal(
//           <div
//             className="
//               fixed
//               right-8
//               top-[96px]
//               bottom-8
//               z-[9999]
//               w-[40vw]
//               rounded-xl
//               border
//               border-slate-200
//               bg-white/95
//               p-4
//               shadow-2xl
//               backdrop-blur
//               dark:border-white/[0.08]
//               dark:bg-[#171717]/95
//             "
//           >
//             <button
//               type="button"
//               className="
//                 absolute
//                 right-3
//                 top-3
//                 z-10
//                 rounded-full
//                 p-1
//                 text-slate-500
//                 hover:bg-slate-100
//                 hover:text-slate-900
//                 dark:text-slate-400
//                 dark:hover:bg-white/[0.08]
//                 dark:hover:text-white
//               "
//               onClick={() => setOpen(false)}
//             >
//               <X size={18} />
//             </button>

//             <div className="flex h-full w-full items-center justify-center overflow-auto">
//               <Image
//                 id={id}
//                 className="max-h-full max-w-full rounded-md object-contain"
//               />
//             </div>
//           </div>,
//           document.body,
//         )}
//     </>
//   );
// };

import { X } from 'lucide-react';
import { createPortal } from 'react-dom';

export const ImageWithPopover = ({
  id,
  previewImageId,
  setPreviewImageId,
}: {
  id?: string;
  previewImageId?: string;
  setPreviewImageId: (id?: string) => void;
}) => {
  if (!id) {
    return null;
  }

  const open = previewImageId === id;

  return (
    <>
      <button
        type="button"
        className="inline-block"
        onClick={() => {
          console.log('preview image id:', id);
          setPreviewImageId(open ? undefined : id);
        }}
      >
        <Image
          id={id}
          className="max-h-[100px] max-w-[160px] rounded-md object-contain"
        />
      </button>

      {open &&
        createPortal(
          <div className="fixed right-8 top-[96px] bottom-8 z-[9999] w-[42vw] rounded-xl border border-slate-200 bg-white/95 p-4 shadow-2xl backdrop-blur dark:border-white/[0.08] dark:bg-[#171717]/95">
            <button
              type="button"
              className="absolute right-3 top-3 z-10 rounded-full p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.08] dark:hover:text-white"
              onClick={() => setPreviewImageId(undefined)}
            >
              <X size={18} />
            </button>

            {/* <div className="mb-2 pr-8 text-xs text-slate-400 break-all">
              image_id: {id}
            </div> */}

            <div className="flex h-[calc(100%-28px)] w-full items-center justify-center overflow-auto">
              <Image
                key={id}
                id={id}
                className="max-h-full max-w-full rounded-md object-contain"
              />
            </div>
          </div>,
          document.body,
        )}
    </>
  );
};
