import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import { useFetchParentFolderList } from '@/hooks/use-file-request';
import { Routes } from '@/routes';
import { useCallback } from 'react';
import { useProfile } from '../user-setting/profile/hooks/use-profile';

export const useNavigateToOtherFolder = () => {
  const { navigateToFiles } = useNavigatePage();

  const navigateToOtherFolder = useCallback(
    (folderId: string) => {
      navigateToFiles(folderId);
    },
    [navigateToFiles],
  );

  return navigateToOtherFolder;
};

export const useSelectBreadcrumbItems = () => {
  const parentFolderList = useFetchParentFolderList();
  const { profile } = useProfile();

  return parentFolderList.length === 1
    ? []
    : parentFolderList.map((x) => ({
        title: x.name === '/' ? profile.userName : x.name,
        path: `${Routes.Files}?folderId=${x.id}`,
      }));
};
