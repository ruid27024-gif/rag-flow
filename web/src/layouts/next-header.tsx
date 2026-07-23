import { RAGFlowAvatar } from '@/components/ragflow-avatar';
import { useTheme } from '@/components/theme-provider';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Segmented, SegmentedValue } from '@/components/ui/segmented';
import { LanguageList, LanguageMap, ThemeEnum } from '@/constants/common';
import { useChangeLanguage } from '@/hooks/logic-hooks';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import { useNavigateWithFromState } from '@/hooks/route-hook';
import { useFetchUserInfo } from '@/hooks/use-user-setting-request';
import { Routes } from '@/routes';
import { getAuthorization } from '@/utils/authorization-util';
import { camelCase } from 'lodash';
import {
  ChevronDown,
  File,
  House,
  Library,
  MessageSquareText,
  Moon,
  Search,
  Shield,
  Sun,
} from 'lucide-react';
import React, { useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation } from 'umi';
import { BellButton } from './bell-button';

import message from '@/components/ui/message';

const handleDocHelpCLick = () => {
  window.open('https://ragflow.io/docs/dev/category/guides', 'target');
};

export function Header() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const navigate = useNavigateWithFromState();
  const { navigateToOldProfile } = useNavigatePage();

  const changeLanguage = useChangeLanguage();
  const { setTheme, theme } = useTheme();

  const {
    data: { language = 'English', avatar, nickname, is_admin_user, role_level },
  } = useFetchUserInfo();

  const handleItemClick = (key: string) => () => {
    changeLanguage(key);
  };

  const items = LanguageList.map((x) => ({
    key: x,
    label: <span>{LanguageMap[x as keyof typeof LanguageMap]}</span>,
  }));

  const onThemeClick = React.useCallback(() => {
    setTheme(theme === ThemeEnum.Dark ? ThemeEnum.Light : ThemeEnum.Dark);
  }, [setTheme, theme]);

  const InitSearchAppApiPath = 'init-search-app-api';

  const tagsData = useMemo(() => {
    const list = [
      { path: Routes.Root, name: t('header.Root'), icon: House },
      { path: Routes.Datasets, name: t('header.dataset'), icon: Library },
      { path: Routes.Chats, name: t('header.chat'), icon: MessageSquareText },
      {
        path: InitSearchAppApiPath,
        name: t('header.search'),
        icon: Search,
        isApi: true,
      },
      // {
      //   path: 'create-dialog-api',
      //   name: t('header.chat'),
      //   icon: MessageSquareText,
      //   isApi: true,
      // },
      // { path: Routes.Searches, name: t('header.search'), icon: Search },
      // { path: Routes.Agents, name: t('header.flow'), icon: Search },
      // { path: Routes.Memories, name: t('header.Memories'), icon: Search },
      { path: Routes.Files, name: t('header.fileManager'), icon: File },
    ];

    if (is_admin_user || role_level === 2) {
      //   list.push({
      //     path: Routes.Datasets,
      //     name: t('header.dataset'),
      //     icon: Library,
      //   });
      list.push({
        path: Routes.AdminFiles,
        name: t('header.admin'),
        icon: Shield,
      });

      list.push({
        path: '/dashboard',
        name: t('header.dashboard'),
        icon: Shield,
      });

      //   list.push({
      //     path: '/admin/services', // 直接写死或定义在 config 中
      //     name: '服务', // 确保 i18n 有这个 key
      //     icon: File, // 使用不同的图标以便区分
      //     isExternal: true, // 👈 打标记，告诉 handleClick 这是一个外部跳转
      // });
    }

    return list;
  }, [t, is_admin_user, role_level]);

  const options = useMemo(() => {
    return tagsData.map((tag) => {
      const HeaderIcon = tag.icon;

      return {
        label:
          tag.path === Routes.Root ? (
            <HeaderIcon className="size-6"></HeaderIcon>
          ) : (
            <span>{tag.name}</span>
          ),
        value: tag.path,
      };
    });
  }, [tagsData]);

  // 2. 封装点击处理函数
  const handleSmartClick = async () => {
    // 这里直接复用了你的逻辑，相当于触发了 'create-dialog-api' 选项
    const targetPath = 'create-dialog-api';

    try {
      const response = await fetch('/v1/debug/create_dialog_from_config', {
        method: 'POST',
        headers: {
          Authorization: getAuthorization() || '',
        },
      });

      const res = await response.json();

      if (res.retcode === 0 && res.data?.id) {
        // 假设 Routes.ChatDefault 是 '/chat' 之类的路径
        // 如果这里报错，请确保你有定义 Routes 或者直接用字符串路径
        navigate(`/next-chat-default/${res.data.id}`);
      } else {
        message.error(res.msg || '新建对话失败！');
      }
    } catch (error) {
      console.error(error);
      message.error('请求失败！');
    }
  };

  const handleChange = async (path: SegmentedValue) => {
    if (path === 'create-dialog-api') {
      try {
        const response = await fetch('/v1/debug/create_dialog_from_config', {
          method: 'POST',
          headers: {
            Authorization: getAuthorization() || '',
          },
        });

        const res = await response.json();

        if (res.retcode === 0 && res.data?.id) {
          navigate(`${Routes.ChatDefault}/${res.data.id}`);
        } else {
          message.error(res.msg || '新建对话失败！');
        }
      } catch (error) {
        console.error(error);
        message.error('请求失败！');
      }

      return;
    }

    if (path === InitSearchAppApiPath) {
      try {
        const response = await fetch('/v1/search/init_search_app', {
          method: 'POST',
          headers: {
            Authorization: getAuthorization() || '',
            'Content-Type': 'application/json',
          },
        });

        const res = await response.json();

        const code = res.retcode ?? res.code;
        const searchId = res.data?.search_id || res.data?.id;

        if (code === 0 && searchId) {
          navigate(`/next-search/${searchId}`);
        } else {
          message.error(res.msg || res.message || '初始化搜索应用失败！');
        }
      } catch (error) {
        console.error(error);
        message.error('请求失败！');
      }

      return;
    }

    navigate(path as Routes);
  };

  const handleLogoClick = useCallback(() => {
    navigate(Routes.Root);
  }, [navigate]);

  const activePath = useMemo(() => {
    if (pathname === '/dashboard' || pathname.startsWith('/dialog')) {
      return '/dashboard';
    }
    if (pathname.startsWith('/next-search')) {
      return InitSearchAppApiPath;
    }

    return pathname;
  }, [pathname]);

  return (
    <section className="py-5 px-10 flex justify-between items-center ">
      <div className="flex items-center gap-4">
        <img
          src="/hengyue.png"
          alt="logo"
          className="h-24 w-48 mr-[12px] cursor-pointer object-contain"
          onClick={handleLogoClick}
        />
      </div>
      {/* <Segmented
        className="flex-1 max-w-[800px] mx-auto justify-between gap-0"
        rounded="xxxl"
        sizeType="xl"
        buttonSize="xl"
        options={options}
        value={pathname}
        onChange={handleChange}
        activeClassName="text-bg-base bg-metallic-gradient border-b-[#00BEB4] border-b-2"
      ></Segmented> */}

      <Segmented
        className="flex-1 max-w-[800px] mx-auto justify-between gap-0"
        rounded="xxxl"
        sizeType="xl"
        buttonSize="xl"
        options={options}
        value={activePath}
        onChange={handleChange}
        activeClassName="text-bg-base bg-metallic-gradient border-b-[#00BEB4] border-b-2"
      ></Segmented>

      <div className="flex items-center gap-5 text-text-badge">
        {/* <a
          target="_blank"
          href="https://discord.com/invite/NjYzJD3GM3"
          rel="noreferrer"
        >
          <IconFontFill name="a-DiscordIconSVGVectorIcon"></IconFontFill>
        </a> */}
        {/* <a
          target="_blank"
          href="https://github.com/infiniflow/ragflow"
          rel="noreferrer"
        >
          <IconFontFill name="GitHub"></IconFontFill>
        </a> */}
        <DropdownMenu>
          <DropdownMenuTrigger>
            <div className="flex items-center gap-1">
              {t(`common.${camelCase(language)}`)}
              <ChevronDown className="size-4" />
            </div>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            {items.map((x) => (
              <DropdownMenuItem key={x.key} onClick={handleItemClick(x.key)}>
                {x.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        {/* <Button variant={'ghost'} onClick={handleDocHelpCLick}>
          <CircleHelp />
        </Button> */}
        <Button variant={'ghost'} onClick={onThemeClick}>
          {theme === 'light' ? <Sun /> : <Moon />}
        </Button>
        <BellButton></BellButton>
        <div className="relative">
          <RAGFlowAvatar
            name={nickname}
            avatar={avatar}
            isPerson
            className="size-8 cursor-pointer"
            onClick={navigateToOldProfile}
          ></RAGFlowAvatar>
          {/* Temporarily hidden */}
          {/* <Badge className="h-5 w-8 absolute font-normal p-0 justify-center -right-8 -top-2 text-bg-base bg-gradient-to-l from-[#42D7E7] to-[#478AF5]">
            Pro
          </Badge> */}
        </div>
      </div>
    </section>
  );
}
