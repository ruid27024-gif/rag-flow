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
import './GroupMemberStatsPage.css';

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
    <div className="relative h-screen overflow-y-auto p-6">{children}</div>
  );
};

/**
 * 顶部统计卡片
 */
const formatCompactStat = (value) => {
  const numericValue = Number(value || 0);

  if (!Number.isFinite(numericValue)) {
    return '0';
  }

  if (Math.abs(numericValue) >= 100000000) {
    return `${(numericValue / 100000000).toFixed(1).replace(/\.0$/, '')}亿`;
  }

  if (Math.abs(numericValue) >= 10000) {
    return `${(numericValue / 10000).toFixed(1).replace(/\.0$/, '')}万`;
  }

  if (Number.isInteger(numericValue)) {
    return numericValue.toLocaleString();
  }

  return numericValue.toFixed(1).replace(/\.0$/, '');
};

const StatCard = ({
  title,
  value,
  icon,
  accentColor,
  insightLabel,
  insightValue,
  compact = false,
}) => {
  return (
    <div
      className={`
        group
        relative
        flex-1
        flex
        min-w-0
        flex-col
        items-center
        rounded-xl
        text-center
        transition-all
        duration-300
        ease-out
        hover:-translate-y-0.5
        hover:bg-slate-50
        dark:hover:bg-white/[0.04]
        ${compact ? 'px-1 py-1.5' : 'px-4 py-3'}
      `}
    >
      <div
        className={`
          flex
          flex-col
          items-center
          justify-center
          rounded-full
          bg-white
          shadow-[inset_0_0_0_1px_rgba(148,163,184,0.18)]
          dark:bg-white/[0.03]
          dark:shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]
          ${compact ? 'h-[46px] w-[46px] border-[4px]' : 'h-[76px] w-[76px] border-[6px]'}
        `}
        style={{ borderColor: `${accentColor}33` }}
      >
        <div
          className={`
            truncate
            font-extrabold
            leading-none
            tabular-nums
            ${compact ? 'max-w-[34px] text-[11px]' : 'max-w-[58px] text-[16px]'}
          `}
          style={{ color: accentColor }}
          title={String(insightValue)}
        >
          {insightValue}
        </div>
        <div
          className={`
            font-semibold
            leading-none
            text-slate-400
            dark:text-slate-500
            ${compact ? 'mt-0.5 text-[8px]' : 'mt-1 text-[10px]'}
          `}
        >
          {insightLabel}
        </div>
      </div>

      <div
        className={`
          max-w-full
          break-all
          font-extrabold
          leading-none
          tabular-nums
          ${compact ? 'mt-2 text-[14px]' : 'mt-3 text-[22px]'}
        `}
        style={{ color: accentColor }}
      >
        {Number(value || 0).toLocaleString()}
      </div>

      <div
        className={`
          flex
          items-center
          justify-center
          rounded-lg
          border-2
          bg-white
          transition-transform
          duration-300
          group-hover:scale-105
          dark:bg-white/[0.03]
          ${compact ? 'mt-2 h-8 w-8' : 'mt-4 h-11 w-11'}
        `}
        style={{
          borderColor: accentColor,
          color: accentColor,
        }}
      >
        {icon}
      </div>

      <div
        className={`
          font-semibold
          leading-[1.2]
          text-slate-700
          dark:text-slate-200
          ${compact ? 'mt-2 max-w-[62px] text-[10px]' : 'mt-3 max-w-[118px] text-[12px]'}
        `}
      >
        {title}
      </div>
    </div>
  );
};

/**
 * 图表卡片
 */
const ChartCard = ({ title, icon, children, hideHeader = false }) => {
  return (
    <div
      className={`
        flex-1
        min-w-[400px]
        rounded-xl
        ${
          hideHeader
            ? ''
            : `
              p-5
              bg-white
              border
              border-slate-200
              shadow-[0_4px_14px_rgba(0,0,0,0.06)]
              dark:bg-white/[0.035]
              dark:border-white/[0.08]
              dark:shadow-[0_8px_30px_rgba(0,0,0,0.35)]
              dark:backdrop-blur-sm
            `
        }
      `}
    >
      {!hideHeader && (
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
      )}

      {children}
    </div>
  );
};

