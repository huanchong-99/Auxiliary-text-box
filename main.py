import tkinter as tk
from tkinter import filedialog, messagebox, font, ttk, colorchooser
import os
from tkinter.scrolledtext import ScrolledText
import re
import json
import base64
from io import BytesIO
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

class TopMostEditor:
    def __init__(self, root):
        self.root = root
        self.filename = None
        # 标签页管理
        self.tabs = []  # 存储所有标签页信息
        self.current_tab_index = 0  # 当前活动标签页索引
        self.tab_counter = 0  # 标签页计数器
        self.setup_ui()
        # 创建第一个标签页
        self.create_new_tab("新建文档")
        
    def setup_ui(self):
        # Configure the main window
        self.root.title("缓冲编辑器（强制置顶）")
        self.root.geometry("800x600")
        self.root.attributes('-topmost', True)  # Make window always on top
        
        # 设置默认灰色背景
        default_bg = "#A0A0A0"  # RGB值160,160,160对应的十六进制颜色代码
        default_fg = "#3D2914"  # 更深的褐色文字
        
        # 应用默认颜色到根窗口
        self.root.configure(bg=default_bg)
        
        # Create main menu
        self.menu_bar = tk.Menu(self.root)
        
        # File menu
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="新建", command=self.new_file, accelerator="Ctrl+N")
        self.file_menu.add_command(label="打开", command=self.open_file, accelerator="Ctrl+O")
        self.file_menu.add_command(label="保存", command=self.save_file, accelerator="Ctrl+S")
        self.file_menu.add_command(label="另存为", command=self.save_as, accelerator="Ctrl+Shift+S")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="退出", command=self.exit_app)
        self.menu_bar.add_cascade(label="文件", menu=self.file_menu)
        
        # Edit menu
        self.edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.edit_menu.add_command(label="撤销", command=self.undo, accelerator="Ctrl+Z")
        self.edit_menu.add_command(label="重做", command=self.redo, accelerator="Ctrl+Y")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="剪切", command=self.cut, accelerator="Ctrl+X")
        self.edit_menu.add_command(label="复制", command=self.copy, accelerator="Ctrl+C")
        self.edit_menu.add_command(label="粘贴", command=self.paste, accelerator="Ctrl+V")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="查找", command=self.find_text, accelerator="Ctrl+F")
        self.menu_bar.add_cascade(label="编辑", menu=self.edit_menu)
        
        # Insert menu
        self.insert_menu = tk.Menu(self.menu_bar, tearoff=0)
        if PIL_AVAILABLE:
            self.insert_menu.add_command(label="插入图片", command=self.insert_image)
        else:
            self.insert_menu.add_command(label="插入图片 (需要安装PIL)", command=self.show_pil_warning, state="disabled")
        self.menu_bar.add_cascade(label="插入", menu=self.insert_menu)
        
        # Format menu
        self.format_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.format_menu.add_command(label="文字颜色", command=self.change_text_color)
        self.format_menu.add_command(label="背景颜色", command=self.change_bg_color)
        self.format_menu.add_command(label="字体选择", command=self.change_font)
        self.menu_bar.add_cascade(label="格式", menu=self.format_menu)
        
        # View menu
        self.view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.view_menu.add_command(label="显示行号", command=self.toggle_line_numbers)
        self.menu_bar.add_cascade(label="查看", menu=self.view_menu)
        
        # Set the menu bar
        self.root.config(menu=self.menu_bar)
        
        # 创建主框架
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建书签式标签页面板
        self.tab_panel = tk.Frame(self.main_frame, width=25, bg=default_bg, relief=tk.FLAT, bd=0)
        self.tab_panel.pack(side=tk.LEFT, fill=tk.Y)
        self.tab_panel.pack_propagate(False)  # 固定宽度
        
        # 标签页容器（书签式叠放）
        self.tab_container = tk.Frame(self.tab_panel, bg=default_bg)
        self.tab_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=5)
        
        # 新建标签页按钮（小图标）
        new_tab_btn = tk.Button(self.tab_panel, text="+", command=lambda: self.create_new_tab(),
                               bg=default_bg, fg=default_fg, relief=tk.FLAT, font=("Arial", 10, "bold"),
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
        self.text_frame = tk.Frame(self.editor_frame, bg=default_bg)
        self.text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.text_editor = tk.Text(self.text_frame, wrap=tk.WORD, undo=True, padx=5, pady=5, 
                              bg=default_bg, fg=default_fg, insertbackground=default_fg)
        self.text_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 初始化内嵌行号相关变量
        self.line_number_widgets = {}  # 存储行号Label组件
        self.show_line_numbers = True
        
        # 添加默认空行以显示行号
        default_lines = "\n" * 60
        self.text_editor.insert("1.0", default_lines)
        self.text_editor.mark_set(tk.INSERT, "1.0")  # 将光标设置到第一行
        
        # 创建并添加滚动条
        self.scrollbar_y = tk.Scrollbar(self.text_frame, orient=tk.VERTICAL, command=self.text_editor.yview,
                                   bg=default_bg)
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_editor.config(yscrollcommand=self.scrollbar_y.set)
        
        # 创建状态栏
        self.status_bar = tk.Label(self.root, text="行: 1 | 列: 0", bd=1, relief=tk.SUNKEN, anchor=tk.W,
                              bg=default_bg, fg=default_fg)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 设置其他框架的背景色
        self.main_frame.configure(bg=default_bg)
        self.editor_frame.configure(bg=default_bg)
        
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
        self.root.bind("<Control-f>", lambda event: self.find_text())
        
        # 设置焦点
        self.text_editor.focus_set()
    
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
            'cursor_pos': '1.0'
        }
        
        # 添加到标签页列表
        self.tabs.append(tab_data)
        
        # 创建标签页UI
        self.create_tab_ui(len(self.tabs) - 1)
        
        # 切换到新标签页
        self.switch_to_tab(len(self.tabs) - 1)
    
    def create_tab_ui(self, tab_index):
        """创建书签式标签页的UI元素"""
        tab_data = self.tabs[tab_index]
        
        # 创建书签式标签页（只显示序号）
        tab_number = str(tab_index + 1)
        if tab_data['modified']:
            tab_number = '*' + tab_number
        
        tab_btn = tk.Button(self.tab_container, text=tab_number,
                           command=lambda: self.switch_to_tab(tab_index),
                           bg="#A0A0A0", fg="#3D2914", relief=tk.RAISED,
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
        
        # 更新窗口标题
        title = current_tab['title']
        if current_tab['modified']:
            title = '*' + title
        self.root.title(f"缓冲编辑器（强制置顶） - {title}")
        
        # 更新filename
        self.filename = current_tab['filename']
    
    def save_current_tab_state(self):
        """保存当前标签页的状态"""
        if not self.tabs or self.current_tab_index >= len(self.tabs):
            return
            
        current_tab = self.tabs[self.current_tab_index]
        
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
            
        self.images = tab_data['images'].copy()
        self.image_info = tab_data['image_info'].copy()
        
        # 设置修改状态
        self.text_editor.edit_modified(tab_data['modified'])
        
        # 更新行号
        self.update_line_numbers()
    
    def update_tab_ui_states(self):
        """更新所有标签页的UI状态"""
        for i, tab in enumerate(self.tabs):
            if i == self.current_tab_index:
                # 当前活动标签页
                tab['ui_button'].config(bg="#8A8A8A", relief=tk.SUNKEN)
            else:
                # 非活动标签页
                tab['ui_button'].config(bg="#A0A0A0", relief=tk.RAISED)
    
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
        context_menu.add_separator()
        context_menu.add_command(label="关闭标签页", command=lambda: self.close_tab(tab_index))
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def rename_tab(self, tab_index):
        """重命名标签页"""
        tab_data = self.tabs[tab_index]
        current_name = tab_data['title'].lstrip('*')  # 移除修改标记
        
        # 创建重命名对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("重命名标签页")
        dialog.geometry("300x120")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
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
                    title = new_name
                    if tab_data['modified']:
                        title = '*' + title
                    self.root.title(f"缓冲编辑器（强制置顶） - {title}")
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
                    ("所有支持的文件", "*.txt;*.py;*.rted"),
                    ("富文本文档", "*.rted"),
                    ("纯文本文件", "*.txt"), 
                    ("Python文件", "*.py"),
                    ("所有文件", "*.*")
                ]
            )
            
            if file_path:
                try:
                    if file_path.lower().endswith('.rted'):
                        # 打开富文本文件
                        self.open_rich_text_file(file_path)
                    else:
                        # 打开纯文本文件
                        self.open_plain_text_file(file_path)
                        
                    # 更新当前标签页信息
                    current_tab = self.tabs[self.current_tab_index]
                    current_tab['filename'] = file_path
                    current_tab['title'] = os.path.basename(file_path)
                    current_tab['modified'] = False
                    
                    # 更新标签页UI（书签式显示序号）
                    tab_number = str(self.current_tab_index + 1)
                    current_tab['ui_button'].config(text=tab_number)
                    
                    self.filename = file_path
                    self.root.title(f"缓冲编辑器（强制置顶） - {os.path.basename(file_path)}")
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
                
                # 在指定位置插入图片
                position = img_data['position']
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
                    'original_image': image
                }
                
                # 绑定右键菜单
                self.bind_image_context_menu(image_name)
                
                # 如果图片可拖动，启用拖动功能
                if img_data.get('draggable', False):
                    self.toggle_image_draggable(image_name, True)
                    
            except Exception as e:
                print(f"恢复图片时出错: {e}")
                messagebox.showwarning("警告", f"无法恢复某个图片: {str(e)}")
    
    def save_file(self):
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
                    
                    # 更新标签页UI（书签式显示序号）
                    tab_number = str(self.current_tab_index + 1)
                    current_tab['ui_button'].config(text=tab_number)
                
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
        # 更新窗口标题，移除星号
        title = self.root.title()
        if title.startswith('*'):
            self.root.title(title[1:])
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
                    # 获取图片在文本中的位置
                    image_pos = self.text_editor.index(image_name)
                    
                    # 将图片转换为base64
                    original_image = image_info['original_image']
                    buffer = BytesIO()
                    original_image.save(buffer, format='PNG')
                    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    
                    save_data['images'].append({
                        'position': image_pos,
                        'file_path': image_info['file_path'],
                        'image_data': image_base64,
                        'draggable': image_info['draggable']
                    })
                except Exception as e:
                    print(f"保存图片时出错: {e}")
        
        # 保存到文件
        with open(self.filename, 'w', encoding='utf-8') as file:
            json.dump(save_data, file, ensure_ascii=False, indent=2)
        
        self.text_editor.edit_modified(False)
        # 更新窗口标题，移除星号
        title = self.root.title()
        if title.startswith('*'):
            self.root.title(title[1:])
        return True
    
    def save_as(self):
        # 检查是否包含图片
        has_images = hasattr(self, 'image_info') and len(self.image_info) > 0
        
        if has_images:
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
            self.filename = file_path
            
            # 更新当前标签页信息
            current_tab = self.tabs[self.current_tab_index]
            current_tab['filename'] = file_path
            current_tab['title'] = os.path.basename(file_path)
            
            # 更新标签页UI（书签式显示序号）
            tab_number = str(self.current_tab_index + 1)
            current_tab['ui_button'].config(text=tab_number)
            
            self.root.title(f"缓冲编辑器（强制置顶） - {os.path.basename(file_path)}")
            return self.save_file()
        return False
    
    def exit_app(self):
        # 检查所有标签页是否有未保存的更改
        for i, tab in enumerate(self.tabs):
            if tab['modified']:
                # 切换到有未保存更改的标签页
                self.switch_to_tab(i)
                response = messagebox.askyesnocancel("未保存的更改", f"标签页 '{tab['title']}' 有未保存的更改，是否保存？")
                if response is None:  # Cancel
                    return
                elif response:  # Yes
                    if not self.save_file():
                        return
        
        self.root.destroy()
    
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
                
                # 在当前光标位置插入图片
                cursor_pos = self.text_editor.index(tk.INSERT)
                image_name = self.text_editor.image_create(cursor_pos, image=photo)
                
                # 保存图片引用和信息，防止被垃圾回收
                if not hasattr(self, 'images'):
                    self.images = []
                if not hasattr(self, 'image_info'):
                    self.image_info = {}
                    
                self.images.append(photo)
                self.image_info[image_name] = {
                    'photo': photo,
                    'draggable': False,
                    'file_path': file_path,
                    'original_image': image
                }
                
                # 为图片绑定右键菜单
                self.bind_image_context_menu(image_name)
                
                # 在图片后添加换行
                self.text_editor.insert(tk.INSERT, "\n")
                
            except Exception as e:
                messagebox.showerror("错误", f"无法插入图片: {str(e)}")
    
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
    
    def toggle_image_draggable(self, image_name, draggable):
        """切换图片的拖动状态"""
        if image_name in self.image_info:
            self.image_info[image_name]['draggable'] = draggable
            
            if draggable:
                # 启用拖动
                self.text_editor.tag_bind(f"image_{image_name}", "<Button-1>", lambda e: self.start_image_drag(e, image_name))
                self.text_editor.tag_bind(f"image_{image_name}", "<B1-Motion>", lambda e: self.drag_image(e, image_name))
                self.text_editor.tag_bind(f"image_{image_name}", "<ButtonRelease-1>", lambda e: self.end_image_drag(e, image_name))
                messagebox.showinfo("提示", "图片拖动已启用，现在可以拖动图片了")
            else:
                # 禁用拖动
                self.text_editor.tag_unbind(f"image_{image_name}", "<Button-1>")
                self.text_editor.tag_unbind(f"image_{image_name}", "<B1-Motion>")
                self.text_editor.tag_unbind(f"image_{image_name}", "<ButtonRelease-1>")
                messagebox.showinfo("提示", "图片拖动已禁用")
    
    def start_image_drag(self, event, image_name):
        """开始拖动图片"""
        self.drag_data = {
            'image_name': image_name,
            'start_x': event.x,
            'start_y': event.y
        }
    
    def drag_image(self, event, image_name):
        """拖动图片过程中"""
        if hasattr(self, 'drag_data') and self.drag_data['image_name'] == image_name:
            # 计算新位置
            new_pos = self.text_editor.index(f"@{event.x},{event.y}")
            
            # 移动图片到新位置
            try:
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
                
            except tk.TclError:
                pass  # 忽略拖动过程中的错误
    
    def end_image_drag(self, event, image_name):
        """结束拖动图片"""
        if hasattr(self, 'drag_data'):
            del self.drag_data
    
    def delete_image(self, image_name):
        """删除图片"""
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
                self.line_numbers,
                self.status_bar,
            ]
            
            for widget in widgets:
                widget.config(bg=bg_color)
                
            # 设置文本相关前景色
            self.text_editor.config(fg=fg_color, insertbackground=fg_color)
            self.line_numbers.config(fg=fg_color)
            self.status_bar.config(fg=fg_color)
            
            # 设置滚动条颜色 (部分平台支持)
            try:
                self.scrollbar_y.config(bg=bg_color, activebackground=bg_color, troughcolor=bg_color)
            except:
                pass
                
            # 设置菜单颜色
            for menu in [self.file_menu, self.edit_menu, self.format_menu, self.view_menu]:
                try:
                    menu.config(bg=bg_color, fg=fg_color, activebackground=bg_color, activeforeground=fg_color)
                except:
                    pass
                    
            # 强制更新UI
            self.root.update_idletasks()
    
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
        
        # 根据亮度决定文本颜色
        if brightness > 128:
            return "#000000"  # 黑色
        else:
            return "#FFFFFF"  # 白色
    
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
            self.line_numbers.configure(font=new_font)
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
                # 创建行号Label
                line_label = tk.Label(self.text_editor, text=f"{line_num:3d}", 
                                    fg="#CCCCCC", bg=self.text_editor.cget("bg"),
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
                # 创建行号Label
                line_label = tk.Label(self.text_editor, text=f"{line_num:3d}", 
                                    fg="#CCCCCC", bg=self.text_editor.cget("bg"),
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
                
                # 更新标签页UI显示（书签式显示序号）
                tab_number = str(self.current_tab_index + 1)
                if not tab_number.startswith('*'):
                    current_tab['ui_button'].config(text='*' + tab_number)
            
            # 更新窗口标题
            if self.root.title()[0] != '*':
                title = self.root.title()
                self.root.title('*' + title)
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

if __name__ == "__main__":
    root = tk.Tk()
    editor = TopMostEditor(root)
    root.protocol("WM_DELETE_WINDOW", editor.exit_app)
    root.mainloop()