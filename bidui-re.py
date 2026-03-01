import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
import os

class ASSFileProcessor:
    """处理ASS文件的核心逻辑"""
    
    @staticmethod
    def extract_subtitle_text(line):
        """从ASS文件的Dialogue行中提取文本"""
        pattern = r'^Dialogue:\s*(\d+),([^,]+),([^,]+),([^,]+),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),(.*)$'
        match = re.match(pattern, line)
        
        if match:
            text = match.group(10)
            text = re.sub(r'{[^}]*}', '', text)
            return match.group(4).strip(), text.strip(), match.group(2).strip(), match.group(3).strip()
        
        return None, "", "", ""
    
    @staticmethod
    def separate_chinese_english(text):
        """分离中英文字幕"""
        if '\\N' in text:
            parts = text.split('\\N', 1)
            if len(parts) == 2:
                part1, part2 = parts[0].strip(), parts[1].strip()
                
                has_chinese1 = any('\u4e00' <= char <= '\u9fff' for char in part1)
                has_chinese2 = any('\u4e00' <= char <= '\u9fff' for char in part2)
                
                if has_chinese1 and not has_chinese2:
                    return part2, part1
                elif has_chinese2 and not has_chinese1:
                    return part1, part2
                else:
                    return part2, part1
        return "", text
    
    def process_ass_file(self, file_path):
        """处理ASS文件并返回提取的字幕"""
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError("请选择有效的ASS文件")
        
        # 尝试不同编码
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
            raise UnicodeDecodeError("无法使用常见编码读取文件")
        
        return self._extract_subtitles_from_lines(lines)
    
    def _extract_subtitles_from_lines(self, lines):
        """从文件行中提取字幕"""
        original_texts = []
        translated_texts = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('Dialogue:'):
                style, text, start_time, end_time = self.extract_subtitle_text(line)
                if text and style in ["译文字幕", "英文字幕"]:
                    if style == "译文字幕":
                        english_part, chinese_part = self.separate_chinese_english(text)
                        if english_part:
                            original_texts.append(english_part)
                        if chinese_part:
                            translated_texts.append(chinese_part)
                    elif style == "英文字幕":
                        original_texts.append(text)
        
        return original_texts, translated_texts


