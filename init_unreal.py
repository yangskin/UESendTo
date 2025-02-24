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

class ContentBrowserToolBarButtonInitializer:
    """用于添加工具栏按钮"""
    @staticmethod
    def add_button(section: str, button_name: str, label: str, tooltip: str,
                   icon_style_set: str, icon_style: str, on_click_function: str):
        menus = unreal.ToolMenus.get()
        menu = menus.find_menu("ContentBrowser.ToolBar")

        entry = unreal.ToolMenuEntry(
            name=button_name,
            type=unreal.MultiBlockType.TOOL_BAR_BUTTON,
            insert_position=unreal.ToolMenuInsert("", unreal.ToolMenuInsertType.DEFAULT)
        )
        entry.set_label(label)
        entry.set_tool_tip(tooltip)
        entry.set_icon(icon_style_set, icon_style)
        entry.set_string_command(
            unreal.ToolMenuStringCommandType.PYTHON,
            string = on_click_function, 
            custom_type = unreal.Name("_placeholder_")
        )

        menu.add_menu_entry(section, entry)
        menus.refresh_all_widgets()

# 初始化send to Photoshop菜单
from send_tools import PhotoshopBridge
MenuInitializer.init_menu(PhotoshopBridge, '_PhotoshopBridge', 'Photoshop', 'open_selected')


# 示例调用：添加 Content Browser 工具栏自定义按钮
ContentBrowserToolBarButtonInitializer.add_button(
    section="Scripts",
    button_name="SendPhotoshopButton",
    label="SendPS",
    tooltip="发送贴图到Photoshop",
    icon_style_set="EditorStyle",
    icon_style="ContentBrowser.AssetActions",
    on_click_function="_PhotoshopBridge.open_selected()"
)