/**
 * 饼图组件
 */
const pieBaseColors = [
  '#ec4899',
  '#0ea5e9',
  '#0891b2',
  '#ef4444',
  '#f97316',
  '#fb7185',
  '#64748b',
  '#1f2937',
  '#fb7185',
  '#0284c7',
  '#dc2626',
  '#c2410c',
];

const hslToHex = (h, s, l) => {
  const saturation = s / 100;
  const lightness = l / 100;
  const chroma = (1 - Math.abs(2 * lightness - 1)) * saturation;
  const huePrime = h / 60;
  const x = chroma * (1 - Math.abs((huePrime % 2) - 1));
  const match = lightness - chroma / 2;

  let red = 0;
  let green = 0;
  let blue = 0;

  if (huePrime >= 0 && huePrime < 1) {
    red = chroma;
    green = x;
  } else if (huePrime >= 1 && huePrime < 2) {
    red = x;
    green = chroma;
  } else if (huePrime >= 2 && huePrime < 3) {
    green = chroma;
    blue = x;
  } else if (huePrime >= 3 && huePrime < 4) {
    green = x;
    blue = chroma;
  } else if (huePrime >= 4 && huePrime < 5) {
    red = x;
    blue = chroma;
  } else {
    red = chroma;
    blue = x;
  }

  const toHex = (value) => {
    return Math.round((value + match) * 255)
      .toString(16)
      .padStart(2, '0');
  };

  return `#${toHex(red)}${toHex(green)}${toHex(blue)}`;
};

const getPieChartColor = (index) => {
  if (index < pieBaseColors.length) {
    return pieBaseColors[index];
  }

  const allowedHues = [205, 216, 228, 345, 355, 8, 18, 28, 335, 198, 212, 2];
  const cycle = Math.floor(index / allowedHues.length);
  const hue = allowedHues[index % allowedHues.length];
  const saturation = 62 + ((cycle * 9) % 22);
  const lightness = 42 + ((cycle * 7) % 16);

  return hslToHex(hue, saturation, lightness);
};

