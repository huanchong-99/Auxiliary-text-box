# 缓冲编辑器（TopMost Editor）

一款基于 Tkinter 打造的轻量级富文本/代码编辑器，主打「窗口置顶」「多标签」与「富格式数据持久化」。

---

## 🌟 亮点特性

1. **强制置顶**：始终停留在桌面最前端，便于随手记录。  
2. **多标签书签式面板**：侧边栏快速切换，支持重命名、颜色标记。  
3. **富文本支持**：
   - 文字多色、多字体、下划线
   - 嵌入与浮动图片（PNG/JPG/GIF）
4. **项目文件（.rtep）**：一次性保存/加载全部标签页及其格式、图片、光标与自定义颜色。  
5. **语法高亮**：内置 Python 规则，可扩展。  
6. **查找替换**：支持大小写、逐个/全部替换。  
7. **自定义 UI**：无边框窗口、灰褐主题、可拖拽缩放。

---

## 📂 文件格式

| 类型 | 扩展名 | 描述 |
| ---- | ------ | ---- |
| 纯文本 | .txt .py 等 | 单文件内容，仅文本 |
| 富文本 | .rted | 单文件，包含图片与格式信息 |
| 项目 | .rtep | 多标签集合，含所有富文本数据 |

---

## 🚀 快速开始

```bash
# 可选：创建虚拟环境
pip install pillow   # 开启图片功能
python main.py       # 启动编辑器
```

### 常用快捷键

| 操作 | 快捷键 |
| ---- | ------ |
| 新建文件 | Ctrl + N |
| 打开文件 | Ctrl + O |
| 保存文件 | Ctrl + S |
| 另存为 | Ctrl + Shift + S |
| 保存项目 | Ctrl + Shift + P |
| 打开项目 | Ctrl + Shift + O |
| 查找 | Ctrl + F |
| 撤销/重做 | Ctrl + Z / Ctrl + Y |
| 剪切/复制/粘贴 | Ctrl + X / C / V |
| 退出 | Ctrl + Q |

---

## 🛠️ 架构概览

```
TopMostEditor (main.py)
├─ UI  初始化 / 自定义窗口
├─ 标签页管理
│  ├─ create_new_tab()
│  ├─ switch_to_tab()
│  └─ save_current_tab_state()
├─ 文件 & 项目 I/O
│  ├─ save_file() / open_file()
│  ├─ save_project()/open_project()
│  └─ import_project_data()/export_project_data()
├─ 富文本处理
│  ├─ change_text_color()
│  ├─ apply_selected_font()
│  └─ 图片拖拽、位置持久化
└─ 编辑辅助
   ├─ apply_syntax_highlighting()
   └─ 查找替换
```

---

## ⚙️ 打包说明（PyInstaller）

已提供 `main.spec`，包含隐藏依赖与 `default_font.json` 资源。执行：

```bash
pyinstaller main.spec
```

---

## 🐞 常见问题

1. **启动报错找不到 Pillow**：执行 `pip install pillow`。  
2. **窗口无法缩放**：请确认未处于最大化状态。  
3. **旧版文件颜色丢失**：1.1+ 版本开始支持多色标签，旧文件将按默认色显示。

---

## 📜 许可证

本项目采用 MIT License，欢迎自由使用与二次开发。