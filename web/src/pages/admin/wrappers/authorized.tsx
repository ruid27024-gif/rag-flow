import { Routes } from '@/routes';
import authorizationUtil from '@/utils/authorization-util';
import { Navigate, Outlet } from 'umi';

export default function AuthorizedAdminWrapper() {
  const isLogin = !!authorizationUtil.getAuthorization();
  // 获取存储的值
  const auth = authorizationUtil.getAuthorization();
  console.log('🛡️ [路由守卫] 当前获取到的 Authorization:', auth);
  console.log(isLogin);
  return isLogin ? <Outlet /> : <Navigate to={Routes.Admin} />;
}
