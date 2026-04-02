import {useState} from "react";

import {HomeChatPanel} from "./HomeChatPanel";
import {HomeSidebar} from "./HomeSidebar";
import {HomeStage} from "./HomeStage";

export default function Home() {
    const [sidebarCollapsed, setSidebarCollapsed] = useState(true);

    return (
        // 1. 移除外层可能导致滚动问题的 overflow-x-auto，改用 flex 布局控制
        <div
            className="relative  flex h-screen w-full overflow-hidden bg-[linear-gradient(180deg,#f8fdff_0%,#ebf8ff_42%,#d7f0ff_100%)] text-slate-700">


            {/* 2. 侧边栏 */}
            <HomeSidebar
                collapsed={sidebarCollapsed}
                onToggle={() => setSidebarCollapsed((collapsed) => !collapsed)}
            />

            <div className={'w-[65%]'}>
                <HomeStage></HomeStage>
            </div>
            <div className={'flex-1'}>
                <HomeChatPanel></HomeChatPanel>
            </div>
        </div>
    );
}
