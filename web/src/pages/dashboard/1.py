import {
  MessageOutlined,
  ReloadOutlined,
  TableOutlined,
  TeamOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import * as echarts from 'echarts';
import { Box, MessagesSquare, UserCheck, Users } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
// 使用相对路径向上找一层到 pages，再进入 dialog
import { LineChartOutlined } from '@ant-design/icons';
import '../dialog/GroupMemberStatsPage.css';

/**
 * 监听当前是否为黑夜模式
 */
const useIsDark = () => {
  const [isDark, setIsDark] = useState(() => {
    if (typeof document === 'undefined') return false;
    return document.documentElement.classList.contains('dark');
  });

  useEffect(() => {
    const updateDark = () => {
      setIsDark(document.documentElement.classList.contains('dark'));
    };

    updateDark();

    const observer = new MutationObserver(updateDark);

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    });

    return () => {
      observer.disconnect();
    };
  }, []);

  return isDark;
};

/**
 * 页面外壳
 */
// const DashboardShell = ({ children }) => {
//   return (
//     <div
//       className="
//         relative
//         h-screen
//         overflow-y-auto
//         bg-[#f5f7fb]
//         text-slate-700
//         dark:bg-[#171717]
//         dark:text-slate-200
//       "
//     >
//       {/* <div
//         className="
//           pointer-events-none
//           absolute inset-0
//           hidden dark:block
//           bg-[radial-gradient(circle_at_20%_10%,rgba(0,190,180,0.16),transparent_28%),radial-gradient(circle_at_90%_20%,rgba(0,190,180,0.10),transparent_24%),linear-gradient(135deg,transparent_0%,transparent_43%,rgba(0,190,180,0.10)_44%,transparent_45%,transparent_100%)]
//         "
//       />

//       <div
//         className="
//           pointer-events-none
//           absolute inset-0
//           hidden dark:block
//           opacity-30
//           bg-[linear-gradient(135deg,transparent_0%,transparent_48%,rgba(0,190,180,0.18)_49%,transparent_50%,transparent_100%)]
//           bg-[length:180px_180px]
//         "
//       /> */}

//       <div className="relative z-10 p-6">{children}</div>
//     </div>
//   );
// };
/**
 * 页面外壳
 */
/**
 * 页面外壳 (纯净版)
 */
const DashboardShell = ({ children }) => {
  return (
    <div
      className="
        h-screen
        overflow-hidden
        bg-[#eef5f1]
        p-3
        text-slate-800
        dark:bg-[#071b16]
      "
    >
      {children}
    </div>
  );
};

/**
 * 顶部统计卡片
 */
const StatCard = ({ title, value, icon, colorClassName, bgClassName }) => {
  return (
    <div
      className="
        group
        relative
        flex-1
        min-w-[240px]
        rounded-2xl
        p-6
        flex
        items-center
        justify-between
        bg-white
        border
        border-slate-100
        shadow-[0_2px_8px_rgba(0,0,0,0.03)]
        transition-all
        duration-300
        ease-out
        hover:-translate-y-1
        hover:shadow-[0_12px_24px_rgba(0,0,0,0.06)]
        dark:bg-white/[0.04]
        dark:border-white/[0.08]
        dark:shadow-none
        dark:hover:bg-white/[0.06]
        dark:hover:shadow-[0_12px_24px_rgba(0,0,0,0.4)]
      "
    >
      {/* 左侧数据区 */}
      <div className="flex flex-col justify-center z-10">
        <div className="mb-3 text-sm font-medium tracking-wide text-slate-400 dark:text-slate-500">
          {title}
        </div>
        <div
          className="
            text-3xl
            font-extrabold
            text-slate-800
            dark:text-white
            tabular-nums
            tracking-tight
          "
        >
          {Number(value || 0).toLocaleString()}
        </div>
      </div>

      {/* 右侧图标区 */}
      <div
        className={`
          relative
          z-10
          flex
          h-12
          w-12
          items-center
          justify-center
          rounded-xl
          text-xl
          transition-transform
          duration-300
          group-hover:scale-110
          ${colorClassName}
          ${bgClassName}
        `}
      >
        {icon}
      </div>

      {/* 可选：悬停时的微弱背景光晕效果（增加精致感） */}
      <div
        className={`
          absolute
          inset-0
          rounded-2xl
          opacity-0
          transition-opacity
          duration-300
          group-hover:opacity-100
          ${bgClassName}
          blur-xl
          -z-0
        `}
      />
    </div>
  );
};

const BigScreenPanel = ({ children, className = '' }) => {
  return (
    <div
      className={`
        rounded-2xl
        border
        border-white/70
        bg-white/90
        shadow-[0_8px_24px_rgba(15,118,110,0.08)]
        backdrop-blur
        dark:border-white/[0.08]
        dark:bg-white/[0.04]
        ${className}
      `}
    >
      {children}
    </div>
  );
};

const BigScreenTitle = ({ icon, title, right }) => {
  return (
    <div
      className="
        flex
        h-10
        items-center
        justify-between
        border-b
        border-slate-100
        px-4
        text-sm
        font-bold
        text-slate-800
        dark:border-white/[0.06]
        dark:text-white
      "
    >
      <div className="flex items-center gap-2">
        {icon}
        <span>{title}</span>
      </div>

      {right ? <div>{right}</div> : null}
    </div>
  );
};

/**
 * 图表卡片
 */
const ChartCard = ({ title, icon, children }) => {
  return (
    <div
      className="
        flex-1
        min-w-[400px]
        rounded-xl
        p-5
        bg-white
        border
        border-slate-200
        shadow-[0_4px_14px_rgba(0,0,0,0.06)]
        dark:bg-white/[0.035]
        dark:border-white/[0.08]
        dark:shadow-[0_8px_30px_rgba(0,0,0,0.35)]
        dark:backdrop-blur-sm
      "
    >
      <div
        className="
          mb-3
          flex
          items-center
          gap-2
          text-base
          font-semibold
          text-slate-800
          dark:text-white
        "
      >
        <span>{icon}</span>
        <span>{title}</span>
      </div>

      {children}
    </div>
  );
};

/**
 * 饼图组件
 */
const PieChart = ({
  title,
  chartData,
  isDark,
  className = 'h-[400px] w-full',
}) => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  useEffect(() => {
    if (!chartRef.current) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const hasData =
      Array.isArray(chartData) && chartData.some((item) => item.value > 0);

    const option = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)',
        backgroundColor: isDark ? '#1b1b1d' : '#ffffff',
        borderColor: isDark ? 'rgba(0,190,180,0.35)' : '#dddddd',
        textStyle: {
          color: isDark ? '#f8fafc' : '#333333',
        },
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        top: 'middle',
        textStyle: {
          color: isDark ? '#cbd5e1' : '#666666',
        },
      },
      graphic: !hasData
        ? {
            type: 'text',
            left: 'center',
            top: 'middle',
            style: {
              text: '暂无数据',
              fontSize: 16,
              fill: isDark ? '#94a3b8' : '#999999',
            },
          }
        : null,
      series: [
        {
          name: title,
          type: 'pie',
          radius: ['42%', '70%'],
          center: ['60%', '55%'],
          avoidLabelOverlap: true,
          itemStyle: {
            borderRadius: 8,
            borderColor: isDark ? '#171717' : '#ffffff',
            borderWidth: 2,
          },
          label: {
            show: true,
            formatter: '{b}\n{d}%',
            color: isDark ? '#e5e7eb' : '#333333',
          },
          labelLine: {
            show: true,
            lineStyle: {
              color: isDark ? 'rgba(0,190,180,0.45)' : '#999999',
            },
          },
          emphasis: {
            scale: true,
            scaleSize: 8,
            label: {
              show: true,
              fontSize: 16,
              fontWeight: 'bold',
              color: isDark ? '#ffffff' : '#333333',
            },
          },
          data: hasData ? chartData : [],
        },
      ],
      color: [
        '#00BEB4',
        '#F87171',
        '#FB923C',
        '#A78BFA',
        '#60A5FA',
        '#FBBF24',
        '#34D399',
        '#22D3EE',
        '#C084FC',
      ],
    };

    chartInstance.current.setOption(option, true);

    const handleResize = () => {
      chartInstance.current?.resize();
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [title, chartData, isDark]);

  useEffect(() => {
    return () => {
      chartInstance.current?.dispose();
      chartInstance.current = null;
    };
  }, []);

  return <div ref={chartRef} className={className} />;
};

