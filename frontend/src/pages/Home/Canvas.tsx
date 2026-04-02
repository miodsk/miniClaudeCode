import {Application, useApplication} from '@pixi/react'
import {Container} from 'pixi.js'
import {extend} from '@pixi/react'
import {useEffect, useRef, useState} from 'react'
import {Live2DModel} from 'untitled-pixi-live2d-engine/cubism-legacy'

extend({Live2DModel, Container})

export default function Live2D() {
    const containerRef = useRef(null);
    const [resizeTarget, setResizeTarget] = useState(undefined);

    useEffect(() => {
        // 组件挂载后，将父容器设置为 resize 目标
        if (containerRef.current) {
            setResizeTarget(containerRef.current);
        }
    }, []);

    return (
        <div
            ref={containerRef}
            className={'h-full w-full'}
        >
            {resizeTarget && (
                <Application
                    background={0x1099bb}
                    resizeTo={resizeTarget}
                    preference="webgl"
                >
                    <Live2DLayer/>
                </Application>
            )}
        </div>
    );
}

function Live2DLayer() {
    const {app} = useApplication()
    // 创建一个 ref 来存储 model 实例
    const modelRef = useRef<Live2DModel | null>(null)
    useEffect(() => {
        async function loadLive2DModel() {
            const model = await Live2DModel.from('/341_school_winter-2023_rip_外套敞开/model.json')
            model.eventMode = 'static';
            model.cursor = 'pointer';
            model.scale.set(0.2)
            model.anchor.set(0.5)
            model.position.set(app.screen.width / 2, app.screen.height * 2 / 5)
            app.stage.addChild(model)
            app.renderer.on('resize', (width: number, height: number) => {
                model.x = width / 2;
                model.y = height / 2;
            });
            model.on('hit', async (hitAreas) => {
                console.log('hitAreas', hitAreas);
                console.log('model', model.elapsedTime)
                await model.motion('nf02', 0, 3);
            });
            // 将 model 实例保存到 ref
            modelRef.current = model
        }

        void loadLive2DModel()
        // 清理函数：组件卸载时移除 model 并释放资源
        return () => {
            if (modelRef.current) {
                app.stage.removeChild(modelRef.current)
                modelRef.current.destroy?.() // 根据实际库的 API 调用销毁方法
                modelRef.current = null
            }
        }
    }, [app])

    return (
        <pixiContainer label="live2d-layer">

        </pixiContainer>
    )
}
