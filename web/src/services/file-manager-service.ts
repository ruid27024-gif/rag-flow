import api from '@/utils/api';
import registerServer from '@/utils/register-server';
import request from '@/utils/request';

const {
  listFile,
  listFile1,
  removeFile,
  uploadFile,
  renameFile,
  getAllParentFolder,
  createFolder,
  connectFileToKnowledge,
  get_document_file,
  getFile,
  moveFile,
  listFileUP,
  get_document_file_download,
} = api;

const methods = {
  listFile: {
    url: listFile,
    method: 'get',
  },
  listFileUP: {
    url: listFileUP,
    method: 'get',
  },
  removeFile: {
    url: removeFile,
    method: 'post',
  },
  uploadFile: {
    url: uploadFile,
    method: 'post',
  },
  renameFile: {
    url: renameFile,
    method: 'post',
  },
  getAllParentFolder: {
    url: getAllParentFolder,
    method: 'get',
  },
  createFolder: {
    url: createFolder,
    method: 'post',
  },
  connectFileToKnowledge: {
    url: connectFileToKnowledge,
    method: 'post',
  },
  getFile: {
    url: getFile,
    method: 'get',
    responseType: 'blob',
  },
  getDocumentFile: {
    url: get_document_file,
    method: 'get',
    responseType: 'blob',
  },
  moveFile: {
    url: moveFile,
    method: 'post',
  },
} as const;

const fileManagerService = registerServer<keyof typeof methods>(
  methods,
  request,
);

export const downloadFile = (data: { docId: string; ext: string }) => {
  return request.get(get_document_file_download(data.docId), {
    params: { ext: data.ext },
    responseType: 'blob',
  });
};
export default fileManagerService;
