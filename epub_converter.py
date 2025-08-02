import zipfile
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import edge_tts
import asyncio
import os
import re
from pydub import AudioSegment
import queue
import threading

class EpubToTTS:
    def __init__(self, epub_path, output_dir):
        self.epub_path = epub_path
        self.output_dir = output_dir
        self.voice = "zh-CN-XiaoxiaoNeural"
        self.is_paused = False
        self.is_stopped = False
        self.chunk_size = 2000  # 每段文本字符数
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def split_text(self, text, chunk_size=2000):
        """将长文本分割成小段"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        sentences = re.split(r'[。！？\n]', text)
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk + sentence) <= chunk_size:
                current_chunk += sentence + "。"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + "。"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks

    async def text_to_speech_chunk(self, text, output_file, max_retries=3):
        """将单个文本段转换为语音，支持重试"""
        for attempt in range(max_retries):
            try:
                communicate = edge_tts.Communicate(text, self.voice)
                await asyncio.wait_for(communicate.save(output_file), timeout=60.0)
                return True
            except Exception as e:
                print(f"TTS段转换失败 (尝试 {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # 等待2秒后重试
                else:
                    print(f"TTS段最终失败: {str(e)}")
                    return False

    async def text_to_speech(self, text, output_file):
        """生产者-消费者模式的TTS转换"""
        print(f"TTS开始: 文本长度={len(text)}, 输出文件={output_file}")
        
        chunks = self.split_text(text, self.chunk_size)
        print(f"文本分割为 {len(chunks)} 段")
        
        if len(chunks) == 1:
            try:
                communicate = edge_tts.Communicate(text, self.voice)
                await asyncio.wait_for(communicate.save(output_file), timeout=120.0)
                print(f"TTS保存完成: {output_file}")
                return
            except Exception as e:
                print(f"TTS转换失败: {str(e)}")
                raise
        
        # 生产者-消费者模式
        task_queue = asyncio.Queue()
        result_dict = {}
        
        # 生产者：将任务放入队列
        for i, chunk in enumerate(chunks):
            await task_queue.put((i, chunk))
        
        # 添加结束标记
        for _ in range(6):  # 6个消费者
            await task_queue.put(None)
        
        # 消费者：处理TTS转换
        async def consumer():
            while True:
                item = await task_queue.get()
                if item is None:
                    break
                
                index, chunk = item
                temp_file = f"{output_file}.temp_{index}.mp3"
                print(f"转换段 {index+1}/{len(chunks)}")
                
                success = await self.text_to_speech_chunk(chunk, temp_file)
                if success:
                    result_dict[index] = temp_file
                
                task_queue.task_done()
        
        # 启动多个消费者
        consumers = [asyncio.create_task(consumer()) for _ in range(6)]
        
        # 等待所有任务完成
        await asyncio.gather(*consumers)
        
        # 按顺序合并音频
        temp_files = [(i, result_dict[i]) for i in sorted(result_dict.keys())]
        success_count = len(temp_files)
        failed_count = len(chunks) - success_count
        
        if failed_count > 0:
            print(f"有 {failed_count} 段转换失败，成功 {success_count} 段")
            if success_count == 0:
                raise Exception("所有段都转换失败")
        
        # 合并音频文件
        try:
            await asyncio.sleep(1)
            self.simple_merge_audio(temp_files, output_file)
            print(f"音频合并完成: {output_file}")
        except Exception as e:
            print(f"音频合并失败: {str(e)}")
            raise
        finally:
            # 清理临时文件
            await asyncio.sleep(2)
            for _, temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception as e:
                    print(f"清理临时文件失败: {temp_file}, {str(e)}")

    def simple_merge_audio(self, temp_files, output_file):
        """简单的音频合并方法，不依赖ffmpeg"""
        try:
            # 按索引排序
            temp_files.sort(key=lambda x: x[0])
            
            # 读取所有音频数据并合并
            with open(output_file, 'wb') as outfile:
                for index, temp_file in temp_files:
                    if os.path.exists(temp_file):
                        with open(temp_file, 'rb') as infile:
                            outfile.write(infile.read())
            
            print(f"简单音频合并完成: {output_file}")
        except Exception as e:
            print(f"简单音频合并失败: {str(e)}")
            raise

    def merge_audio_files(self, temp_files, output_file):
        """使用pydub合并音频文件（需要ffmpeg）"""
        try:
            temp_files.sort(key=lambda x: x[0])
            
            combined = AudioSegment.empty()
            for index, temp_file in temp_files:
                if os.path.exists(temp_file):
                    audio = AudioSegment.from_mp3(temp_file)
                    combined += audio
                    combined += AudioSegment.silent(duration=300)
            
            combined.export(output_file, format="mp3")
        except Exception as e:
            print(f"pydub合并失败: {str(e)}")
            raise

    def get_toc_structure(self):
        """获取目录结构"""
        with zipfile.ZipFile(self.epub_path, 'r') as zip_ref:
            print("=== EPUB文件列表 ===")
            for file in zip_ref.namelist():
                print(f"文件: {file}")
            
            ncx_path = None
            for file in zip_ref.namelist():
                if file.endswith('toc.ncx'):
                    ncx_path = file
                    break
            
            print(f"找到目录文件: {ncx_path}")
            
            if not ncx_path:
                return []
            
            with zip_ref.open(ncx_path) as file:
                content = file.read()
                tree = ET.ElementTree(ET.fromstring(content))
                root = tree.getroot()
                
                ns = {'': 'http://www.daisy.org/z3986/2005/ncx/'}
                nav_points = root.findall('.//navPoint', ns)
                
                print(f"=== 目录结构 ===")
                chapters = []
                for i, nav_point in enumerate(nav_points, 1):
                    title_elem = nav_point.find('navLabel/text', ns)
                    content_elem = nav_point.find('content', ns)
                    
                    if title_elem is not None and content_elem is not None:
                        title = f"{i}.{title_elem.text}"
                        href = content_elem.get('src')
                        chapters.append({'title': title, 'href': href})
                        print(f"章节 {i}: 标题='{title}', 链接='{href}'")
                
                return chapters

    def extract_chapter_text_by_position(self, chapter_href, next_chapter_href=None):
        """根据位置提取章节文本"""
        print(f"按位置提取章节: {chapter_href}")
        
        try:
            with zipfile.ZipFile(self.epub_path, 'r') as zip_ref:
                chapter_path = chapter_href.split('#')[0]
                print(f"章节文件路径: {chapter_path}")
                
                with zip_ref.open(chapter_path) as file:
                    content = file.read().decode('utf-8')
                    print(f"文件内容长度: {len(content)} 字符")
                
                # 如果有下一章节，尝试在同一文件中分割
                if next_chapter_href and next_chapter_href.startswith(chapter_path):
                    current_pos = chapter_href.split('#filepos')[1] if '#filepos' in chapter_href else '0'
                    next_pos = next_chapter_href.split('#filepos')[1] if '#filepos' in next_chapter_href else str(len(content))
                    
                    print(f"当前位置: {current_pos}, 下一位置: {next_pos}")
                    
                    try:
                        start_pos = int(current_pos)
                        end_pos = int(next_pos)
                        
                        print(f"提取范围: {start_pos} - {end_pos}")
                        # 提取指定范围的内容
                        chapter_content = content[start_pos:end_pos]
                        print(f"章节内容长度: {len(chapter_content)} 字符")
                        soup = BeautifulSoup(chapter_content, 'html.parser')
                    except Exception as e:
                        print(f"位置解析失败: {e}, 使用整个文件")
                        soup = BeautifulSoup(content, 'html.parser')
                else:
                    print("使用整个文件内容")
                    soup = BeautifulSoup(content, 'html.parser')
                
                # 移除脚本和样式
                for script in soup(["script", "style"]):
                    script.decompose()
                
                text = soup.get_text()
                text = re.sub(r'\s+', ' ', text).strip()
                
                print(f"最终提取文本长度: {len(text)} 字符")
                if len(text) > 0:
                    preview = text[:200] + "..." if len(text) > 200 else text
                    print(f"文本预览: {preview}")
                else:
                    print("警告: 提取的文本为空!")
                
                return text
                
        except Exception as e:
            print(f"提取章节文本时发生异常: {e}")
            import traceback
            traceback.print_exc()
            return ""

    async def convert_selected_chapters(self, selected_chapters, progress_callback, max_concurrent=3):
        print(f"=== 开始转换章节 ===")
        print(f"总章节数: {len(selected_chapters)}")
        
        total_chapters = len(selected_chapters)
        completed = 0
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def convert_single_chapter(chapter, index):
            nonlocal completed
            print(f"开始处理章节 {index+1}: {chapter['title']}")
            
            async with semaphore:
                if self.is_stopped:
                    print(f"章节 {index+1} 被停止")
                    return
                
                while self.is_paused and not self.is_stopped:
                    await asyncio.sleep(0.1)
                
                if self.is_stopped:
                    print(f"章节 {index+1} 被停止")
                    return
                
                progress_callback(completed, total_chapters, chapter['title'], "处理中...")
                
                print(f"提取章节文本: {chapter['title']}")
                # 获取下一章节信息用于更好的文本分割
                next_chapter = selected_chapters[index + 1] if index + 1 < len(selected_chapters) else None
                next_href = next_chapter['href'] if next_chapter else None
                
                # 使用改进的文本提取方法
                text = self.extract_chapter_text_by_position(chapter['href'], next_href)
                print(f"文本提取完成，长度: {len(text)}")
                
                if not text:
                    completed += 1
                    print(f"章节 {index+1} 内容为空，跳过")
                    progress_callback(completed, total_chapters, chapter['title'], "跳过(空)")
                    return
                
                safe_title = re.sub(r'[^\w\s.-]', '', chapter['title'])
                safe_title = re.sub(r'[-\s]+', '-', safe_title)
                output_file = os.path.join(self.output_dir, f"{safe_title}.mp3")
                print(f"输出文件: {output_file}")
                
                try:
                    print(f"开始TTS转换: {chapter['title']}")
                    await self.text_to_speech(text, output_file)
                    completed += 1
                    print(f"章节 {index+1} 转换完成")
                    progress_callback(completed, total_chapters, chapter['title'], "完成")
                except Exception as e:
                    completed += 1
                    print(f"章节 {index+1} 转换失败: {str(e)}")
                    progress_callback(completed, total_chapters, chapter['title'], f"失败: {str(e)}")
        
        print("创建并发任务...")
        tasks = [convert_single_chapter(chapter, i) for i, chapter in enumerate(selected_chapters)]
        print(f"任务数量: {len(tasks)}")
        
        await asyncio.gather(*tasks, return_exceptions=True)
        print("=== 所有章节处理完成 ===")
    
    async def convert_with_callback(self, progress_callback):
        """转换整个EPUB为音频文件，带进度回调"""
        chapters = self.get_toc_structure()
        await self.convert_selected_chapters(chapters, progress_callback)
    
    def pause(self):
        self.is_paused = True
    
    def resume(self):
        self.is_paused = False
    
    def stop(self):
        self.is_stopped = True
        self.is_paused = False