class SubtitleDisplay:
    """管理字幕显示和界面交互"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("ASS字幕文件原文译文并排显示工具")
        self.root.geometry("1920x1080")
        
        # 初始化状态
        self.show_original = True
        self.show_translation = True
        self.show_combined = False
        self.original_texts = []
        self.translated_texts = []
        
        # 字体设置
        self.font_size = 10
        self.font_name = "TkDefaultFont"
        
        # 滚动位置
        self.left_scroll_position = 0.0
        self.combined_scroll_position = 0.0
        
        # 搜索相关
        self.search_term = ""
        self.search_results = []
        self.current_search_index = -1
        self.last_search_type = None
        
        # 文件处理器
        self.file_processor = ASSFileProcessor()
        
        # 构建界面
        self.setup_ui()
        self.setup_shortcuts()
    
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding="5")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.file_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path_var, width=80).grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(file_frame, text="选择ASS文件", command=self.select_file).grid(row=0, column=1)
        
        file_frame.columnconfigure(0, weight=1)

        # 搜索框区域
        self.search_frame = ttk.Frame(main_frame)
        
        ttk.Label(self.search_frame, text="搜索:").grid(row=0, column=0, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var, width=40)
        self.search_entry.grid(row=0, column=1, padx=(0, 5))
        
        ttk.Button(self.search_frame, text="查找下一个", command=self.search_next).grid(
            row=0, column=2, padx=(0, 5))
        ttk.Button(self.search_frame, text="查找上一个", command=self.search_previous).grid(
            row=0, column=3, padx=(0, 5))
        ttk.Button(self.search_frame, text="关闭", command=self.hide_search).grid(row=0, column=4)
        
        # 显示区域
        display_frame = ttk.Frame(main_frame)
        display_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 左侧原文框
        self.left_frame = ttk.LabelFrame(display_frame, text="原文（英文字幕）", padding="5")
        self.left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        self.left_scrollbar = ttk.Scrollbar(self.left_frame)
        self.left_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.left_text = tk.Text(self.left_frame, yscrollcommand=self.on_left_scroll, 
                                wrap=tk.WORD, width=60, font=(self.font_name, self.font_size))
        self.left_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.left_scrollbar.config(command=self.on_scroll_command)
        
        # 右侧译文框
        self.right_frame = ttk.LabelFrame(display_frame, text="译文（中文字幕）", padding="5")
        self.right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.right_scrollbar = ttk.Scrollbar(self.right_frame)
        self.right_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.right_text = tk.Text(self.right_frame, yscrollcommand=self.on_right_scroll, 
                                 wrap=tk.WORD, width=60, font=(self.font_name, self.font_size))
        self.right_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.right_scrollbar.config(command=self.on_scroll_command)

        # 为文本框绑定焦点事件
        self.left_text.bind('<FocusIn>', lambda e: setattr(self, 'last_focused_text', self.left_text))
        self.right_text.bind('<FocusIn>', lambda e: setattr(self, 'last_focused_text', self.right_text))
        
        # 组合显示框
        self.combined_frame = ttk.LabelFrame(display_frame, text="原文译文结合", padding="5")
        
        self.combined_scrollbar = ttk.Scrollbar(self.combined_frame)
        self.combined_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.combined_text = tk.Text(self.combined_frame, yscrollcommand=self.combined_scrollbar.set, 
                                   wrap=tk.WORD, width=120, font=(self.font_name, self.font_size))
        self.combined_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.combined_scrollbar.config(command=self.combined_text.yview)
        
        # 按钮区域
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
        main_frame.rowconfigure(2, weight=1)
        display_frame.columnconfigure(0, weight=1)
        display_frame.columnconfigure(1, weight=1)
        display_frame.rowconfigure(0, weight=1)
        self.left_frame.columnconfigure(0, weight=1)
        self.left_frame.rowconfigure(0, weight=1)
        self.right_frame.columnconfigure(0, weight=1)
        self.right_frame.rowconfigure(0, weight=1)
        self.combined_frame.columnconfigure(0, weight=1)
        self.combined_frame.rowconfigure(0, weight=1)
    
    def setup_shortcuts(self):
        """设置快捷键"""
        # 不需要事件参数的方法
        shortcuts_no_event = {
            '<Control-o>': self.process_file,
            '<Control-O>': self.process_file,
            '<Control-Shift-s>': self.save_originals,
            '<Control-Shift-S>': self.save_originals,
            '<Control-Shift-t>': self.save_translations,
            '<Control-Shift-T>': self.save_translations,
            '<Control-Shift-c>': self.toggle_combined,
            '<Control-Shift-C>': self.toggle_combined,
            '<Control-Shift-x>': self.toggle_original,
            '<Control-Shift-X>': self.toggle_original,
            '<Control-Shift-z>': self.toggle_translation,
            '<Control-Shift-Z>': self.toggle_translation,
            '<Control-f>': self.show_search,
            '<Control-F>': self.show_search,
            '<F5>': self.process_file,
            '<F1>': self.show_shortcut_help,
            '<Return>': self.search_next
        }
        
        # 需要事件参数的方法
        shortcuts_with_event = {
            '<Control-MouseWheel>': self.change_font_size
        }
        
        for key, command in shortcuts_no_event.items():
            self.root.bind(key, lambda e, cmd=command: cmd())
        
        for key, command in shortcuts_with_event.items():
            self.root.bind(key, lambda e, cmd=command: cmd(e))
        
        self.root.focus_set()
    
    def on_left_scroll(self, *args):
        """左边文本框滚动时的回调"""
        self.left_scrollbar.set(*args)
        self.right_text.yview_moveto(args[0])
    
    def on_right_scroll(self, *args):
        """右边文本框滚动时的回调"""
        self.right_scrollbar.set(*args)
        self.left_text.yview_moveto(args[0])
    
    def on_scroll_command(self, *args):
        """滚动条拖动时的回调"""
        self.left_text.yview(*args)
        self.right_text.yview(*args)
    
    def select_file(self):
        """选择文件"""
        file_path = filedialog.askopenfilename(
            title="选择ASS字幕文件",
            filetypes=[("ASS文件", "*.ass"), ("所有文件", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)
    
    def process_file(self):
        """处理文件"""
        file_path = self.file_path_var.get()
        try:
            self.original_texts, self.translated_texts = self.file_processor.process_ass_file(file_path)
            self.display_subtitles()
        except Exception as e:
            messagebox.showerror("错误", str(e))
    
    def display_subtitles(self):
        """显示提取的字幕"""
        # 清空文本框
        self.left_text.delete(1.0, tk.END)
        self.right_text.delete(1.0, tk.END)
        self.combined_text.delete(1.0, tk.END)
        
        # 显示原文
        if self.original_texts:
            for text in self.original_texts:
                self.left_text.insert(tk.END, f"{text}\n\n")
        else:
            self.left_text.insert(tk.END, "未找到英文字幕\n")
        
        # 显示译文
        if self.translated_texts:
            for text in self.translated_texts:
                self.right_text.insert(tk.END, f"{text}\n\n")
        else:
            self.right_text.insert(tk.END, "未找到中文字幕\n")
        
        # 更新组合显示
        if self.show_combined:
            self.update_combined_display()
    
    def save_originals(self):
        """保存原文"""
        self.save_text_content(self.left_text, "原文", "_原文.txt")
    
    def save_translations(self):
        """保存译文"""
        self.save_text_content(self.right_text, "译文", "_译文.txt")
    
    def save_text_content(self, text_widget, content_type, file_suffix):
        """保存文本内容到文件"""
        content = text_widget.get(1.0, tk.END).strip()
        default_message = f"未找到{content_type.lower()}字幕\n"
        
        if not content or content == default_message:
            messagebox.showwarning("警告", f"没有可保存的{content_type}")
            return
        
        ass_path = self.file_path_var.get()
        if not ass_path:
            messagebox.showerror("错误", "请先选择ASS文件")
            return
        
        dir_path = os.path.dirname(ass_path)
        file_name = os.path.splitext(os.path.basename(ass_path))[0]
        output_path = os.path.join(dir_path, f"{file_name}{file_suffix}")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(text_widget.get(1.0, tk.END))
            print(f"{content_type}已保存到: {output_path}")
        except Exception as e:
            print(f"保存{content_type}时出错: {str(e)}")
    
    def toggle_combined(self):
        """切换组合显示"""
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
        self.combined_text.delete(1.0, tk.END)
        max_lines = max(len(self.original_texts), len(self.translated_texts))
        
        for i in range(max_lines):
            if self.show_original and i < len(self.original_texts):
                self.combined_text.insert(tk.END, f"{self.original_texts[i]}\n")
            if self.show_translation and i < len(self.translated_texts):
                self.combined_text.insert(tk.END, f"{self.translated_texts[i]}\n")
            if (self.show_original and i < len(self.original_texts)) or (self.show_translation and i < len(self.translated_texts)):
                self.combined_text.insert(tk.END, "\n")
        
        self.combined_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def toggle_original(self):
        """切换原文显示"""
        if self.show_combined:
            current_scroll = self.combined_text.yview()[0]
            self.show_original = not self.show_original
            self.update_combined_display()
            self.combined_text.yview_moveto(current_scroll)
        else:
            current_scroll = self.left_text.yview()[0]
            if self.show_original:
                self.left_frame.grid_remove()
                self.show_original = False
            else:
                self.left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
                self.show_original = True
            self.left_text.yview_moveto(current_scroll)
            self.right_text.yview_moveto(current_scroll)
    
    def toggle_translation(self):
        """切换译文显示"""
        if self.show_combined:
            current_scroll = self.combined_text.yview()[0]
            self.show_translation = not self.show_translation
            self.update_combined_display()
            self.combined_text.yview_moveto(current_scroll)
        else:
            current_scroll = self.left_text.yview()[0]
            if self.show_translation:
                self.right_frame.grid_remove()
                self.show_translation = False
            else:
                self.right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
                self.show_translation = True
            self.left_text.yview_moveto(current_scroll)
            self.right_text.yview_moveto(current_scroll)
    
    def show_search(self):
        """显示搜索框"""
        self.search_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.search_entry.focus_set()
        self.populate_search_with_selection()
    
    def populate_search_with_selection(self):
        """用选中的文本填充搜索框"""
        selected_text = ""
        
        if self.show_combined:
            try:
                selected_text = self.combined_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            except tk.TclError:
                pass
        else:
            try:
                selected_text = self.left_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            except tk.TclError:
                try:
                    selected_text = self.right_text.get(tk.SEL_FIRST, tk.SEL_LAST)
                except tk.TclError:
                    pass
        
        if selected_text:
            self.search_var.set(selected_text)
    
    def get_search_target(self):
        """确定搜索目标文本框"""
        if self.show_combined:
            return self.combined_text, "combined"
        
        if hasattr(self, 'last_focused_text'):
            if self.last_focused_text == self.left_text:
                return self.left_text, "original"
            elif self.last_focused_text == self.right_text:
                return self.right_text, "translation"
        
        focused_widget = self.root.focus_get()
        if focused_widget == self.left_text:
            return self.left_text, "original"
        elif focused_widget == self.right_text:
            return self.right_text, "translation"
        
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

        return self.right_text, "translation"
    
    def hide_search(self):
        """隐藏搜索框"""
        self.search_frame.grid_remove()
        self.clear_highlight()
        self.root.focus_set()
    
    def clear_highlight(self):
        """清除高亮"""
        for widget in [self.left_text, self.right_text, self.combined_text]:
            widget.tag_remove("highlight", "1.0", tk.END)
    
    def highlight_pattern(self, text_widget, pattern):
        """高亮匹配的文本"""
        text_widget.tag_configure("highlight", background="yellow")
        text_widget.tag_remove("highlight", "1.0", tk.END)
        
        if not pattern:
            return []
        
        matches = []
        start = "1.0"
        
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
        """查找下一个"""
        self.perform_search(forward=True)
    
    def search_previous(self):
        """查找上一个"""
        self.perform_search(forward=False)
    
    def perform_search(self, forward=True):
        """执行搜索"""
        search_term = self.search_var.get().strip()
        if not search_term:
            return
        
        target_widget, search_type = self.get_search_target()
        
        if (search_term != self.search_term or 
            search_type != getattr(self, 'last_search_type', None)):
            self.search_term = search_term
            self.last_search_type = search_type
            self.search_results = self.highlight_pattern(target_widget, search_term)
            self.current_search_index = -1
        
        if not self.search_results:
            messagebox.showinfo("搜索", "未找到匹配项")
            return
        
        if forward:
            self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
        else:
            self.current_search_index = (self.current_search_index - 1) % len(self.search_results)
        
        self.jump_to_search_result()
    
    def jump_to_search_result(self):
        """跳转到搜索结果"""
        if not self.search_results or self.current_search_index < 0:
            return
        
        target_widget, search_type = self.get_search_target()
        pos, end = self.search_results[self.current_search_index]
        
        target_widget.see(pos)
        target_widget.focus_set()
        target_widget.tag_remove(tk.SEL, "1.0", tk.END)
        target_widget.tag_add(tk.SEL, pos, end)
        
        self.sync_scroll_for_search(search_type, pos)
    
    def sync_scroll_for_search(self, search_type, pos):
        """为搜索同步滚动"""
        if not self.show_combined:
            try:
                line_num = int(pos.split('.')[0])
                if search_type == "original":
                    self.right_text.yview_moveto((line_num - 1) / float(self.left_text.index(tk.END).split('.')[0]))
                elif search_type == "translation":
                    self.left_text.yview_moveto((line_num - 1) / float(self.right_text.index(tk.END).split('.')[0]))
            except:
                pass
    
    def change_font_size(self, event):
        """改变字体大小"""
        if event.delta > 0 or event.num == 4:
            self.font_size = min(self.font_size + 1, 30)
        elif event.delta < 0 or event.num == 5:
            self.font_size = max(self.font_size - 1, 6)
        
        for widget in [self.left_text, self.right_text, self.combined_text]:
            widget.config(font=(self.font_name, self.font_size))
    
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
    
    def run(self):
        """运行应用程序"""
        self.root.mainloop()


if __name__ == "__main__":
    app = SubtitleDisplay(tk.Tk())
    app.run()