const PieChart = ({
  title,
  chartData,
  isDark,
  className = 'h-[400px] w-full',
}) => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  const total = useMemo(() => {
    if (!Array.isArray(chartData)) return 0;

    return chartData.reduce((sum, item) => {
      return sum + Number(item.value || 0);
    }, 0);
  }, [chartData]);
  const hasChartData =
    Array.isArray(chartData) && chartData.some((item) => item.value > 0);

  useEffect(() => {
    if (!chartRef.current) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const safeData = Array.isArray(chartData) ? chartData : [];

    const hasData = safeData.some((item) => Number(item.value || 0) > 0);

    const colorList = safeData.map((_, index) => getPieChartColor(index));

    const displayData = hasData
      ? safeData.map((item, index) => ({
          name: item.name,
          value: Number(item.value || 0),
          itemStyle: {
            color: colorList[index % colorList.length],
          },
        }))
      : [
          {
            name: '暂无数据',
            value: 1,
            itemStyle: {
              color: isDark ? 'rgba(255,255,255,0.12)' : '#e5e7eb',
            },
          },
        ];

    const option = {
      backgroundColor: 'transparent',

      color: colorList,

      tooltip: {
        trigger: 'item',
        confine: true,
        backgroundColor: isDark ? '#1b1b1d' : '#ffffff',
        borderColor: isDark ? 'rgba(255,255,255,0.16)' : '#e5e7eb',
        textStyle: {
          color: isDark ? '#f8fafc' : '#334155',
        },
        formatter: (params) => {
          if (!hasData) {
            return '暂无数据';
          }

          return `
            <div style="min-width: 120px;">
              <div style="font-weight: 700; margin-bottom: 6px;">
                ${params.name}
              </div>
              <div>
                数值：
                <span style="font-weight: 700;">
                  ${Number(params.value || 0).toLocaleString()}
                </span>
              </div>
              <div>
                占比：
                <span style="font-weight: 700;">
                  ${params.percent}%
                </span>
              </div>
            </div>
          `;
        },
      },

      legend: {
        type: 'scroll',
        orient: 'vertical',
        right: 8,
        top: 'center',
        height: '78%',
        itemWidth: 10,
        itemHeight: 10,
        itemGap: 10,
        textStyle: {
          color: 'rgba(255,255,255,0.90)',
          fontSize: 12,
        },
        pageTextStyle: {
          color: 'rgba(255,255,255,0.90)',
        },
        pageIconColor: 'rgba(255,255,255,0.90)',
        pageIconInactiveColor: 'rgba(255,255,255,0.30)',
        formatter: (name) => {
          const current = safeData.find((item) => item.name === name);
          const value = Number(current?.value || 0);
          const percent = total > 0 ? Math.round((value / total) * 100) : 0;

          return `${name}  ${percent}%`;
        },
      },

      graphic: [],

      series: [
        {
          name: title,
          type: 'pie',

          // 圆环大小
          radius: ['52%', '76%'],

          // 往左一点，右边留给图例
          center: ['36%', '52%'],

          avoidLabelOverlap: true,

          minAngle: 3,

          itemStyle: {
            borderRadius: 6,
            borderColor: 'transparent',
            borderWidth: 0,
          },

          label: {
            show: true,
            position: 'outside',
            color: '#ffffff',
            fontSize: 12,
            formatter: (params) => {
              if (!hasData) return '';

              // 小于 3% 的不显示外部标签，避免太乱
              if (params.percent < 3) return '';

              return `${params.name}\n${params.percent}%`;
            },
          },

          labelLine: {
            show: true,
            length: 12,
            length2: 8,
            lineStyle: {
              color: 'rgba(255,255,255,0.55)',
            },
          },

          emphasis: {
            scale: true,
            scaleSize: 8,
            itemStyle: {
              shadowBlur: 16,
              shadowColor: 'rgba(34,197,94,0.35)',
            },
            label: {
              show: true,
              fontSize: 13,
              fontWeight: 'bold',
            },
          },

          data: displayData,
        },
      ],
    };

    chartInstance.current.setOption(option, true);

    const resizeTimer = window.setTimeout(() => {
      chartInstance.current?.resize();
    }, 0);

    const handleResize = () => {
      chartInstance.current?.resize();
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.clearTimeout(resizeTimer);
      window.removeEventListener('resize', handleResize);
    };
  }, [title, chartData, isDark, total]);

  useEffect(() => {
    const chartElement = chartRef.current;

    if (!chartElement || typeof ResizeObserver === 'undefined') {
      return undefined;
    }

    const resizeObserver = new ResizeObserver(() => {
      chartInstance.current?.resize();
    });

    resizeObserver.observe(chartElement);

    return () => {
      resizeObserver.disconnect();
    };
  }, []);

  useEffect(() => {
    return () => {
      chartInstance.current?.dispose();
      chartInstance.current = null;
    };
  }, []);

  return (
    <div
      className={`${className} relative overflow-hidden rounded-xl`}
      style={{
        background:
          'linear-gradient(135deg, #86efac 0%, #34d399 52%, #2dd4bf 100%)',
        boxShadow: '0 12px 24px rgba(34,197,94,0.18)',
      }}
    >
      <div
        className="
          pointer-events-none
          absolute
          z-20
          max-w-[128px]
          -translate-x-1/2
          -translate-y-1/2
          text-center
          text-white
        "
        style={{
          left: '36%',
          top: '52%',
        }}
      >
        <div className="text-[13px] font-extrabold leading-tight">{title}</div>
        <div className="mt-3 text-[24px] font-black leading-none tabular-nums">
          {hasChartData ? Number(total || 0).toLocaleString() : '暂无数据'}
        </div>
      </div>
      <div ref={chartRef} className="relative z-10 h-full w-full" />
    </div>
  );
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
const memberChartColors = [
  '#00BEB4',
  '#F472B6',
  '#A78BFA',
  '#F59E0B',
  '#EF4444',
  '#22D3EE',
  '#60A5FA',
  '#34D399',
  '#F97316',
  '#C084FC',
];

