import React from 'react';
import { useParams } from 'react-router-dom';
import { useNavigate } from 'umi';
import FileTreePreview from './FileTreePreview';

const IndexPage: React.FC = () => {
  const params = useParams();
  const navigate = useNavigate();

  const kbId = params.id as string;

  return (
    <div style={{ padding: 24 }}>
      <FileTreePreview
        open={true}
        onClose={() => navigate('/admin-files')}
        kbId={kbId}
      />
    </div>
  );
};

export default IndexPage;
