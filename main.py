import tkinter as tk
from tkinter import filedialog, messagebox, font, ttk, colorchooser
import os
from tkinter.scrolledtext import ScrolledText
import re
import json
import base64
from io import BytesIO
try:
    from ctypes import windll
    WINDOWS_API_AVAILABLE = True
except ImportError:
    WINDOWS_API_AVAILABLE = False
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

class TopMostEditor:
    def __init__(self, root):
        self.root = root
        self.parent_window = None  # 用于存储父窗口引用
        self.filename = None
        # 标签页管理
        self.tabs = []  # 存储所有标签页信息
        self.current_tab_index = 0  # 当前活动标签页索引
        self.tab_counter = 0  # 标签页计数器
        # 项目管理
        self.project_filename = None  # 当前项目文件路径
        self.project_modified = False  # 项目是否有未保存的更改
        self.project_name = "未命名项目"  # 项目名称
        # 初始化图片拖拽相关属性
        self.drag_data = None
        self.drag_canvas = None  # 用于自由拖拽的Canvas覆盖层
        self.floating_images = {}  # 存储浮动图片Label组件
        self.setup_ui()
        # 创建第一个标签页
        self.create_new_tab("新建文档")
        
    def setup_ui(self):
        # Configure the main window
        self.root.geometry("600x400+300+200")  # 缩小窗口并设置初始位置
        self.root.attributes('-topmost', True)  # Make window always on top
        
        # 设置默认灰色背景（设为实例变量）
        self.default_bg = "#A0A0A0"  # RGB值160,160,160对应的十六进制颜色代码
        self.default_fg = "#3D2914"  # 更深的褐色文字
        
        # 设置窗口标题（初始化后会被update_window_title更新）
        self.root.title("缓冲编辑器（强制置顶）")
        
        # 移除系统标题栏
        self.root.overrideredirect(True)
        
        # 应用默认颜色到根窗口
        self.root.configure(bg=self.default_bg)
        
        # 创建自定义标题栏
        self.create_custom_title_bar()
        
        # 创建自定义菜单栏框架（替代系统菜单栏，因为Windows不支持颜色自定义）
        self.custom_menu_frame = tk.Frame(self.root, bg=self.default_bg, height=30)
        self.custom_menu_frame.pack(fill=tk.X, side=tk.TOP)
        self.custom_menu_frame.pack_propagate(False)
        
        # 创建菜单按钮
        self.create_custom_menu_buttons()
        
        # 创建主框架
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建书签式标签页面板
        self.tab_panel = tk.Frame(self.main_frame, width=25, bg=self.default_bg, relief=tk.FLAT, bd=0)
        self.tab_panel.pack(side=tk.LEFT, fill=tk.Y)
        self.tab_panel.pack_propagate(False)  # 固定宽度
        
        # 标签页容器（书签式叠放）
        self.tab_container = tk.Frame(self.tab_panel, bg=self.default_bg)
        self.tab_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=5)
        
        # 新建标签页按钮（小图标）
        new_tab_btn = tk.Button(self.tab_panel, text="+", command=lambda: self.create_new_tab(),
                               bg=self.default_bg, fg=self.default_fg, relief=tk.FLAT, font=("Arial", 10, "bold"),
                               width=2, height=1)
        new_tab_btn.pack(side=tk.BOTTOM, pady=2)
        
        # 创建工具提示
        self.tooltip = None
        self.tooltip_window = None
        
        # 创建编辑器区域框架
        self.editor_area = tk.Frame(self.main_frame)
        self.editor_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 创建一个框架容纳编辑器
        self.editor_frame = tk.Frame(self.editor_area)
        self.editor_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建文本编辑器（移除独立行号组件）
        self.text_frame = tk.Frame(self.editor_frame, bg=self.default_bg)
        self.text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.text_editor = tk.Text(self.text_frame, wrap=tk.WORD, undo=True, padx=5, pady=5, 
                              bg=self.default_bg, fg=self.default_fg, insertbackground=self.default_fg)
        self.text_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 初始化内嵌行号相关变量
        self.line_number_widgets = {}  # 存储行号Label组件
        self.show_line_numbers = True
        
        # 添加默认空行以显示行号
        default_lines = "\n" * 60
        self.text_editor.insert("1.0", default_lines)
        self.text_editor.mark_set(tk.INSERT, "1.0")  # 将光标设置到第一行
        
        # 重置修改状态，避免启动时显示未保存更改
        self.text_editor.edit_modified(False)
        
        # 创建ttk样式用于滚动条
        style = ttk.Style()
        style.theme_use('clam')  # 使用clam主题以支持颜色自定义
        style.configure("Custom.Vertical.TScrollbar", 
                       background=self.default_bg,
                       troughcolor=self.default_bg,
                       bordercolor=self.default_bg,
                       arrowcolor=self.default_fg,
                       darkcolor=self.default_bg,
                       lightcolor=self.default_bg)
        
        # 创建并添加滚动条
        self.scrollbar_y = ttk.Scrollbar(self.text_frame, orient=tk.VERTICAL, command=self.text_editor.yview,
                                        style="Custom.Vertical.TScrollbar")
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_editor.config(yscrollcommand=self.scrollbar_y.set)
        
        # 创建拖拽Canvas覆盖层（初始时隐藏）
        self.create_drag_canvas()
        
        # 创建状态栏
        self.status_bar = tk.Label(self.root, text="行: 1 | 列: 0", bd=1, relief=tk.SUNKEN, anchor=tk.W,
                              bg=self.default_bg, fg=self.default_fg)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 设置其他框架的背景色
        self.main_frame.configure(bg=self.default_bg)
        self.editor_frame.configure(bg=self.default_bg)
        
        # 配置编辑器字体
        self.default_font = font.Font(family="Consolas", size=10)
        self.text_editor.configure(font=self.default_font)
        
        # 配置语法高亮标签
        self.text_editor.tag_configure("keyword", foreground="blue")
        self.text_editor.tag_configure("string", foreground="green")
        self.text_editor.tag_configure("comment", foreground="gray")
        self.text_editor.tag_configure("function", foreground="purple")
        self.text_editor.tag_configure("number", foreground="orange")
        
        # 显示行号
        self.show_line_numbers = True
        self.update_line_numbers()
        
        # 绑定事件
        self.text_editor.bind("<KeyRelease>", self.on_key_release)
        self.text_editor.bind("<Button-1>", self.update_cursor_position)
        self.text_editor.bind("<<Modified>>", self.update_modified)
        self.text_editor.bind('<Configure>', self.on_text_changed)
        self.text_editor.bind('<MouseWheel>', self.on_text_changed)
        self.text_editor.bind('<KeyPress>', self.on_text_changed)
        self.text_editor.bind('<ButtonRelease>', self.on_text_changed)
        
        # 键盘快捷键
        self.root.bind("<Control-n>", lambda event: self.new_file())
        self.root.bind("<Control-o>", lambda event: self.open_file())
        self.root.bind("<Control-s>", lambda event: self.save_file())
        self.root.bind("<Control-Shift-S>", lambda event: self.save_as())
        self.root.bind("<Control-Shift-P>", lambda event: self.save_project())
        self.root.bind("<Control-Shift-O>", lambda event: self.open_project())
        self.root.bind("<Control-f>", lambda event: self.find_text())
        self.root.bind("<Control-q>", lambda event: self.exit_app())
        self.root.bind("<Control-z>", lambda event: self.undo())
        self.root.bind("<Control-y>", lambda event: self.redo())
        self.root.bind("<Control-x>", lambda event: self.cut())
        self.root.bind("<Control-c>", lambda event: self.copy())
        self.root.bind("<Control-v>", lambda event: self.paste())
        
        # 创建窗口边缘调整大小区域
        self.create_resize_borders()
        
        # 设置焦点
        self.text_editor.focus_set()
        
        # 更新窗口标题
        self.update_window_title()
    
    def create_custom_title_bar(self):
        """创建自定义标题栏"""
        self.title_bar = tk.Frame(self.root, bg=self.default_bg, height=30)
        self.title_bar.pack(fill=tk.X, side=tk.TOP)
        self.title_bar.pack_propagate(False)
        
        # 标题文字
        self.title_label = tk.Label(self.title_bar, text="缓冲编辑器（强制置顶）", 
                                   bg=self.default_bg, fg=self.default_fg, font=("Arial", 9))
        self.title_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 窗口控制按钮框架
        button_frame = tk.Frame(self.title_bar, bg=self.default_bg)
        button_frame.pack(side=tk.RIGHT, padx=5)
        
        # 关闭按钮
        close_btn = tk.Button(button_frame, text="×", bg=self.default_bg, fg=self.default_fg,
                             relief=tk.FLAT, width=3, command=self.exit_app)
        close_btn.pack(side=tk.RIGHT, padx=2)
        
        # 最大化按钮
        maximize_btn = tk.Button(button_frame, text="□", bg=self.default_bg, fg=self.default_fg,
                                relief=tk.FLAT, width=3, command=self.toggle_maximize)
        maximize_btn.pack(side=tk.RIGHT, padx=2)
        
        # 最小化按钮
        minimize_btn = tk.Button(button_frame, text="—", bg=self.default_bg, fg=self.default_fg,
                                relief=tk.FLAT, width=3, command=self.minimize_window)
        minimize_btn.pack(side=tk.RIGHT, padx=2)
        
        # 绑定拖拽事件
        self.title_bar.bind("<Button-1>", self.start_drag)
        self.title_bar.bind("<B1-Motion>", self.drag_window)
        self.title_label.bind("<Button-1>", self.start_drag)
        self.title_label.bind("<B1-Motion>", self.drag_window)
        
        # 存储拖拽起始位置
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_maximized = False
    
    def create_resize_borders(self):
        """创建窗口边缘调整大小区域"""
        # 调整大小相关变量
        self.resize_border_width = 5  # 边框宽度
        self.is_resizing = False
        self.resize_direction = None
        self.resize_start_x = 0
        self.resize_start_y = 0
        self.resize_start_width = 0
        self.resize_start_height = 0
        
        # 创建四个边框用于调整大小
        # 顶部边框
        self.top_border = tk.Frame(self.root, bg=self.default_bg, height=self.resize_border_width, cursor="sb_v_double_arrow")
        self.top_border.place(x=0, y=0, relwidth=1)
        
        # 底部边框
        self.bottom_border = tk.Frame(self.root, bg=self.default_bg, height=self.resize_border_width, cursor="sb_v_double_arrow")
        self.bottom_border.place(x=0, rely=1, y=-self.resize_border_width, relwidth=1)
        
        # 左侧边框
        self.left_border = tk.Frame(self.root, bg=self.default_bg, width=self.resize_border_width, cursor="sb_h_double_arrow")
        self.left_border.place(x=0, y=0, relheight=1)
        
        # 右侧边框
        self.right_border = tk.Frame(self.root, bg=self.default_bg, width=self.resize_border_width, cursor="sb_h_double_arrow")
        self.right_border.place(relx=1, x=-self.resize_border_width, y=0, relheight=1)
        
        # 四个角落用于对角线调整大小
        # 左上角
        self.top_left_corner = tk.Frame(self.root, bg=self.default_bg, width=self.resize_border_width*2, 
                                       height=self.resize_border_width*2, cursor="size_nw_se")
        self.top_left_corner.place(x=0, y=0)
        
        # 右上角
        self.top_right_corner = tk.Frame(self.root, bg=self.default_bg, width=self.resize_border_width*2, 
                                        height=self.resize_border_width*2, cursor="size_ne_sw")
        self.top_right_corner.place(relx=1, x=-self.resize_border_width*2, y=0)
        
        # 左下角
        self.bottom_left_corner = tk.Frame(self.root, bg=self.default_bg, width=self.resize_border_width*2, 
                                          height=self.resize_border_width*2, cursor="size_ne_sw")
        self.bottom_left_corner.place(x=0, rely=1, y=-self.resize_border_width*2)
        
        # 右下角
        self.bottom_right_corner = tk.Frame(self.root, bg=self.default_bg, width=self.resize_border_width*2, 
                                           height=self.resize_border_width*2, cursor="size_nw_se")
        self.bottom_right_corner.place(relx=1, x=-self.resize_border_width*2, rely=1, y=-self.resize_border_width*2)
        
        # 绑定调整大小事件
        self.bind_resize_events()
    
    def bind_resize_events(self):
        """绑定调整大小事件"""
        # 边框事件
        self.top_border.bind("<Button-1>", lambda e: self.start_resize(e, "top"))
        self.top_border.bind("<B1-Motion>", self.resize_window)
        self.top_border.bind("<ButtonRelease-1>", self.end_resize)
        
        self.bottom_border.bind("<Button-1>", lambda e: self.start_resize(e, "bottom"))
        self.bottom_border.bind("<B1-Motion>", self.resize_window)
        self.bottom_border.bind("<ButtonRelease-1>", self.end_resize)
        
        self.left_border.bind("<Button-1>", lambda e: self.start_resize(e, "left"))
        self.left_border.bind("<B1-Motion>", self.resize_window)
        self.left_border.bind("<ButtonRelease-1>", self.end_resize)
        
        self.right_border.bind("<Button-1>", lambda e: self.start_resize(e, "right"))
        self.right_border.bind("<B1-Motion>", self.resize_window)
        self.right_border.bind("<ButtonRelease-1>", self.end_resize)
        
        # 角落事件
        self.top_left_corner.bind("<Button-1>", lambda e: self.start_resize(e, "top_left"))
        self.top_left_corner.bind("<B1-Motion>", self.resize_window)
        self.top_left_corner.bind("<ButtonRelease-1>", self.end_resize)
        
        self.top_right_corner.bind("<Button-1>", lambda e: self.start_resize(e, "top_right"))
        self.top_right_corner.bind("<B1-Motion>", self.resize_window)
        self.top_right_corner.bind("<ButtonRelease-1>", self.end_resize)
        
        self.bottom_left_corner.bind("<Button-1>", lambda e: self.start_resize(e, "bottom_left"))
        self.bottom_left_corner.bind("<B1-Motion>", self.resize_window)
        self.bottom_left_corner.bind("<ButtonRelease-1>", self.end_resize)
        
        self.bottom_right_corner.bind("<Button-1>", lambda e: self.start_resize(e, "bottom_right"))
        self.bottom_right_corner.bind("<B1-Motion>", self.resize_window)
        self.bottom_right_corner.bind("<ButtonRelease-1>", self.end_resize)
    
    def start_resize(self, event, direction):
        """开始调整窗口大小"""
        if self.is_maximized:
            return  # 最大化状态下不允许调整大小
            
        self.is_resizing = True
        self.resize_direction = direction
        self.resize_start_x = event.x_root
        self.resize_start_y = event.y_root
        self.resize_start_width = self.root.winfo_width()
        self.resize_start_height = self.root.winfo_height()
        self.resize_start_window_x = self.root.winfo_x()
        self.resize_start_window_y = self.root.winfo_y()
    
    def resize_window(self, event):
        """调整窗口大小"""
        if not self.is_resizing:
            return
            
        dx = event.x_root - self.resize_start_x
        dy = event.y_root - self.resize_start_y
        
        new_width = self.resize_start_width
        new_height = self.resize_start_height
        new_x = self.resize_start_window_x
        new_y = self.resize_start_window_y
        
        # 设置最小窗口大小
        min_width = 300
        min_height = 200
        
        # 根据调整方向计算新的窗口大小和位置
        if "right" in self.resize_direction:
            new_width = max(min_width, self.resize_start_width + dx)
        elif "left" in self.resize_direction:
            new_width = max(min_width, self.resize_start_width - dx)
            if new_width > min_width:
                new_x = self.resize_start_window_x + dx
            else:
                new_x = self.resize_start_window_x + (self.resize_start_width - min_width)
                
        if "bottom" in self.resize_direction:
            new_height = max(min_height, self.resize_start_height + dy)
        elif "top" in self.resize_direction:
            new_height = max(min_height, self.resize_start_height - dy)
            if new_height > min_height:
                new_y = self.resize_start_window_y + dy
            else:
                new_y = self.resize_start_window_y + (self.resize_start_height - min_height)
        
        # 应用新的窗口大小和位置
        self.root.geometry(f"{int(new_width)}x{int(new_height)}+{int(new_x)}+{int(new_y)}")
    
    def end_resize(self, event):
        """结束调整窗口大小"""
        self.is_resizing = False
        self.resize_direction = None
    
    def create_drag_canvas(self):
        """创建用于图片自由拖拽的Canvas覆盖层"""
        self.drag_canvas = tk.Canvas(self.text_frame, highlightthickness=0, 
                                   bg=self.default_bg, bd=0)
        # 初始时不显示Canvas
        self.drag_canvas.place_forget()
    
    def start_drag(self, event):
        """开始拖拽窗口"""
        self.drag_start_x = event.x_root - self.root.winfo_x()
        self.drag_start_y = event.y_root - self.root.winfo_y()
    
    def drag_window(self, event):
        """拖拽窗口"""
        if not self.is_maximized:
            x = event.x_root - self.drag_start_x
            y = event.y_root - self.drag_start_y
            self.root.geometry(f"+{x}+{y}")
    
    def minimize_window(self):
        """最小化窗口"""
        # 通过父窗口实现最小化
        parent = self.root.master
        if parent:
            parent.iconify()
        else:
            self.root.withdraw()
    

    
    def toggle_maximize(self):
        """切换最大化状态"""
        if self.is_maximized:
            self.root.state('normal')
            self.is_maximized = False
            # 还原时显示调整大小边框
            self.show_resize_borders()
        else:
            self.root.state('zoomed')
            self.is_maximized = True
            # 最大化时隐藏调整大小边框
            self.hide_resize_borders()
    
    def show_resize_borders(self):
        """显示调整大小边框"""
        if hasattr(self, 'top_border'):
            self.top_border.place(x=0, y=0, relwidth=1)
            self.bottom_border.place(x=0, rely=1, y=-self.resize_border_width, relwidth=1)
            self.left_border.place(x=0, y=0, relheight=1)
            self.right_border.place(relx=1, x=-self.resize_border_width, y=0, relheight=1)
            self.top_left_corner.place(x=0, y=0)
            self.top_right_corner.place(relx=1, x=-self.resize_border_width*2, y=0)
            self.bottom_left_corner.place(x=0, rely=1, y=-self.resize_border_width*2)
            self.bottom_right_corner.place(relx=1, x=-self.resize_border_width*2, rely=1, y=-self.resize_border_width*2)
    
    def hide_resize_borders(self):
        """隐藏调整大小边框"""
        if hasattr(self, 'top_border'):
            self.top_border.place_forget()
            self.bottom_border.place_forget()
            self.left_border.place_forget()
            self.right_border.place_forget()
            self.top_left_corner.place_forget()
            self.top_right_corner.place_forget()
            self.bottom_left_corner.place_forget()
            self.bottom_right_corner.place_forget()

    def create_custom_menu_buttons(self):
        """创建自定义菜单按钮"""
        # 文件菜单按钮
        file_btn = tk.Menubutton(self.custom_menu_frame, text="文件", 
                                bg=self.default_bg, fg=self.default_fg, 
                                relief=tk.FLAT, padx=10)
        file_btn.pack(side=tk.LEFT)
        
        file_menu = tk.Menu(file_btn, tearoff=0, bg=self.default_bg, fg=self.default_fg)
        file_menu.add_command(label="新建 (Ctrl+N)", command=self.new_file)
        file_menu.add_command(label="打开 (Ctrl+O)", command=self.open_file)
        file_menu.add_separator()
        file_menu.add_command(label="保存 (Ctrl+S)", command=self.save_file)
        file_menu.add_command(label="另存为 (Ctrl+Shift+S)", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="保存项目 (Ctrl+Shift+P)", command=self.save_project)
        file_menu.add_command(label="项目另存为", command=self.save_project_as)
        file_menu.add_command(label="打开项目 (Ctrl+Shift+O)", command=self.open_project)
        file_menu.add_separator()
        file_menu.add_command(label="退出 (Ctrl+Q)", command=self.exit_app)
        file_btn.config(menu=file_menu)
        
        # 编辑菜单按钮
        edit_btn = tk.Menubutton(self.custom_menu_frame, text="编辑", 
                                bg=self.default_bg, fg=self.default_fg, 
                                relief=tk.FLAT, padx=10)
        edit_btn.pack(side=tk.LEFT)
        
        edit_menu = tk.Menu(edit_btn, tearoff=0, bg=self.default_bg, fg=self.default_fg)
        edit_menu.add_command(label="撤销 (Ctrl+Z)", command=self.undo)
        edit_menu.add_command(label="重做 (Ctrl+Y)", command=self.redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="剪切 (Ctrl+X)", command=self.cut)
        edit_menu.add_command(label="复制 (Ctrl+C)", command=self.copy)
        edit_menu.add_command(label="粘贴 (Ctrl+V)", command=self.paste)
        edit_menu.add_separator()
        edit_menu.add_command(label="查找 (Ctrl+F)", command=self.find_text)
        edit_btn.config(menu=edit_menu)
        
        # 插入菜单按钮
        insert_btn = tk.Menubutton(self.custom_menu_frame, text="插入", 
                                  bg=self.default_bg, fg=self.default_fg, 
                                  relief=tk.FLAT, padx=10)
        insert_btn.pack(side=tk.LEFT)
        
        insert_menu = tk.Menu(insert_btn, tearoff=0, bg=self.default_bg, fg=self.default_fg)
        if PIL_AVAILABLE:
            insert_menu.add_command(label="插入图片", command=self.insert_image)
        else:
            insert_menu.add_command(label="插入图片 (需要安装PIL)", command=self.show_pil_warning, state="disabled")
        insert_btn.config(menu=insert_menu)
        
        # 格式菜单按钮
        format_btn = tk.Menubutton(self.custom_menu_frame, text="格式", 
                                  bg=self.default_bg, fg=self.default_fg, 
                                  relief=tk.FLAT, padx=10)
        format_btn.pack(side=tk.LEFT)
        
        format_menu = tk.Menu(format_btn, tearoff=0, bg=self.default_bg, fg=self.default_fg)
        format_menu.add_command(label="文字颜色", command=self.change_text_color)
        format_menu.add_command(label="背景颜色", command=self.change_bg_color)
        format_menu.add_command(label="字体选择", command=self.change_font)
        format_btn.config(menu=format_menu)
        
        # 查看菜单按钮
        view_btn = tk.Menubutton(self.custom_menu_frame, text="查看", 
                                bg=self.default_bg, fg=self.default_fg, 
                                relief=tk.FLAT, padx=10)
        view_btn.pack(side=tk.LEFT)
        
        view_menu = tk.Menu(view_btn, tearoff=0, bg=self.default_bg, fg=self.default_fg)
        view_menu.add_command(label="显示行号", command=self.toggle_line_numbers)
        view_menu.add_separator()
        view_menu.add_command(label="透明度控制", command=self.show_transparency_control)
        view_btn.config(menu=view_menu)
    
    def create_new_tab(self, title="新建文档"):
        """创建新的标签页"""
        self.tab_counter += 1
        if title == "新建文档":
            title = f"新建文档{self.tab_counter}"
        
        # 创建标签页数据
        tab_data = {
            'id': self.tab_counter,
            'title': title,
            'filename': None,
            'content': '',
            'images': [],
            'image_info': {},
            'modified': False,
            'cursor_pos': '1.0',
            'custom_color': None  # 自定义颜色
        }
        
        # 添加到标签页列表
        self.tabs.append(tab_data)
        
        # 创建标签页UI
        self.create_tab_ui(len(self.tabs) - 1)
        
        # 切换到新标签页
        self.switch_to_tab(len(self.tabs) - 1)
        
        # 为新标签页添加默认空行
        default_lines = "\n" * 60
        self.text_editor.insert("1.0", default_lines)
        self.text_editor.mark_set(tk.INSERT, "1.0")  # 将光标设置到第一行
        
        # 更新行号显示
        if self.show_line_numbers:
            self.update_line_numbers()
        
        # 重置修改状态，避免新建标签页时显示未保存更改
        self.text_editor.edit_modified(False)
    
    def create_tab_ui(self, tab_index):
        """创建书签式标签页的UI元素"""
        tab_data = self.tabs[tab_index]
        
        # 创建书签式标签页（显示标题第一个字符）
        tab_display = tab_data['title'][0] if tab_data['title'] else str(tab_index + 1)
        
        # 确定标签页颜色
        bg_color = tab_data.get('custom_color', self.default_bg)
        fg_color = self.get_contrast_color(bg_color) if tab_data.get('custom_color') else self.default_fg
        
        tab_btn = tk.Button(self.tab_container, text=tab_display,
                           command=lambda: self.switch_to_tab(tab_index),
                           bg=bg_color, fg=fg_color, relief=tk.RAISED,
                           font=("Arial", 8, "bold"), width=2, height=1,
                           bd=1)
        tab_btn.pack(pady=1)
        
        # 绑定鼠标事件
        tab_btn.bind("<Enter>", lambda e: self.show_tooltip(e, tab_data['title']))
        tab_btn.bind("<Leave>", lambda e: self.hide_tooltip())
        tab_btn.bind("<Button-3>", lambda e: self.show_tab_context_menu(e, tab_index))
        
        # 保存UI引用
        tab_data['ui_button'] = tab_btn
        tab_data['ui_frame'] = None  # 书签式不需要frame
        tab_data['ui_close'] = None  # 关闭功能通过右键菜单实现
    
    def switch_to_tab(self, tab_index):
        """切换到指定标签页"""
        if tab_index < 0 or tab_index >= len(self.tabs):
            return
        
        # 清理拖拽Canvas状态
        self.cleanup_drag_canvas()
        
        # 保存当前标签页状态
        if self.tabs and self.current_tab_index < len(self.tabs):
            self.save_current_tab_state()
        
        # 更新当前标签页索引
        self.current_tab_index = tab_index
        current_tab = self.tabs[tab_index]
        
        # 更新UI状态
        self.update_tab_ui_states()
        
        # 加载标签页内容
        self.load_tab_content(current_tab)
        
        # 更新filename
        self.filename = current_tab['filename']
        
        # 更新窗口标题
        self.update_window_title()
    
    def save_current_tab_state(self):
        """保存当前标签页的状态"""
        if not self.tabs or self.current_tab_index >= len(self.tabs):
            return
            
        # 检查text_editor是否仍然有效
        try:
            if not hasattr(self, 'text_editor') or not self.text_editor.winfo_exists():
                return
        except tk.TclError:
            return
            
        current_tab = self.tabs[self.current_tab_index]
        
        try:
            # 保存内容
            current_tab['content'] = self.text_editor.get(1.0, tk.END)
            
            # 保存光标位置
            current_tab['cursor_pos'] = self.text_editor.index(tk.INSERT)
            
            # 保存修改状态
            current_tab['modified'] = self.text_editor.edit_modified()
            
            # 保存图片信息
            if hasattr(self, 'images'):
                current_tab['images'] = self.images.copy()
            if hasattr(self, 'image_info'):
                current_tab['image_info'] = self.image_info.copy()
            if hasattr(self, 'floating_images'):
                current_tab['floating_images'] = list(self.floating_images.keys())
        except tk.TclError:
            # 如果组件已被销毁，跳过保存
            pass
    
    def load_tab_content(self, tab_data):
        """加载标签页内容"""
        # 清空编辑器
        self.text_editor.delete(1.0, tk.END)
        
        # 加载文本内容
        if tab_data['content']:
            self.text_editor.insert(1.0, tab_data['content'])
        
        # 恢复光标位置
        try:
            self.text_editor.mark_set(tk.INSERT, tab_data['cursor_pos'])
        except tk.TclError:
            self.text_editor.mark_set(tk.INSERT, '1.0')
        
        # 恢复图片
        if hasattr(self, 'images'):
            self.images.clear()
        else:
            self.images = []
        if hasattr(self, 'image_info'):
            self.image_info.clear()
        else:
            self.image_info = {}
            
        # 清理现有浮动图片
        if hasattr(self, 'floating_images'):
            for image_label in self.floating_images.values():
                image_label.destroy()
            self.floating_images.clear()
        else:
            self.floating_images = {}
        
        # 复制图片数据
        if 'images' in tab_data:
            self.images = tab_data['images'].copy()
        if 'image_info' in tab_data:
            self.image_info = tab_data['image_info'].copy()
            
            # 重新创建浮动图片
            for image_name, info in self.image_info.items():
                # 检查是否为浮动图片（通过is_floating标记或原有的label字段）
                if info.get('is_floating', False) or 'label' in info:
                    try:
                        # 创建新的Label
                        image_label = tk.Label(self.text_editor, image=info['photo'], bg='white', relief='solid', bd=1)
                        x = info.get('x', 10)
                        y = info.get('y', 10)
                        image_label.place(x=x, y=y)
                        
                        # 更新引用
                        self.floating_images[image_name] = image_label
                        info['label'] = image_label
                        
                        # 重新绑定事件
                        self.bind_floating_image_context_menu(image_name)
                        if info.get('draggable', False):
                            self.toggle_floating_image_draggable(image_name, True)
                    except Exception as e:
                        print(f"创建浮动图片失败: {e}")
                        # 如果创建失败，跳过这个图片
                        continue
                else:
                    # 对于嵌入式图片，需要重新插入到文本编辑器中
                    try:
                        # 在文本末尾插入图片（因为原位置可能已经无效）
                        new_image_name = self.text_editor.image_create(tk.END, image=info['photo'])
                        
                        # 更新图片信息中的名称（因为Tkinter会生成新的图片ID）
                        if image_name != new_image_name:
                            # 如果名称改变了，需要更新image_info字典
                            self.image_info[new_image_name] = self.image_info.pop(image_name)
                            image_name = new_image_name
                        
                        # 重新绑定右键菜单
                        self.bind_image_context_menu(image_name)
                        if info.get('draggable', False):
                            self.toggle_image_draggable(image_name, True)
                    except Exception as e:
                        print(f"创建嵌入式图片失败: {e}")
                        continue
        
        # 设置修改状态
        self.text_editor.edit_modified(tab_data['modified'])
        
        # 更新行号
        self.update_line_numbers()
    
    def update_tab_ui_states(self):
        """更新所有标签页的UI状态"""
        for i, tab in enumerate(self.tabs):
            try:
                # 检查UI组件是否仍然有效
                if 'ui_button' in tab and tab['ui_button'].winfo_exists():
                    # 获取标签页的自定义颜色或默认颜色
                    custom_color = tab.get('custom_color')
                    
                    if i == self.current_tab_index:
                        # 当前活动标签页
                        if custom_color:
                            # 如果有自定义颜色，使其稍微深一点表示活动状态
                            active_color = self.darken_color(custom_color, 0.8)
                            text_color = self.get_contrast_color(active_color)
                            tab['ui_button'].config(bg=active_color, fg=text_color, relief=tk.SUNKEN)
                        else:
                            # 使用默认的活动颜色
                            active_bg = "#8A8A8A"
                            tab['ui_button'].config(bg=active_bg, fg=self.default_fg, relief=tk.SUNKEN)
                    else:
                        # 非活动标签页
                        if custom_color:
                            text_color = self.get_contrast_color(custom_color)
                            tab['ui_button'].config(bg=custom_color, fg=text_color, relief=tk.RAISED)
                        else:
                            tab['ui_button'].config(bg=self.default_bg, fg=self.default_fg, relief=tk.RAISED)
            except tk.TclError:
                # 如果组件已被销毁，跳过更新
                continue
    
    def show_tooltip(self, event, text):
        """显示工具提示"""
        self.hide_tooltip()  # 先隐藏之前的提示
        
        x = event.widget.winfo_rootx() + 30
        y = event.widget.winfo_rooty() + 10
        
        self.tooltip_window = tk.Toplevel(self.root)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tooltip_window, text=text, 
                        background="#FFFFCC", foreground="#000000",
                        relief=tk.SOLID, borderwidth=1,
                        font=("Arial", 8))
        label.pack()
    
    def hide_tooltip(self):
        """隐藏工具提示"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
    
    def show_tab_context_menu(self, event, tab_index):
        """显示标签页右键菜单"""
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="重命名", command=lambda: self.rename_tab(tab_index))
        context_menu.add_command(label="自定义颜色", command=lambda: self.customize_tab_color(tab_index))
        context_menu.add_separator()
        context_menu.add_command(label="关闭标签页", command=lambda: self.close_tab(tab_index))
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def customize_tab_color(self, tab_index):
        """自定义标签页颜色"""
        tab_data = self.tabs[tab_index]
        
        # 打开颜色选择器
        color = colorchooser.askcolor(
            title="选择标签页颜色",
            initialcolor=tab_data.get('custom_color', '#f0f0f0')
        )
        
        if color[1]:  # 如果用户选择了颜色
            # 保存颜色到标签页数据
            tab_data['custom_color'] = color[1]
            
            # 应用颜色到标签页按钮
            self.apply_tab_color(tab_index, color[1])
            
            # 更新UI状态
            self.update_tab_ui_states()
    
    def apply_tab_color(self, tab_index, color):
        """应用颜色到标签页"""
        tab_data = self.tabs[tab_index]
        tab_button = tab_data.get('ui_button')
        
        if tab_button and tab_button.winfo_exists():
            try:
                # 设置背景颜色
                tab_button.config(bg=color)
                
                # 根据背景颜色自动选择合适的文字颜色
                text_color = self.get_contrast_color(color)
                tab_button.config(fg=text_color)
                
            except tk.TclError:
                pass
    
    def rename_tab(self, tab_index):
        """重命名标签页"""
        tab_data = self.tabs[tab_index]
        current_name = tab_data['title'].lstrip('*')  # 移除修改标记
        
        # 创建重命名对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("重命名标签页")
        dialog.geometry("300x120")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 添加拖拽和调整大小功能
        self.make_window_draggable_resizable(dialog)
        
        # 居中显示
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        tk.Label(dialog, text="新名称:").pack(pady=10)
        
        entry = tk.Entry(dialog, width=30)
        entry.pack(pady=5)
        entry.insert(0, current_name)
        entry.select_range(0, tk.END)
        entry.focus()
        
        def confirm_rename():
            new_name = entry.get().strip()
            if new_name and new_name != current_name:
                tab_data['title'] = new_name
                # 更新窗口标题（如果是当前标签页）
                if tab_index == self.current_tab_index:
                    self.update_window_title()
                # 刷新所有标签页UI以更新显示
                self.refresh_all_tabs_ui()
            dialog.destroy()
        
        def cancel_rename():
            dialog.destroy()
        
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="确定", command=confirm_rename).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="取消", command=cancel_rename).pack(side=tk.LEFT, padx=5)
        
        # 绑定回车键
        entry.bind('<Return>', lambda e: confirm_rename())
        dialog.bind('<Escape>', lambda e: cancel_rename())
    
    def close_tab(self, tab_index):
        """关闭指定标签页"""
        if len(self.tabs) <= 1:
            messagebox.showinfo("提示", "至少需要保留一个标签页")
            return
        
        tab_to_close = self.tabs[tab_index]
        
        # 检查是否需要保存
        if tab_to_close['modified']:
            # 先切换到要关闭的标签页
            if tab_index != self.current_tab_index:
                self.switch_to_tab(tab_index)
            
            response = messagebox.askyesnocancel("未保存的更改", f"标签页 '{tab_to_close['title']}' 有未保存的更改，是否保存？")
            if response is None:  # Cancel
                return
            elif response:  # Yes
                if not self.save_file():
                    return
        
        # 销毁UI
        if tab_to_close['ui_button']:
            tab_to_close['ui_button'].destroy()
        
        # 从列表中移除
        self.tabs.pop(tab_index)
        
        # 调整当前标签页索引
        if tab_index < self.current_tab_index:
            self.current_tab_index -= 1
        elif tab_index == self.current_tab_index:
            # 如果关闭的是当前标签页，切换到相邻标签页
            if self.current_tab_index >= len(self.tabs):
                self.current_tab_index = len(self.tabs) - 1
            self.switch_to_tab(self.current_tab_index)
        
        # 重新创建所有标签页UI（更新索引）
        self.refresh_all_tabs_ui()
    
    def refresh_all_tabs_ui(self):
        """刷新所有标签页的UI"""
        # 清空容器
        for widget in self.tab_container.winfo_children():
            widget.destroy()
        
        # 重新创建所有标签页UI
        for i, tab in enumerate(self.tabs):
            self.create_tab_ui(i)
            # 重新绑定事件（因为索引可能改变）
            tab['ui_button'].bind("<Enter>", lambda e, title=tab['title']: self.show_tooltip(e, title))
            tab['ui_button'].bind("<Leave>", lambda e: self.hide_tooltip())
            tab['ui_button'].bind("<Button-3>", lambda e, idx=i: self.show_tab_context_menu(e, idx))
        
        # 更新UI状态
        self.update_tab_ui_states()
        
    def new_file(self):
        # 创建新的标签页
        self.create_new_tab()
    
    def open_file(self):
        if self.check_save_changes():
            file_path = filedialog.askopenfilename(
                filetypes=[
                    ("所有支持的文件", "*.txt;*.py;*.rted;*.rtep"),
                    ("富文本编辑器项目", "*.rtep"),
                    ("富文本文档", "*.rted"),
                    ("纯文本文件", "*.txt"), 
                    ("Python文件", "*.py"),
                    ("所有文件", "*.*")
                ]
            )
            
            if file_path:
                try:
                    if file_path.lower().endswith('.rtep'):
                        # 打开项目文件
                        with open(file_path, 'r', encoding='utf-8') as file:
                            project_data = json.load(file)
                        
                        if self.import_project_data(project_data):
                            self.project_filename = file_path
                            self.project_name = os.path.splitext(os.path.basename(file_path))[0]
                            self.project_modified = False
                            self.update_window_title()
                            messagebox.showinfo("成功", f"项目已加载: {file_path}")
                    elif file_path.lower().endswith('.rted'):
                        # 打开富文本文件
                        self.open_rich_text_file(file_path)
                        
                        # 更新当前标签页信息
                        current_tab = self.tabs[self.current_tab_index]
                        current_tab['filename'] = file_path
                        current_tab['title'] = os.path.basename(file_path)
                        current_tab['modified'] = False
                        
                        # 更新标签页UI（书签式显示标题第一个字符）
                        tab_display = current_tab['title'][0] if current_tab['title'] else str(self.current_tab_index + 1)
                        current_tab['ui_button'].config(text=tab_display)
                        
                        self.filename = file_path
                        self.update_window_title()
                        self.update_line_numbers()
                        self.apply_syntax_highlighting()
                    else:
                        # 打开纯文本文件
                        self.open_plain_text_file(file_path)
                        
                        # 更新当前标签页信息
                        current_tab = self.tabs[self.current_tab_index]
                        current_tab['filename'] = file_path
                        current_tab['title'] = os.path.basename(file_path)
                        current_tab['modified'] = False
                        
                        # 更新标签页UI（书签式显示标题第一个字符）
                        tab_display = current_tab['title'][0] if current_tab['title'] else str(self.current_tab_index + 1)
                        current_tab['ui_button'].config(text=tab_display)
                        
                        self.filename = file_path
                        self.update_window_title()
                        self.update_line_numbers()
                        self.apply_syntax_highlighting()
                except Exception as e:
                    messagebox.showerror("错误", f"无法打开文件: {str(e)}")
    
    def open_plain_text_file(self, file_path):
        """打开纯文本文件"""
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            self.text_editor.delete(1.0, tk.END)
            self.text_editor.insert(1.0, content)
            
            # 清理图片信息
            if hasattr(self, 'image_info'):
                self.image_info.clear()
            if hasattr(self, 'images'):
                self.images.clear()
            
            # 重置修改状态，避免打开文件时显示未保存更改
            self.text_editor.edit_modified(False)
    
    def open_rich_text_file(self, file_path):
        """打开富文本文件"""
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # 清空编辑器
        self.text_editor.delete(1.0, tk.END)
        
        # 清理旧的图片信息
        if hasattr(self, 'image_info'):
            self.image_info.clear()
        else:
            self.image_info = {}
        if hasattr(self, 'images'):
            self.images.clear()
        else:
            self.images = []
        
        # 插入文本内容
        text_content = data.get('text', '')
        self.text_editor.insert(1.0, text_content)
        
        # 清理现有浮动图片
        if hasattr(self, 'floating_images'):
            for image_label in self.floating_images.values():
                image_label.destroy()
            self.floating_images.clear()
        else:
            self.floating_images = {}
        
        # 恢复图片
        images_data = data.get('images', [])
        for img_data in images_data:
            try:
                # 从base64恢复图片
                image_base64 = img_data['image_data']
                image_bytes = base64.b64decode(image_base64)
                image = Image.open(BytesIO(image_bytes))
                
                # 创建PhotoImage
                photo = ImageTk.PhotoImage(image)
                
                # 生成唯一的图片名称
                import time
                image_name = f"image_{int(time.time() * 1000000)}"
                
                # 根据图片类型进行不同处理
                image_type = img_data.get('type', 'embedded')  # 默认为嵌入式图片（向后兼容）
                
                if image_type == 'floating':  # 浮动图片
                    # 创建浮动Label
                    image_label = tk.Label(self.text_editor, image=photo, bg='white', relief='solid', bd=1)
                    x = img_data.get('x', 10)
                    y = img_data.get('y', 10)
                    image_label.place(x=x, y=y)
                    
                    # 保存图片信息
                    self.images.append(photo)
                    self.floating_images[image_name] = image_label
                    self.image_info[image_name] = {
                        'photo': photo,
                        'draggable': img_data.get('draggable', False),
                        'file_path': img_data.get('file_path', ''),
                        'original_image': image,
                        'label': image_label,
                        'x': x,
                        'y': y
                    }
                    
                    # 绑定右键菜单
                    self.bind_floating_image_context_menu(image_name)
                    
                    # 如果图片可拖动，启用拖动功能
                    if img_data.get('draggable', False):
                        self.toggle_floating_image_draggable(image_name, True)
                        
                else:  # 传统嵌入式图片
                    # 在指定位置插入图片
                    position = img_data.get('position', '1.0')
                    try:
                        # 尝试在原位置插入
                        image_name = self.text_editor.image_create(position, image=photo)
                    except tk.TclError:
                        # 如果原位置无效，在末尾插入
                        image_name = self.text_editor.image_create(tk.END, image=photo)
                    
                    # 保存图片信息
                    self.images.append(photo)
                    self.image_info[image_name] = {
                        'photo': photo,
                        'draggable': img_data.get('draggable', False),
                        'file_path': img_data.get('file_path', ''),
                        'original_image': image,
                        'x_offset': img_data.get('x_offset', 0),
                        'y_offset': img_data.get('y_offset', 0)
                    }
                    
                    # 绑定右键菜单
                    self.bind_image_context_menu(image_name)
                    
                    # 如果图片可拖动，启用拖动功能
                    if img_data.get('draggable', False):
                        self.toggle_image_draggable(image_name, True)
                    
            except Exception as e:
                print(f"恢复图片时出错: {e}")
                messagebox.showwarning("警告", f"无法恢复某个图片: {str(e)}")
        
        # 重置修改状态，避免打开文件时显示未保存更改
        self.text_editor.edit_modified(False)
    
    def save_file(self):
        # 保存前先同步当前标签页状态
        self.save_current_tab_state()
        
        if self.filename:
            try:
                # 检查文件扩展名
                if self.filename.lower().endswith('.rted'):
                    # 保存为富文本格式
                    result = self.save_rich_text_file()
                else:
                    # 保存为纯文本格式
                    result = self.save_plain_text_file()
                
                if result:
                    # 更新当前标签页信息
                    current_tab = self.tabs[self.current_tab_index]
                    current_tab['modified'] = False
                    current_tab['title'] = os.path.basename(self.filename)
                    
                    # 重置文本编辑器的修改状态
                    self.text_editor.edit_modified(False)
                    
                    # 更新标签页UI（书签式显示标题第一个字符）
                    tab_display = current_tab['title'][0] if current_tab['title'] else str(self.current_tab_index + 1)
                    current_tab['ui_button'].config(text=tab_display)
                    
                    # 更新窗口标题
                    self.update_window_title()
                
                return result
            except Exception as e:
                messagebox.showerror("错误", f"无法保存文件: {str(e)}")
                return False
        else:
            return self.save_as()
    
    def save_plain_text_file(self):
        """保存为纯文本文件"""
        # 检查是否包含图片
        if hasattr(self, 'image_info') and len(self.image_info) > 0:
            response = messagebox.askyesno("警告", "保存为纯文本文件将丢失所有图片，是否继续？")
            if not response:
                return False
        
        content = self.text_editor.get(1.0, tk.END)
        with open(self.filename, "w", encoding="utf-8") as file:
            file.write(content)
        
        self.text_editor.edit_modified(False)
        return True
    
    def save_rich_text_file(self):
        """保存为富文本格式"""
        # 获取文本内容
        content = self.text_editor.get(1.0, tk.END)
        
        # 准备保存数据
        save_data = {
            'version': '1.0',
            'text': content,
            'images': []
        }
        
        # 保存图片信息
        if hasattr(self, 'image_info'):
            for image_name, image_info in self.image_info.items():
                try:
                    # 将图片转换为base64
                    original_image = image_info['original_image']
                    buffer = BytesIO()
                    original_image.save(buffer, format='PNG')
                    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    
                    image_data = {
                        'file_path': image_info['file_path'],
                        'image_data': image_base64,
                        'draggable': image_info['draggable']
                    }
                    
                    # 检查是否为浮动图片
                    if 'label' in image_info:  # 浮动图片
                        image_data.update({
                            'type': 'floating',
                            'x': image_info.get('x', 10),
                            'y': image_info.get('y', 10)
                        })
                    else:  # 传统图片（插入到文本编辑器中）
                        try:
                            image_pos = self.text_editor.index(image_name)
                            image_data.update({
                                'type': 'embedded',
                                'position': image_pos,
                                'x_offset': image_info.get('x_offset', 0),
                                'y_offset': image_info.get('y_offset', 0)
                            })
                        except tk.TclError:
                            # 如果无法获取位置，跳过这个图片
                            continue
                    
                    save_data['images'].append(image_data)
                except Exception as e:
                    print(f"保存图片时出错: {e}")
        
        # 保存到文件
        with open(self.filename, 'w', encoding='utf-8') as file:
            json.dump(save_data, file, ensure_ascii=False, indent=2)
        
        self.text_editor.edit_modified(False)
        return True
    
    def save_as(self):
        # 检查是否有多个标签页
        has_multiple_tabs = len(self.tabs) > 1
        # 检查是否包含图片
        has_images = hasattr(self, 'image_info') and len(self.image_info) > 0
        
        if has_multiple_tabs:
            # 多标签页情况下，优先推荐项目格式
            filetypes = [
                ("项目文件 (推荐，保存所有标签页)", "*.rtep"),
                ("富文本文档 (仅当前标签页)", "*.rted"),
                ("纯文本文件 (仅当前标签页，图片将丢失)", "*.txt"),
                ("Python文件 (仅当前标签页，图片将丢失)", "*.py"),
                ("所有文件", "*.*")
            ]
            default_ext = ".rtep"
        elif has_images:
            filetypes = [
                ("富文本文档 (推荐)", "*.rted"),
                ("纯文本文件 (图片将丢失)", "*.txt"),
                ("Python文件 (图片将丢失)", "*.py"),
                ("所有文件", "*.*")
            ]
            default_ext = ".rted"
        else:
            filetypes = [
                ("纯文本文件", "*.txt"),
                ("Python文件", "*.py"),
                ("富文本文档", "*.rted"),
                ("所有文件", "*.*")
            ]
            default_ext = ".txt"
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=default_ext,
            filetypes=filetypes
        )
        
        if file_path:
            # 检查文件扩展名，决定保存方式
            if file_path.lower().endswith('.rtep'):
                # 保存为项目文件
                if self.save_project_to_file(file_path):
                    self.project_filename = file_path
                    self.project_name = os.path.splitext(os.path.basename(file_path))[0]
                    self.update_window_title()
                    return True
                return False
            else:
                # 保存为单文件
                self.filename = file_path
                
                # 更新当前标签页信息
                current_tab = self.tabs[self.current_tab_index]
                current_tab['filename'] = file_path
                current_tab['title'] = os.path.basename(file_path)
                
                # 更新标签页UI（书签式显示标题第一个字符）
                tab_display = current_tab['title'][0] if current_tab['title'] else str(self.current_tab_index + 1)
                current_tab['ui_button'].config(text=tab_display)
                
                result = self.save_file()
                if result:
                    self.update_window_title()
                return result
        return False
    
    def exit_app(self):
        # 清理拖拽Canvas状态
        self.cleanup_drag_canvas()
        
        # 清理浮动图片
        if hasattr(self, 'floating_images'):
            for image_label in self.floating_images.values():
                try:
                    image_label.destroy()
                except tk.TclError:
                    pass
            self.floating_images.clear()
        
        # 检查项目是否有未保存的更改
        if not self.check_project_changes():
            return
        
        # 关闭主窗口
        try:
            self.root.destroy()
        except tk.TclError:
            pass  # 窗口已经被销毁
        
        # 如果有父窗口引用，也关闭父窗口
        try:
            if hasattr(self, 'parent_window') and self.parent_window and self.parent_window.winfo_exists():
                self.parent_window.destroy()
        except tk.TclError:
            pass  # 父窗口已经被销毁
    
    def check_save_changes(self):
        if self.text_editor.edit_modified():
            response = messagebox.askyesnocancel("未保存的更改", "是否保存更改?")
            if response is None:  # Cancel
                return False
            elif response:  # Yes
                return self.save_file()
        return True
    
    def undo(self):
        try:
            self.text_editor.edit_undo()
        except tk.TclError:
            pass
    
    def redo(self):
        try:
            self.text_editor.edit_redo()
        except tk.TclError:
            pass
    
    def cut(self):
        self.text_editor.event_generate("<<Cut>>")
        self.update_line_numbers()
    
    def copy(self):
        self.text_editor.event_generate("<<Copy>>")
    
    def paste(self):
        self.text_editor.event_generate("<<Paste>>")
        self.update_line_numbers()
    
    def insert_image(self):
        """插入图片到文本编辑器中"""
        if not PIL_AVAILABLE:
            messagebox.showerror("错误", "需要安装PIL库才能插入图片\n请运行: pip install Pillow")
            return
            
        file_path = filedialog.askopenfilename(
            title="选择图片文件",
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff"),
                ("PNG文件", "*.png"),
                ("JPEG文件", "*.jpg *.jpeg"),
                ("GIF文件", "*.gif"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            try:
                # 打开并调整图片大小
                image = Image.open(file_path)
                
                # 获取原始尺寸
                original_width, original_height = image.size
                
                # 设置最大尺寸
                max_width = 400
                max_height = 300
                
                # 计算缩放比例
                width_ratio = max_width / original_width
                height_ratio = max_height / original_height
                scale_ratio = min(width_ratio, height_ratio, 1.0)  # 不放大图片
                
                # 调整图片尺寸
                new_width = int(original_width * scale_ratio)
                new_height = int(original_height * scale_ratio)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 转换为PhotoImage
                photo = ImageTk.PhotoImage(image)
                
                # 创建浮动图片Label
                image_label = tk.Label(self.text_editor, image=photo, bg='white', relief='solid', bd=1)
                
                # 获取插入位置
                cursor_pos = self.text_editor.index(tk.INSERT)
                bbox = self.text_editor.bbox(cursor_pos)
                if bbox:
                    x, y, width, height = bbox
                else:
                    x, y = 10, 10
                
                # 放置图片Label
                image_label.place(x=x, y=y)
                
                # 生成唯一的图片名称
                import time
                image_name = f"floating_image_{int(time.time() * 1000)}"
                
                # 保存图片引用和信息，防止被垃圾回收
                if not hasattr(self, 'images'):
                    self.images = []
                if not hasattr(self, 'image_info'):
                    self.image_info = {}
                    
                self.images.append(photo)
                self.floating_images[image_name] = image_label
                self.image_info[image_name] = {
                    'photo': photo,
                    'draggable': False,
                    'file_path': file_path,
                    'original_image': image,
                    'x': x,
                    'y': y,
                    'label': image_label
                }
                
                # 为图片绑定右键菜单
                self.bind_floating_image_context_menu(image_name)
                
            except Exception as e:
                messagebox.showerror("错误", f"无法插入图片: {str(e)}")
    
    def bind_floating_image_context_menu(self, image_name):
        """为浮动图片绑定右键菜单和拖拽功能"""
        image_label = self.floating_images[image_name]
        
        def on_image_right_click(event):
            # 创建右键菜单
            context_menu = tk.Menu(self.root, tearoff=0)
            
            # 检查当前拖拽状态
            is_draggable = self.image_info[image_name].get('draggable', False)
            drag_text = "禁用拖动" if is_draggable else "启用拖动"
            
            context_menu.add_command(
                label=drag_text,
                command=lambda: self.toggle_floating_image_draggable(image_name, not is_draggable)
            )
            context_menu.add_separator()
            context_menu.add_command(
                label="删除图片",
                command=lambda: self.delete_floating_image(image_name)
            )
            
            # 显示菜单
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        
        # 绑定右键点击事件
        image_label.bind("<Button-3>", on_image_right_click)
    
    def bind_image_context_menu(self, image_name):
        """为图片绑定右键菜单"""
        def on_image_right_click(event):
            # 创建右键菜单
            context_menu = tk.Menu(self.root, tearoff=0)
            
            # 获取图片信息
            image_info = self.image_info.get(image_name, {})
            is_draggable = image_info.get('draggable', False)
            
            # 添加菜单项
            if is_draggable:
                context_menu.add_command(label="禁用拖动", command=lambda: self.toggle_image_draggable(image_name, False))
            else:
                context_menu.add_command(label="启用拖动", command=lambda: self.toggle_image_draggable(image_name, True))
            
            context_menu.add_separator()
            context_menu.add_command(label="删除图片", command=lambda: self.delete_image(image_name))
            
            # 显示菜单
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        
        # 绑定右键点击事件到图片
        # 注意：这里需要通过特殊方式绑定到嵌入的图片
        self.text_editor.tag_add(f"image_{image_name}", f"{image_name}", f"{image_name}+1c")
        self.text_editor.tag_bind(f"image_{image_name}", "<Button-3>", on_image_right_click)
    
    def toggle_floating_image_draggable(self, image_name, draggable):
        """切换浮动图片的拖拽状态"""
        if image_name not in self.floating_images:
            return
            
        image_label = self.floating_images[image_name]
        self.image_info[image_name]['draggable'] = draggable
        
        if draggable:
            # 启用拖动
            image_label.bind("<Button-1>", lambda e: self.start_floating_image_drag(e, image_name))
            image_label.bind("<B1-Motion>", lambda e: self.drag_floating_image(e, image_name))
            image_label.bind("<ButtonRelease-1>", lambda e: self.end_floating_image_drag(e, image_name))
            image_label.config(cursor="hand2")
        else:
            # 禁用拖动
            image_label.unbind("<Button-1>")
            image_label.unbind("<B1-Motion>")
            image_label.unbind("<ButtonRelease-1>")
            image_label.config(cursor="")
    
    def toggle_image_draggable(self, image_name, draggable):
        """切换图片的拖动状态"""
        if image_name in self.image_info:
            self.image_info[image_name]['draggable'] = draggable
            
            if draggable:
                # 启用拖动
                self.text_editor.tag_bind(f"image_{image_name}", "<Button-1>", lambda e: self.start_image_drag(e, image_name))
                self.text_editor.tag_bind(f"image_{image_name}", "<B1-Motion>", lambda e: self.drag_image(e, image_name))
                self.text_editor.tag_bind(f"image_{image_name}", "<ButtonRelease-1>", lambda e: self.end_image_drag(e, image_name))
            else:
                # 禁用拖动
                self.text_editor.tag_unbind(f"image_{image_name}", "<Button-1>")
                self.text_editor.tag_unbind(f"image_{image_name}", "<B1-Motion>")
                self.text_editor.tag_unbind(f"image_{image_name}", "<ButtonRelease-1>")
    
    def start_floating_image_drag(self, event, image_name):
        """开始拖拽浮动图片"""
        self.drag_data = {
            'image_name': image_name,
            'start_x': event.x,
            'start_y': event.y
        }
    
    def drag_floating_image(self, event, image_name):
        """拖拽浮动图片过程中"""
        if not hasattr(self, 'drag_data') or not self.drag_data:
            return
            
        if self.drag_data['image_name'] != image_name:
            return
            
        # 计算移动距离
        dx = event.x - self.drag_data['start_x']
        dy = event.y - self.drag_data['start_y']
        
        # 获取当前位置
        image_label = self.floating_images[image_name]
        current_x = image_label.winfo_x()
        current_y = image_label.winfo_y()
        
        # 计算新位置
        new_x = current_x + dx
        new_y = current_y + dy
        
        # 确保图片不会拖出编辑器边界
        editor_width = self.text_editor.winfo_width()
        editor_height = self.text_editor.winfo_height()
        image_width = image_label.winfo_width()
        image_height = image_label.winfo_height()
        
        new_x = max(0, min(new_x, editor_width - image_width))
        new_y = max(0, min(new_y, editor_height - image_height))
        
        # 移动图片
        image_label.place(x=new_x, y=new_y)
        
        # 更新图片信息
        self.image_info[image_name]['x'] = new_x
        self.image_info[image_name]['y'] = new_y
    
    def end_floating_image_drag(self, event, image_name):
        """结束拖拽浮动图片"""
        self.drag_data = None
    
    def start_image_drag(self, event, image_name):
        """开始拖动图片"""
        # 检查是否为浮动图片，如果是则不处理（浮动图片有自己的拖拽方法）
        if image_name in self.image_info and 'label' in self.image_info[image_name]:
            return
            
        try:
            original_pos = self.text_editor.index(image_name)
        except tk.TclError:
            # 如果无法获取位置，可能是浮动图片，直接返回
            return
            
        self.drag_data = {
            'image_name': image_name,
            'start_x': event.x,
            'start_y': event.y,
            'original_pos': original_pos
        }
        
        # 激活Canvas覆盖层进行自由拖拽
        if self.drag_canvas:
            # 获取文本编辑器的尺寸和位置
            self.text_editor.update_idletasks()
            x = self.text_editor.winfo_x()
            y = self.text_editor.winfo_y()
            width = self.text_editor.winfo_width()
            height = self.text_editor.winfo_height()
            
            # 显示Canvas覆盖层
            self.drag_canvas.place(x=x, y=y, width=width, height=height)
            
            # 在Canvas上创建图片副本用于拖拽显示
            if image_name in self.image_info:
                photo = self.image_info[image_name]['photo']
                self.drag_canvas.delete("drag_image")  # 清除之前的拖拽图片
                self.drag_canvas.create_image(event.x, event.y, image=photo, tags="drag_image")
                
                # 绑定Canvas的鼠标事件
                self.drag_canvas.bind("<B1-Motion>", lambda e: self.canvas_drag_image(e, image_name))
                self.drag_canvas.bind("<ButtonRelease-1>", lambda e: self.canvas_end_drag(e, image_name))
                # 添加Canvas点击事件，用于检测点击空白区域
                self.drag_canvas.bind("<Button-1>", lambda e: self.canvas_click_handler(e, image_name))
                self.drag_canvas.focus_set()
    
    def drag_image(self, event, image_name):
        """拖动图片过程中"""
        if hasattr(self, 'drag_data') and self.drag_data['image_name'] == image_name:
            # 检查是否为浮动图片，如果是则不处理
            if image_name in self.image_info and 'label' in self.image_info[image_name]:
                return
                
            try:
                # 计算鼠标移动的距离
                dx = event.x - self.drag_data['start_x']
                dy = event.y - self.drag_data['start_y']
                
                # 更新图片的偏移量
                if image_name in self.image_info:
                    self.image_info[image_name]['x_offset'] = dx
                    self.image_info[image_name]['y_offset'] = dy
                    
                    # 尝试找到最接近的文本位置
                    try:
                        new_pos = self.text_editor.index(f"@{event.x},{event.y}")
                        
                        # 获取图片对象
                        photo = self.image_info[image_name]['photo']
                        
                        # 删除原位置的图片
                        current_pos = self.text_editor.index(image_name)
                        self.text_editor.delete(current_pos)
                        
                        # 在新位置插入图片
                        new_image_name = self.text_editor.image_create(new_pos, image=photo)
                        
                        # 更新图片信息
                        old_info = self.image_info.pop(image_name)
                        self.image_info[new_image_name] = old_info
                        
                        # 重新绑定事件
                        self.bind_image_context_menu(new_image_name)
                        if old_info['draggable']:
                            self.toggle_image_draggable(new_image_name, True)
                        
                        # 更新拖动数据
                        self.drag_data['image_name'] = new_image_name
                        self.drag_data['start_x'] = event.x
                        self.drag_data['start_y'] = event.y
                        
                    except tk.TclError:
                        pass  # 忽略无效位置
                        
            except Exception as e:
                pass  # 忽略拖动过程中的错误
    
    def canvas_click_handler(self, event, image_name):
        """处理Canvas点击事件"""
        # 检查点击位置是否在拖拽图片上
        items = self.drag_canvas.find_overlapping(event.x-10, event.y-10, event.x+10, event.y+10)
        drag_image_found = False
        
        for item in items:
            tags = self.drag_canvas.gettags(item)
            if "drag_image" in tags:
                drag_image_found = True
                break
        
        # 如果点击的不是拖拽图片，结束拖拽
        if not drag_image_found:
            self.canvas_end_drag(event, image_name)
    
    def canvas_drag_image(self, event, image_name):
        """在Canvas上拖拽图片"""
        if hasattr(self, 'drag_data') and self.drag_data['image_name'] == image_name:
            # 更新Canvas上的图片位置
            self.drag_canvas.coords("drag_image", event.x, event.y)
            
            # 计算偏移量
            dx = event.x - self.drag_data['start_x']
            dy = event.y - self.drag_data['start_y']
            
            # 更新图片信息中的偏移量
            if image_name in self.image_info:
                self.image_info[image_name]['x_offset'] = dx
                self.image_info[image_name]['y_offset'] = dy
    
    def cleanup_drag_canvas(self):
        """清理拖拽Canvas状态"""
        if self.drag_canvas:
            try:
                # 解绑所有事件
                self.drag_canvas.unbind("<B1-Motion>")
                self.drag_canvas.unbind("<ButtonRelease-1>")
                self.drag_canvas.unbind("<Button-1>")
                
                # 隐藏Canvas覆盖层
                self.drag_canvas.place_forget()
                self.drag_canvas.delete("drag_image")
                
                # 清理焦点
                self.text_editor.focus_set()
            except tk.TclError:
                pass
        
        # 清理拖拽数据
        self.drag_data = None
    
    def canvas_end_drag(self, event, image_name):
        """结束Canvas拖拽"""
        if hasattr(self, 'drag_data') and self.drag_data and self.drag_data.get('image_name') == image_name:
            # 检查是否为浮动图片，如果是则不处理
            if image_name in self.image_info and 'label' in self.image_info[image_name]:
                self.cleanup_drag_canvas()
                return
                
            try:
                # 计算最终位置
                final_pos = self.text_editor.index(f"@{event.x},{event.y}")
                
                # 获取图片对象
                photo = self.image_info[image_name]['photo']
                
                # 删除原位置的图片
                current_pos = self.text_editor.index(image_name)
                self.text_editor.delete(current_pos)
                
                # 在新位置插入图片
                new_image_name = self.text_editor.image_create(final_pos, image=photo)
                
                # 更新图片信息
                old_info = self.image_info.pop(image_name)
                self.image_info[new_image_name] = old_info
                
                # 重新绑定事件
                self.bind_image_context_menu(new_image_name)
                if old_info.get('draggable', False):
                    self.toggle_image_draggable(new_image_name, True)
                    
            except tk.TclError:
                # 如果无法在新位置插入，恢复到原位置
                try:
                    original_pos = self.drag_data['original_pos']
                    photo = self.image_info[image_name]['photo']
                    new_image_name = self.text_editor.image_create(original_pos, image=photo)
                    
                    # 更新图片信息
                    old_info = self.image_info.pop(image_name)
                    self.image_info[new_image_name] = old_info
                    
                    # 重新绑定事件
                    self.bind_image_context_menu(new_image_name)
                    if old_info.get('draggable', False):
                        self.toggle_image_draggable(new_image_name, True)
                except:
                    pass
        
        # 清理Canvas状态
        self.cleanup_drag_canvas()
    
    def end_image_drag(self, event, image_name):
        """结束拖动图片"""
        if hasattr(self, 'drag_data'):
            del self.drag_data
    
    def delete_floating_image(self, image_name):
        """删除浮动图片"""
        if image_name not in self.floating_images:
            return
            
        response = messagebox.askyesno("确认删除", "确定要删除这张图片吗？")
        if response:
            # 销毁Label组件
            image_label = self.floating_images[image_name]
            image_label.destroy()
            
            # 清理数据
            del self.floating_images[image_name]
            if image_name in self.image_info:
                del self.image_info[image_name]
    
    def delete_image(self, image_name):
        """删除图片"""
        # 检查是否为浮动图片，如果是则调用专门的删除方法
        if image_name in self.image_info and 'label' in self.image_info[image_name]:
            self.delete_floating_image(image_name)
            return
            
        try:
            # 删除文本中的图片
            current_pos = self.text_editor.index(image_name)
            self.text_editor.delete(current_pos)
            
            # 清理图片信息
            if image_name in self.image_info:
                del self.image_info[image_name]
                
            messagebox.showinfo("提示", "图片已删除")
        except tk.TclError:
            messagebox.showerror("错误", "无法删除图片")
    
    def show_pil_warning(self):
        """显示PIL库未安装的警告"""
        messagebox.showwarning("功能不可用", "插入图片功能需要安装PIL库\n\n请在命令行中运行:\npip install Pillow")
    
    def find_text(self):
        search_window = tk.Toplevel(self.root)
        search_window.title("查找")
        search_window.geometry("300x100")
        search_window.transient(self.root)
        search_window.attributes('-topmost', True)
        
        # 添加拖拽和调整大小功能
        self.make_window_draggable_resizable(search_window)
        
        tk.Label(search_window, text="查找:").grid(row=0, column=0, padx=5, pady=5)
        search_entry = tk.Entry(search_window, width=30)
        search_entry.grid(row=0, column=1, padx=5, pady=5)
        search_entry.focus_set()
        
        case_var = tk.BooleanVar()
        tk.Checkbutton(search_window, text="区分大小写", variable=case_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5)
        
        def do_find():
            self.text_editor.tag_remove('search', '1.0', tk.END)
            search_text = search_entry.get()
            if search_text:
                start_pos = '1.0'
                while True:
                    if case_var.get():
                        start_pos = self.text_editor.search(search_text, start_pos, stopindex=tk.END, nocase=False)
                    else:
                        start_pos = self.text_editor.search(search_text, start_pos, stopindex=tk.END, nocase=True)
                    
                    if not start_pos:
                        break
                    
                    end_pos = f"{start_pos}+{len(search_text)}c"
                    self.text_editor.tag_add('search', start_pos, end_pos)
                    start_pos = end_pos
                    
                self.text_editor.tag_config('search', background='yellow')
        
        tk.Button(search_window, text="查找全部", command=do_find).grid(row=2, column=0, padx=5, pady=5)
        tk.Button(search_window, text="关闭", command=search_window.destroy).grid(row=2, column=1, padx=5, pady=5)
        
        search_window.protocol("WM_DELETE_WINDOW", search_window.destroy)
    
    def change_text_color(self):
        color = colorchooser.askcolor(title="选择文字颜色")
        if color[1]:
            # 检查是否有选中的文本
            try:
                selected_text = self.text_editor.get(tk.SEL_FIRST, tk.SEL_LAST)
                if selected_text:
                    # 创建或更新标签用于选中文本的颜色
                    tag_name = f"color_{color[1].replace('#', '')}"
                    self.text_editor.tag_configure(tag_name, foreground=color[1])
                    # 应用颜色标签到选中文本
                    self.text_editor.tag_add(tag_name, tk.SEL_FIRST, tk.SEL_LAST)
                    return
            except tk.TclError:
                # 没有选中文本，应用到全局
                pass
                
            # 如果没有选中文本或出现错误，则应用到全局
            self.text_editor.config(fg=color[1])
    
    def change_bg_color(self):
        color = colorchooser.askcolor(title="选择背景颜色")
        if color[1]:
            # 获取背景和对比前景色
            bg_color = color[1]
            fg_color = self.get_contrast_color(bg_color)
            
            # 应用背景色到所有主要组件
            widgets = [
                self.root,
                self.main_frame,
                self.editor_frame,
                self.text_frame,
                self.text_editor,
                self.status_bar,
            ]
            
            for widget in widgets:
                widget.config(bg=bg_color)
                
            # 设置文本相关前景色
            self.text_editor.config(fg=fg_color, insertbackground=fg_color)
            self.status_bar.config(fg=fg_color)
            
            # 更新行号组件的颜色
            for line_widget in self.line_number_widgets.values():
                line_widget.config(bg=bg_color, fg=fg_color)
            
            # 设置滚动条颜色 (部分平台支持)
            try:
                self.scrollbar_y.config(bg=bg_color, activebackground=bg_color, troughcolor=bg_color)
            except:
                pass
                
            # 菜单颜色需要重新创建菜单按钮来更新
            # 这里暂时跳过菜单颜色更新，因为菜单是局部变量
                    
            # 强制更新UI
            self.root.update_idletasks()
    
    def darken_color(self, hex_color, factor=0.8):
        """使颜色变深"""
        try:
            # 移除#号
            hex_color = hex_color.lstrip('#')
            
            # 转换为RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # 应用变深因子
            r = int(r * factor)
            g = int(g * factor)
            b = int(b * factor)
            
            # 确保值在0-255范围内
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            
            # 转换回十六进制
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color  # 如果出错，返回原颜色
    
    def get_contrast_color(self, hex_color):
        """根据背景色计算合适的前景色"""
        # 移除开头的 #
        if hex_color.startswith('#'):
            hex_color = hex_color[1:]
            
        # 将颜色转换为RGB值
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # 计算亮度
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        
        # 根据亮度动态计算字体颜色，实现自然过渡
        if brightness > 128:
            # 浅色背景：字体颜色 = 255 - brightness * 0.8
            font_brightness = int(255 - brightness * 0.8)
            # 确保值在有效范围内
            font_brightness = max(0, min(255, font_brightness))
            hex_value = format(font_brightness, '02x')
            return f"#{hex_value}{hex_value}{hex_value}"
        else:
            # 深色背景：字体颜色 = brightness * 1.2 + 100
            font_brightness = int(brightness * 1.2 + 100)
            # 确保值在有效范围内
            font_brightness = max(0, min(255, font_brightness))
            hex_value = format(font_brightness, '02x')
            return f"#{hex_value}{hex_value}{hex_value}"
    
    def change_font(self):
        font_window = tk.Toplevel(self.root)
        font_window.title("字体选择")
        font_window.geometry("400x300")
        font_window.transient(self.root)
        font_window.attributes('-topmost', True)
        
        font_families = sorted(font.families())
        font_sizes = [str(size) for size in [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 36, 48, 72]]
        
        # Current font settings
        current_font = self.default_font
        current_family = current_font.actual()['family']
        current_size = current_font.actual()['size']
        
        tk.Label(font_window, text="字体:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        family_var = tk.StringVar(value=current_family)
        family_combo = ttk.Combobox(font_window, textvariable=family_var, values=font_families, state="readonly")
        family_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        tk.Label(font_window, text="大小:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        size_var = tk.IntVar(value=current_size)
        size_combo = ttk.Combobox(font_window, textvariable=size_var, values=font_sizes, state="readonly")
        size_combo.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        bold_var = tk.BooleanVar(value='bold' in current_font.actual()['weight'])
        italic_var = tk.BooleanVar(value='italic' in current_font.actual()['slant'])
        
        ttk.Checkbutton(font_window, text="粗体", variable=bold_var).grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Checkbutton(font_window, text="斜体", variable=italic_var).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        preview_frame = tk.Frame(font_window, bd=1, relief=tk.SUNKEN)
        preview_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky=tk.NSEW)
        
        preview_text = tk.Text(preview_frame, height=5, width=40)
        preview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        preview_text.insert(1.0, "AaBbCcDdEe\n123456789")
        
        def update_preview(*args):
            weight = "bold" if bold_var.get() else "normal"
            slant = "italic" if italic_var.get() else "roman"
            preview_font = font.Font(family=family_var.get(), size=size_var.get(), weight=weight, slant=slant)
            preview_text.configure(font=preview_font)
        
        family_combo.bind("<<ComboboxSelected>>", update_preview)
        size_combo.bind("<<ComboboxSelected>>", update_preview)
        
        def apply_font():
            weight = "bold" if bold_var.get() else "normal"
            slant = "italic" if italic_var.get() else "roman"
            new_font = font.Font(family=family_var.get(), size=size_var.get(), weight=weight, slant=slant)
            self.text_editor.configure(font=new_font)
            # 更新所有行号组件的字体
            for line_widget in self.line_number_widgets.values():
                line_widget.configure(font=new_font)
            self.default_font = new_font
            self.update_line_numbers()
            font_window.destroy()
        
        tk.Button(font_window, text="应用", command=apply_font).grid(row=4, column=0, padx=5, pady=5)
        tk.Button(font_window, text="取消", command=font_window.destroy).grid(row=4, column=1, padx=5, pady=5)
        
        update_preview()
    
    def toggle_line_numbers(self):
        self.show_line_numbers = not self.show_line_numbers
        if self.show_line_numbers:
            self.update_line_numbers()
        else:
            # 隐藏所有行号
            for widget in self.line_number_widgets.values():
                try:
                    widget.destroy()
                except:
                    pass
            self.line_number_widgets.clear()
    
    def update_line_numbers(self):
        if not self.show_line_numbers:
            return
            
        # 清除所有行号组件
        for widget in self.line_number_widgets.values():
            try:
                widget.destroy()
            except:
                pass
        self.line_number_widgets.clear()
        
        # 获取文本总行数
        total_lines = int(self.text_editor.index('end-1c').split('.')[0])
        
        for line_num in range(1, total_lines + 1):
            line_start = f"{line_num}.0"
            line_end = f"{line_num}.end"
            
            # 获取该行的内容
            line_content = self.text_editor.get(line_start, line_end)
            
            # 如果该行为空或只有空白字符，显示行号
            if not line_content.strip():
                # 创建行号Label（使用较浅的前景色）
                line_number_fg = "#CCCCCC"  # 行号的前景色
                line_label = tk.Label(self.text_editor, text=f"{line_num:3d}", 
                                    fg=line_number_fg, bg=self.text_editor.cget("bg"),
                                    font=("Arial", 8), anchor="e", width=3)
                
                # 在行首嵌入Label
                self.text_editor.window_create(line_start, window=line_label)
                
                # 保存组件引用
                self.line_number_widgets[line_num] = line_label
    
    def update_line_numbers_smart(self):
        """智能更新行号，只处理发生变化的行"""
        if not self.show_line_numbers:
            return
            
        # 获取当前光标所在行
        current_line = int(self.text_editor.index(tk.INSERT).split('.')[0])
        
        # 检查当前行及其前后几行
        start_line = max(1, current_line - 2)
        end_line = min(int(self.text_editor.index('end-1c').split('.')[0]), current_line + 2)
        
        for line_num in range(start_line, end_line + 1):
            line_start = f"{line_num}.0"
            line_end = f"{line_num}.end"
            
            # 获取该行的内容（排除嵌入的组件）
            line_content = self.text_editor.get(line_start, line_end)
            
            # 检查是否已有行号组件
            has_line_number = line_num in self.line_number_widgets
            
            # 如果该行为空且没有行号，添加行号
            if not line_content.strip() and not has_line_number:
                # 创建行号Label（使用较浅的前景色）
                line_number_fg = "#CCCCCC"  # 行号的前景色
                line_label = tk.Label(self.text_editor, text=f"{line_num:3d}", 
                                    fg=line_number_fg, bg=self.text_editor.cget("bg"),
                                    font=("Arial", 8), anchor="e", width=3)
                
                # 在行首嵌入Label
                self.text_editor.window_create(line_start, window=line_label)
                
                # 保存组件引用
                self.line_number_widgets[line_num] = line_label
            
            # 如果该行有内容且有行号，移除行号
            elif line_content.strip() and has_line_number:
                # 销毁行号组件
                try:
                    self.line_number_widgets[line_num].destroy()
                except:
                    pass
                
                # 从字典中移除
                del self.line_number_widgets[line_num]
    
    def make_window_draggable_resizable(self, window):
        """为弹窗添加拖拽和调整大小功能"""
        # 保持系统标题栏，通过标题栏实现拖拽
        # 不需要额外的拖拽绑定，系统标题栏本身就支持拖拽
        pass
        
        # 创建调整大小边框
        border_width = 3
        
        # 四个边框
        top_border = tk.Frame(window, bg=self.default_bg, height=border_width, cursor="sb_v_double_arrow")
        top_border.place(x=0, y=0, relwidth=1)
        
        bottom_border = tk.Frame(window, bg=self.default_bg, height=border_width, cursor="sb_v_double_arrow")
        bottom_border.place(x=0, rely=1, y=-border_width, relwidth=1)
        
        left_border = tk.Frame(window, bg=self.default_bg, width=border_width, cursor="sb_h_double_arrow")
        left_border.place(x=0, y=0, relheight=1)
        
        right_border = tk.Frame(window, bg=self.default_bg, width=border_width, cursor="sb_h_double_arrow")
        right_border.place(relx=1, x=-border_width, y=0, relheight=1)
        
        # 四个角落
        top_left_corner = tk.Frame(window, bg=self.default_bg, width=border_width*2, height=border_width*2, cursor="size_nw_se")
        top_left_corner.place(x=0, y=0)
        
        top_right_corner = tk.Frame(window, bg=self.default_bg, width=border_width*2, height=border_width*2, cursor="size_ne_sw")
        top_right_corner.place(relx=1, x=-border_width*2, y=0)
        
        bottom_left_corner = tk.Frame(window, bg=self.default_bg, width=border_width*2, height=border_width*2, cursor="size_ne_sw")
        bottom_left_corner.place(x=0, rely=1, y=-border_width*2)
        
        bottom_right_corner = tk.Frame(window, bg=self.default_bg, width=border_width*2, height=border_width*2, cursor="size_nw_se")
        bottom_right_corner.place(relx=1, x=-border_width*2, rely=1, y=-border_width*2)
        
        # 调整大小功能
        def start_resize(event, direction):
            window.is_resizing = True
            window.resize_direction = direction
            window.resize_start_x = event.x_root
            window.resize_start_y = event.y_root
            window.resize_start_width = window.winfo_width()
            window.resize_start_height = window.winfo_height()
            window.resize_start_window_x = window.winfo_x()
            window.resize_start_window_y = window.winfo_y()
        
        def resize_window(event):
            if not hasattr(window, 'is_resizing') or not window.is_resizing:
                return
                
            dx = event.x_root - window.resize_start_x
            dy = event.y_root - window.resize_start_y
            
            new_width = window.resize_start_width
            new_height = window.resize_start_height
            new_x = window.resize_start_window_x
            new_y = window.resize_start_window_y
            
            min_width = 200
            min_height = 100
            
            if "right" in window.resize_direction:
                new_width = max(min_width, window.resize_start_width + dx)
            elif "left" in window.resize_direction:
                new_width = max(min_width, window.resize_start_width - dx)
                if new_width > min_width:
                    new_x = window.resize_start_window_x + dx
                else:
                    new_x = window.resize_start_window_x + (window.resize_start_width - min_width)
                    
            if "bottom" in window.resize_direction:
                new_height = max(min_height, window.resize_start_height + dy)
            elif "top" in window.resize_direction:
                new_height = max(min_height, window.resize_start_height - dy)
                if new_height > min_height:
                    new_y = window.resize_start_window_y + dy
                else:
                    new_y = window.resize_start_window_y + (window.resize_start_height - min_height)
            
            window.geometry(f"{int(new_width)}x{int(new_height)}+{int(new_x)}+{int(new_y)}")
        
        def end_resize(event):
            window.is_resizing = False
            window.resize_direction = None
        
        # 绑定调整大小事件
        borders = [
            (top_border, "top"), (bottom_border, "bottom"),
            (left_border, "left"), (right_border, "right"),
            (top_left_corner, "top_left"), (top_right_corner, "top_right"),
            (bottom_left_corner, "bottom_left"), (bottom_right_corner, "bottom_right")
        ]
        
        for border, direction in borders:
            border.bind("<Button-1>", lambda e, d=direction: start_resize(e, d))
            border.bind("<B1-Motion>", resize_window)
            border.bind("<ButtonRelease-1>", end_resize)
    
    def show_transparency_control(self):
        """显示透明度控制窗口"""
        # 创建透明度控制窗口
        transparency_window = tk.Toplevel(self.root)
        transparency_window.title("透明度控制")
        transparency_window.geometry("300x150")
        transparency_window.transient(self.root)
        transparency_window.grab_set()
        
        # 添加拖拽和调整大小功能
        self.make_window_draggable_resizable(transparency_window)
        
        # 居中显示
        transparency_window.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        # 获取当前透明度值（如果没有设置过，默认为1.0）
        current_alpha = getattr(self, 'current_alpha', 1.0)
        
        # 标题标签
        tk.Label(transparency_window, text="调整窗口透明度:", font=("Arial", 10)).pack(pady=10)
        
        # 透明度值显示标签
        alpha_label = tk.Label(transparency_window, text=f"当前透明度: {int(current_alpha * 100)}%", font=("Arial", 9))
        alpha_label.pack(pady=5)
        
        # 透明度滑块
        def on_alpha_change(value):
            alpha = float(value) / 100.0
            self.current_alpha = alpha
            self.root.attributes('-alpha', alpha)
            alpha_label.config(text=f"当前透明度: {int(alpha * 100)}%")
        
        alpha_scale = tk.Scale(transparency_window, from_=10, to=100, orient=tk.HORIZONTAL,
                              command=on_alpha_change, length=250)
        alpha_scale.set(int(current_alpha * 100))
        alpha_scale.pack(pady=10)
        
        # 按钮框架
        button_frame = tk.Frame(transparency_window)
        button_frame.pack(pady=10)
        
        # 重置按钮
        def reset_transparency():
            alpha_scale.set(100)
            on_alpha_change(100)
        
        tk.Button(button_frame, text="重置", command=reset_transparency).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="关闭", command=transparency_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def on_text_changed(self, event=None):
        # 延迟更新行号，避免频繁更新
        if hasattr(self, '_line_number_update_id'):
            self.root.after_cancel(self._line_number_update_id)
        self._line_number_update_id = self.root.after(100, self.update_line_numbers_smart)
    
    def on_key_release(self, event):
        self.update_line_numbers()
        self.update_cursor_position()
        
        # Apply syntax highlighting for certain file types
        if self.filename and (self.filename.endswith('.py') or self.filename.endswith('.pyw')):
            self.apply_syntax_highlighting()
    
    def update_cursor_position(self, event=None):
        cursor_position = self.text_editor.index(tk.INSERT)
        line, column = cursor_position.split('.')
        self.status_bar.config(text=f"行: {line} | 列: {column}")
    
    def update_modified(self, event=None):
        """更新修改状态"""
        if self.text_editor.edit_modified():
            # 更新当前标签页的修改状态
            if self.tabs and self.current_tab_index < len(self.tabs):
                current_tab = self.tabs[self.current_tab_index]
                current_tab['modified'] = True
                
                # 标记项目为已修改
                self.mark_project_modified()
                
                # 标签页按钮不显示修改状态，保持原有显示
                # tab_display = current_tab['title'][0] if current_tab['title'] else str(self.current_tab_index + 1)
                # current_tab['ui_button'].config(text=tab_display)
            
            # 更新窗口标题（现在由update_window_title统一处理）
            self.update_window_title()
            # 不要重置edit_modified状态，让它保持为True直到文件被保存
    
    def apply_syntax_highlighting(self):
        # Clear all tags
        for tag in ["keyword", "string", "comment", "function", "number"]:
            self.text_editor.tag_remove(tag, "1.0", tk.END)
        
        # Define patterns for Python syntax
        patterns = [
            (r'\b(False|None|True|and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield)\b', 'keyword'),
            (r'"""[\s\S]*?"""', 'string'),
            (r"'''[\s\S]*?'''", 'string'),
            (r'"[^"\\]*(\\.[^"\\]*)*"', 'string'),
            (r"'[^'\\]*(\\.[^'\\]*)*'", 'string'),
            (r'#.*$', 'comment'),
            (r'\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\()', 'function'),
            (r'\b\d+\b', 'number'),
        ]
        
        content = self.text_editor.get("1.0", tk.END)
        for pattern, tag in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                start = "1.0 + %dc" % match.start()
                end = "1.0 + %dc" % match.end()
                self.text_editor.tag_add(tag, start, end)
    
    # ==================== 项目管理功能 ====================
    
    def export_project_data(self):
        """导出项目数据结构"""
        # 保存当前标签页状态
        self.save_current_tab_state()
        
        import datetime
        import time
        
        project_data = {
            "version": "1.0",
            "project_name": self.project_name,
            "created_time": datetime.datetime.now().isoformat(),
            "modified_time": datetime.datetime.now().isoformat(),
            "current_tab_index": self.current_tab_index,
            "tabs": []
        }
        
        # 导出所有标签页数据
        for tab in self.tabs:
            tab_data = {
                "id": tab['id'],
                "title": tab['title'],
                "filename": tab['filename'],
                "content": tab['content'],
                "images": [],
                "image_info": {},
                "modified": tab['modified'],
                "cursor_pos": tab['cursor_pos'],
                "custom_color": tab['custom_color']
            }
            
            # 处理图片信息
            if 'image_info' in tab and tab['image_info']:
                for image_name, image_info in tab['image_info'].items():
                    try:
                        # 将图片转换为base64
                        original_image = image_info['original_image']
                        buffer = BytesIO()
                        original_image.save(buffer, format='PNG')
                        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        
                        image_data = {
                            'name': image_name,
                            'file_path': image_info['file_path'],
                            'image_data': image_base64,
                            'draggable': image_info['draggable']
                        }
                        
                        # 检查是否为浮动图片
                        if 'label' in image_info:  # 浮动图片
                            image_data.update({
                                'type': 'floating',
                                'x': image_info.get('x', 10),
                                'y': image_info.get('y', 10)
                            })
                        else:  # 嵌入式图片
                            image_data.update({
                                'type': 'embedded',
                                'x_offset': image_info.get('x_offset', 0),
                                'y_offset': image_info.get('y_offset', 0)
                            })
                        
                        tab_data['images'].append(image_data)
                    except Exception as e:
                        print(f"导出图片时出错: {e}")
            
            project_data['tabs'].append(tab_data)
        
        return project_data
    
    def import_project_data(self, project_data):
        """导入并恢复项目状态"""
        try:
            import time
            
            # 清空当前所有标签页
            for tab in self.tabs:
                if tab.get('ui_button'):
                    tab['ui_button'].destroy()
            
            # 清理浮动图片
            if hasattr(self, 'floating_images'):
                for image_label in self.floating_images.values():
                    try:
                        image_label.destroy()
                    except tk.TclError:
                        pass
                self.floating_images.clear()
            
            # 重置标签页列表和索引
            self.tabs = []
            self.tab_counter = 0
            self.current_tab_index = 0
            
            # 恢复项目信息
            self.project_name = project_data.get('project_name', '未命名项目')
            target_tab_index = project_data.get('current_tab_index', 0)
            
            # 恢复所有标签页
            for tab_data in project_data.get('tabs', []):
                self.tab_counter += 1
                
                # 创建标签页数据结构
                new_tab = {
                    'id': tab_data.get('id', self.tab_counter),
                    'title': tab_data.get('title', f'标签页{self.tab_counter}'),
                    'filename': tab_data.get('filename'),
                    'content': tab_data.get('content', ''),
                    'images': [],
                    'image_info': {},
                    'modified': False,  # 导入后所有标签页都应该是未修改状态
                    'cursor_pos': tab_data.get('cursor_pos', '1.0'),
                    'custom_color': tab_data.get('custom_color')
                }
                
                # 恢复图片信息
                for img_data in tab_data.get('images', []):
                    try:
                        # 从base64恢复图片
                        image_base64 = img_data['image_data']
                        image_bytes = base64.b64decode(image_base64)
                        image = Image.open(BytesIO(image_bytes))
                        
                        # 创建PhotoImage
                        photo = ImageTk.PhotoImage(image)
                        
                        image_name = img_data.get('name', f"image_{int(time.time() * 1000000)}")
                        
                        # 保存图片信息到标签页
                        new_tab['images'].append(photo)
                        
                        # 根据图片类型设置不同的属性
                        image_info = {
                            'photo': photo,
                            'draggable': img_data.get('draggable', False),
                            'file_path': img_data.get('file_path', ''),
                            'original_image': image
                        }
                        
                        if img_data.get('type') == 'floating':
                            # 浮动图片
                            image_info.update({
                                'is_floating': True,
                                'x': img_data.get('x', 10),
                                'y': img_data.get('y', 10)
                            })
                        else:
                            # 嵌入式图片
                            image_info.update({
                                'x_offset': img_data.get('x_offset', 0),
                                'y_offset': img_data.get('y_offset', 0)
                            })
                        
                        new_tab['image_info'][image_name] = image_info
                        
                    except Exception as e:
                        print(f"恢复图片时出错: {e}")
                
                # 添加到标签页列表
                self.tabs.append(new_tab)
                
                # 创建标签页UI
                self.create_tab_ui(len(self.tabs) - 1)
            
            # 如果没有标签页，创建一个默认标签页
            if not self.tabs:
                self.create_new_tab("新建文档")
                target_tab_index = 0
            
            # 切换到目标标签页（避免保存当前状态，因为是导入过程）
            if target_tab_index < len(self.tabs):
                # 直接设置索引，不调用switch_to_tab避免保存当前状态
                self.current_tab_index = target_tab_index
                current_tab = self.tabs[target_tab_index]
                self.update_tab_ui_states()
                self.load_tab_content(current_tab)
                self.filename = current_tab['filename']
                self.update_window_title()
            else:
                # 切换到第一个标签页
                self.current_tab_index = 0
                current_tab = self.tabs[0]
                self.update_tab_ui_states()
                self.load_tab_content(current_tab)
                self.filename = current_tab['filename']
                self.update_window_title()
            
            # 重置项目修改状态
            self.project_modified = False
            
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"导入项目数据时出错: {str(e)}")
            return False
    
    def save_project(self):
        """保存项目"""
        if self.project_filename:
            return self.save_project_to_file(self.project_filename)
        else:
            return self.save_project_as()
    
    def save_project_as(self):
        """项目另存为"""
        file_path = filedialog.asksaveasfilename(
            title="保存项目",
            defaultextension=".rtep",
            filetypes=[
                ("富文本编辑器项目", "*.rtep"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            if self.save_project_to_file(file_path):
                self.project_filename = file_path
                self.project_name = os.path.splitext(os.path.basename(file_path))[0]
                self.update_window_title()
                return True
        return False
    
    def save_project_to_file(self, file_path):
        """保存项目到指定文件"""
        try:
            project_data = self.export_project_data()
            
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(project_data, file, ensure_ascii=False, indent=2)
            
            # 重置项目修改状态
            self.project_modified = False
            
            # 重置所有标签页的修改状态
            for tab in self.tabs:
                tab['modified'] = False
            
            # 重置当前文本编辑器的修改状态
            if hasattr(self, 'text_editor') and self.text_editor.winfo_exists():
                self.text_editor.edit_modified(False)
            
            # 更新窗口标题
            self.update_window_title()
            
            messagebox.showinfo("成功", f"项目已保存到: {file_path}")
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"保存项目时出错: {str(e)}")
            return False
    
    def open_project(self):
        """打开项目文件"""
        if self.check_project_changes():
            file_path = filedialog.askopenfilename(
                title="打开项目",
                filetypes=[
                    ("富文本编辑器项目", "*.rtep"),
                    ("所有文件", "*.*")
                ]
            )
            
            if file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        project_data = json.load(file)
                    
                    if self.import_project_data(project_data):
                        self.project_filename = file_path
                        self.project_name = os.path.splitext(os.path.basename(file_path))[0]
                        self.project_modified = False
                        self.update_window_title()
                        messagebox.showinfo("成功", f"项目已加载: {file_path}")
                    
                except Exception as e:
                    messagebox.showerror("错误", f"打开项目时出错: {str(e)}")
    
    def check_project_changes(self):
        """检查项目是否有未保存的更改"""
        # 检查是否有标签页被修改
        has_modified_tabs = any(tab.get('modified', False) for tab in self.tabs)
        
        if has_modified_tabs or self.project_modified:
            response = messagebox.askyesnocancel(
                "未保存的更改", 
                "当前项目有未保存的更改，是否保存？"
            )
            if response is None:  # Cancel
                return False
            elif response:  # Yes
                return self.save_project()
        return True
    
    def update_window_title(self):
        """更新窗口标题"""
        title = f"缓冲编辑器（强制置顶） - {self.project_name}"
        
        # 检查是否有未保存的更改
        has_changes = any(tab.get('modified', False) for tab in self.tabs) or self.project_modified
        if has_changes:
            title = '*' + title
        
        self.root.title(title)
        if hasattr(self, 'title_label'):
            self.title_label.config(text=title)
    
    def mark_project_modified(self):
        """标记项目为已修改"""
        if not self.project_modified:
            self.project_modified = True
            self.update_window_title()

if __name__ == "__main__":
    # 创建父窗口用于任务栏显示
    hidden_root = tk.Tk()
    hidden_root.title("缓冲编辑器（强制置顶）")
    hidden_root.geometry("1x1+0+0")  # 设置为最小尺寸并移到角落
    hidden_root.attributes('-alpha', 0.01)  # 设置为几乎透明
    
    # 创建主窗口作为子窗口
    root = tk.Toplevel(hidden_root)
    editor = TopMostEditor(root)
    editor.parent_window = hidden_root  # 设置父窗口引用
    
    # 设置关闭事件处理
    def on_closing():
        editor.exit_app()
        hidden_root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    hidden_root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # 绑定父窗口的最小化事件到子窗口
    def on_parent_iconify(event=None):
        root.withdraw()
    
    def on_parent_deiconify(event=None):
        root.deiconify()
        root.lift()
    
    hidden_root.bind('<Unmap>', on_parent_iconify)
    hidden_root.bind('<Map>', on_parent_deiconify)
    
    root.mainloop()