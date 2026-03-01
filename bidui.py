import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
import os

class ASSSubtitleProcessor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ASS字幕文件原文译文并排显示工具")
        self.root.geometry("1920x1080")
        
        # 添加显示状态变量
        self.show_original = True
        self.show_translation = True
        self.show_combined = False
        self.original_texts = []
        self.translated_texts = []
        
        # 字体大小变量
        self.font_size = 10
        self.font_name = "TkDefaultFont"

        # 初始化滚动位置变量
        self.left_scroll_position = 0.0
        self.combined_scroll_position = 0.0

        # 搜索相关变量
        self.search_term = ""
        self.search_results = []
        self.current_search_index = -1
        
        self.setup_ui()
        self.setup_shortcuts()
        
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding="5")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.file_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path_var, width=80).grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(file_frame, text="选择ASS文件", command=self.select_file).grid(row=0, column=1)
        
        file_frame.columnconfigure(0, weight=1)

        # 搜索框区域（初始隐藏）
        self.search_frame = ttk.Frame(main_frame)
        # 默认不显示，通过Ctrl+F触发显示
        # self.search_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(self.search_frame, text="搜索:").grid(row=0, column=0, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var, width=40)
        self.search_entry.grid(row=0, column=1, padx=(0, 5))
        
        ttk.Button(self.search_frame, text="查找下一个", command=self.search_next).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(self.search_frame, text="查找上一个", command=self.search_previous).grid(row=0, column=3, padx=(0, 5))
        ttk.Button(self.search_frame, text="关闭", command=self.hide_search).grid(row=0, column=4)
        
        # 显示区域
        display_frame = ttk.Frame(main_frame)
        display_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 左侧原文框
        self.left_frame = ttk.LabelFrame(display_frame, text="原文（英文字幕）", padding="5")
        self.left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        self._left_scrollbar = ttk.Scrollbar(self.left_frame)  # 保存为实例变量
        self._left_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.left_text = tk.Text(self.left_frame, yscrollcommand=self.on_left_scroll, wrap=tk.WORD, width=60)
        self.left_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self._left_scrollbar.config(command=self.on_scroll_command)
        
        # 右侧译文框
        self.right_frame = ttk.LabelFrame(display_frame, text="译文（中文字幕）", padding="5")
        self.right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self._right_scrollbar = ttk.Scrollbar(self.right_frame)  # 保存为实例变量
        self._right_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.right_text = tk.Text(self.right_frame, yscrollcommand=self.on_right_scroll, wrap=tk.WORD, width=60)
        self.right_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self._right_scrollbar.config(command=self.on_scroll_command)

        # 为文本框绑定焦点事件
        self.left_text.bind('<FocusIn>', lambda e: setattr(self, '_last_focused_text', self.left_text))
        self.right_text.bind('<FocusIn>', lambda e: setattr(self, '_last_focused_text', self.right_text))
        
        # 组合显示框（原文译文结合）
        self.combined_frame = ttk.LabelFrame(display_frame, text="原文译文结合", padding="5")
        # 初始时不显示
        # self.combined_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        combined_scrollbar = ttk.Scrollbar(self.combined_frame)
        combined_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.combined_text = tk.Text(self.combined_frame, yscrollcommand=combined_scrollbar.set, wrap=tk.WORD, width=120)
        self.combined_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        combined_scrollbar.config(command=self.combined_text.yview)
        
        # 按钮区域 - 分为两行
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(10, 5))
        
        # 第一行按钮
        row1_frame = ttk.Frame(button_frame)
        row1_frame.pack(side=tk.TOP, pady=(0, 5))
        
        ttk.Button(row1_frame, text="处理文件", command=self.process_file).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(row1_frame, text="保存原文", command=self.save_originals).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(row1_frame, text="保存译文", command=self.save_translations).pack(side=tk.LEFT)
        
        # 第二行按钮
        row2_frame = ttk.Frame(button_frame)
        row2_frame.pack(side=tk.TOP, pady=(0, 0))
        
        ttk.Button(row2_frame, text="原译结合", command=self.toggle_combined).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(row2_frame, text="隐藏原文", command=self.toggle_original).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(row2_frame, text="隐藏译文", command=self.toggle_translation).pack(side=tk.LEFT)
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)  # 改为row=2，因为搜索框在row=1
        display_frame.columnconfigure(0, weight=1)
        display_frame.columnconfigure(1, weight=1)
        display_frame.rowconfigure(0, weight=1)
        self.left_frame.columnconfigure(0, weight=1)
        self.left_frame.rowconfigure(0, weight=1)
        self.right_frame.columnconfigure(0, weight=1)
        self.right_frame.rowconfigure(0, weight=1)
        self.combined_frame.columnconfigure(0, weight=1)
        self.combined_frame.rowconfigure(0, weight=1)
    def update_last_focused(self, event):
        """更新最后获得焦点的文本框"""
        self.last_focused_text_widget = event.widget
    def on_left_scroll(self, *args):
        """左边文本框滚动时的回调"""
        # 更新左边滚动条
        self._left_scrollbar.set(*args)
        
        # 同步右边文本框的滚动位置
        self.right_text.yview_moveto(args[0])
    
    def on_right_scroll(self, *args):
        """右边文本框滚动时的回调"""
        # 更新右边滚动条
        self._right_scrollbar.set(*args)
        
        # 同步左边文本框的滚动位置
        self.left_text.yview_moveto(args[0])
    
    def on_scroll_command(self, *args):
        """滚动条拖动时的回调"""
        # 同时滚动两个文本框
        self.left_text.yview(*args)
        self.right_text.yview(*args)
        
    def setup_shortcuts(self):
        """设置快捷键"""
        # 处理文件: Ctrl+O
        self.root.bind('<Control-o>', lambda e: self.process_file())
        self.root.bind('<Control-O>', lambda e: self.process_file())
        
        # 保存原文: Ctrl+S
        self.root.bind('<Control-Shift-s>', lambda e: self.save_originals())
        self.root.bind('<Control-Shift-S>', lambda e: self.save_originals())
        
        # 保存译文: Ctrl+T
        self.root.bind('<Control-Shift-t>', lambda e: self.save_translations())
        self.root.bind('<Control-Shift-T>', lambda e: self.save_translations())
        
        # 原译结合: Ctrl+C
        self.root.bind('<Control-Shift-c>', lambda e: self.toggle_combined())
        self.root.bind('<Control-Shift-C>', lambda e: self.toggle_combined())
        
        # 隐藏原文: Ctrl+X
        self.root.bind('<Control-Shift-x>', lambda e: self.toggle_original())
        self.root.bind('<Control-Shift-X>', lambda e: self.toggle_original())
        
        # 隐藏译文: Ctrl+Z
        self.root.bind('<Control-Shift-z>', lambda e: self.toggle_translation())
        self.root.bind('<Control-Shift-Z>', lambda e: self.toggle_translation())

        # 搜索: Ctrl+F
        self.root.bind('<Control-f>', lambda e: self.show_search())
        self.root.bind('<Control-F>', lambda e: self.show_search())
        
        # F5 刷新/处理文件
        self.root.bind('<F5>', lambda e: self.process_file())
        
        # F1 显示快捷键帮助
        self.root.bind('<F1>', lambda e: self.show_shortcut_help())
        
        # Ctrl+鼠标滚轮调节字体大小
        self.root.bind('<Control-MouseWheel>', self.change_font_size)

        # 为搜索框添加回车键搜索
        self.root.bind('<Return>', lambda e: self.search_next())
        
        # 为按钮添加键盘提示
        self.root.focus_set()
    
    def change_font_size(self, event):
        """通过Ctrl+鼠标滚轮调节字体大小"""
        if event.delta > 0 or event.num == 4:  # 向上滚动或Button4（Linux）
            self.font_size = min(self.font_size + 1, 30)  # 最大30号字体
        elif event.delta < 0 or event.num == 5:  # 向下滚动或Button5（Linux）
            self.font_size = max(self.font_size - 1, 6)   # 最小6号字体
        
        # 重新配置所有Text控件的字体
        self.left_text.config(font=(self.font_name, self.font_size))
        self.right_text.config(font=(self.font_name, self.font_size))
        self.combined_text.config(font=(self.font_name, self.font_size))
    
    def show_shortcut_help(self):
        """显示快捷键帮助"""
        help_text = """
快捷键说明：
Ctrl+O: 选择并处理文件
Ctrl+Shift+S: 保存原文
Ctrl+Shift+T: 保存译文
Ctrl+Shift+C: 切换原译结合模式
Ctrl+Shift+X: 隐藏/显示原文
Ctrl+Shift+Z: 隐藏/显示译文
Ctrl+鼠标滚轮: 调节文字大小
Ctrl+F: 搜索文本
F5: 重新处理当前文件
F1: 显示此帮助
        """
        messagebox.showinfo("快捷键帮助", help_text)
    
    def show_search(self):
        """显示搜索框，并自动填充当前选中的文本（支持原文、译文、组合模式）"""
        self.search_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.search_entry.focus_set()

        selected_text = ""
        
        if self.show_combined:
            # 组合模式：只从 combined_text 获取
            try:
                selected_text = self.combined_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            except tk.TclError:
                pass
        else:
            # 普通模式：优先检查 left_text，再检查 right_text
            try:
                selected_text = self.left_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            except tk.TclError:
                try:
                    selected_text = self.right_text.get(tk.SEL_FIRST, tk.SEL_LAST)
                except tk.TclError:
                    pass  # 两个都没选中
        
        if selected_text:
            self.search_var.set(selected_text)
    def get_search_target(self):
        """确定搜索目标文本框"""
        # 如果处于组合模式，直接返回组合框
        if self.show_combined:
            return self.combined_text, "combined"
        
        # 在普通模式下，优先使用“最近获得过焦点”的文本框
        # 我们通过绑定 <FocusIn> 事件来记录 last_focused_text
        if hasattr(self, '_last_focused_text'):
            if self._last_focused_text == self.left_text:
                return self.left_text, "original"
            elif self._last_focused_text == self.right_text:
                return self.right_text, "translation"
        
        # 如果没有记录，默认按当前焦点（兼容性兜底）
        focused_widget = self.root.focus_get()
        if focused_widget == self.left_text:
            return self.left_text, "original"
        elif focused_widget == self.right_text:
            return self.right_text, "translation"
        
        # 最终默认：如果都没焦点，且无记录，则根据是否有选中文本来推测
        try:
            if self.left_text.get(tk.SEL_FIRST, tk.SEL_LAST):
                return self.left_text, "original"
        except tk.TclError:
            pass
        try:
            if self.right_text.get(tk.SEL_FIRST, tk.SEL_LAST):
                return self.right_text, "translation"
        except tk.TclError:
            pass

        # 实在无法判断，保守返回译文（保持原逻辑）
        return self.right_text, "translation"

    def hide_search(self):
        """隐藏搜索框"""
        self.search_frame.grid_remove()
        # 清除高亮
        self.clear_highlight()
        # 焦点回到主窗口
        self.root.focus_set()

    def clear_highlight(self):
        """清除所有文本框的高亮"""
        self.left_text.tag_remove("highlight", "1.0", tk.END)
        self.right_text.tag_remove("highlight", "1.0", tk.END)
        self.combined_text.tag_remove("highlight", "1.0", tk.END)

    def highlight_pattern(self, text_widget, pattern, start_index="1.0"):
        """高亮匹配的文本"""
        text_widget.tag_configure("highlight", background="yellow")
        
        # 清除之前的高亮
        text_widget.tag_remove("highlight", "1.0", tk.END)
        
        if not pattern:
            return []
        
        # 查找所有匹配项
        start = start_index
        matches = []
        while True:
            pos = text_widget.search(pattern, start, stopindex=tk.END, nocase=1)
            if not pos:
                break
            end = f"{pos}+{len(pattern)}c"
            text_widget.tag_add("highlight", pos, end)
            matches.append((pos, end))
            start = end
        
        return matches

    def search_next(self):
        """查找下一个匹配项"""
        search_term = self.search_var.get().strip()
        if not search_term:
            return
        
        # 获取搜索目标
        target_widget, search_type = self.get_search_target()
        
        # 如果搜索词改变，重新搜索
        if (search_term != self.search_term or 
            search_type != getattr(self, 'last_search_type', None)):
            self.search_term = search_term
            self.last_search_type = search_type
            self.search_results = []
            self.current_search_index = -1
            
            if search_type == "combined":
                # 在组合文本中搜索
                self.search_results = self.highlight_pattern(target_widget, search_term)
            else:
                # 在单个文本框中搜索
                self.search_results = self.highlight_pattern(target_widget, search_term)
        
        if not self.search_results:
            messagebox.showinfo("搜索", "未找到匹配项")
            return
        
        # 移动到下一个结果
        self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
        self.jump_to_search_result()

    def search_previous(self):
        """查找上一个匹配项"""
        search_term = self.search_var.get().strip()
        if not search_term:
            return
        
        # 获取搜索目标
        target_widget, search_type = self.get_search_target()
        
        # 如果搜索词改变或搜索目标改变，重新搜索
        if (search_term != self.search_term or 
            search_type != getattr(self, 'last_search_type', None)):
            self.search_term = search_term
            self.last_search_type = search_type
            self.search_results = []
            self.current_search_index = 0
            
            if search_type == "combined":
                # 在组合文本中搜索
                self.search_results = self.highlight_pattern(target_widget, search_term)
            else:
                # 在单个文本框中搜索
                self.search_results = self.highlight_pattern(target_widget, search_term)
        
        if not self.search_results:
            messagebox.showinfo("搜索", "未找到匹配项")
            return
        
        # 移动到上一个结果
        self.current_search_index = (self.current_search_index - 1) % len(self.search_results)
        self.jump_to_search_result()

    def jump_to_search_result(self):
        """跳转到当前搜索结果"""
        if not self.search_results or self.current_search_index < 0:
            return
        
        # 获取搜索目标
        target_widget, search_type = self.get_search_target()
        
        pos, end = self.search_results[self.current_search_index]
        
        # 跳转到搜索结果位置
        target_widget.see(pos)
        target_widget.focus_set()
        
        # 选中匹配的文本
        target_widget.tag_remove(tk.SEL, "1.0", tk.END)
        target_widget.tag_add(tk.SEL, pos, end)
        
        # 如果是普通模式且搜索的是原文框，同步滚动译文框
        if not self.show_combined and search_type == "original":
            try:
                # 计算行号
                line_num = int(pos.split('.')[0])
                # 将右文本框滚动到相同位置
                self.right_text.yview_moveto((line_num - 1) / float(self.left_text.index(tk.END).split('.')[0]))
            except:
                pass
        # 如果是普通模式且搜索的是译文框，同步滚动原文框
        elif not self.show_combined and search_type == "translation":
            try:
                # 计算行号
                line_num = int(pos.split('.')[0])
                # 将左文本框滚动到相同位置
                self.left_text.yview_moveto((line_num - 1) / float(self.right_text.index(tk.END).split('.')[0]))
            except:
                pass
    def toggle_combined(self):
        """切换原译结合显示"""
        if self.show_combined:
            # 保存组合框的滚动位置
            self.combined_scroll_position = self.combined_text.yview()[0]

            # 隐藏组合显示，显示原文和译文框
            self.combined_frame.grid_remove()
            if self.show_original:
                self.left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
            if self.show_translation:
                self.right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
            self.show_combined = False

            # 恢复左右文本框的滚动位置
            if hasattr(self, 'left_scroll_position'):
                self.left_text.yview_moveto(self.left_scroll_position)
                self.right_text.yview_moveto(self.left_scroll_position)
        else:
            # 保存左右文本框的滚动位置
            self.left_scroll_position = self.left_text.yview()[0]

            # 隐藏原文和译文框，显示组合显示
            self.left_frame.grid_remove()
            self.right_frame.grid_remove()
            
            # 如果有内容则显示组合文本
            if self.original_texts or self.translated_texts:
                self.update_combined_display()
            
            self.show_combined = True

            # 恢复组合框的滚动位置
            if hasattr(self, 'combined_scroll_position'):
                self.combined_text.yview_moveto(self.combined_scroll_position)
    
    def update_combined_display(self):
        """更新组合显示的内容"""
        # 清空组合文本框
        self.combined_text.delete(1.0, tk.END)
        
        # 计算最大行数
        max_lines = max(len(self.original_texts), len(self.translated_texts))
        
        # 逐行添加原文和译文（根据当前显示设置）
        for i in range(max_lines):
            if self.show_original and i < len(self.original_texts):
                self.combined_text.insert(tk.END, f"{self.original_texts[i]}\n")
            if self.show_translation and i < len(self.translated_texts):
                self.combined_text.insert(tk.END, f"{self.translated_texts[i]}\n")
            if (self.show_original and i < len(self.original_texts)) or (self.show_translation and i < len(self.translated_texts)):
                self.combined_text.insert(tk.END, "\n")  # 添加空行分隔
        
        # 确保组合框是显示的
        self.combined_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def toggle_original(self):
        """切换原文显示/隐藏"""
        if self.show_combined:
            # 在组合显示模式下切换原文显示
            # 保存当前滚动位置
            current_scroll = self.combined_text.yview()[0]
            self.show_original = not self.show_original
            self.update_combined_display()

            # 恢复滚动位置
            self.combined_text.yview_moveto(current_scroll)
        else:
            # 保存当前滚动位置
            current_scroll = self.left_text.yview()[0]
            # 在普通模式下切换原文显示
            if self.show_original:
                # 隐藏原文
                self.left_frame.grid_remove()
                self.show_original = False
            else:
                # 显示原文
                self.left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
                self.show_original = True
            # 恢复滚动位置
            self.left_text.yview_moveto(current_scroll)
            self.right_text.yview_moveto(current_scroll)
    
    def toggle_translation(self):
        """切换译文显示/隐藏"""
        if self.show_combined:
            # 在组合显示模式下切换译文显示
            # 保存当前滚动位置
            current_scroll = self.combined_text.yview()[0]
            self.show_translation = not self.show_translation
            self.update_combined_display()

            # 恢复滚动位置
            self.combined_text.yview_moveto(current_scroll)
        else:
            # 保存当前滚动位置
            current_scroll = self.left_text.yview()[0]
            # 在普通模式下切换译文显示
            if self.show_translation:
                # 隐藏译文
                self.right_frame.grid_remove()
                self.show_translation = False
            else:
                # 显示译文
                self.right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
                self.show_translation = True
            # 恢复滚动位置
            self.left_text.yview_moveto(current_scroll)
            self.right_text.yview_moveto(current_scroll)
    
    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="选择ASS字幕文件",
            filetypes=[("ASS文件", "*.ass"), ("所有文件", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)
    
    def extract_subtitle_text(self, line):
        """从ASS文件的Dialogue行中提取文本"""
        # 使用更灵活的正则表达式来匹配Dialogue行
        # 格式: Dialogue: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        pattern = r'^Dialogue:\s*(\d+),([^,]+),([^,]+),([^,]+),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),(.*)$'
        match = re.match(pattern, line)
        
        if match:
            layer = match.group(1)
            start_time = match.group(2)
            end_time = match.group(3)
            style = match.group(4)
            name = match.group(5)
            margin_l = match.group(6)
            margin_r = match.group(7)
            margin_v = match.group(8)
            effect = match.group(9)
            text = match.group(10)
            
            # 移除样式标签，如{\pos(400,300)}或{\r英文字幕}
            text = re.sub(r'{[^}]*}', '', text)
            return style.strip(), text.strip(), start_time.strip(), end_time.strip()
        
        return None, "", "", ""
    
    def separate_chinese_english(self, text):
        """分离中英文字幕，假设格式为"中文\\N英文"或"英文\\N中文" """
        if '\\N' in text:
            parts = text.split('\\N', 1)  # 只分割第一个\N
            if len(parts) == 2:
                part1, part2 = parts[0].strip(), parts[1].strip()
                
                # 简单判断哪部分是中文，哪部分是英文
                # 中文字符的Unicode范围是4e00-9fff
                has_chinese1 = any('\u4e00' <= char <= '\u9fff' for char in part1)
                has_chinese2 = any('\u4e00' <= char <= '\u9fff' for char in part2)
                
                if has_chinese1 and not has_chinese2:
                    # part1是中文，part2是英文
                    return part2, part1  # 英文, 中文
                elif has_chinese2 and not has_chinese1:
                    # part2是中文，part1是英文
                    return part1, part2  # 英文, 中文
                else:
                    # 如果无法确定，返回原值
                    return part2, part1  # 默认认为后半部分是中文
        return "", text  # 如果没有分隔符，认为整个是中文
    
    def process_file(self):
        file_path = self.file_path_var.get()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("错误", "请选择有效的ASS文件")
            return
        
        try:
            # 尝试不同的编码方式
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            lines = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        lines = file.readlines()
                    break
                except UnicodeDecodeError:
                    continue
            
            if lines is None:
                messagebox.showerror("错误", "无法使用常见编码读取文件")
                return
            
            original_texts = []  # 存储原文（英文字幕）
            translated_texts = []  # 存储译文（中文字幕）
            
            for line in lines:
                line = line.strip()
                if line.startswith('Dialogue:'):
                    style, text, start_time, end_time = self.extract_subtitle_text(line)
                    if text and style in ["译文字幕", "英文字幕"]:
                        if style == "译文字幕":
                            # 分离中英文字幕
                            english_part, chinese_part = self.separate_chinese_english(text)
                            if english_part:
                                original_texts.append(english_part)
                            if chinese_part:
                                translated_texts.append(chinese_part)
                        elif style == "英文字幕":
                            # 这是纯英文字幕
                            original_texts.append(text)
            
            # 保存原始数据
            self.original_texts = original_texts
            self.translated_texts = translated_texts
            
            # 清空文本框
            self.left_text.delete(1.0, tk.END)
            self.right_text.delete(1.0, tk.END)
            self.combined_text.delete(1.0, tk.END)
            
            # 显示原文
            if original_texts:
                for text in original_texts:
                    self.left_text.insert(tk.END, f"{text}\n\n")
            else:
                self.left_text.insert(tk.END, "未找到英文字幕\n")
            
            # 显示译文
            if translated_texts:
                for text in translated_texts:
                    self.right_text.insert(tk.END, f"{text}\n\n")
            else:
                self.right_text.insert(tk.END, "未找到中文字幕\n")
                
            # 如果当前是组合显示模式，更新组合显示
            if self.show_combined:
                self.update_combined_display()
                
        except Exception as e:
            messagebox.showerror("错误", f"处理文件时出错: {str(e)}")
    
    def save_originals(self):
        content = self.left_text.get(1.0, tk.END).strip()
        if not content or content == "未找到英文字幕\n":
            messagebox.showwarning("警告", "没有可保存的原文")
            return
        
        # 获取ASS文件路径并生成原文.txt路径
        ass_path = self.file_path_var.get()
        if not ass_path:
            messagebox.showerror("错误", "请先选择ASS文件")
            return
        
        # 生成原文.txt文件路径
        dir_path = os.path.dirname(ass_path)
        file_name = os.path.splitext(os.path.basename(ass_path))[0]
        output_path = os.path.join(dir_path, f"{file_name}_原文.txt")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(self.left_text.get(1.0, tk.END))
            # messagebox.showinfo("成功", f"原文已保存到: {output_path}")
            print(f"原文已保存到: {output_path}")
        except Exception as e:
            # messagebox.showerror("错误", f"保存原文时出错: {str(e)}")
            print(f"保存原文时出错: {str(e)}")
    
    def save_translations(self):
        content = self.right_text.get(1.0, tk.END).strip()
        if not content or content == "未找到中文字幕\n":
            messagebox.showwarning("警告", "没有可保存的译文")
            return
        
        # 获取ASS文件路径并生成译文.txt路径
        ass_path = self.file_path_var.get()
        if not ass_path:
            messagebox.showerror("错误", "请先选择ASS文件")
            return
        
        # 生成译文.txt文件路径
        dir_path = os.path.dirname(ass_path)
        file_name = os.path.splitext(os.path.basename(ass_path))[0]
        output_path = os.path.join(dir_path, f"{file_name}_译文.txt")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(self.right_text.get(1.0, tk.END))
            # messagebox.showinfo("成功", f"译文已保存到: {output_path}")
            print(f"译文已保存到: {output_path}")
        except Exception as e:
            # messagebox.showerror("错误", f"保存译文时出错: {str(e)}")
            print(f"保存译文时出错: {str(e)}")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = ASSSubtitleProcessor()
    app.run()