const getMemberIdentity = (member, index) => {
  return member.user_id || member.nickname || `unknown-${index}`;
};

const getStableColorIndex = (value) => {
  return String(value)
    .split('')
    .reduce((sum, char) => sum + char.charCodeAt(0), 0);
};

const createMemberColorMap = (members) => {
  const usedColorIndexes = new Set();

  return members.reduce((map, member, index) => {
    const key = getMemberIdentity(member, index);
    let colorIndex = getStableColorIndex(key) % memberChartColors.length;

    while (
      usedColorIndexes.has(colorIndex) &&
      usedColorIndexes.size < memberChartColors.length
    ) {
      colorIndex = (colorIndex + 1) % memberChartColors.length;
    }

    usedColorIndexes.add(colorIndex);
    map[key] = memberChartColors[colorIndex];

    return map;
  }, {});
};

const SingleGroupMemberMetricChart = ({
  title,
  group,
  isDark,
  metricType,
  chartType = 'bar',
  orientation = 'vertical',
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
    const memberColorMap = createMemberColorMap(members);
    const isToken = metricType === 'token';
    const isHorizontal = orientation === 'horizontal';

    const memberItems = members.map((member, index) => {
      const key = getMemberIdentity(member, index);

      return {
        key,
        name: member.nickname || member.user_id || '未知成员',
        value: isToken
          ? Number(member.token_usage || 0)
          : Number(member.dialog_count || 0),
        color:
          memberColorMap[key] ||
          memberChartColors[index % memberChartColors.length],
      };
    });

    const displayItems = isHorizontal
      ? [...memberItems].sort((a, b) => b.value - a.value)
      : memberItems;

    const categories = displayItems.map((item) => item.name);
    const values = displayItems.map((item) => item.value);

    const hasData = values.some((value) => value > 0);

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
        left: isHorizontal ? 95 : 70,
        right: isHorizontal ? 58 : 35,
        top: 35,
        bottom: isHorizontal ? 35 : categories.length > 6 ? 90 : 55,
      },

      xAxis: {
        type: isHorizontal ? 'value' : 'category',
        name: isHorizontal && !isToken ? '次' : '',
        nameLocation: 'end',
        nameGap: 8,
        nameTextStyle: {
          color: isDark ? '#cbd5e1' : '#666666',
        },
        data: isHorizontal ? undefined : categories,
        axisTick: {
          alignWithLabel: true,
        },
        axisLabel: {
          interval: isHorizontal ? undefined : 0,
          rotate: !isHorizontal && categories.length > 6 ? 35 : 0,
          color: isDark ? '#cbd5e1' : '#666666',
          overflow: 'truncate',
          width: isHorizontal ? undefined : 100,
          align: !isHorizontal && categories.length > 6 ? 'right' : 'center',
          formatter: isHorizontal
            ? (value) => Number(value || 0).toLocaleString()
            : undefined,
        },
        axisLine: {
          lineStyle: {
            color: isDark ? 'rgba(255,255,255,0.18)' : '#dddddd',
          },
        },
      },

      yAxis: {
        type: isHorizontal ? 'category' : 'value',
        data: isHorizontal ? categories : undefined,
        inverse: isHorizontal,
        name: isHorizontal ? '' : isToken ? 'Token' : '次数',
        nameTextStyle: {
          color: isDark ? '#cbd5e1' : '#666666',
        },
        axisLabel: {
          color: isDark ? '#cbd5e1' : '#666666',
          overflow: 'truncate',
          width: isHorizontal ? 80 : undefined,
          formatter: isHorizontal
            ? undefined
            : (value) => Number(value || 0).toLocaleString(),
        },
        axisTick: {
          alignWithLabel: true,
        },
        axisLine: {
          lineStyle: {
            color: isDark ? 'rgba(255,255,255,0.18)' : '#dddddd',
          },
        },
        splitLine: {
          show: !isHorizontal,
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
          barWidth: chartType === 'bar' ? (isHorizontal ? 14 : 28) : undefined,
          barMaxWidth: chartType === 'bar' ? 40 : undefined,
          data: values,
          itemStyle: {
            color: (params) => {
              return displayItems[params.dataIndex]?.color || '#00BEB4';
            },
            borderRadius:
              chartType === 'bar'
                ? isHorizontal
                  ? [0, 999, 999, 0]
                  : [6, 6, 0, 0]
                : 0,
          },
          lineStyle:
            chartType === 'line'
              ? {
                  color: '#00BEB4',
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
                        color: '#00BEB455',
                      },
                      {
                        offset: 1,
                        color: '#00BEB400',
                      },
                    ],
                  },
                }
              : undefined,
          label:
            chartType === 'bar'
              ? {
                  show: true,
                  position: isHorizontal ? 'right' : 'top',
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
  }, [title, group, isDark, metricType, chartType, orientation]);

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
 * 一个 Token 竖向柱形图
 * 一个 问答次数横向柱形图
 */
