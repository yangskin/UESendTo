"""
菜单工具初始化脚本
"""
import unreal

# 初始化菜单
class MenuInitializer:
    """菜单初始化器基类"""
    @staticmethod
    def init_menu(bridge_class, bridge_name: str, menu_label: str, method_name: str):
        """初始化编辑器菜单"""
        # 声明全局变量
        globals()[bridge_name] = bridge_class()

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
            name=f'SendTo{menu_label}',
            type=unreal.MultiBlockType.MENU_ENTRY
        )
        entry.set_label(f'Send to {menu_label}')
        entry.set_string_command(
            unreal.ToolMenuStringCommandType.PYTHON,
            '',
            f'{bridge_name}.{method_name}()'
        )
        
        send_menu.add_menu_entry('Settings', entry)

# 初始化send to Photoshop菜单
from send_tools import PhotoshopBridge
MenuInitializer.init_menu(PhotoshopBridge, '_PhotoshopBridge', 'Photoshop', 'open_selected')