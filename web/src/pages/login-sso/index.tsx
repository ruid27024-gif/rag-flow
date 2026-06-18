import { useLogin } from '@/hooks/use-login-request';
import { useEffect } from 'react';
import { useLocation, useNavigate } from 'umi';

import './index.less';

import request from '@/utils/request';

const LoginSSO = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { login } = useLogin();

  useEffect(() => {
    const performSSO = async () => {
      const params = new URLSearchParams(location.search);
      const ssoToken = params.get('token');

      if (!ssoToken) {
        // 如果没有 token，跳回登录页
        navigate('/login');
        return;
      }

      try {
        // --- 你的 SSO 逻辑开始 ---
        const ssoResponse = await request(
          'http://10.1.2.182:8787/sso/SsoOtherSys',
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            data: { token: ssoToken },
          },
        );

        if (ssoResponse.data && ssoResponse.data.code === 200) {
          const idCard = ssoResponse.data.msg;

          const verifyResponse = await request('/v1/user/verify_sso', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            data: { idCard: idCard },
          });

          if (verifyResponse.data.code === 0) {
            const data = verifyResponse.data.data;
            const { email, password } = data;

            if (email && password) {
              const code = await login({ email: email.trim(), password });
              if (code === 0) {
                navigate('/'); // 登录成功，跳转首页
              } else {
                navigate('/login');
              }
            }
          } else {
            alert('用户不存在');
            navigate('/login');
          }
        } else {
          alert('SSO 验证失败');
          navigate('/login');
        }
        // --- 你的 SSO 逻辑结束 ---
      } catch (error) {
        console.error(error);
        navigate('/login');
      }
    };

    performSSO();
  }, [location, navigate, login]);

  // 页面内容可以是空的，或者一个简单的 loading 提示
  // 大气的加载界面 UI
  return (
    <div className="flex h-screen w-full items-center justify-center bg-white dark:bg-slate-900">
      <div className="flex flex-col items-center gap-6">
        {/* 1. 呼吸灯加载动画 */}
        <div className="relative flex h-20 w-20 items-center justify-center">
          {/* 背景光晕 */}
          <div className="absolute inset-0 animate-pulse rounded-full bg-blue-500/20 blur-xl" />
          {/* 旋转圆环 */}
          <div className="h-16 w-16 animate-spin rounded-full border-4 border-blue-100 border-t-blue-600 dark:border-slate-700 dark:border-t-blue-400" />
          {/* 中心图标 */}
          <div className="absolute flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 text-white shadow-lg dark:bg-blue-500">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
              />
            </svg>
          </div>
        </div>

        {/* 2. 优雅的文案 */}
        <div className="text-center">
          <h2 className="text-xl font-semibold text-slate-800 dark:text-slate-100">
            正在安全连接...
          </h2>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            身份验证中，请稍候
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginSSO;
