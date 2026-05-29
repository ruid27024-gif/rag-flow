import { useLogout } from '@/hooks/use-login-request';
import { Routes } from '@/routes';
import { useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'umi';

export const useHandleMenuClick = () => {
  const navigate = useNavigate();
  const [active, setActive] = useState<Routes>();
  const { logout } = useLogout();
  const location = useLocation();
  useEffect(() => {
    const path = (location.pathname.split('/')?.[2] || '') as Routes;
    if (path) {
      setActive(('/' + path) as Routes);
    }
  }, [location]);

  const handleMenuClick = useCallback(
    (key: Routes) => () => {
      if (key === Routes.Logout) {
        logout();
      } else {
        setActive(key);
        navigate(`${Routes.UserSetting}${key}`);
      }
    },
    [logout, navigate],
  );

  //   const handleMenuClick = useCallback(
  //   (key: Routes) => () => {
  //     if (key === Routes.Logout) {
  //       logout();
  //     } else {
  //       setActive(key);
  //       // 核心修改：判断如果是管理员路径，就直接跳转，不再拼接 user-setting
  //       if (key.startsWith('/admin')) {
  //         navigate(key);
  //       } else {
  //         navigate(`${Routes.UserSetting}${key}`);
  //       }
  //     }
  //   },
  //   [logout, navigate],
  // );

  return { handleMenuClick, active, setActive };
};
