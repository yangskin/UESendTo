"""
虚幻引擎贴图编辑工具。
提供贴图实时同步编辑功能。
"""

import unreal
import os
import subprocess
from typing import List, Optional, Tuple
from PIL import Image
from psd_tools import PSDImage
from psd_tools.api.layers import PixelLayer

# 配置项
PHOTOSHOP_CUSTOM_PATH = os.environ.get('THM_PHOTOSHOP_ROOT', "")  # 优先使用环境变量中的自定义Photoshop安装路径
PHOTOSHOP_DEFAULT_PATH = os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'Adobe')  # 默认Photoshop安装路径

class TickTimer:
    """定时器基类，用于处理虚幻引擎的 tick 事件。
    tick事件是游戏引擎中按固定时间间隔执行的更新事件。
    """
    
    def __init__(self, interval: float = 1.0):
        self._tick = unreal.register_slate_post_tick_callback(self._timer)
        self.interval = interval
        self._current_interval = 0.0

    def _timer(self, delta: float) -> None:
        self._current_interval += delta
        if self._current_interval < self.interval:
            return
        self._current_interval = 0.0

    def stop(self) -> None:
        if self._tick:
            unreal.unregister_slate_post_tick_callback(self._tick)

class IMonitorCallback:
    def cleanup_all_temp_file(self) -> None:
        pass

    def stop_monitor(self, monitor: 'TextureMonitor') -> None:
        pass

class TextureMonitor(TickTimer):
    """监控贴图文件变化并自动重新导入。
    继承自TickTimer类，用于检测贴图文件是否发生变化。
    """
    
    def __init__(self, texture_path: str, asset_path: str, 
                 callback: IMonitorCallback, process: subprocess.Popen):
        """
        Args:
            texture_path: 贴图文件的本地路径
            asset_path: 虚幻引擎中资产的路径
            callback: 回调接口实例
            process: Photoshop进程实例
        """
        if not os.path.exists(texture_path):
            return

        self.texture_path = texture_path
        self.asset_path = asset_path
        self.callback = callback
        self.process = process
        # 记录文件的最后修改时间
        self.last_modified = os.path.getmtime(texture_path)

        super().__init__(1.0)  # 调用父类初始化方法，设置1秒的检查间隔

    def _timer(self, delta: float) -> None:
        """定时器回调函数
        
        定期检查贴图文件是否发生变化，并在需要时进行清理或重新导入
        
        Args:
            delta: 两帧之间的时间间隔
        """
        super()._timer(delta)
        
        # 检查贴图文件是否存在
        if not os.path.exists(self.texture_path):
            return

        # 检查是否需要清理资源
        if self._should_cleanup():
            self._cleanup()
            return

        # 检查贴图是否发生变化
        self._check_for_changes()

    def _should_cleanup(self) -> bool:
        """检查是否需要清理资源"""
        return self.process.poll() == 0

    def _cleanup(self) -> None:
        """清理临时文件和进程"""
        self.callback.cleanup_all_temp_file()
        self.callback.stop_monitor(self)
        self.process.terminate()

    def _check_for_changes(self) -> None:
        """检查并处理贴图变化
        通过比较文件修改时间来检测文件是否被修改
        """
        current_modified = os.path.getmtime(self.texture_path)
        if current_modified == self.last_modified:
            return

        self.last_modified = current_modified
        self._reimport_texture()

    def _reimport_texture(self) -> None:
        """重新导入贴图并保持设置"""
        if not unreal.EditorAssetLibrary.does_asset_exist(self.asset_path):
            return

        texture = unreal.EditorAssetLibrary.load_asset(self.asset_path)
        settings = self._store_texture_settings(texture)
        self._do_reimport()
        self._restore_texture_settings(texture, settings)

    def _store_texture_settings(self, texture: unreal.Texture2D) -> dict:
        """存储贴图关键设置
        
        保存贴图的重要属性，以便在重新导入后恢复这些设置
        
        Args:
            texture: 虚幻引擎的贴图对象
            
        Returns:
            包含贴图设置的字典
        """
        return {
            'srgb': texture.get_editor_property("srgb"),  # 是否使用sRGB色彩空间
            'compression_settings': texture.get_editor_property("compression_settings"),  # 压缩设置
            'lod_group': texture.get_editor_property("lod_group")  # LOD(细节层次)组设置
        }

    def _do_reimport(self) -> None:
        """执行贴图重新导入"""
        import_data = unreal.AutomatedAssetImportData()
        import_data.set_editor_property("destination_path", os.path.dirname(self.asset_path))
        import_data.set_editor_property("filenames", [self.texture_path])
        import_data.set_editor_property("replace_existing", True)
        
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        tools.import_assets_automated(import_data)

    def _restore_texture_settings(self, texture: unreal.Texture2D, settings: dict) -> None:
        """恢复贴图设置"""
        for prop, value in settings.items():
            texture.set_editor_property(prop, value)