/**
 * 单指标成员柱形图
 */
/**
 * 所有组成员合并图表
 * metricType: token | dialog
 * chartType: line | bar
 */
const CombinedGroupMemberMetricChart = ({
  title,
  groups,
  isDark,
  metricType,
  chartType,
  className = 'h-[460px] w-full',
}) => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  const groupColors = [
    '#00BEB4',
    '#F87171',
    '#FB923C',
    '#A78BFA',
    '#60A5FA',
    '#FBBF24',
    '#34D399',
    '#22D3EE',
    '#C084FC',
    '#F472B6',
  ];

  useEffect(() => {
    if (!chartRef.current) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const safeGroups = Array.isArray(groups) ? groups : [];

    /**
     * 把后端数据拍平成：
     * [
     *   {
     *     group_id,
     *     group_name,
     *     member_name,
     *     label,
     *     token_usage,
     *     dialog_count
     *   }
     * ]
     */
    const flatMembers = safeGroups.flatMap((group) => {
      const members = Array.isArray(group.members) ? group.members : [];

      return members.map((member) => {
        const groupName = group.group_name || group.group_id;
        const memberName = member.nickname || member.user_id;

        return {
          group_id: group.group_id,
          group_name: groupName,
          member_name: memberName,
          label: `${memberName}`,
          token_usage: Number(member.token_usage || 0),
          dialog_count: Number(member.dialog_count || 0),
        };
      });
    });

    const categories = flatMembers.map((item) => item.label);

    const isToken = metricType === 'token';

    const hasData = flatMembers.some((item) => {
      return isToken ? item.token_usage > 0 : item.dialog_count > 0;
    });

    /**
     * 每个组一条 series
     * 当前组对应的位置有值，其他位置用 null
     * 这样 legend 就能清晰区分组
     */
    const series = safeGroups.map((group, groupIndex) => {
      const groupName = group.group_name || group.group_id;
      const groupColor = groupColors[groupIndex % groupColors.length];

      return {
        name: groupName,
        type: chartType,
        smooth: chartType === 'line',
        connectNulls: false,
        symbolSize: chartType === 'line' ? 8 : 0,

        // 关键：柱状图用 stack，让不同组的柱子共用类目中心
        stack: chartType === 'bar' ? 'memberMetric' : undefined,

        // 建议不要用百分比太大，固定宽度更稳
        barWidth: chartType === 'bar' ? 28 : undefined,
        barMaxWidth: chartType === 'bar' ? 36 : undefined,

        data: flatMembers.map((item) => {
          if (item.group_id !== group.group_id) {
            return null;
          }

          return isToken ? item.token_usage : item.dialog_count;
        }),
        itemStyle: {
          color: groupColor,
          borderRadius: chartType === 'bar' ? [6, 6, 0, 0] : 0,
        },
        lineStyle:
          chartType === 'line'
            ? {
                color: groupColor,
                width: 3,
              }
            : undefined,
        areaStyle:
          chartType === 'line'
            ? {
                color: {
                  type: 'linear',
                  x: 0,
                  y: 0,
                  x2: 0,
                  y2: 1,
                  colorStops: [
                    {
                      offset: 0,
                      color: `${groupColor}55`,
                    },
                    {
                      offset: 1,
                      color: `${groupColor}00`,
                    },
                  ],
                },
              }
            : undefined,
        label:
          chartType === 'bar'
            ? {
                show: true,
                position: 'top',
                color: isDark ? '#e5e7eb' : '#333333',
                formatter: (params) => {
                  if (params.value == null) return '';
                  return Number(params.value || 0).toLocaleString();
                },
              }
            : undefined,
      };
    });

    const option = {
      backgroundColor: 'transparent',

      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: chartType === 'bar' ? 'shadow' : 'line',
        },
        backgroundColor: isDark ? '#1b1b1d' : '#ffffff',
        borderColor: isDark ? 'rgba(0,190,180,0.35)' : '#dddddd',
        textStyle: {
          color: isDark ? '#f8fafc' : '#333333',
        },
        formatter: (params) => {
          const validParams = params.filter((item) => item.value != null);

          if (!validParams.length) return '';

          const currentIndex = validParams[0].dataIndex;
          const currentMember = flatMembers[currentIndex];

          let html = `
            <div>
              <div style="margin-bottom: 6px;">
                ${currentMember?.group_name || ''}
                /
                ${currentMember?.member_name || ''}
              </div>
          `;

          validParams.forEach((item) => {
            html += `
              <div>
                <span style="
                  display:inline-block;
                  width:8px;
                  height:8px;
                  border-radius:50%;
                  background:${item.color};
                  margin-right:6px;
                "></span>
                ${item.seriesName}：
                ${Number(item.value || 0).toLocaleString()}
              </div>
            `;
          });

          html += '</div>';

          return html;
        },
      },

      legend: {
        top: 0,
        type: 'scroll',
        textStyle: {
          color: isDark ? '#cbd5e1' : '#666666',
        },
        pageTextStyle: {
          color: isDark ? '#cbd5e1' : '#666666',
        },
      },

      grid: {
        left: 70,
        right: 40,
        top: 70,
        bottom: 110,
      },

      // 在 xAxis 配置中
      xAxis: {
        type: 'category',
        data: categories,

        // 👇 核心修复：强制刻度线与标签对齐，柱子也会随之对齐
        axisTick: {
          alignWithLabel: true,
        },

        axisLabel: {
          interval: 0,
          rotate: categories.length > 6 ? 35 : 0,
          color: isDark ? '#cbd5e1' : '#666666',
          overflow: 'truncate',
          width: 110,
          // 👇 视觉微调：当文字旋转时，使用右对齐让文字尾部刚好对准柱子中心
          align: categories.length > 6 ? 'right' : 'center',
          // align: 'center',
        },

        axisLine: {
          lineStyle: {
            color: isDark ? 'rgba(255,255,255,0.18)' : '#dddddd',
          },
        },
      },

      yAxis: {
        type: 'value',
        name: isToken ? 'Token' : '次数',
        nameTextStyle: {
          color: isDark ? '#cbd5e1' : '#666666',
        },
        axisLabel: {
          color: isDark ? '#cbd5e1' : '#666666',
          formatter: (value) => Number(value || 0).toLocaleString(),
        },
        splitLine: {
          lineStyle: {
            color: isDark ? 'rgba(255,255,255,0.08)' : '#eeeeee',
          },
        },
      },

      graphic: !hasData
        ? {
            type: 'text',
            left: 'center',
            top: 'middle',
            style: {
              text: '暂无数据',
              fontSize: 15,
              fill: isDark ? '#94a3b8' : '#999999',
            },
          }
        : null,

      series,
    };

    chartInstance.current.setOption(option, true);

    const handleResize = () => {
      chartInstance.current?.resize();
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [title, groups, isDark, metricType, chartType]);

  useEffect(() => {
    return () => {
      chartInstance.current?.dispose();
      chartInstance.current = null;
    };
  }, []);

  return <div ref={chartRef} className={className} />;
};

