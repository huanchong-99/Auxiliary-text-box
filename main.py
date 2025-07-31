import tkinter as tk
from tkinter import filedialog, messagebox, font, ttk, colorchooser
import os
from tkinter.scrolledtext import ScrolledText
import re

class TopMostEditor:
    def __init__(self, root):
        self.root = root
        self.filename = None
        self.setup_ui()
        
    def setup_ui(self):
        # Configure the main window
        self.root.title("缓冲编辑器（强制置顶）")
        self.root.geometry("800x600")
        self.root.attributes('-topmost', True)  # Make window always on top
        
        # 设置默认灰色背景
        default_bg = "#A0A0A0"  # RGB值160,160,160对应的十六进制颜色代码
        default_fg = "#000000"  # 黑色文字
        
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
        
        # 创建一个框架容纳编辑器和行号
        self.editor_frame = tk.Frame(self.main_frame)
        self.editor_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建行号显示区域
        self.line_numbers = tk.Text(self.editor_frame, width=4, padx=3, pady=0, 
                               takefocus=0, border=0, background=default_bg, foreground=default_fg,
                               state='disabled', wrap='none')
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # 创建文本编辑器
        self.text_frame = tk.Frame(self.editor_frame, bg=default_bg)
        self.text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.text_editor = tk.Text(self.text_frame, wrap=tk.WORD, undo=True, padx=5, pady=5, 
                              bg=default_bg, fg=default_fg, insertbackground=default_fg)
        self.text_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
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
        self.line_numbers.configure(font=self.default_font)
        
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
        
    def new_file(self):
        if self.check_save_changes():
            self.text_editor.delete(1.0, tk.END)
            self.filename = None
            self.root.title("缓冲编辑器（强制置顶）")
            self.update_line_numbers()
    
    def open_file(self):
        if self.check_save_changes():
            file_path = filedialog.askopenfilename(
                filetypes=[
                    ("Text Files", "*.txt"), 
                    ("Python Files", "*.py"),
                    ("All Files", "*.*")
                ]
            )
            
            if file_path:
                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read()
                        self.text_editor.delete(1.0, tk.END)
                        self.text_editor.insert(1.0, content)
                        self.filename = file_path
                        self.root.title(f"缓冲编辑器（强制置顶） - {os.path.basename(file_path)}")
                        self.update_line_numbers()
                        self.apply_syntax_highlighting()
                except Exception as e:
                    messagebox.showerror("错误", f"无法打开文件: {str(e)}")
    
    def save_file(self):
        if self.filename:
            try:
                content = self.text_editor.get(1.0, tk.END)
                with open(self.filename, "w", encoding="utf-8") as file:
                    file.write(content)
                self.text_editor.edit_modified(False)
                return True
            except Exception as e:
                messagebox.showerror("错误", f"无法保存文件: {str(e)}")
                return False
        else:
            return self.save_as()
    
    def save_as(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[
                ("Text Files", "*.txt"),
                ("Python Files", "*.py"),
                ("All Files", "*.*")
            ]
        )
        
        if file_path:
            self.filename = file_path
            self.root.title(f"缓冲编辑器（强制置顶） - {os.path.basename(file_path)}")
            return self.save_file()
        return False
    
    def exit_app(self):
        if self.check_save_changes():
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
        self.update_line_numbers()
    
    def update_line_numbers(self):
        if not hasattr(self, 'line_numbers'):
            return
            
        # 清除所有文本
        self.line_numbers.config(state='normal')
        self.line_numbers.delete(1.0, tk.END)
        
        if self.show_line_numbers:
            # 显示行号
            i = self.text_editor.index("@0,0")
            while True:
                dline = self.text_editor.dlineinfo(i)
                if dline is None:
                    break
                
                linenum = str(i).split('.')[0]
                self.line_numbers.insert(tk.END, f"{linenum}\n")
                i = self.text_editor.index(f"{i}+1line")
                
            # 显示行号文本框
            self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        else:
            # 隐藏行号文本框
            self.line_numbers.pack_forget()
            
        self.line_numbers.config(state='disabled')
    
    def on_text_changed(self, event=None):
        self.update_line_numbers()
        
        # 同步滚动 - 直接设置行号文本框的yview位置
        first, _ = self.text_editor.yview()
        self.line_numbers.yview_moveto(first)
    
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
        if self.text_editor.edit_modified():
            if self.root.title()[0] != '*':
                title = self.root.title()
                self.root.title('*' + title)
        self.text_editor.edit_modified(False)
    
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