class PhotoshopBridge(IMonitorCallback):
    """处理与 Photoshop 的交互。
    实现了在虚幻引擎和Photoshop之间的文件交互功能。
    """

    def __init__(self):
        self.asset_path = ''  # 虚幻引擎中的资产路径
        self.texture_monitors: List[TextureMonitor] = []  # 贴图监视器列表

    def cleanup_all_temp_file(self) -> None:
        """实现接口方法：清理所有临时文件"""
        for monitors in self.texture_monitors:
            #替换后缀为'tga'
            if os.path.exists(monitors.texture_path):
                os.remove(monitors.texture_path)
                
            tga_texture_path = monitors.texture_path.replace('.psd', '.tga')
            if os.path.exists(tga_texture_path):
                os.remove(tga_texture_path)

    def stop_monitor(self, monitor: TextureMonitor) -> None:
        """实现接口方法：停止监控器"""
        if monitor in self.texture_monitors:
            monitor.stop()
            self.texture_monitors.remove(monitor)

    def open_selected(self) -> None:
        """在 Photoshop 中打开选中的贴图"""

        ps_path = self._find_photoshop()
        if ps_path:

            export_path = self._export_texture()
            if export_path == None:
                return
            
            self._launch_photoshop(ps_path, export_path)

    #参考https://mp.weixin.qq.com/s/Gw1W0kwTcst9ecAw4zck2A
    def _save_to_psd(self, tga_path, save_path):
        image = Image.open(tga_path)
        image_obj = image.convert("RGBA")
        
        # 将PIL图像转换为PSD格式
        psd = PSDImage.frompil(image_obj)

        psd.save(save_path) 
        image.close()

    def _export_texture(self) -> Optional[List[Tuple[str, str]]]:
        """导出选中的贴图"""
        assets = unreal.EditorUtilityLibrary.get_selected_assets()
        texture_assets = []
        for asset in assets:
            if isinstance(asset, unreal.Texture2D):
                texture_assets.append(asset)

        if len(texture_assets) == 0:
            unreal.EditorDialog.show_message(
                title='错误',
                message='请选择一个贴图资产',
                message_type=unreal.AppMsgType.OK
            )
            return None

        request = []

        for asset in texture_assets:
            temp_path = os.path.join(os.environ.get('TEMP'), f"{asset.get_name()}.tga")
            psd_temp_path = os.path.join(os.environ.get('TEMP'), f"{asset.get_name()}.psd")

            task = unreal.AssetExportTask()
            task.set_editor_property('automated', True)
            task.set_editor_property('filename', temp_path)
            task.set_editor_property('object', asset)
            task.set_editor_property('prompt', False)
            task.set_editor_property('exporter', unreal.TextureExporterTGA())
            unreal.Exporter.run_asset_export_task(task)

            self._save_to_psd(temp_path, psd_temp_path)

            request.append((psd_temp_path, asset.get_path_name()))

        return request

    def _find_photoshop(self) -> Optional[str]:
        """查找 Photoshop 安装路径"""
        # 首先检查自定义路径
        if PHOTOSHOP_CUSTOM_PATH and os.path.exists(PHOTOSHOP_CUSTOM_PATH):
            adobe_path = PHOTOSHOP_CUSTOM_PATH
        else:
            adobe_path = PHOTOSHOP_DEFAULT_PATH
        
        # 在指定路径中查找photoshop.exe
        for root, _, files in os.walk(adobe_path):
            if 'photoshop.exe' in (f.lower() for f in files):
                return os.path.join(root, 'photoshop.exe')
                
        # 如果在自定义路径中未找到，且使用的是自定义路径，则尝试默认路径
        if adobe_path != PHOTOSHOP_DEFAULT_PATH:
            for root, _, files in os.walk(PHOTOSHOP_DEFAULT_PATH):
                if 'photoshop.exe' in (f.lower() for f in files):
                    return os.path.join(root, 'photoshop.exe')
        
        # 如果都未找到，显示错误对话框
        unreal.EditorDialog.show_message(
            title='错误',
            message='未找到Photoshop安装路径，请检查安装或配置自定义路径',
            message_type=unreal.AppMsgType.OK
        )
        return None

    def _launch_photoshop(self, ps_path: str, texture_path: List[Tuple[str, str]]) -> None:
        """启动 Photoshop 并监控贴图变化"""

        # 组合命令行
        command = [ps_path]
        for item in texture_path:
            command.append(item[0])

        # 启动Photoshop     
        process = subprocess.Popen(command)

        # 监控贴图变化
        for item in texture_path:
            self.texture_monitors.append(
                TextureMonitor(item[0], item[1], self, process)
            )