/**
 * 单个组内成员指标图表
 * metricType: token | dialog
 * chartType: line | bar
 */
const SingleGroupMemberMetricChart = ({
  title,
  group,
  isDark,
  metricType,
  chartType = 'bar',
  className = 'h-[360px] w-full',
}) => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  useEffect(() => {
    if (!chartRef.current) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const members = Array.isArray(group?.members) ? group.members : [];

    const isToken = metricType === 'token';

    const categories = members.map((member) => {
      return member.nickname || member.user_id || '未知成员';
    });

    const values = members.map((member) => {
      return isToken
        ? Number(member.token_usage || 0)
        : Number(member.dialog_count || 0);
    });

    const hasData = values.some((value) => value > 0);

    const mainColor = isToken ? '#00BEB4' : '#FBBF24';

    const option = {
      backgroundColor: 'transparent',

      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: chartType === 'bar' ? 'shadow' : 'line',
        },
        backgroundColor: isDark ? '#1b1b1d' : '#ffffff',
        borderColor: isDark ? 'rgba(0,190,180,0.35)' : '#dddddd',
        textStyle: {
          color: isDark ? '#f8fafc' : '#333333',
        },
        formatter: (params) => {
          if (!params?.length) return '';

          const item = params[0];

          return `
            <div>
              <div style="margin-bottom: 6px;">
                ${item.axisValue}
              </div>
              <div>
                <span style="
                  display:inline-block;
                  width:8px;
                  height:8px;
                  border-radius:50%;
                  background:${item.color};
                  margin-right:6px;
                "></span>
                ${isToken ? 'Token 消耗' : '问答次数'}：
                ${Number(item.value || 0).toLocaleString()}
              </div>
            </div>
          `;
        },
      },

      grid: {
        left: 70,
        right: 35,
        top: 35,
        bottom: categories.length > 6 ? 90 : 55,
      },

      xAxis: {
        type: 'category',
        data: categories,
        axisTick: {
          alignWithLabel: true,
        },
        axisLabel: {
          interval: 0,
          rotate: categories.length > 6 ? 35 : 0,
          color: isDark ? '#cbd5e1' : '#666666',
          overflow: 'truncate',
          width: 100,
          align: categories.length > 6 ? 'right' : 'center',
        },
        axisLine: {
          lineStyle: {
            color: isDark ? 'rgba(255,255,255,0.18)' : '#dddddd',
          },
        },
      },

      yAxis: {
        type: 'value',
        name: isToken ? 'Token' : '次数',
        nameTextStyle: {
          color: isDark ? '#cbd5e1' : '#666666',
        },
        axisLabel: {
          color: isDark ? '#cbd5e1' : '#666666',
          formatter: (value) => Number(value || 0).toLocaleString(),
        },
        splitLine: {
          lineStyle: {
            color: isDark ? 'rgba(255,255,255,0.08)' : '#eeeeee',
          },
        },
      },

      graphic: !hasData
        ? {
            type: 'text',
            left: 'center',
            top: 'middle',
            style: {
              text: '暂无数据',
              fontSize: 15,
              fill: isDark ? '#94a3b8' : '#999999',
            },
          }
        : null,

      series: [
        {
          name: title,
          type: chartType,
          smooth: chartType === 'line',
          symbolSize: chartType === 'line' ? 8 : 0,
          barWidth: chartType === 'bar' ? 28 : undefined,
          barMaxWidth: chartType === 'bar' ? 40 : undefined,
          data: values,
          itemStyle: {
            color: mainColor,
            borderRadius: chartType === 'bar' ? [6, 6, 0, 0] : 0,
          },
          lineStyle:
            chartType === 'line'
              ? {
                  color: mainColor,
                  width: 3,
                }
              : undefined,
          areaStyle:
            chartType === 'line'
              ? {
                  color: {
                    type: 'linear',
                    x: 0,
                    y: 0,
                    x2: 0,
                    y2: 1,
                    colorStops: [
                      {
                        offset: 0,
                        color: `${mainColor}55`,
                      },
                      {
                        offset: 1,
                        color: `${mainColor}00`,
                      },
                    ],
                  },
                }
              : undefined,
          label:
            chartType === 'bar'
              ? {
                  show: true,
                  position: 'top',
                  color: isDark ? '#e5e7eb' : '#333333',
                  formatter: (params) => {
                    return Number(params.value || 0).toLocaleString();
                  },
                }
              : undefined,
        },
      ],
    };

    chartInstance.current.setOption(option, true);

    const handleResize = () => {
      chartInstance.current?.resize();
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [title, group, isDark, metricType, chartType]);

  useEffect(() => {
    return () => {
      chartInstance.current?.dispose();
      chartInstance.current = null;
    };
  }, []);

  return <div ref={chartRef} className={className} />;
};
/**
 * 所有组成员合并展示
 * 一个 Token 折线图
 * 一个 问答次数柱状图
 */
