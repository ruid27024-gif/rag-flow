import { Card, CardContent } from '@/components/ui/card';
import { Docagg } from '@/interfaces/database/chat';
import FileIcon from '../file-icon';
import NewDocumentLink from '../new-document-link';

export function ReferenceDocumentList({ list }: { list: Docagg[] }) {
  return (
    <section className="flex gap-3 flex-wrap">
      {list.map((item) => (
        // <Card key={item.doc_id}>
        <Card key={item.doc_id} className="w-[220px] flex-shrink-0">
          {/* <CardContent className="p-1.5 max-w-[200px] min-w-0"> */}
          <CardContent className="p-1.5">
            <div className="flex items-center gap-2">
              <FileIcon id={item.doc_id} name={item.doc_name}></FileIcon>
              <NewDocumentLink
                documentId={item.doc_id}
                documentName={item.doc_name}
                prefix="document"
                link={item.url}
                className="flex-1 truncate text-text-sub-title-invert"
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
