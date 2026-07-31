import React from 'react';
import FileTreePreview from './FileTreePreview';
const IndexPage: React.FC = () => {
  return (
    <div style={{ padding: 24 }}>
      <FileTreePreview open={true} onClose={() => {}} />
    </div>
  );
};

export default IndexPage;
