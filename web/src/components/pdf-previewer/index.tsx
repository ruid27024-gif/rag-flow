import { IReferenceChunk } from '@/interfaces/database/chat';
import { IChunk } from '@/interfaces/database/knowledge';
import FileError from '@/pages/document-viewer/file-error';
import { Skeleton } from 'antd';
import { useEffect, useRef, useState } from 'react';
import {
  AreaHighlight,
  Highlight,
  IHighlight,
  PdfHighlighter,
  PdfLoader,
  Popup,
} from 'react-pdf-highlighter';

import {
  useGetChunkHighlights,
  useGetDocumentUrl,
} from '@/hooks/use-document-request';
import styles from './index.less';

interface IProps {
  chunk: IChunk | IReferenceChunk;
  documentId: string;
  visible: boolean;
}

const HighlightPopup = ({
  comment,
}: {
  comment: { text: string; emoji: string };
}) =>
  comment.text ? (
    <div className="Highlight__popup">
      {comment.emoji} {comment.text}
    </div>
  ) : null;

// const DocumentPreviewer = ({ chunk, documentId, visible }: IProps) => {
//   const getDocumentUrl = useGetDocumentUrl(documentId);
//   const { highlights: state, setWidthAndHeight } = useGetChunkHighlights(chunk);
//   const ref = useRef<(highlight: IHighlight) => void>(() => {});
//   const [loaded, setLoaded] = useState(false);
//   const url = getDocumentUrl();
//   const error = useCatchDocumentError(url);

//   const resetHash = () => {};

//   useEffect(() => {
//     setLoaded(visible);
//   }, [visible]);

//   useEffect(() => {
//     if (state.length > 0 && loaded) {
//       setLoaded(false);
//       ref.current(state[0]);
//     }
//   }, [state, loaded]);

//   return (
//     <div className={styles.documentContainer}>
//       <PdfLoader
//         url={url}
//         beforeLoad={<Skeleton active />}
//         workerSrc="/pdfjs-dist/pdf.worker.min.js"
//         errorMessage={<FileError>{error}</FileError>}
//         cMapUrl="/cmaps/"
//         cMapPacked={true}
//       >
//         {(pdfDocument) => {
//           pdfDocument.getPage(1).then((page) => {
//             const viewport = page.getViewport({ scale: 1 });
//             const width = viewport.width;
//             const height = viewport.height;
//             setWidthAndHeight(width, height);
//           });

//           return (
//             <PdfHighlighter
//               pdfDocument={pdfDocument}
//               enableAreaSelection={(event) => event.altKey}
//               onScrollChange={resetHash}
//               scrollRef={(scrollTo) => {
//                 ref.current = scrollTo;
//                 setLoaded(true);
//               }}
//               onSelectionFinished={() => null}
//               highlightTransform={(
//                 highlight,
//                 index,
//                 setTip,
//                 hideTip,
//                 viewportToScaled,
//                 screenshot,
//                 isScrolledTo,
//               ) => {
//                 const isTextHighlight = !Boolean(
//                   highlight.content && highlight.content.image,
//                 );

//                 const component = isTextHighlight ? (
//                   <Highlight
//                     isScrolledTo={isScrolledTo}
//                     position={highlight.position}
//                     comment={highlight.comment}
//                   />
//                 ) : (
//                   <AreaHighlight
//                     isScrolledTo={isScrolledTo}
//                     highlight={highlight}
//                     onChange={() => {}}
//                   />
//                 );

//                 return (
//                   <Popup
//                     popupContent={<HighlightPopup {...highlight} />}
//                     onMouseOver={(popupContent) =>
//                       setTip(highlight, () => popupContent)
//                     }
//                     onMouseOut={hideTip}
//                     key={index}
//                   >
//                     {component}
//                   </Popup>
//                 );
//               }}
//               highlights={state}
//             />
//           );
//         }}
//       </PdfLoader>
//     </div>
//   );
// };

// export default DocumentPreviewer;

import { getAuthorization } from '@/utils/authorization-util';

// 保留你原来 PdfLoader、PdfHighlighter 等组件的 import

