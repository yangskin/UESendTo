import unreal
import os
import subprocess

class Tick_timer():
    __tick_elapsed__ = 0
    __tick__ = None
    interval:float = 1.0

    def __init__(self, interval = 1.0):
        self.interval = interval
        self.__tick__ = unreal.register_slate_post_tick_callback(self._timer)

    def _timer(self, delta):
        self.__tick_elapsed__ += delta

        if self.__tick_elapsed__ < self.interval:
            return
        
        self.__tick_elapsed__ = 0

    def _stop(self):
        unreal.unregister_slate_post_tick_callback(self.__tick__)

class Check_texture_refs(Tick_timer):
    asset_path = ''
    folder_path = ''
    current_check_texture_file_path = ''
    last_mod_time = 0
    popen:subprocess.Popen = None

    def __init__(self, texture_path, asset_path, popen:subprocess.Popen):
        if not os.path.exists(texture_path):
            return

        self.asset_path = asset_path
        self.current_check_texture_file_path = texture_path
        self.last_mod_time = os.path.getmtime(self.current_check_texture_file_path)
        self.popen = popen

        super().__init__(1.0)

    def _timer(self, delta):

        super()._timer(delta)
        
        if os.path.exists(self.current_check_texture_file_path):

            if self.popen.poll() is not None:
                self._stop()
                os.remove(self.current_check_texture_file_path)
                return

            current_mod_time = os.path.getmtime(self.current_check_texture_file_path)
            if current_mod_time != self.last_mod_time:
                self.last_mod_time = current_mod_time 

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

class open_phtoshop():

    asset_path = ''

    def find_phtoshop_exe_path(self):
        possible_paths = [
            os.environ.get("PROGRAMFILES", "C:\\Program Files"),
        ]

        for base_path in possible_paths:
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.lower() == "photoshop.exe":
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
                Check_texture_refs(export_tex_path, self.asset_path, process)
                
global open_phtoshop_obj 
open_phtoshop_obj = open_phtoshop()

menus = unreal.ToolMenus.get()
menu:unreal.ToolMenu = menus.find_menu('ContentBrowser.AssetContextMenu')

send_menu:unreal.ToolMenu = menu.add_sub_menu(menu.get_name(), 'GetAssetActions', 'send', 'send', '')
send_menu.menu_type = unreal.MultiBoxType.MENU

entry:unreal.ToolMenuEntry = unreal.ToolMenuEntry(name='send.sendPhtoshop', type=unreal.MultiBlockType.MENU_ENTRY)
entry.set_label('send to photoshop')
entry.set_string_command(unreal.ToolMenuStringCommandType.PYTHON, '', 'open_phtoshop_obj.open()')

send_menu.add_menu_entry('Settings', entry)