const getGroupOptionValue = (group, index) => {
  return String(group.group_id || `${group.group_name || 'group'}-${index}`);
};

const getGroupDisplayName = (group) => {
  return group.group_name || group.group_id || '未命名组';
};

const GroupCombinedCharts = ({ groups, isDark }) => {
  const safeGroups = useMemo(() => {
    return Array.isArray(groups) ? groups : [];
  }, [groups]);

  const groupOptions = useMemo(() => {
    return safeGroups.map((group, index) => ({
      value: getGroupOptionValue(group, index),
      label: getGroupDisplayName(group),
    }));
  }, [safeGroups]);

  const [selectedGroupKey, setSelectedGroupKey] = useState('');

  useEffect(() => {
    setSelectedGroupKey((currentKey) => {
      if (!groupOptions.length) {
        return '';
      }

      const hasCurrentGroup = groupOptions.some((item) => {
        return item.value === currentKey;
      });

      return hasCurrentGroup ? currentKey : groupOptions[0].value;
    });
  }, [groupOptions]);

  const effectiveSelectedGroupKey =
    selectedGroupKey || groupOptions[0]?.value || '';

  const selectedGroup = useMemo(() => {
    const selectedIndex = groupOptions.findIndex((item) => {
      return item.value === effectiveSelectedGroupKey;
    });

    return selectedIndex >= 0 ? safeGroups[selectedIndex] : safeGroups[0];
  }, [effectiveSelectedGroupKey, groupOptions, safeGroups]);

  if (!safeGroups.length || !selectedGroup) {
    return null;
  }

  const selectedGroupName = getGroupDisplayName(selectedGroup);

  return (
    <div className="mt-[22px]">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-lg font-semibold text-slate-900 dark:text-white">
          <TeamOutlined className="text-[#00BEB4]" />
          组内成员使用统计
        </div>

        <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
          <span className="whitespace-nowrap">选择组</span>
          <select
            value={effectiveSelectedGroupKey}
            onChange={(event) => setSelectedGroupKey(event.target.value)}
            className="
              h-9
              min-w-[180px]
              rounded-md
              border
              border-slate-200
              bg-white
              px-3
              text-sm
              text-slate-700
              outline-none
              transition-colors
              hover:border-[#00BEB4]
              focus:border-[#00BEB4]
              focus:ring-2
              focus:ring-[#00BEB4]/15
              dark:border-white/[0.08]
              dark:bg-white/[0.035]
              dark:text-slate-200
            "
          >
            {groupOptions.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div
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
          {selectedGroupName}
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
              title={`${selectedGroupName} Token 消耗`}
              group={selectedGroup}
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
              title={`${selectedGroupName} 问答次数`}
              group={selectedGroup}
              isDark={isDark}
              metricType="dialog"
              chartType="bar"
              orientation="horizontal"
              className="h-[360px] w-full"
            />
          </div>
        </div>
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
      title: {
        text: '各组tokens使用趋势图',
        left: 0,
        top: 0,
        textStyle: {
          color: isDark ? '#f8fafc' : '#0f172a',
          fontSize: 15,
          fontWeight: 700,
        },
      },
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
        top: 28,
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
        top: 92,
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
    const chartElement = chartRef.current;

    if (!chartElement || typeof ResizeObserver === 'undefined') {
      return undefined;
    }

    const resizeObserver = new ResizeObserver(() => {
      chartInstance.current?.resize();
    });

    resizeObserver.observe(chartElement);

    return () => {
      resizeObserver.disconnect();
    };
  }, []);

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
    <div>
      <div
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

const PeriodBubbleSelector = ({ value = 'all', onChange }) => {
  const options = [
    { label: '全部', value: 'all' },
    { label: '天', value: 'day' },
    { label: '周', value: 'week' },
    { label: '月', value: 'month' },
    { label: '年', value: 'year' },
  ];

  const selectedValue = value || 'all';

  const current =
    options.find((item) => item.value === selectedValue) || options[0];

  return (
    <div
      className="
        relative
        flex
        items-center
        overflow-hidden
        text-white
      "
      style={{
        width: '100%',
        minWidth: 0,
        maxWidth: 380,
        height: 76,
        borderRadius: 38,
        paddingLeft: 22,
        paddingRight: 88,
        background:
          'linear-gradient(90deg, #86efac 0%, #4ade80 48%, #2dd4bf 100%)',
        boxShadow: '0 10px 24px rgba(34,197,94,0.22)',
      }}
    >
      {/* 背景装饰圆 */}
      <div
        className="pointer-events-none absolute rounded-full"
        style={{
          left: -34,
          top: -38,
          width: 108,
          height: 108,
          backgroundColor: 'rgba(255,255,255,0.14)',
        }}
      />

      <div
        className="pointer-events-none absolute rounded-full"
        style={{
          right: 78,
          bottom: -48,
          width: 120,
          height: 120,
          backgroundColor: 'rgba(255,255,255,0.10)',
        }}
      />

      {/* 左侧选项区：两行月份风格 */}
      <div
        className="
          relative
          z-10
          grid
          w-full
          grid-cols-3
          gap-x-5
          gap-y-2
          text-[12px]
          font-bold
          leading-none
        "
      >
        {options.map((item) => {
          const active = selectedValue === item.value;

          return (
            <button
              key={item.value}
              type="button"
              onClick={() => onChange(item.value)}
              className={`
                flex
                h-6
                items-center
                justify-center
                rounded-full
                px-2
                transition-all
                duration-200
                ${active ? 'text-white' : 'text-white/95 hover:bg-white/20'}
              `}
              style={
                active
                  ? {
                      backgroundColor: '#059669',
                      boxShadow: '0 4px 10px rgba(5,150,105,0.30)',
                    }
                  : undefined
              }
            >
              {item.label}
            </button>
          );
        })}
      </div>

      {/* 右侧白色圆圈：显示当前选中 */}
      <div
        style={{
          position: 'absolute',
          right: 10,
          top: '50%',
          zIndex: 50,
          width: 62,
          height: 62,
          transform: 'translateY(-50%)',
          borderRadius: '9999px',
          backgroundColor: '#ffffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow:
            '0 8px 18px rgba(0,0,0,0.18), inset 0 0 0 6px rgba(34,197,94,0.14)',
        }}
      >
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: '9999px',
            backgroundColor: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#059669',
            fontSize: current.label.length > 1 ? 16 : 20,
            fontWeight: 900,
            lineHeight: 1,
            whiteSpace: 'nowrap',
            boxShadow: 'inset 0 2px 5px rgba(15,23,42,0.10)',
          }}
        >
          {current.label}
        </div>
      </div>
    </div>
  );
};

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

  const activeGroups = useMemo(() => {
    return backendData.filter((item) => {
      return (
        Number(item.total_tokens || 0) > 0 ||
        Number(item.total_dialogs || 0) > 0
      );
    }).length;
  }, [backendData]);

  const averageTokensPerGroup = totalGroups > 0 ? totalTokens / totalGroups : 0;
  const averageDialogsPerGroup =
    totalGroups > 0 ? totalDialogs / totalGroups : 0;
  const averageMembersPerGroup =
    totalGroups > 0 ? totalMembers / totalGroups : 0;

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
      <div className="mb-3 flex flex-wrap items-start justify-between gap-4">
        <h1
          className="
      m-0
      flex
      items-center
      gap-2.5
      text-[28px]
      font-bold
      text-slate-900
      dark:text-white
    "
        >
          <TeamOutlined className="text-[#00BEB4]" />
          团队数据仪表盘
        </h1>

        <div className="flex shrink-0 items-center gap-3">
          {/* 刷新 */}
          <button
            onClick={() => fetchData(period)}
            disabled={fetchingRef.current}
            className="
          flex
          h-9
          cursor-pointer
          items-center
          gap-1.5
          rounded-md
          border
          border-[#00BEB4]
          bg-white
          px-4
          text-sm
          text-[#00BEB4]
          transition-colors
          hover:bg-[#00BEB4]/10
          disabled:cursor-not-allowed
          disabled:opacity-60
          dark:bg-white/[0.035]
          dark:hover:bg-white/[0.07]
        "
          >
            <ReloadOutlined />
            刷新
          </button>

          <div
            className={`
                  relative
                  flex
                  h-9
                  w-[160px]
                  items-center
                  rounded-full
                  border
                  border-slate-200
                  bg-slate-100
                  p-1
                  transition-colors
                  dark:border-white/[0.08]
                  dark:bg-white/[0.06]
                  ${switchSide === 'left' ? 'page-switch-left' : 'page-switch-right'}
              `}
          >
            <button
              type="button"
              className={`
                  relative z-10 flex-1 rounded-full text-sm transition-colors
                  ${
                    switchSide === 'left'
                      ? 'text-slate-900 dark:text-white'
                      : 'text-slate-500 dark:text-slate-400'
                  }
                  `}
              onClick={(event) => {
                event.preventDefault();
              }}
            >
              看板
            </button>

            <button
              type="button"
              className={`
                  relative z-10 flex-1 rounded-full text-sm transition-colors
                  ${
                    switchSide === 'right'
                      ? 'text-slate-900 dark:text-white'
                      : 'text-slate-500 dark:text-slate-400'
                  }
                  `}
              onClick={handleGoLog}
            >
              日志
            </button>

            <div
              className={`
                  absolute
                  top-1
                  h-7
                  w-[calc(50%-4px)]
                  rounded-full
                  bg-white
                  shadow-sm
                  transition-transform
                  duration-300
                  dark:bg-[#00BEB4]
                  ${
                    switchSide === 'left'
                      ? 'left-1 translate-x-0'
                      : 'left-1 translate-x-full'
                  }
                  `}
            />
          </div>
        </div>
      </div>

      <div className="group-dashboard-layout">
        <div className="dashboard-area-1-6">
          {/* 1号区域：总 Token 消耗 / 总问答次数 / 组数量 / 成员数量 */}
          <div className="dashboard-area-1 dashboard-panel">
            <div className="dashboard-section-title">
              <TeamOutlined className="text-[#00BEB4]" />
              总览
            </div>

            <div className="dashboard-overview-stats">
              <StatCard
                title="总 Token 消耗"
                value={totalTokens}
                accentColor="#D75A8B"
                insightLabel="组均"
                insightValue={formatCompactStat(averageTokensPerGroup)}
                icon={<Box className="h-4 w-4" />}
                compact
              />

              <StatCard
                title="总问答次数"
                value={totalDialogs}
                accentColor="#C85B9B"
                insightLabel="组均"
                insightValue={formatCompactStat(averageDialogsPerGroup)}
                icon={<MessagesSquare className="h-4 w-4" />}
                compact
              />

              <StatCard
                title="组数量"
                value={totalGroups}
                accentColor="#B55DB9"
                insightLabel="活跃组"
                insightValue={
                  totalGroups > 0 ? `${activeGroups}/${totalGroups}` : '0'
                }
                icon={<Users className="h-4 w-4" />}
                compact
              />

              <StatCard
                title="成员数量"
                value={totalMembers}
                accentColor="#D75A8B"
                insightLabel="组均"
                insightValue={formatCompactStat(averageMembersPerGroup)}
                icon={<UserCheck className="h-4 w-4" />}
                compact
              />
            </div>
          </div>

          {/* 6号区域：组统计明细 */}
          <div className="dashboard-area-6">
            <div>
              <div
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
                <h2
                  className="
            mb-4
            flex
            items-center
            gap-2
            text-lg
            font-semibold
            text-slate-900
            dark:text-white
          "
                >
                  <TableOutlined className="text-[#00BEB4]" />
                  明细表
                </h2>

                <div className="w-full overflow-x-auto">
                  <table className="w-full border-collapse text-left text-sm text-center">
                    <thead>
                      <tr className="bg-slate-100 dark:bg-white/[0.04]">
                        <th className={thClassName}>组名称</th>

                        <th className={thClassName}>
                          <ThunderboltOutlined className="mr-1.5 text-[#fa8c16]" />
                          Token 消耗
                        </th>

                        <th className={thClassName}>
                          <MessageOutlined className="mr-1.5 text-[#00BEB4]" />
                          问答次数
                        </th>

                        <th className={thClassName}>
                          <TeamOutlined className="mr-1.5 text-[#34D399]" />
                          成员数
                        </th>
                      </tr>
                    </thead>

                    <tbody>
                      {backendData.length > 0 ? (
                        backendData.map((item) => (
                          <tr
                            key={item.group_id}
                            className="
                      transition-colors
                      hover:bg-slate-50
                      dark:hover:bg-white/[0.04]
                    "
                          >
                            <td className={tdClassName}>{item.group_name}</td>

                            <td className={tdClassName}>
                              {Number(item.total_tokens || 0).toLocaleString()}
                            </td>

                            <td className={tdClassName}>
                              {Number(item.total_dialogs || 0).toLocaleString()}
                            </td>

                            <td className={tdClassName}>
                              {item.members?.length || 0}
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td
                            colSpan={4}
                            className="
                      p-[30px]
                      text-center
                      text-slate-400
                      dark:text-slate-500
                    "
                          >
                            暂无数据
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 2号区域：各组 tokens 使用趋势图 */}
        <div className="dashboard-area-2">
          <GroupDailyTokenChartCard groups={backendData} isDark={isDark} />
        </div>

        <div className="dashboard-area-3-4">
          {/* 3号区域：选择日期 */}
          <div className="dashboard-area-3">
            <div className="dashboard-period-wrapper">
              <PeriodBubbleSelector
                value={period}
                onChange={handlePeriodChange}
              />
            </div>
          </div>

          {/* 4号区域：组间对比，放在选择日期下方，同属第一排 */}
          <div className="dashboard-area-4">
            <div className="dashboard-compare-vertical">
              <div>
                <PieChart
                  title="模型Token消耗占比"
                  chartData={tokenPieData}
                  isDark={isDark}
                  className="dashboard-compare-chart"
                />
              </div>

              <div>
                <PieChart
                  title="问答次数占比"
                  chartData={dialogPieData}
                  isDark={isDark}
                  className="dashboard-compare-chart"
                />
              </div>
            </div>
          </div>
        </div>

        {/* 5号区域：组内成员使用统计 */}
        <div className="dashboard-area-5">
          <GroupCombinedCharts groups={backendData} isDark={isDark} />
        </div>
      </div>
    </DashboardShell>
  );
};

export default GroupStatsDashboard;