const DocumentPreviewer = ({ chunk, documentId, visible }: IProps) => {
  const getDocumentUrl = useGetDocumentUrl(documentId);

  const { highlights: state, setWidthAndHeight } = useGetChunkHighlights(chunk);

  const ref = useRef<(highlight: IHighlight) => void>(() => {});

  const [loaded, setLoaded] = useState(false);

  // PDF.js 最终加载的 Blob URL
  const [previewUrl, setPreviewUrl] = useState('');

  const [previewLoading, setPreviewLoading] = useState(false);

  const [previewError, setPreviewError] = useState('');

  const sourceUrl = getDocumentUrl();

  const resetHash = () => {};

  /*
   * 使用项目登录凭证请求受保护的 PDF，
   * 然后转换为本地 Blob URL。
   */
  useEffect(() => {
    if (!visible || !documentId || !sourceUrl) {
      return;
    }

    const abortController = new AbortController();
    let objectUrl = '';

    const loadPdf = async () => {
      setPreviewLoading(true);
      setPreviewError('');
      setPreviewUrl('');

      try {
        const authorization = getAuthorization();

        const headers: HeadersInit = {};

        if (authorization) {
          headers.Authorization = authorization;
        }

        const response = await fetch(sourceUrl, {
          method: 'GET',
          headers,
          credentials: 'include',
          signal: abortController.signal,
        });

        if (!response.ok) {
          const responseText = await response.text();

          throw new Error(
            `获取 PDF 失败：${response.status} ${
              responseText || response.statusText
            }`,
          );
        }

        const contentType = response.headers.get('content-type') || '';

        /*
         * 防止后端返回 JSON 错误内容，
         * 然后被 PDF.js 当成 PDF 解析。
         */
        if (
          contentType.includes('application/json') ||
          contentType.includes('text/html')
        ) {
          const responseText = await response.text();

          throw new Error(`文件接口返回的不是 PDF：${responseText}`);
        }

        const responseBlob = await response.blob();

        if (abortController.signal.aborted) {
          return;
        }

        const pdfBlob = new Blob([responseBlob], {
          type: responseBlob.type || contentType || 'application/pdf',
        });

        objectUrl = URL.createObjectURL(pdfBlob);

        setPreviewUrl(objectUrl);
      } catch (error) {
        if (abortController.signal.aborted) {
          return;
        }

        console.error('加载高亮预览 PDF 失败：', error);

        setPreviewError(
          error instanceof Error ? error.message : '加载 PDF 失败',
        );
      } finally {
        if (!abortController.signal.aborted) {
          setPreviewLoading(false);
        }
      }
    };

    loadPdf();

    return () => {
      abortController.abort();

      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [documentId, sourceUrl, visible]);

  /*
   * 面板显示后，等待 PDFHighlighter 注册滚动方法。
   */
  useEffect(() => {
    setLoaded(visible);
  }, [visible]);

  /*
   * PDF 加载完成后滚动到第一个高亮区域。
   */
  useEffect(() => {
    if (state.length > 0 && loaded) {
      setLoaded(false);
      ref.current(state[0]);
    }
  }, [state, loaded]);

  if (!visible) {
    return null;
  }

  if (previewLoading) {
    return (
      <div className={styles.documentContainer}>
        <Skeleton active />
      </div>
    );
  }

  if (previewError) {
    return (
      <div className={styles.documentContainer}>
        <FileError>{previewError}</FileError>
      </div>
    );
  }

  if (!previewUrl) {
    return (
      <div className={styles.documentContainer}>
        <Skeleton active />
      </div>
    );
  }

  return (
    <div className={styles.documentContainer}>
      <PdfLoader
        // 这里不再传后端 URL，而是传已经鉴权获取的 Blob URL
        url={previewUrl}
        beforeLoad={<Skeleton active />}
        workerSrc="/pdfjs-dist/pdf.worker.min.js"
        errorMessage={<FileError>PDF 文件解析失败</FileError>}
        cMapUrl="/cmaps/"
        cMapPacked
      >
        {(pdfDocument) => {
          pdfDocument
            .getPage(1)
            .then((page) => {
              const viewport = page.getViewport({
                scale: 1,
              });

              setWidthAndHeight(viewport.width, viewport.height);
            })
            .catch((error) => {
              console.error('读取 PDF 第一页失败：', error);
            });

          return (
            <PdfHighlighter
              pdfDocument={pdfDocument}
              enableAreaSelection={(event) => event.altKey}
              onScrollChange={resetHash}
              scrollRef={(scrollTo) => {
                ref.current = scrollTo;
                setLoaded(true);
              }}
              onSelectionFinished={() => null}
              highlightTransform={(
                highlight,
                index,
                setTip,
                hideTip,
                viewportToScaled,
                screenshot,
                isScrolledTo,
              ) => {
                const isTextHighlight = !Boolean(
                  highlight.content && highlight.content.image,
                );

                const component = isTextHighlight ? (
                  <Highlight
                    isScrolledTo={isScrolledTo}
                    position={highlight.position}
                    comment={highlight.comment}
                  />
                ) : (
                  <AreaHighlight
                    isScrolledTo={isScrolledTo}
                    highlight={highlight}
                    onChange={() => {}}
                  />
                );

                return (
                  <Popup
                    key={index}
                    popupContent={<HighlightPopup {...highlight} />}
                    onMouseOver={(popupContent) =>
                      setTip(highlight, () => popupContent)
                    }
                    onMouseOut={hideTip}
                  >
                    {component}
                  </Popup>
                );
              }}
              highlights={state}
            />
          );
        }}
      </PdfLoader>
    </div>
  );
};

export default DocumentPreviewer;