const GroupCombinedCharts = ({ groups, isDark }) => {
  if (!Array.isArray(groups) || groups.length === 0) {
    return null;
  }

  return (
    <div className="mt-[22px]">
      <div className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900 dark:text-white">
        <TeamOutlined className="text-[#00BEB4]" />
        组内成员使用统计
      </div>

      <div className="flex flex-col gap-5">
        {groups.map((group) => {
          const groupName = group.group_name || group.group_id;

          return (
            <div
              key={group.group_id}
              className="
                rounded-xl
                p-5
                bg-white
                border
                border-slate-200
                shadow-[0_4px_14px_rgba(0,0,0,0.06)]
                dark:bg-white/[0.035]
                dark:border-white/[0.08]
                dark:shadow-[0_8px_30px_rgba(0,0,0,0.35)]
                dark:backdrop-blur-sm
              "
            >
              <div className="mb-5 flex items-center gap-2 text-base font-semibold text-slate-900 dark:text-white">
                <TeamOutlined className="text-[#00BEB4]" />
                {groupName}
              </div>

              <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
                <div
                  className="
                    rounded-lg
                    border
                    border-slate-100
                    p-4
                    dark:border-white/[0.06]
                    dark:bg-white/[0.02]
                  "
                >
                  <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-white">
                    <ThunderboltOutlined className="text-[#00BEB4]" />
                    组员 Token 消耗趋势
                  </div>

                  <SingleGroupMemberMetricChart
                    title={`${groupName} Token 消耗`}
                    group={group}
                    isDark={isDark}
                    metricType="token"
                    chartType="bar"
                    className="h-[360px] w-full"
                  />
                </div>

                <div
                  className="
                    rounded-lg
                    border
                    border-slate-100
                    p-4
                    dark:border-white/[0.06]
                    dark:bg-white/[0.02]
                  "
                >
                  <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-white">
                    <MessageOutlined className="text-[#FBBF24]" />
                    组员问答次数对比
                  </div>

                  <SingleGroupMemberMetricChart
                    title={`${groupName} 问答次数`}
                    group={group}
                    isDark={isDark}
                    metricType="dialog"
                    chartType="bar"
                    className="h-[360px] w-full"
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const GroupDailyTokenLineChart = ({
  groups,
  isDark,
  className = 'h-[460px] w-full',
}) => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  const groupColors = [
    '#00BEB4',
    '#F87171',
    '#FB923C',
    '#A78BFA',
    '#60A5FA',
    '#FBBF24',
    '#34D399',
    '#22D3EE',
    '#C084FC',
    '#F472B6',
  ];

  useEffect(() => {
    if (!chartRef.current) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const safeGroups = Array.isArray(groups) ? groups : [];

    const dateSet = new Set();

    safeGroups.forEach((group) => {
      const dailyTokens = Array.isArray(group.daily_tokens)
        ? group.daily_tokens
        : [];

      dailyTokens.forEach((item) => {
        if (item.date) {
          dateSet.add(item.date);
        }
      });
    });

    const dates = Array.from(dateSet).sort();

    const hasData = safeGroups.some((group) => {
      return (
        Array.isArray(group.daily_tokens) &&
        group.daily_tokens.some((item) => Number(item.tokens || 0) > 0)
      );
    });

    const series = safeGroups.map((group, index) => {
      const groupName = group.group_name || group.group_id;
      const groupColor = groupColors[index % groupColors.length];

      const tokenMap = new Map(
        (group.daily_tokens || []).map((item) => [
          item.date,
          Number(item.tokens || 0),
        ]),
      );

      return {
        name: groupName,
        type: 'line',
        smooth: true,
        symbolSize: 7,
        data: dates.map((date) => tokenMap.get(date) || 0),
        itemStyle: {
          color: groupColor,
        },
        lineStyle: {
          color: groupColor,
          width: 3,
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              {
                offset: 0,
                color: `${groupColor}44`,
              },
              {
                offset: 1,
                color: `${groupColor}00`,
              },
            ],
          },
        },
      };
    });

    const option = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: isDark ? '#1b1b1d' : '#ffffff',
        borderColor: isDark ? 'rgba(0,190,180,0.35)' : '#dddddd',
        textStyle: {
          color: isDark ? '#f8fafc' : '#333333',
        },
        formatter: (params) => {
          if (!params?.length) return '';

          let html = `<div style="margin-bottom: 6px;">${params[0].axisValue}</div>`;

          params.forEach((item) => {
            html += `
              <div>
                <span style="
                  display:inline-block;
                  width:8px;
                  height:8px;
                  border-radius:50%;
                  background:${item.color};
                  margin-right:6px;
                "></span>
                ${item.seriesName}：${Number(item.value || 0).toLocaleString()}
              </div>
            `;
          });

          return html;
        },
      },
      legend: {
        top: 0,
        type: 'scroll',
        textStyle: {
          color: isDark ? '#cbd5e1' : '#666666',
        },
        pageTextStyle: {
          color: isDark ? '#cbd5e1' : '#666666',
        },
      },
      grid: {
        left: 70,
        right: 40,
        top: 70,
        bottom: dates.length > 8 ? 90 : 50,
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: {
          interval: 0,
          rotate: dates.length > 8 ? 35 : 0,
          color: isDark ? '#cbd5e1' : '#666666',
        },
        axisLine: {
          lineStyle: {
            color: isDark ? 'rgba(255,255,255,0.18)' : '#dddddd',
          },
        },
        axisTick: {
          show: false,
        },
      },
      yAxis: {
        type: 'value',
        name: 'Token',
        nameTextStyle: {
          color: isDark ? '#cbd5e1' : '#666666',
        },
        axisLabel: {
          color: isDark ? '#cbd5e1' : '#666666',
          formatter: (value) => Number(value || 0).toLocaleString(),
        },
        splitLine: {
          lineStyle: {
            color: isDark ? 'rgba(255,255,255,0.08)' : '#eeeeee',
          },
        },
      },
      dataZoom:
        dates.length > 14
          ? [
              {
                type: 'slider',
                start: 0,
                end: Math.min(100, Math.floor((14 / dates.length) * 100)),
                bottom: 12,
                height: 24,
                borderColor: isDark ? 'rgba(255,255,255,0.12)' : '#dddddd',
                textStyle: {
                  color: isDark ? '#cbd5e1' : '#666666',
                },
                backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : '#f5f5f5',
                fillerColor: isDark
                  ? 'rgba(0,190,180,0.25)'
                  : 'rgba(0,190,180,0.18)',
              },
            ]
          : [],
      graphic: !hasData
        ? {
            type: 'text',
            left: 'center',
            top: 'middle',
            style: {
              text: '暂无每日 Token 数据',
              fontSize: 15,
              fill: isDark ? '#94a3b8' : '#999999',
            },
          }
        : null,
      series,
    };

    chartInstance.current.setOption(option, true);

    const handleResize = () => {
      chartInstance.current?.resize();
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [groups, isDark]);

  useEffect(() => {
    return () => {
      chartInstance.current?.dispose();
      chartInstance.current = null;
    };
  }, []);

  return <div ref={chartRef} className={className} />;
};

const GroupDailyTokenChartCard = ({ groups, isDark }) => {
  return (
    <div className="mt-[22px]">
      <div className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900 dark:text-white">
        <LineChartOutlined className="text-[#fa8c16]" />
        各组tokens使用趋势图
      </div>
      <div
        className="
        mt-[22px]
        rounded-xl
        p-5
        bg-white
        border
        border-slate-200
        shadow-[0_4px_14px_rgba(0,0,0,0.06)]
        dark:bg-white/[0.035]
        dark:border-white/[0.08]
        dark:shadow-[0_8px_30px_rgba(0,0,0,0.35)]
        dark:backdrop-blur-sm
      "
      >
        <div className="mb-3 flex items-center gap-2 text-base font-semibold text-slate-900 dark:text-white">
          <ThunderboltOutlined className="text-[#00BEB4]" />
          各组每日 Token 消耗趋势
        </div>

        <GroupDailyTokenLineChart
          groups={groups}
          isDark={isDark}
          className="h-[460px] w-full"
        />
      </div>
    </div>
  );
};

/**
 * 主页面
 */

const periodOptions = [
  { label: '全部', value: 'all' },
  { label: '天', value: 'day' },
  { label: '周', value: 'week' },
  { label: '月', value: 'month' },
  { label: '年', value: 'year' },
];

const GroupStatsDashboard = () => {
  const [switchSide, setSwitchSide] = useState<'left' | 'right'>('left');
  const navigate = useNavigate();
  const handleGoLog = useCallback(() => {
    setSwitchSide('right');

    window.setTimeout(() => {
      navigate('/dialog');
    }, 250);
  }, [navigate]);

  const [backendData, setBackendData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [period, setPeriod] = useState('all');
  const isDark = useIsDark();

  /**
   * 防止 React StrictMode 开发环境请求两次
   */
  const fetchingRef = useRef(false);
  const didInitFetchRef = useRef(false);

  //   const fetchData = useCallback(async () => {
  //     if (fetchingRef.current) {
  //       return;
  //     }

  //     fetchingRef.current = true;

  //     try {
  //       setLoading(true);
  //       setErrorMsg('');

  //       const res = await fetch('/v1/api/group_member_stats', {
  //         method: 'GET',
  //         credentials: 'include',
  //         headers: {
  //           'Content-Type': 'application/json',
  //         },
  //       });

  //       if (!res.ok) {
  //         throw new Error(`接口请求失败，状态码：${res.status}`);
  //       }

  //       const json = await res.json();

  //       let list = [];

  //       if (Array.isArray(json)) {
  //         list = json;
  //       } else if (Array.isArray(json.data)) {
  //         list = json.data;
  //       } else {
  //         throw new Error('接口返回格式不正确');
  //       }

  //       setBackendData(list);
  //     } catch (error) {
  //       console.error('获取组统计数据失败:', error);
  //       setErrorMsg(error instanceof Error ? error.message : '获取数据失败');
  //     } finally {
  //       setLoading(false);
  //       fetchingRef.current = false;
  //     }
  //   }, []);
  const fetchData = useCallback(
    async (periodValue = period) => {
      if (fetchingRef.current) {
        return;
      }

      fetchingRef.current = true;

      try {
        setLoading(true);
        setErrorMsg('');

        const res = await fetch('/v1/api/group_member_stats', {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            period: periodValue,
          }),
        });

        if (!res.ok) {
          throw new Error(`接口请求失败，状态码：${res.status}`);
        }

        const json = await res.json();

        let list = [];

        if (Array.isArray(json)) {
          list = json;
        } else if (Array.isArray(json.data)) {
          list = json.data;
        } else {
          throw new Error('接口返回格式不正确');
        }

        setBackendData(list);
      } catch (error) {
        console.error('获取组统计数据失败:', error);
        setErrorMsg(error instanceof Error ? error.message : '获取数据失败');
      } finally {
        setLoading(false);
        fetchingRef.current = false;
      }
    },
    [period],
  );

  const handlePeriodChange = useCallback(
    (nextPeriod) => {
      if (nextPeriod === period) return;

      setPeriod(nextPeriod);
      fetchData(nextPeriod);
    },
    [period, fetchData],
  );

  useEffect(() => {
    if (didInitFetchRef.current) {
      return;
    }

    didInitFetchRef.current = true;
    fetchData();
  }, [fetchData]);

  const tokenPieData = useMemo(() => {
    return backendData.map((item) => ({
      name: item.group_name || item.group_id,
      value: Number(item.total_tokens || 0),
    }));
  }, [backendData]);

  const dialogPieData = useMemo(() => {
    return backendData.map((item) => ({
      name: item.group_name || item.group_id,
      value: Number(item.total_dialogs || 0),
    }));
  }, [backendData]);

  const totalTokens = useMemo(() => {
    return backendData.reduce(
      (sum, item) => sum + Number(item.total_tokens || 0),
      0,
    );
  }, [backendData]);

  const totalDialogs = useMemo(() => {
    return backendData.reduce(
      (sum, item) => sum + Number(item.total_dialogs || 0),
      0,
    );
  }, [backendData]);

  const totalGroups = useMemo(() => {
    return backendData.length;
  }, [backendData]);

  const totalMembers = useMemo(() => {
    return backendData.reduce(
      (sum, item) => sum + Number(item.members?.length || 0),
      0,
    );
  }, [backendData]);

  const thClassName = `
    px-3
    py-[13px]
    border-b
    border-slate-200
    font-bold
    whitespace-nowrap
    text-slate-800
    dark:border-white/[0.08]
    dark:text-white
  `;

  const tdClassName = `
    px-3
    py-[13px]
    border-b
    border-slate-200
    text-slate-600
    dark:border-white/[0.06]
    dark:text-slate-300
  `;

  if (loading) {
    return (
      <DashboardShell>
        <div
          className="
            flex
            min-h-[calc(100vh-48px)]
            items-center
            justify-center
            text-base
            text-slate-500
            dark:text-slate-400
          "
        >
          数据加载中...
        </div>
      </DashboardShell>
    );
  }

  if (errorMsg) {
    return (
      <DashboardShell>
        <div
          className="
            flex
            min-h-[calc(100vh-48px)]
            items-center
            justify-center
            text-base
            text-red-500
          "
        >
          {errorMsg}
        </div>
      </DashboardShell>
    );
  }

  return (
  <DashboardShell>
    <div className="flex h-full flex-col overflow-hidden rounded-3xl bg-[#f8fbfa] shadow-[0_12px_40px_rgba(0,0,0,0.08)] dark:bg-[#0b1715]">
      {/* 顶部绿色标题栏 */}
      <div
        className="
          flex
          h-14
          shrink-0
          items-center
          justify-between
          bg-gradient-to-r
          from-[#0f7a4f]
          via-[#13966d]
          to-[#17b890]
          px-5
          text-white
        "
      >
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/18">
            <TeamOutlined className="text-lg" />
          </div>

          <div>
            <div className="text-lg font-bold tracking-wide">
              团队数据可视化大屏
            </div>
            <div className="text-xs text-white/75">
              Team Data Visualization Dashboard
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* 周期筛选 */}
          <div className="flex overflow-hidden rounded-full bg-white/15 p-1">
            {periodOptions.map((item) => {
              const active = period === item.value;

              return (
                <button
                  key={item.value}
                  onClick={() => handlePeriodChange(item.value)}
                  className={`
                    h-7
                    rounded-full
                    px-3
                    text-xs
                    transition-all
                    ${
                      active
                        ? 'bg-white text-[#0f7a4f] shadow-sm'
                        : 'text-white/85 hover:bg-white/10'
                    }
                  `}
                >
                  {item.label}
                </button>
              );
            })}
          </div>

          <button
            onClick={() => fetchData(period)}
            disabled={fetchingRef.current}
            className="
              flex
              h-8
              items-center
              gap-1.5
              rounded-full
              bg-white/15
              px-3
              text-xs
              text-white
              transition-colors
              hover:bg-white/25
              disabled:opacity-60
            "
          >
            <ReloadOutlined />
            刷新
          </button>

          <button
            onClick={handleGoLog}
            className="
              h-8
              rounded-full
              bg-white
              px-4
              text-xs
              font-semibold
              text-[#0f7a4f]
              shadow-sm
              transition
              hover:bg-[#ecfdf5]
            "
          >
            查看日志
          </button>
        </div>
      </div>

      {/* 主体区域 */}
      <div className="grid min-h-0 flex-1 grid-cols-12 gap-3 p-3">
        {/* 左侧导航/概览栏 */}
        <div className="col-span-2 flex min-h-0 flex-col gap-3">
          <BigScreenPanel className="shrink-0 overflow-hidden">
            <div className="bg-gradient-to-r from-[#ff5f9e] to-[#ff8cc6] px-4 py-3 text-white">
              <div className="text-sm font-bold">数据总览</div>
              <div className="text-xs text-white/80">Overview</div>
            </div>

            <div className="grid grid-cols-2 gap-2 p-3">
              <div className="rounded-xl bg-[#fff1f6] p-3">
                <div className="text-xs text-slate-500">Token</div>
                <div className="mt-1 text-lg font-black text-[#ec4899]">
                  {Number(totalTokens || 0).toLocaleString()}
                </div>
              </div>

              <div className="rounded-xl bg-[#eef8ff] p-3">
                <div className="text-xs text-slate-500">问答</div>
                <div className="mt-1 text-lg font-black text-[#3b82f6]">
                  {Number(totalDialogs || 0).toLocaleString()}
                </div>
              </div>

              <div className="rounded-xl bg-[#f4f0ff] p-3">
                <div className="text-xs text-slate-500">组数</div>
                <div className="mt-1 text-lg font-black text-[#8b5cf6]">
                  {Number(totalGroups || 0).toLocaleString()}
                </div>
              </div>

              <div className="rounded-xl bg-[#ecfdf5] p-3">
                <div className="text-xs text-slate-500">成员</div>
                <div className="mt-1 text-lg font-black text-[#10b981]">
                  {Number(totalMembers || 0).toLocaleString()}
                </div>
              </div>
            </div>
          </BigScreenPanel>

          <BigScreenPanel className="min-h-0 flex-1 overflow-hidden">
            <BigScreenTitle
              icon={<TeamOutlined className="text-[#13966d]" />}
              title="团队列表"
            />

            <div className="h-full overflow-y-auto px-3 py-2">
              {backendData.map((item, index) => (
                <div
                  key={item.group_id}
                  className="
                    mb-2
                    rounded-xl
                    bg-gradient-to-r
                    from-[#f5fbf8]
                    to-white
                    p-3
                    shadow-sm
                    dark:from-white/[0.04]
                    dark:to-white/[0.02]
                  "
                >
                  <div className="flex items-center justify-between">
                    <div className="min-w-0 text-sm font-bold text-slate-700 dark:text-white">
                      <span className="mr-2 inline-flex h-5 w-5 items-center justify-center rounded-full bg-[#13966d] text-[10px] text-white">
                        {index + 1}
                      </span>
                      <span className="truncate">
                        {item.group_name || item.group_id}
                      </span>
                    </div>
                  </div>

                  <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] text-slate-500">
                    <div>
                      Token：
                      <span className="font-bold text-[#ec4899]">
                        {Number(item.total_tokens || 0).toLocaleString()}
                      </span>
                    </div>
                    <div>
                      问答：
                      <span className="font-bold text-[#3b82f6]">
                        {Number(item.total_dialogs || 0).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </BigScreenPanel>
        </div>

        {/* 中间主区域 */}
        <div className="col-span-7 grid min-h-0 grid-rows-[220px_1fr_230px] gap-3">
          {/* 上方两个饼图 */}
          <div className="grid min-h-0 grid-cols-2 gap-3">
            <BigScreenPanel className="min-h-0 overflow-hidden">
              <BigScreenTitle
                icon={<Box className="h-4 w-4 text-[#ff7a45]" />}
                title="模型 Token 消耗占比"
              />

              <PieChart
                title="各组 Token 消耗占比"
                chartData={tokenPieData}
                isDark={isDark}
                className="h-[170px] w-full"
              />
            </BigScreenPanel>

            <BigScreenPanel className="min-h-0 overflow-hidden">
              <BigScreenTitle
                icon={<MessagesSquare className="h-4 w-4 text-[#3b82f6]" />}
                title="问答次数占比"
              />

              <PieChart
                title="各组问答次数占比"
                chartData={dialogPieData}
                isDark={isDark}
                className="h-[170px] w-full"
              />
            </BigScreenPanel>
          </div>

          {/* 中间主趋势图 */}
          <BigScreenPanel className="min-h-0 overflow-hidden">
            <BigScreenTitle
              icon={<LineChartOutlined className="text-[#13966d]" />}
              title="各组每日 Token 消耗趋势"
              right={
                <span className="rounded-full bg-[#ecfdf5] px-3 py-1 text-xs text-[#13966d]">
                  Daily Trend
                </span>
              }
            />

            <GroupDailyTokenLineChart
              groups={backendData}
              isDark={isDark}
              className="h-[330px] w-full"
            />
          </BigScreenPanel>

          {/* 底部组明细表 */}
          <BigScreenPanel className="min-h-0 overflow-hidden">
            <BigScreenTitle
              icon={<TableOutlined className="text-[#8b5cf6]" />}
              title="组统计明细"
            />

            <div className="h-[180px] overflow-y-auto px-4 py-2">
              <table className="w-full border-collapse text-center text-xs">
                <thead className="sticky top-0 z-10 bg-white dark:bg-[#111]">
                  <tr className="text-slate-500">
                    <th className="py-2">组名称</th>
                    <th className="py-2">Token 消耗</th>
                    <th className="py-2">问答次数</th>
                    <th className="py-2">成员数</th>
                  </tr>
                </thead>

                <tbody>
                  {backendData.length > 0 ? (
                    backendData.map((item) => (
                      <tr
                        key={item.group_id}
                        className="border-t border-slate-100 hover:bg-[#f8fafc] dark:border-white/[0.06]"
                      >
                        <td className="py-2 font-semibold text-slate-700 dark:text-slate-200">
                          {item.group_name || item.group_id}
                        </td>
                        <td className="py-2 text-[#ec4899]">
                          {Number(item.total_tokens || 0).toLocaleString()}
                        </td>
                        <td className="py-2 text-[#3b82f6]">
                          {Number(item.total_dialogs || 0).toLocaleString()}
                        </td>
                        <td className="py-2 text-[#10b981]">
                          {item.members?.length || 0}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="py-8 text-slate-400">
                        暂无数据
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </BigScreenPanel>
        </div>

        {/* 右侧成员分析区域 */}
        <div className="col-span-3 flex min-h-0 flex-col gap-3">
          {/* 右上粉紫色强调卡 */}
          <BigScreenPanel className="shrink-0 overflow-hidden">
            <div
              className="
                relative
                overflow-hidden
                bg-gradient-to-br
                from-[#ff5f9e]
                via-[#d946ef]
                to-[#8b5cf6]
                p-4
                text-white
              "
            >
              <div className="relative z-10">
                <div className="text-sm font-bold">团队活跃度</div>
                <div className="mt-1 text-xs text-white/75">
                  Activity Summary
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="rounded-2xl bg-white/18 p-3">
                    <div className="text-xs text-white/75">平均 Token</div>
                    <div className="mt-1 text-xl font-black">
                      {totalGroups > 0
                        ? Math.round(totalTokens / totalGroups).toLocaleString()
                        : 0}
                    </div>
                  </div>

                  <div className="rounded-2xl bg-white/18 p-3">
                    <div className="text-xs text-white/75">平均问答</div>
                    <div className="mt-1 text-xl font-black">
                      {totalGroups > 0
                        ? Math.round(totalDialogs / totalGroups).toLocaleString()
                        : 0}
                    </div>
                  </div>
                </div>
              </div>

              <div className="absolute -right-8 -top-8 h-28 w-28 rounded-full bg-white/20" />
              <div className="absolute -bottom-10 right-10 h-24 w-24 rounded-full bg-white/10" />
            </div>
          </BigScreenPanel>

          {/* 分组成员图表 */}
          <BigScreenPanel className="min-h-0 flex-1 overflow-hidden">
            <BigScreenTitle
              icon={<TeamOutlined className="text-[#ec4899]" />}
              title="组内成员使用统计"
            />

            <div className="h-full overflow-y-auto p-3">
              {backendData.map((group) => {
                const groupName = group.group_name || group.group_id;

                return (
                  <div
                    key={group.group_id}
                    className="
                      mb-3
                      rounded-2xl
                      border
                      border-slate-100
                      bg-[#fbfbff]
                      p-3
                      dark:border-white/[0.06]
                      dark:bg-white/[0.03]
                    "
                  >
                    <div className="mb-2 flex items-center justify-between">
                      <div className="flex items-center gap-2 text-sm font-bold text-slate-800 dark:text-white">
                        <span className="h-2 w-2 rounded-full bg-[#13966d]" />
                        {groupName}
                      </div>

                      <span className="rounded-full bg-[#ecfdf5] px-2 py-0.5 text-[11px] text-[#13966d]">
                        {group.members?.length || 0} 人
                      </span>
                    </div>

                    <div className="mb-2 rounded-xl bg-white p-2 shadow-sm dark:bg-white/[0.03]">
                      <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300">
                        <ThunderboltOutlined className="text-[#00BEB4]" />
                        组员 Token 消耗
                      </div>

                      <SingleGroupMemberMetricChart
                        title={`${groupName} Token 消耗`}
                        group={group}
                        isDark={isDark}
                        metricType="token"
                        chartType="bar"
                        className="h-[150px] w-full"
                      />
                    </div>

                    <div className="rounded-xl bg-white p-2 shadow-sm dark:bg-white/[0.03]">
                      <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300">
                        <MessageOutlined className="text-[#FBBF24]" />
                        组员问答次数
                      </div>

                      <SingleGroupMemberMetricChart
                        title={`${groupName} 问答次数`}
                        group={group}
                        isDark={isDark}
                        metricType="dialog"
                        chartType="bar"
                        className="h-[150px] w-full"
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </BigScreenPanel>
        </div>
      </div>
    </div>
  </DashboardShell>
);
};

export default GroupStatsDashboard;
