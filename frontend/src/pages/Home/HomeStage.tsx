import Live2D from './Canvas.tsx'

export function HomeStage() {
    return (
        <div
            className={'h-full w-full ml-2 mt-5 rounded-[2rem] border border-sky-200/80 bg-white/70 shadow-[0_24px_70px_rgba(148,197,255,0.25)] backdrop-blur-2xl flex flex-col items-center justify-center gap-4 p-4'}>
            <div className={'h-[75%]'}>
                <Live2D></Live2D>
            </div>
            <div className={'h-[25%]'}>
                用来展示当前角色状态，语言
            </div>
        </div>
    );
}
