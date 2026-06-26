import Image from '@/components/image';
import SvgIcon from '@/components/svg-icon';
import { IReference, IReferenceChunk } from '@/interfaces/database/chat';
import { getExtension } from '@/utils/document-util';
import DOMPurify from 'dompurify';
import { useCallback, useEffect, useMemo } from 'react';
import Markdown from 'react-markdown';
import reactStringReplace from 'react-string-replace';
import SyntaxHighlighter from 'react-syntax-highlighter';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import { visitParents } from 'unist-util-visit-parents';

import { useTranslation } from 'react-i18next';

import { HomeIcon } from '@/components/svg-icon';
import 'katex/dist/katex.min.css'; // `rehype-katex` does not import the CSS for you

import { useFetchDocumentThumbnailsByIds } from '@/hooks/use-document-request';
import {
  currentReg,
  preprocessLaTeX,
  replaceTextByOldReg,
  replaceThinkToSection,
  showImage,
} from '@/utils/chat';
import classNames from 'classnames';
import { omit } from 'lodash';
import { pipe } from 'lodash/fp';
import { Button } from '../ui/button';
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from '../ui/hover-card';
import styles from './index.less';

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

const getChunkIndex = (match: string) => Number(match);
// TODO: The display of the table is inconsistent with the display previously placed in the MessageItem.
const MarkdownContent = ({
  reference,
  clickDocumentButton,
  content,
}: {
  content: string;
  loading: boolean;
  reference: IReference;
  clickDocumentButton?: (documentId: string, chunk: IReferenceChunk) => void;
}) => {
  // console.log("------------------MarkdownContent-----------------------")
  // console.log(content)
  // console.log(reference)

  const { t } = useTranslation();
  const { setDocumentIds, data: fileThumbnails } =
    useFetchDocumentThumbnailsByIds();
  // const contentWithCursor = useMemo(() => {
  //   let text = DOMPurify.sanitize(content, {
  //     ADD_TAGS: ['think', 'section'],
  //     ADD_ATTR: ['class'],
  //   });

  //   // let text = content;
  //   if (text === '') {
  //     text = t('chat.searching');
  //   }
  //   const nextText = replaceTextByOldReg(text);
  //   return pipe(replaceThinkToSection, preprocessLaTeX)(nextText);
  // }, [content, t]);

  //   const replaceSourceHeading = useCallback((text: string) => {
  //   return text
  //     .replace(
  //       /(【(?:从[^】]+来说|综合总结)】)/g,
  //       (_match, heading) => {
  //         return `\n\n<source-heading>${heading}</source-heading>\n\n`;
  //       },
  //     )
  //     .replace(/^\n+/, '');
  // }, []);

  // const replaceSourceHeading = useCallback((text: string) => {
  //   return text
  //     .replace(
  //       /(【(?:从[^】]+来说|综合总结)】)/g,
  //       (_match, heading) => {
  //         const displayHeading = heading
  //           .replace(/^【从(.+?)来说】$/, '$1')
  //           .replace(/^【(.+?)】$/, '$1');

  //         return `\n\n<source-heading>${displayHeading}</source-heading>\n\n`;
  //       },
  //     )
  //     .replace(/^\n+/, '');
  // }, []);

  const replaceSourceHeading = useCallback((text: string) => {
    const replaceHeadingOutsideThink = (segment: string) => {
      return segment.replace(
        /(【(?:从[^】]+来说|综合总结)】)/g,
        (_match, heading) => {
          const displayHeading = heading
            .replace(/^【从(.+?)来说】$/, '$1')
            .replace(/^【(.+?)】$/, '$1');

          return `\n\n<source-heading>${displayHeading}</source-heading>\n\n`;
        },
      );
    };

    let result = '';
    let cursor = 0;
    const lowerText = text.toLowerCase();

    while (cursor < text.length) {
      const thinkStart = lowerText.indexOf('<think', cursor);

      // 后面没有 think，剩余内容全部是正文，正常替换
      if (thinkStart === -1) {
        result += replaceHeadingOutsideThink(text.slice(cursor));
        break;
      }

      // think 前面的正文，正常替换
      result += replaceHeadingOutsideThink(text.slice(cursor, thinkStart));

      const openTagEnd = text.indexOf('>', thinkStart);

      // 流式场景：<think 标签还没完整，后面都按 think 原样保留
      if (openTagEnd === -1) {
        result += text.slice(thinkStart);
        break;
      }

      const closeTagStart = lowerText.indexOf('</think>', openTagEnd + 1);

      // 流式场景：think 还没闭合，think 到结尾都原样保留
      if (closeTagStart === -1) {
        result += text.slice(thinkStart);
        break;
      }

      // 完整 think 块，原样保留，不替换里面的标题
      result += text.slice(thinkStart, closeTagStart + '</think>'.length);

      cursor = closeTagStart + '</think>'.length;
    }

    return result.replace(/^\n+/, '');
  }, []);

  const removeEmptySourceSections = (text: string) =>
    text.replace(
      /\n*<source-heading>[^<]+<\/source-heading>\s*(?:该来源未检索到相关内容。|该来源未检索到相关内容)\s*/g,
      '\n\n',
    );

  // const contentWithCursor = useMemo(() => {
  //   let text = content || '';

  //   if (text === '') {
  //     text = t('chat.searching');
  //   }

  //   text = replaceSourceHeading(text);

  //   text = DOMPurify.sanitize(text, {
  //     ADD_TAGS: ['think', 'section', 'source-heading'],
  //     ADD_ATTR: ['class'],
  //   });

  //   const nextText = replaceTextByOldReg(text);

  //   return pipe(replaceThinkToSection, preprocessLaTeX)(nextText);
  // }, [content, t, replaceSourceHeading]);

  const contentWithCursor = useMemo(() => {
    let text = content || '';

    if (text === '') {
      text = t('chat.searching');
    }

    // 只替换 think 外面的来源标题
    text = replaceSourceHeading(text);
    text = removeEmptySourceSections(text);

    text = DOMPurify.sanitize(text, {
      ADD_TAGS: ['think', 'section', 'source-heading'],
      ADD_ATTR: ['class'],
    });

    const nextText = replaceTextByOldReg(text);

    return pipe(replaceThinkToSection, preprocessLaTeX)(nextText);
  }, [content, t, replaceSourceHeading]);

  useEffect(() => {
    const docAggs = reference?.doc_aggs;
    setDocumentIds(Array.isArray(docAggs) ? docAggs.map((x) => x.doc_id) : []);
  }, [reference, setDocumentIds]);

  const handleDocumentButtonClick = useCallback(
    (
      documentId: string,
      chunk: IReferenceChunk,
      isPdf: boolean,
      documentUrl?: string,
    ) =>
      () => {
        if (!isPdf) {
          if (!documentUrl) {
            return;
          }
          window.open(documentUrl, '_blank');
        } else {
          clickDocumentButton?.(documentId, chunk);
        }
      },
    [clickDocumentButton],
  );

  const rehypeWrapReference = () => {
    return function wrapTextTransform(tree: any) {
      visitParents(tree, 'text', (node, ancestors) => {
        const latestAncestor = ancestors.at(-1);
        if (
          latestAncestor.tagName !== 'custom-typography' &&
          latestAncestor.tagName !== 'code'
        ) {
          node.type = 'element';
          node.tagName = 'custom-typography';
          node.properties = {};
          node.children = [{ type: 'text', value: node.value }];
        }
      });
    };
  };

  // 直接对应原始 chunks 列表的索引
  const getReferenceInfo = useCallback(
    (chunkIndex: number) => {
      const chunks = reference?.chunks ?? [];
      const chunkItem = chunks[chunkIndex];
      // const document = reference?.doc_aggs?.find(
      //   (x) => x?.doc_id === chunkItem?.document_id,
      // );
      const docIndex = reference?.doc_aggs?.findIndex(
        (x) => x?.doc_id === chunkItem?.document_id,
      );
      const document = reference?.doc_aggs?.[docIndex];
      const documentId = document?.doc_id;
      const documentUrl = document?.url;
      const fileThumbnail = documentId ? fileThumbnails[documentId] : '';
      const fileExtension = documentId ? getExtension(document?.doc_name) : '';
      const imageId = chunkItem?.image_id;

      return {
        documentUrl,
        fileThumbnail,
        fileExtension,
        imageId,
        chunkItem,
        documentId,
        document,
        docIndex, // 返回索引
      };
    },
    [fileThumbnails, reference],
  );

  const getPopoverContent = useCallback(
    (chunkIndex: number) => {
      const {
        documentUrl,
        fileThumbnail,
        fileExtension,
        imageId,
        chunkItem,
        documentId,
        document,
      } = getReferenceInfo(chunkIndex);

      return (
        <div key={chunkItem?.id} className="flex gap-2">
          {imageId && (
            <HoverCard>
              <HoverCardTrigger>
                <Image
                  id={imageId}
                  className={styles.referenceChunkImage}
                ></Image>
              </HoverCardTrigger>
              <HoverCardContent>
                <Image
                  id={imageId}
                  className={styles.referenceImagePreview}
                ></Image>
              </HoverCardContent>
            </HoverCard>
          )}
          <div className={'space-y-2 max-w-[40vw]'}>
            <div
              dangerouslySetInnerHTML={{
                __html: DOMPurify.sanitize(chunkItem?.content ?? ''),
              }}
              className={classNames(styles.chunkContentText)}
            ></div>
            {documentId && (
              <section className="flex gap-1">
                {fileThumbnail ? (
                  <img
                    src={fileThumbnail}
                    alt=""
                    className={styles.fileThumbnail}
                  />
                ) : (
                  <SvgIcon
                    name={`file-icon/${fileExtension}`}
                    width={24}
                  ></SvgIcon>
                )}
                <Button
                  variant="link"
                  className={'text-wrap p-0'}
                  onClick={handleDocumentButtonClick(
                    documentId,
                    chunkItem,
                    fileExtension === 'pdf',
                    documentUrl,
                  )}
                >
                  {document?.doc_name}
                </Button>
              </section>
            )}
          </div>
        </div>
      );
    },
    [getReferenceInfo, handleDocumentButtonClick],
  );

  const renderReference = useCallback(
    (text: string) => {
      let replacedText = reactStringReplace(text, currentReg, (match, i) => {
        // 从匹配字符串中提取数字
        const chunkIndex = getChunkIndex(match);

        const {
          documentUrl,
          fileExtension,
          imageId,
          chunkItem,
          documentId,
          docIndex,
        } =
          // 调用 getReferenceInfo 函数，根据 chunkIndex 获取：
          getReferenceInfo(chunkIndex);

        const docType = chunkItem?.doc_type;

        return showImage(docType) ? (
          <section>
            <Image
              id={imageId}
              className={styles.referenceInnerChunkImage}
              onClick={
                documentId
                  ? handleDocumentButtonClick(
                      documentId,
                      chunkItem,
                      fileExtension === 'pdf',
                      documentUrl,
                    )
                  : () => {}
              }
            ></Image>
            {/* <span className="text-accent-primary"> {imageId}</span> */}
          </section>
        ) : (
          <HoverCard key={i}>
            <HoverCardTrigger>
              {/* <CircleAlert className="size-4 inline-block" /> */}
              {/* <span className="inline-flex items-center justify-center w-5 h-5 text-xs font-medium text-white bg-accent-primary rounded-full">
                {docIndex + 1} 
              </span> */}

              <span
                className={`inline-flex items-center justify-center w-5 h-5 text-xs font-medium text-white rounded-full ${getNumberColor(docIndex + 1)}`}
              >
                {docIndex + 1}
              </span>
            </HoverCardTrigger>
            <HoverCardContent className="max-w-3xl">
              {getPopoverContent(chunkIndex)}
            </HoverCardContent>
          </HoverCard>
        );
      });

      // replacedText = reactStringReplace(replacedText, curReg, (match, i) => (
      //   <span className={styles.cursor} key={i}></span>
      // ));

      return replacedText;
    },
    [getPopoverContent, getReferenceInfo, handleDocumentButtonClick],
  );

  return (
    // <Markdown
    //   rehypePlugins={[rehypeWrapReference, rehypeKatex, rehypeRaw]}
    //   remarkPlugins={[remarkGfm, remarkMath]}
    //   className={styles.markdownContentWrapper}
    //   components={
    //     {
    //       'custom-typography': ({ children }: { children: string }) =>
    //         renderReference(children),
    //       code(props: any) {
    //         const { children, className, ...rest } = props;
    //         const restProps = omit(rest, 'node');
    //         const match = /language-(\w+)/.exec(className || '');
    //         return match ? (
    //           <SyntaxHighlighter
    //             {...restProps}
    //             PreTag="div"
    //             language={match[1]}
    //             wrapLongLines
    //           >
    //             {String(children).replace(/\n$/, '')}
    //           </SyntaxHighlighter>
    //         ) : (
    //           <code
    //             {...restProps}
    //             className={classNames(className, 'text-wrap')}
    //           >
    //             {children}
    //           </code>
    //         );
    //       },
    //     } as any
    //   }
    // >
    //   {contentWithCursor}
    // </Markdown>

    <Markdown
      rehypePlugins={[rehypeWrapReference, rehypeKatex, rehypeRaw]}
      remarkPlugins={[remarkGfm, remarkMath]}
      className={styles.markdownContentWrapper}
      components={
        {
          // 1. 优化【来源标题】的样式，并加入图标
          'source-heading': ({ children }: { children: React.ReactNode }) => (
            <div
              className="
        mt-8 mb-4 
        flex items-center gap-3
        text-lg font-extrabold 
        text-green-900 dark:text-green-500
      "
            >
              {/* 👇 在这里插入你的知识库图标 */}
              <HomeIcon
                name="datasets"
                width="24" // 标题里的图标建议稍微小一点，比如 24px
              />

              {/* 标题文字 */}
              <span>{children}</span>
            </div>
          ),

          // 2. 优化【自定义排版/引用包裹】的渲染逻辑
          'custom-typography': ({ children }: { children: string }) => {
            return renderReference(children);
          },

          // 3. 优化【代码块】的样式
          code(props: any) {
            const { children, className, ...rest } = props;
            const restProps = omit(rest, 'node');
            const match = /language-(\w+)/.exec(className || '');

            return match ? (
              <SyntaxHighlighter
                {...restProps}
                PreTag="div"
                language={match[1]}
                wrapLongLines
                className="rounded-md my-2"
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            ) : (
              <code
                {...restProps}
                className={classNames(
                  className,
                  'text-wrap',
                  'px-1.5 py-0.5',
                  'bg-gray-100 dark:bg-gray-800',
                  'rounded',
                  'text-sm',
                )}
              >
                {children}
              </code>
            );
          },
        } as any
      }
    >
      {contentWithCursor}
    </Markdown>
  );
};

export default MarkdownContent;
