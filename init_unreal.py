"""
虚幻引擎贴图编辑工具初始化脚本
"""
import unreal
from send_tools import PhotoshopBridge

# 初始化菜单
class MenuInitializer:
    """菜单初始化器基类"""
    def __init__(self, bridge_class, bridge_name: str, menu_label: str, method_name: str):
        self.bridge_class = bridge_class
        self.bridge_name = bridge_name
        self.menu_label = menu_label
        self.method_name = method_name
        
    def init_menu(self):
        """初始化编辑器菜单"""
        # 声明全局变量
        globals()[self.bridge_name] = self.bridge_class()

        menu = unreal.ToolMenus.get().find_menu('ContentBrowser.AssetContextMenu')
        
        send_menu = menu.add_sub_menu(
            menu.get_name(),
            'GetAssetActions', 
            'send',
            'Send',
            ''
        )
        send_menu.menu_type = unreal.MultiBoxType.MENU
        
        entry = unreal.ToolMenuEntry(
            name=f'SendTo{self.menu_label}',
            type=unreal.MultiBlockType.MENU_ENTRY
        )
        entry.set_label(f'Send to {self.menu_label}')
        entry.set_string_command(
            unreal.ToolMenuStringCommandType.PYTHON,
            '',
            f'{self.bridge_name}.{self.method_name}()'
        )
        
        send_menu.add_menu_entry('Settings', entry)

# 初始化send to Photoshop菜单
photoshop_menu = MenuInitializer(PhotoshopBridge, '_PhotoshopBridge', 'Photoshop', 'open_selected')
photoshop_menu.init_menu()

