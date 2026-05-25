import SvgIcon from '@/components/svg-icon';
import { useAuth } from '@/hooks/auth-hooks';
import {
  useLogin,
  useLoginChannels,
  useLoginWithChannel,
  useRegister,
} from '@/hooks/use-login-request';
import { useSystemConfig } from '@/hooks/use-system-request';
import { rsaPsw } from '@/utils';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'umi';

import Spotlight from '@/components/spotlight';
import { Button, ButtonLoading } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { BgSvg } from './bg';
import FlipCard3D from './card';
import './index.less';

import request from '@/utils/request';

const Login = () => {
  const [title, setTitle] = useState('login');
  const navigate = useNavigate();
  const { login, loading: signLoading } = useLogin();
  const { register, loading: registerLoading } = useRegister();
  const { channels, loading: channelsLoading } = useLoginChannels();
  const { login: loginWithChannel, loading: loginWithChannelLoading } =
    useLoginWithChannel();
  const { t } = useTranslation('translation', { keyPrefix: 'login' });
  const [isLoginPage, setIsLoginPage] = useState(true);

  const [isUserInteracting, setIsUserInteracting] = useState(true);

  const loading =
    signLoading ||
    registerLoading ||
    channelsLoading ||
    loginWithChannelLoading;
  const { config } = useSystemConfig();
  const registerEnabled = config?.registerEnabled !== 0;
  const { isLogin } = useAuth();
  const location = useLocation();
  // const { isLogin } = useAuth();
  // useEffect(() => {
  //   if (isLogin) {
  //     navigate('/');
  //   }
  // }, [isLogin, navigate]);

  useEffect(() => {
    // 第一步：检查 URL 是否有 SSO token
    const params = new URLSearchParams(location.search);
    const ssoToken = params.get('token');

    if (ssoToken) {
      // 执行 SSO 登录
      const performSSO = async () => {
        try {
          // 1. 调用 SSO 验证接口
          const ssoResponse = await request(
            'http://192.168.1.24:8686/dev-api/sso/SsoOtherSys',
            {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              data: { token: ssoToken }, // 注意：这里是 data 而不是 body，根据您的 request 库配置调整
            },
          );

          // 2. 验证 SSO 响应
          if (ssoResponse.data && ssoResponse.data.code === 200) {
            const idCard = ssoResponse.data.msg; // 获取身份证号

            // 3. 调用您的后端接口验证用户是否存在
            const verifyResponse = await request('/v1/user/verify_sso', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json', // 确保这一行存在
              },
              data: { idCard: idCard }, // 确保参数名是 idCard
            });
            // 4. 处理后端验证结果
            if (verifyResponse.data.code === 0) {
              const mockRagflowLoginData = verifyResponse.data.data;

              const email = mockRagflowLoginData['email'];
              const nickname = mockRagflowLoginData['nickname'];
              const password = mockRagflowLoginData['password'];

              try {
                // 1. 简单的非空检查 (可选，比 zod 更轻量)
                if (!email || !password) {
                  console.error('邮箱或密码不能为空');
                  return;
                }

                // // 2. 密码加密 (保留原有的加密逻辑)
                // const rsaPassWord = rsaPsw(password);

                // 3. 直接触发 useLogin 中的 mutateAsync
                // 这里的 login 是你从 useLogin() 解构出来的函数
                const code = await login({
                  email: email.trim(),
                  password: password,
                });

                // 4. 根据返回结果处理业务
                if (code === 0) {
                  // 登录成功，跳转到首页
                  // alert("hhhhhhhhh")
                  await new Promise((resolve) => setTimeout(resolve, 100));

                  navigate('/');
                } else {
                  // 可以在这里处理后端返回的具体错误提示
                  console.log('登录失败，错误码:', code);
                }
              } catch (errorInfo) {
                // 捕获网络错误或异常
                console.log('登录过程发生异常:', errorInfo);
              }
            } else {
              // 用户不存在于数据库中
              alert('用户不存在，请联系管理员');
              navigate('/login');
            }
          } else {
            // SSO 验证失败
            console.error('SSO 验证失败:', ssoResponse.msg);
            alert(`SSO 验证失败: ${ssoResponse.msg || '未知错误'}`);
            navigate('/login');
          }
        } catch (error) {
          console.error('SSO 登录失败', error);
          alert('网络请求失败，请检查网络连接');
          navigate('/login');
        }
      };

      performSSO();
    }
    // 第二步：如果没有 SSO token 但已登录，直接跳转首页
    else if (isLogin) {
      navigate('/');
    }
    // 第三步：既无 token 也未登录 -> 保持当前页面
  }, [location, isLogin, navigate]);

  const handleLoginWithChannel = async (channel: string) => {
    await loginWithChannel(channel);
  };

  const changeTitle = () => {
    setIsLoginPage(title !== 'login');
    if (title === 'login' && !registerEnabled) {
      return;
    }

    setTimeout(() => {
      setTitle(title === 'login' ? 'register' : 'login');
    }, 200);
    // setTitle((title) => (title === 'login' ? 'register' : 'login'));
  };

  const FormSchema = z
    .object({
      nickname: z.string().optional(),
      email: z
        .string()
        // .email()
        .min(1, { message: t('emailPlaceholder') })
        // 手机号 + 邮箱
        .refine(
          (val) => {
            // 1. 简单的邮箱正则
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            // 2. 简单的手机号正则 (这里匹配 11 位数字，可根据需要调整)
            const phoneRegex = /^1\d{10}$/;

            // 只要满足其中一个就通过
            return emailRegex.test(val) || phoneRegex.test(val);
          },
          {
            message: t('emailPlaceholder'), // 提示语可以改成 "请输入有效的邮箱或手机号"
          },
        ),
      password: z.string().min(1, { message: t('passwordPlaceholder') }),
      remember: z.boolean().optional(),
    })
    .superRefine((data, ctx) => {
      if (title === 'register' && !data.nickname) {
        ctx.addIssue({
          path: ['nickname'],
          message: 'nicknamePlaceholder',
          code: z.ZodIssueCode.custom,
        });
      }
    });
  const form = useForm({
    defaultValues: {
      nickname: '',
      email: '',
      password: '',
      confirmPassword: '',
      remember: false,
    },
    resolver: zodResolver(FormSchema),
  });

  const onCheck = async (params) => {
    console.log('params', params);
    try {
      // const params = await form.validateFields();

      const rsaPassWord = rsaPsw(params.password) as string;

      if (title === 'login') {
        const code = await login({
          email: `${params.email}`.trim(),
          password: rsaPassWord,
        });
        if (code === 0) {
          navigate('/');
        }
      } else {
        const code = await register({
          nickname: params.nickname,
          email: params.email,
          password: rsaPassWord,
        });
        if (code === 0) {
          setTitle('login');
        }
      }
    } catch (errorInfo) {
      console.log('Failed:', errorInfo);
    }
  };

  return (
    <>
      <Spotlight opcity={0.4} coverage={60} color={'rgb(128, 255, 248)'} />
      <Spotlight
        opcity={0.3}
        coverage={12}
        X={'10%'}
        Y={'-10%'}
        color={'rgb(128, 255, 248)'}
      />
      <Spotlight
        opcity={0.3}
        coverage={12}
        X={'90%'}
        Y={'-10%'}
        color={'rgb(128, 255, 248)'}
      />
      <div className=" h-[inherit] relative overflow-auto">
        <BgSvg isPaused={isUserInteracting} />

        <div className="absolute top-3 flex flex-col items-center mb-12 w-full text-text-primary">
          <div className="flex items-center mb-4 w-full pl-10 pt-10 ">
            <div className="w-12 h-12 p-2 rounded-lg flex items-center justify-center mr-3">
              <img
                src={'/hf.svg'}
                alt="logo"
                // className="size-8 mr-[12] cursor-pointer"
                className="size-16 mr-[12px] cursor-pointer"
              />
            </div>
            {/* <div className="text-xl font-bold self-center">{t('Company')}</div> */}
          </div>
          {/* <h1 className="pl-3 text-4xl text-transparent bg-clip-text bg-gradient-to-r from-[#065F46] to-[#34D399]">
            {t('title')}
          </h1> */}
          <h1
            className="pl-3 text-4xl font-extrabold text-transparent bg-clip-text animate-shine, font-['Georgia','Times_New_Roman','serif']"
            style={{
              // 从深绿色(#065F46) 渐变到 亮绿色(#34D399)
              background: 'linear-gradient(90deg, #065F46, #34D399)',
              backgroundSize: '100% 100%', // 如果不需要流光扫过，尺寸改回100%
              WebkitBackgroundClip: 'text',
              backgroundClip: 'text',
              // willChange: 'background-position', // 静态渐变可以删掉这行
            }}
          >
            {t('title')}
          </h1>

          <p className="text-sm text-gray-400 text-center mt-6 mb-10">
            {t('annotation')}
          </p>
          {/* border border-accent-primary rounded-full */}
          {/* <div className="mt-4 px-6 py-1 text-sm font-medium text-cyan-600  hover:bg-cyan-50 transition-colors duration-200 border-glow relative overflow-hidden">
            {t('start')}
          </div> */}
        </div>
        <div className="relative z-10 flex flex-col items-center justify-center min-h-[1050px] px-4 sm:px-6 lg:px-8">
          {/* Logo and Header */}

          {/* Login Form */}
          <FlipCard3D isLoginPage={isLoginPage}>
            <div className="flex flex-col items-center justify-center w-full">
              <div className="text-center mb-8">
                <h2 className="text-xl font-semibold text-text-primary">
                  {title === 'login' ? t('loginTitle') : t('signUpTitle')}
                </h2>
              </div>
              <div className=" w-full max-w-[540px] bg-bg-component backdrop-blur-sm rounded-2xl shadow-xl pt-14 pl-10 pr-10 pb-2 border border-border-button ">
                <Form {...form}>
                  <form
                    className="flex flex-col gap-8 text-text-primary "
                    onSubmit={form.handleSubmit((data) => onCheck(data))}
                  >
                    <FormField
                      control={form.control}
                      name="email"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel required>{t('emailLabel')}</FormLabel>
                          <FormControl>
                            <Input
                              placeholder={t('emailPlaceholder')}
                              autoComplete="email"
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    {title === 'register' && (
                      <FormField
                        control={form.control}
                        name="nickname"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel required>{t('nicknameLabel')}</FormLabel>
                            <FormControl>
                              <Input
                                placeholder={t('nicknamePlaceholder')}
                                autoComplete="username"
                                {...field}
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    )}

                    <FormField
                      control={form.control}
                      name="password"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel required>{t('passwordLabel')}</FormLabel>
                          <FormControl>
                            <div className="relative">
                              <Input
                                type={'password'}
                                placeholder={t('passwordPlaceholder')}
                                autoComplete={
                                  title === 'login'
                                    ? 'current-password'
                                    : 'new-password'
                                }
                                {...field}
                              />
                              {/* <button
                                type="button"
                                className="absolute inset-y-0 right-0 pr-3 flex items-center"
                                onClick={() => setShowPassword(!showPassword)}
                              >
                                {showPassword ? (
                                  <EyeOff className="h-4 w-4 text-gray-500" />
                                ) : (
                                  <Eye className="h-4 w-4 text-gray-500" />
                                )}
                              </button> */}
                            </div>
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    {title === 'login' && (
                      <FormField
                        control={form.control}
                        name="remember"
                        render={({ field }) => (
                          <FormItem>
                            <FormControl>
                              <div className="flex gap-2">
                                <Checkbox
                                  checked={field.value}
                                  onCheckedChange={(checked) => {
                                    field.onChange(checked);
                                  }}
                                />
                                <FormLabel
                                  className={cn(' hover:text-text-primary', {
                                    'text-text-disabled': !field.value,
                                    'text-text-primary': field.value,
                                  })}
                                >
                                  {t('rememberMe')}
                                </FormLabel>
                              </div>
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    )}
                    <ButtonLoading
                      type="submit"
                      loading={loading}
                      className="bg-metallic-gradient border-b-[#00BEB4] border-b-2 hover:bg-metallic-gradient hover:border-b-[#02bcdd] w-full my-8"
                    >
                      {title === 'login' ? t('login') : t('continue')}
                    </ButtonLoading>
                    {title === 'login' && channels && channels.length > 0 && (
                      <div className="mt-3 border">
                        {channels.map((item) => (
                          <Button
                            variant={'transparent'}
                            key={item.channel}
                            onClick={() => handleLoginWithChannel(item.channel)}
                            style={{ marginTop: 10 }}
                          >
                            <div className="flex items-center">
                              <SvgIcon
                                name={item.icon || 'sso'}
                                width={20}
                                height={20}
                                style={{ marginRight: 5 }}
                              />
                              Sign in with {item.display_name}
                            </div>
                          </Button>
                        ))}
                      </div>
                    )}
                  </form>
                </Form>

                {/* {title === 'login' && registerEnabled && (
                  <div className="mt-10 text-right">
                    <p className="text-text-disabled text-sm">
                      {t('signInTip')}
                      <Button
                        variant={'transparent'}
                        onClick={changeTitle}
                        className="text-accent-primary/90 hover:text-accent-primary hover:bg-transparent font-medium border-none transition-colors duration-200"
                      >
                        {t('signUp')}
                      </Button>
                    </p>
                  </div>
                )} */}
                {title === 'register' && (
                  <div className="mt-10 text-right">
                    <p className="text-text-disabled text-sm">
                      {t('signUpTip')}
                      <Button
                        variant={'transparent'}
                        onClick={changeTitle}
                        className="text-accent-primary/90 hover:text-accent-primary hover:bg-transparent font-medium border-none transition-colors duration-200"
                      >
                        {t('login')}
                      </Button>
                    </p>
                  </div>
                )}
              </div>
            </div>
          </FlipCard3D>
        </div>
      </div>
    </>
  );
};

export default Login;
