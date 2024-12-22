import unreal
import os
import subprocess

'''
Tick_timer 类用于管理一个定时器，该定时器在指定的时间间隔内触发。

interval: 定时器的时间间隔，默认为1.0秒。
_tick: 用于存储定时器的回调标识。
_current_tick_interval: 记录自上次触发以来的时间累积。

方法:
__init__(interval): 构造函数，初始化定时器并注册Slate后置tick回调。
_timer(delta): 定时器回调函数，处理时间累积并触发定时事件。
_stop(): 停止定时器，注销Slate后置tick回调。
'''
class Tick_timer():
    _tick = None
    interval:float = 1.0
    _current_tick_interval = 0

    def __init__(self, interval = 1.0):
        self.interval = interval
        self._tick = unreal.register_slate_post_tick_callback(self._timer)

    def _timer(self, delta):
        self._current_tick_interval += delta

        if self._current_tick_interval < self.interval:
            return
        
        self._current_tick_interval = 0

    def _stop(self):
        unreal.unregister_slate_post_tick_callback(self._tick)

"""
该类用于检查纹理引用，并在纹理文件更新时自动重新导入资产。

- `asset_path`: 纹理资产的路径。
- `folder_path`: 纹理文件所在的文件夹路径（未在代码中使用）。
- `current_check_texture_file_path`: 当前检查的纹理文件路径。
- `last_mod_time`: 上次修改纹理文件的时间戳。
- `popen`: 用于执行外部命令的子进程。

该类继承自`Tick_timer`，并定期检查纹理文件是否被修改。如果文件被修改，它将重新加载纹理资产，并尝试保留原有的sRGB、压缩设置和LOD组设置。

- `__init__(self, texture_path, asset_path, popen:subprocess.Popen)`: 构造函数，初始化检查器并设置定时器。
- `_timer(self, delta)`: 定时器回调函数，检查纹理文件是否被修改，并在必要时重新导入资产。
"""
class Check_texture_refs(Tick_timer):
    asset_path = ''
    folder_path = ''
    current_check_texture_file_path = ''
    last_mod_time = 0
    open_phtoshop_ins = None
    process:subprocess.Popen = None

    def __init__(self, texture_path, asset_path, open_phtoshop_ins, process:subprocess.Popen):
        if not os.path.exists(texture_path):
            return

        self.asset_path = asset_path
        self.current_check_texture_file_path = texture_path
        self.last_mod_time = os.path.getmtime(self.current_check_texture_file_path)
        self.open_phtoshop_ins = open_phtoshop_ins
        self.process = process

        super().__init__(1.0)

    def _timer(self, delta):

        super()._timer(delta)
        
        if os.path.exists(self.current_check_texture_file_path):

            if self.process.poll() is not None:
                if self.process.poll() == 0:
                    self._stop()
                    for export_path in self.open_phtoshop_ins.export_paths:
                        if os.path.exists(export_path):
                            os.remove(export_path)
                    self.process.terminate()
                    return

            current_mod_time = os.path.getmtime(self.current_check_texture_file_path)
            if current_mod_time != self.last_mod_time:
                self.last_mod_time = current_mod_time 

                #ue5.5以前版本重新导入贴图后无法保持之前的设置，需要把关键设置记录，并在重新导入后重新设置。
                current_texture:unreal.Texture2D = unreal.EditorAssetLibrary.load_asset(self.asset_path)
                srgb = current_texture.get_editor_property("srgb")
                compression_settings = current_texture.get_editor_property("compression_settings")
                lod_group = current_texture.get_editor_property("lod_group")

                asset_tools:unreal.AssetTools = unreal.AssetToolsHelpers.get_asset_tools()
                data = unreal.AutomatedAssetImportData()
                data.set_editor_property("destination_path", self.asset_path[:self.asset_path.rfind("/")])
                data.set_editor_property("filenames", [self.current_check_texture_file_path])
                data.set_editor_property("replace_existing", True)
                asset_tools.import_assets_automated(data)

                current_texture.set_editor_property("srgb", srgb)
                current_texture.set_editor_property("compression_settings", compression_settings)
                current_texture.set_editor_property("lod_group", lod_group)

'''
open_phtoshop 类用于在 Unreal 编辑器中导出选中的纹理，并尝试打开 Photoshop 来处理这些纹理。

find_phtoshop_exe_path 方法会搜索系统中可能安装的 Photoshop 可执行文件路径。
export_select_texture 方法会导出选中的纹理文件到临时目录，并返回导出文件的路径。
open 方法会调用上述两个方法，如果找到 Photoshop 并成功导出纹理，则会启动 Photoshop 打开导出的纹理文件。
'''
class open_phtoshop():

    asset_path = ''
    export_paths = []

    def find_phtoshop_exe_path(self):
        possible_paths = [
            os.environ.get('PROGRAMFILES', 'C:\\Program Files') + '\\Adobe',
        ]

        for base_path in possible_paths:
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.lower() == 'photoshop.exe':
                        return os.path.join(root, file)
        
        return None
    
    def export_select_texture(self):
        assets:unreal.Array = unreal.EditorUtilityLibrary.get_selected_assets_of_class(unreal.Texture2D)
        if len(assets) > 0:
            self.asset_path = assets[0].get_path_name()

            temp_dir = os.environ.get('TEMP')
            export_path = os.path.join(temp_dir, assets[0].get_name() + ".tga")
            
            task = unreal.AssetExportTask()
            task.set_editor_property('automated', True)
            task.set_editor_property('filename', export_path)
            task.set_editor_property('object', assets[0])
            task.set_editor_property('prompt', False)
            task.set_editor_property('exporter', unreal.TextureExporterTGA())
            unreal.Exporter.run_asset_export_task(task)
  
            return str(export_path)
        return None

    def open(self):
        export_tex_path = self.export_select_texture()
        if export_tex_path != None:
            ps_path = self.find_phtoshop_exe_path()
            if ps_path != None:
                command = [ps_path, export_tex_path]
                process = subprocess.Popen(command)
                self.export_paths.append(export_tex_path)
                Check_texture_refs(export_tex_path, self.asset_path, self, process)
                
"""
该代码段用于在Unreal Engine的内容浏览器资产上下文菜单中添加一个子菜单项，以便用户可以将资产发送到Photoshop。具体实现包括：
1. 获取内容浏览器的工具菜单。
2. 在工具菜单中添加一个名为'GetAssetActions'的子菜单。
3. 在子菜单中添加一个名为'send to photoshop'的菜单项。
4. 当用户选择此菜单项时，将调用`open_phtoshop_obj.open()`方法打开Photoshop。
"""
global open_phtoshop_obj 
open_phtoshop_obj = open_phtoshop()

menus = unreal.ToolMenus.get()
menu:unreal.ToolMenu = menus.find_menu('ContentBrowser.AssetContextMenu')

send_menu:unreal.ToolMenu = menu.add_sub_menu(menu.get_name(), 'GetAssetActions', 'send', 'Send', '')
send_menu.menu_type = unreal.MultiBoxType.MENU

entry:unreal.ToolMenuEntry = unreal.ToolMenuEntry(name='SendPhtoshop', type=unreal.MultiBlockType.MENU_ENTRY)
entry.set_label('Send to photoshop')
entry.set_string_command(unreal.ToolMenuStringCommandType.PYTHON, '', 'open_phtoshop_obj.open()')

send_menu.add_menu_entry('Settings', entry)

