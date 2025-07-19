import zipfile
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import edge_tts
import asyncio
import os
import re

class EpubToTTS:
    def __init__(self, epub_path, output_dir):
        self.epub_path = epub_path
        self.output_dir = output_dir
        self.voice = "zh-CN-XiaoxiaoNeural"
        self.is_paused = False
        self.is_stopped = False
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def get_toc_structure(self):
        """获取目录结构"""
        with zipfile.ZipFile(self.epub_path, 'r') as zip_ref:
            ncx_path = None
            for file in zip_ref.namelist():
                if file.endswith('toc.ncx'):
                    ncx_path = file
                    break
            
            if not ncx_path:
                return []
            
            with zip_ref.open(ncx_path) as file:
                content = file.read()
                tree = ET.ElementTree(ET.fromstring(content))
                root = tree.getroot()
                
                ns = {'': 'http://www.daisy.org/z3986/2005/ncx/'}
                nav_points = root.findall('.//navPoint', ns)
                
                chapters = []
                for i, nav_point in enumerate(nav_points, 1):
                    title_elem = nav_point.find('navLabel/text', ns)
                    content_elem = nav_point.find('content', ns)
                    
                    if title_elem is not None and content_elem is not None:
                        title = f"{i}.{title_elem.text}"
                        href = content_elem.get('src')
                        chapters.append({'title': title, 'href': href})
                
                return chapters
    
    def extract_chapter_text(self, chapter_href):
        """提取章节文本内容"""
        with zipfile.ZipFile(self.epub_path, 'r') as zip_ref:
            chapter_path = chapter_href.split('#')[0]
            
            full_path = None
            for file in zip_ref.namelist():
                if file.endswith(chapter_path):
                    full_path = file
                    break
            
            if not full_path:
                return ""
            
            with zip_ref.open(full_path) as file:
                content = file.read().decode('utf-8')
                soup = BeautifulSoup(content, 'html.parser')
                
                for script in soup(["script", "style"]):
                    script.decompose()
                
                text = soup.get_text()
                text = re.sub(r'\s+', ' ', text).strip()
                return text
    
    async def text_to_speech(self, text, output_file):
        """将文本转换为语音"""
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(output_file)
    
    async def convert_selected_chapters(self, selected_chapters, progress_callback):
        """转换选中的章节为音频文件"""
        total_chapters = len(selected_chapters)
        
        for i, chapter in enumerate(selected_chapters):
            if self.is_stopped:
                break
                
            # 等待暂停状态
            while self.is_paused and not self.is_stopped:
                await asyncio.sleep(0.1)
            
            if self.is_stopped:
                break
            
            progress_callback(i, total_chapters, chapter['title'], "处理中...")
            
            text = self.extract_chapter_text(chapter['href'])
            
            if not text:
                progress_callback(i+1, total_chapters, chapter['title'], "跳过(空)")
                continue
            
            safe_title = re.sub(r'[^\w\s.-]', '', chapter['title'])
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
            output_file = f"{self.output_dir}/{safe_title}.mp3"
            
            try:
                await self.text_to_speech(text, output_file)
                progress_callback(i+1, total_chapters, chapter['title'], "完成")
            except Exception as e:
                progress_callback(i+1, total_chapters, chapter['title'], f"失败: {str(e)}")
    
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
