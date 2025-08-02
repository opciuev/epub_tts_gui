import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import asyncio
import threading
from epub_converter import EpubToTTS
import re

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

class EpubTTSGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("EPUB转TTS工具")
        self.root.geometry("900x700")
        
        self.epub_path = ""
        self.output_path = ""
        self.converter = None
        self.is_running = False
        self.is_paused = False
        self.chapters = []
        
        self.setup_ui()
    
    def setup_ui(self):
        # 文件选择区域
        file_frame = ttk.Frame(self.root, padding="10")
        file_frame.pack(fill=tk.X)
        
        ttk.Label(file_frame, text="EPUB文件:").pack(anchor=tk.W)
        
        file_input_frame = ttk.Frame(file_frame)
        file_input_frame.pack(fill=tk.X, pady=5)
        
        self.file_var = tk.StringVar()
        self.file_entry = ttk.Entry(file_input_frame, textvariable=self.file_var, state="readonly")
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(file_input_frame, text="选择文件", command=self.select_file).pack(side=tk.RIGHT, padx=(5,0))
        
        # 拖拽提示
        if DND_AVAILABLE:
            ttk.Label(file_frame, text="提示: 可以直接拖拽EPUB文件到输入框", font=("", 8)).pack(anchor=tk.W)
        
        # 输出路径区域
        output_frame = ttk.Frame(self.root, padding="10")
        output_frame.pack(fill=tk.X)
        
        ttk.Label(output_frame, text="输出路径:").pack(anchor=tk.W)
        
        output_input_frame = ttk.Frame(output_frame)
        output_input_frame.pack(fill=tk.X, pady=5)
        
        self.output_var = tk.StringVar()
        self.output_entry = ttk.Entry(output_input_frame, textvariable=self.output_var)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(output_input_frame, text="选择路径", command=self.select_output).pack(side=tk.RIGHT, padx=(5,0))
        
        # 同目录选项和并发设置
        options_frame = ttk.Frame(output_frame)
        options_frame.pack(fill=tk.X, pady=5)
        
        self.same_dir_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="在EPUB同目录下创建同名文件夹", 
                       variable=self.same_dir_var, command=self.toggle_same_dir).pack(side=tk.LEFT)
        
        # 并发线程数选择
        concurrent_frame = ttk.Frame(options_frame)
        concurrent_frame.pack(side=tk.RIGHT)
        
        ttk.Label(concurrent_frame, text="并发线程数:").pack(side=tk.LEFT, padx=(20,5))
        self.concurrent_var = tk.StringVar(value="3")
        concurrent_combo = ttk.Combobox(concurrent_frame, textvariable=self.concurrent_var, 
                                       values=["1", "2", "3", "4", "5", "6"], width=5, state="readonly")
        concurrent_combo.pack(side=tk.LEFT)
        
        # 章节选择区域
        chapter_frame = ttk.LabelFrame(self.root, text="章节选择", padding="10")
        chapter_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 全选/取消全选按钮
        select_frame = ttk.Frame(chapter_frame)
        select_frame.pack(fill=tk.X, pady=(0,5))
        
        ttk.Button(select_frame, text="全选", command=self.select_all_chapters).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(select_frame, text="取消全选", command=self.deselect_all_chapters).pack(side=tk.LEFT)
        
        # 章节列表
        list_container = ttk.Frame(chapter_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        # 创建Treeview显示章节
        columns = ("选择", "章节", "状态")
        self.chapter_tree = ttk.Treeview(list_container, columns=columns, show="headings", height=12)
        
        self.chapter_tree.heading("选择", text="选择")
        self.chapter_tree.heading("章节", text="章节")
        self.chapter_tree.heading("状态", text="状态")
        
        self.chapter_tree.column("选择", width=60)
        self.chapter_tree.column("章节", width=500)
        self.chapter_tree.column("状态", width=100)
        
        # 滚动条
        chapter_scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.chapter_tree.yview)
        self.chapter_tree.configure(yscrollcommand=chapter_scrollbar.set)
        
        self.chapter_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        chapter_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定双击事件切换选择状态
        self.chapter_tree.bind("<Double-1>", self.toggle_chapter_selection)
        
        # 控制按钮区域
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)
        
        self.start_btn = ttk.Button(control_frame, text="开始转换", command=self.start_conversion)
        self.start_btn.pack(side=tk.LEFT, padx=(0,5))
        
        self.pause_btn = ttk.Button(control_frame, text="暂停", command=self.pause_conversion, state="disabled")
        self.pause_btn.pack(side=tk.LEFT, padx=(0,5))
        
        self.continue_btn = ttk.Button(control_frame, text="继续", command=self.continue_conversion, state="disabled")
        self.continue_btn.pack(side=tk.LEFT, padx=(0,5))
        
        self.restart_btn = ttk.Button(control_frame, text="从头开始", command=self.restart_conversion)
        self.restart_btn.pack(side=tk.LEFT, padx=(0,5))
        
        self.stop_btn = ttk.Button(control_frame, text="结束", command=self.stop_conversion, state="disabled")
        self.stop_btn.pack(side=tk.LEFT, padx=(0,5))
        
        # 新增：保存文本按钮
        self.save_text_btn = ttk.Button(control_frame, text="保存文本", command=self.save_selected_text)
        self.save_text_btn.pack(side=tk.LEFT)
        
        # 进度条
        progress_frame = ttk.Frame(self.root, padding="10")
        progress_frame.pack(fill=tk.X)
        
        ttk.Label(progress_frame, text="转换进度:").pack(anchor=tk.W)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.progress_label = ttk.Label(progress_frame, text="0/0")
        self.progress_label.pack(anchor=tk.W)
        
        # 设置拖拽支持
        if DND_AVAILABLE:
            self.file_entry.drop_target_register(DND_FILES)
            self.file_entry.dnd_bind('<<Drop>>', self.on_drop)
    
    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="选择EPUB文件",
            filetypes=[("EPUB files", "*.epub"), ("All files", "*.*")]
        )
        if file_path:
            self.load_epub_file(file_path)
    
    def load_epub_file(self, file_path):
        # 统一路径格式
        file_path = os.path.normpath(file_path)
        self.file_var.set(file_path)
        self.epub_path = file_path
        if self.same_dir_var.get():
            self.set_same_dir_output()
        
        # 加载章节列表
        self.load_chapters()
    
    def load_chapters(self):
        """加载EPUB章节列表"""
        try:
            temp_converter = EpubToTTS(self.epub_path, "temp")
            self.chapters = temp_converter.get_toc_structure()
            
            # 清空现有列表
            for item in self.chapter_tree.get_children():
                self.chapter_tree.delete(item)
            
            # 添加章节到列表
            for chapter in self.chapters:
                self.chapter_tree.insert("", "end", values=("☑", chapter['title'], "待转换"))
            
        except Exception as e:
            messagebox.showerror("错误", f"读取EPUB章节失败: {str(e)}")
    
    def select_all_chapters(self):
        """全选章节"""
        for item in self.chapter_tree.get_children():
            values = list(self.chapter_tree.item(item)["values"])
            values[0] = "☑"
            self.chapter_tree.item(item, values=values)
    
    def deselect_all_chapters(self):
        """取消全选章节"""
        for item in self.chapter_tree.get_children():
            values = list(self.chapter_tree.item(item)["values"])
            values[0] = "☐"
            self.chapter_tree.item(item, values=values)
    
    def toggle_chapter_selection(self, event):
        """切换章节选择状态"""
        item = self.chapter_tree.selection()[0]
        values = list(self.chapter_tree.item(item)["values"])
        values[0] = "☐" if values[0] == "☑" else "☑"
        self.chapter_tree.item(item, values=values)
    
    def get_selected_chapters(self):
        """获取选中的章节"""
        selected_chapters = []
        for i, item in enumerate(self.chapter_tree.get_children()):
            values = self.chapter_tree.item(item)["values"]
            if values[0] == "☑":
                selected_chapters.append(self.chapters[i])
        return selected_chapters
    
    def select_output(self):
        dir_path = filedialog.askdirectory(title="选择输出目录")
        if dir_path:
            # 统一路径格式
            dir_path = os.path.normpath(dir_path)
            self.output_var.set(dir_path)
            self.output_path = dir_path
            # 用户手动选择路径时，自动取消同目录选项
            self.same_dir_var.set(False)
            self.output_entry.config(state="normal")
    
    def toggle_same_dir(self):
        if self.same_dir_var.get():
            self.output_entry.config(state="readonly")
            if self.epub_path:
                self.set_same_dir_output()
        else:
            self.output_entry.config(state="normal")
            self.output_var.set("")  # 清空输出路径
    
    def set_same_dir_output(self):
        if self.epub_path:
            epub_dir = os.path.dirname(self.epub_path)
            epub_name = os.path.splitext(os.path.basename(self.epub_path))[0]
            output_dir = os.path.join(epub_dir, epub_name + "_audio")
            # 统一路径格式
            output_dir = os.path.normpath(output_dir)
            self.output_var.set(output_dir)
            self.output_path = output_dir
    
    def on_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        if files and files[0].endswith('.epub'):
            self.load_epub_file(files[0])
    
    def start_conversion(self):
        print("=== 开始转换流程 ===")
        if not self.epub_path:
            print("错误: 未选择EPUB文件")
            messagebox.showerror("错误", "请选择EPUB文件")
            return
        
        output_path = self.output_var.get().strip()
        print(f"EPUB路径: {self.epub_path}")
        print(f"输出路径: {output_path}")
        
        if not output_path:
            print("错误: 未设置输出路径")
            messagebox.showerror("错误", "请设置输出路径")
            return
        
        selected_chapters = self.get_selected_chapters()
        print(f"选中章节数: {len(selected_chapters)}")
        
        if not selected_chapters:
            print("错误: 未选择章节")
            messagebox.showerror("错误", "请至少选择一个章节")
            return
        
        print("设置运行状态...")
        self.is_running = True
        self.is_paused = False
        self.update_button_states()
        
        print("启动转换线程...")
        thread = threading.Thread(target=self.run_conversion, args=(selected_chapters, output_path))
        thread.daemon = True
        thread.start()
        print("转换线程已启动")

    def run_conversion(self, selected_chapters, output_path):
        print(f"=== 转换线程开始 ===")
        print(f"章节数: {len(selected_chapters)}")
        print(f"输出目录: {output_path}")
        
        try:
            max_concurrent = int(self.concurrent_var.get())
            print(f"并发数: {max_concurrent}")
            
            print("创建转换器...")
            self.converter = EpubToTTS(self.epub_path, output_path)
            print("转换器创建成功")
            
            print("开始异步转换...")
            asyncio.run(self.converter.convert_selected_chapters(selected_chapters, self.update_progress, max_concurrent))
            print("转换完成")
            
        except Exception as e:
            print(f"转换异常: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("错误", f"转换失败: {str(e)}")
        finally:
            print("转换线程结束")
            self.is_running = False
            self.root.after(0, self.update_button_states)

    def update_progress(self, current, total, chapter_title, status):
        print(f"进度更新: {current}/{total} - {chapter_title} - {status}")
        def update_ui():
            progress = (current / total) * 100 if total > 0 else 0
            self.progress_var.set(progress)
            self.progress_label.config(text=f"{current}/{total}")
            
            for item in self.chapter_tree.get_children():
                values = list(self.chapter_tree.item(item)["values"])
                if values[1] == chapter_title:
                    values[2] = status
                    self.chapter_tree.item(item, values=values)
                    break
        
        self.root.after(0, update_ui)
    
    def pause_conversion(self):
        self.is_paused = True
        if self.converter:
            self.converter.pause()
        self.update_button_states()
    
    def continue_conversion(self):
        self.is_paused = False
        if self.converter:
            self.converter.resume()
        self.update_button_states()
    
    def restart_conversion(self):
        self.stop_conversion()
        # 重置章节状态
        for item in self.chapter_tree.get_children():
            values = list(self.chapter_tree.item(item)["values"])
            if values[0] == "☑":
                values[2] = "待转换"
                self.chapter_tree.item(item, values=values)
        self.progress_var.set(0)
        self.progress_label.config(text="0/0")
        self.start_conversion()
    
    def stop_conversion(self):
        self.is_running = False
        self.is_paused = False
        if self.converter:
            self.converter.stop()
        self.update_button_states()
    
    def update_button_states(self):
        if self.is_running:
            if self.is_paused:
                self.start_btn.config(state="disabled")
                self.pause_btn.config(state="disabled")
                self.continue_btn.config(state="normal")
                self.stop_btn.config(state="normal")
            else:
                self.start_btn.config(state="disabled")
                self.pause_btn.config(state="normal")
                self.continue_btn.config(state="disabled")
                self.stop_btn.config(state="normal")
        else:
            self.start_btn.config(state="normal")
            self.pause_btn.config(state="disabled")
            self.continue_btn.config(state="disabled")
            self.stop_btn.config(state="disabled")

    def save_selected_text(self):
        """保存选中章节的文本到文件"""
        if not self.epub_path:
            messagebox.showerror("错误", "请先选择EPUB文件")
            return
        
        selected_chapters = self.get_selected_chapters()
        if not selected_chapters:
            messagebox.showerror("错误", "请至少选择一个章节")
            return
        
        # 如果正在转换，警告用户
        if self.is_running:
            result = messagebox.askyesno("警告", 
                "当前正在进行转换，保存文本可能会影响转换进程。\n是否继续？")
            if not result:
                return
        
        # 根据选中章节数量自动生成文件名
        epub_name = os.path.splitext(os.path.basename(self.epub_path))[0]
        if len(selected_chapters) == 1:
            chapter_name = re.sub(r'[^\w\s.-]', '', selected_chapters[0]['title'])
            default_name = f"{epub_name}_{chapter_name}.txt"
        else:
            default_name = f"{epub_name}_选中{len(selected_chapters)}章节.txt"
        
        save_path = filedialog.asksaveasfilename(
            title="保存文本文件",
            initialfile=default_name,
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if not save_path:
            return
        
        try:
            # 在单独线程中执行，避免阻塞UI和影响转换
            def save_text_thread():
                try:
                    temp_converter = EpubToTTS(self.epub_path, "temp")
                    
                    with open(save_path, 'w', encoding='utf-8') as f:
                        for i, chapter in enumerate(selected_chapters):
                            f.write(f"=== 章节 {i+1}: {chapter['title']} ===\n\n")
                            
                            text = temp_converter.extract_chapter_text(chapter['href'])
                            f.write(f"原始文本长度: {len(text)} 字符\n\n")
                            f.write(text)
                            f.write("\n\n" + "="*50 + "\n\n")
                    
                    # 在主线程中显示成功消息
                    self.root.after(0, lambda: messagebox.showinfo("成功", f"文本已保存到: {save_path}"))
                    
                except Exception as e:
                    # 在主线程中显示错误消息
                    self.root.after(0, lambda: messagebox.showerror("错误", f"保存文本失败: {str(e)}"))
            
            # 启动保存线程
            save_thread = threading.Thread(target=save_text_thread)
            save_thread.daemon = True
            save_thread.start()
            
        except Exception as e:
            messagebox.showerror("错误", f"保存文本失败: {str(e)}")

if __name__ == "__main__":
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = EpubTTSGUI(root)
    root.mainloop()















