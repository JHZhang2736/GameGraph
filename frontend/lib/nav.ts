export interface NavItem {
  href: string;
  label: string;
}

export interface NavGroup {
  title: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    title: "资料库",
    items: [
      { href: "/games", label: "游戏入库" },
      { href: "/graph", label: "知识图谱" },
    ],
  },
  {
    title: "创意流程",
    items: [
      { href: "/profile", label: "开发者画像" },
      { href: "/opportunities", label: "机会框架" },
      { href: "/concepts", label: "概念卡" },
      { href: "/prototype", label: "原型简报" },
    ],
  },
];

export const OVERVIEW_ITEM: NavItem = { href: "/overview", label: "总览" };
