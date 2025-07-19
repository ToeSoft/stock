import os
import platform
import shutil
from datetime import datetime
from functools import partial
import json

# from easyocr import easyocr
from kivy.config import Config
from pybroker import YFinance

from compute_utils import compute_us_indicators
from utils import startGetData, getData

# 注册字体文件
font_path = os.path.join("font", 'SourceHanSansCN-Normal.otf')

# 设置全局默认字体 必须在 导入其他 kivy 模块之前调用
Config.set('kivy', 'default_font', str(['SourceHanSansCN', font_path]))

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.uix.togglebutton import ToggleButton

# 文件路径用于保存列表数据
DATA_FILE = os.path.join('stock_list.json')


class MyApp(App):
    def build(self):
        self.title = '股票数据爬取'
        self.root = BoxLayout(orientation='horizontal')

        # 左侧布局（添加爬取按钮和输入框）
        left_layout = BoxLayout(orientation='vertical', size_hint=(0.55, 1), padding=[10, 10], spacing=10)

        # **新增布局 - 输入框和提示** #
        # 爬取线程布局
        thread_crawl_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, spacing=10)
        self.crawl_input = TextInput(
            hint_text='设置爬取线程数',
            size_hint_y=None,
            height=60,
            size_hint_x=0.7,  # 输入框占用 70% 宽度
            multiline=False,
            text=f'{int(os.cpu_count() / 2)}',
            input_filter='int',
        )
        crawl_label = Label(
            text="爬取线程",
            size_hint_x=0.3,  # 标签占用 30% 宽度
            size_hint_y=None,
            height=60
        )
        thread_crawl_layout.add_widget(self.crawl_input)
        thread_crawl_layout.add_widget(crawl_label)

        # # 识别线程布局
        # thread_recog_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, spacing=10)
        # self.recog_input = TextInput(
        #     hint_text='设置识别线程数',
        #     size_hint_y=None,
        #     height=60,
        #     size_hint_x=0.7,
        #     multiline=False,
        #     text=f'{os.cpu_count()}',
        #     input_filter='int',
        #
        # )
        # recog_label = Label(
        #     text="识别线程",
        #     size_hint_x=0.3,
        #     size_hint_y=None,
        #     height=60
        # )
        # thread_recog_layout.add_widget(self.recog_input)
        # thread_recog_layout.add_widget(recog_label)

        # **添加到左侧布局上** #
        left_layout.add_widget(thread_crawl_layout)
        # left_layout.add_widget(thread_recog_layout)

        # 添加爬取按钮
        self.scrape_button = Button(text='开始爬取', size_hint_y=None, height=60)
        self.scrape_button.bind(on_press=self.start_scraping)  # 绑定点击事件

        # 添加爬取按钮
        self.merge_button = Button(text='合并结果', size_hint_y=None, height=60)
        self.merge_button.bind(on_press=self.start_merge)  # 绑定点击事件

        # 添加打开结果文件夹按钮
        self.open_button = Button(text='打开结果文件夹', size_hint_y=None, height=60)
        self.open_button.bind(on_press=self.open_folder)

        # 设置输入框的 size_hint_x 为 0.9（占用 90% 宽度）
        self.input_field = TextInput(
            hint_text='输入股票代码, 例如 sz300750 是宁德时代的代码',
            size_hint_y=None,
            height=60,
            size_hint_x=0.9,  # 输入框占用容器的 90% 宽度
            multiline=False,  # 禁止多行输入
            on_text_validate=self.add_text  # 回车触发 add_text 方法
        )

        # 创建单选框布局
        self.radio_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, spacing=10)

        # 输出格式选择 - 输出 txt
        self.txt_radio = ToggleButton(group='output', state='down')  # 设置为选中状态
        txt_label = Label(text="输出 TXT", size_hint_y=None, height=60)
        self.radio_layout.add_widget(self.txt_radio)
        self.radio_layout.add_widget(txt_label)

        # 输出格式选择 - 输出 Excel
        self.excel_radio = ToggleButton(group='output', state='normal')  # 默认为未选中
        excel_label = Label(text="输出 Excel", size_hint_y=None, height=60)
        self.radio_layout.add_widget(self.excel_radio)
        self.radio_layout.add_widget(excel_label)

        # 将输入框和添加按钮放入水平布局
        input_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, spacing=10)
        add_button = Button(text='添加', size_hint_y=None, height=60, size_hint_x=0.1)  # 按钮占用 10% 宽度
        add_button.bind(on_press=self.add_text)
        use_tips = Label(
            text="使用说明:\n请在输入框中输入股票代码,然后点击添加按钮,添加好所需要的股票之后点击开始爬取,耐心等待",
            size_hint_y=0.9,
            height=60,
            size_hint_x=1,
            text_size=(300, None),  # Limit the text width to 300px, and let height adjust automatically
            halign='left',
            valign='top',
        )

        # 添加输入框和按钮到水平布局
        input_layout.add_widget(self.input_field)
        input_layout.add_widget(add_button)

        left_layout.add_widget(use_tips)

        # 在scrape_button 上方添加打开结果文件夹按钮
        left_layout.add_widget(self.radio_layout)

        left_layout.add_widget(self.open_button)
        # 在输入框上方添加爬取按钮
        left_layout.add_widget(self.scrape_button)
        left_layout.add_widget(self.merge_button)
        left_layout.add_widget(input_layout)

        # 右侧布局（文本列表）
        right_layout = ScrollView(size_hint=(0.45, 1))
        self.text_list_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.text_list_layout.bind(minimum_height=self.text_list_layout.setter('height'))

        right_layout.add_widget(self.text_list_layout)

        # 将左右布局添加到根布局
        self.root.add_widget(left_layout)
        self.root.add_widget(right_layout)

        # 加载已保存的列表
        self.load_data()

        return self.root

    def open_folder(self, instance):
        path = os.path.join('result')
        if platform.system() == 'Darwin':  # macOS
            os.system(f'open "{path}"')
        elif platform.system() == 'Windows':  # Windows
            os.system(f'start {path}')
        else:
            raise NotImplementedError("Unsupported operating system")

    def start_scraping(self, instance):
        self.show_loading_popup()
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                items = json.load(f)
            output_format = 'txt' if self.txt_radio.state == 'down' else 'excel'
            startGetData(items, self.onFinish, self.onError, output_format, int(self.crawl_input.text))

    def start_merge(self, instance):
        base_path = os.path.join('result')

        if not os.path.exists(base_path):
            Clock.schedule_once(lambda dt: self.show_tips_popup("没有 result 文件夹", True), 0)
            return

        # 遍历所有子文件夹（日期文件夹）
        sub_dirs = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
        if not sub_dirs:
            Clock.schedule_once(lambda dt: self.show_tips_popup("没有任何子文件夹", True), 0)
            return

        merged_count = 0

        for folder in sub_dirs:
            folder_path = os.path.join(base_path, folder)
            txt_files = [f for f in os.listdir(folder_path) if f.endswith('.txt') and not f.startswith('合并结果')]

            if not txt_files:
                continue  # 如果该子文件夹没有 txt 文件，跳过

            merged_content = ""
            for file_name in txt_files:
                file_path = os.path.join(folder_path, file_name)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        merged_content += f"===== {file_name} =====\n{content}\n\n"
                except Exception as e:
                    print(f"读取文件失败: {file_path} - {e}")

            # 保存合并结果
            merged_path = os.path.join(folder_path, f"merge({folder}).txt")
            try:
                with open(merged_path, "w", encoding="utf-8") as f:
                    f.write(merged_content)
                merged_count += 1
            except Exception as e:
                print(f"保存合并文件失败: {merged_path} - {e}")

        # 弹窗提示最终结果
        if merged_count > 0:
            Clock.schedule_once(lambda dt: self.show_tips_popup(f"已合并 {merged_count} 个文件夹", False), 0)
        else:
            Clock.schedule_once(lambda dt: self.show_tips_popup("没有需要合并的文件", True), 0)

    def onFinish(self):
        Clock.schedule_once(lambda dt: self.close_loading_popup(), 0)
        Clock.schedule_once(lambda dt: self.show_tips_popup("爬取完成", False), 0)
        Clock.schedule_once(lambda dt: self.text_list_layout.clear_widgets(), 0)
        Clock.schedule_once(lambda dt: self.load_data(), 0)

    def onError(self, text, auto_dismiss=False):
        Clock.schedule_once(lambda dt: self.show_tips_popup(text, auto_dismiss), 0)

    def show_loading_popup(self):
        # 创建弹出框
        self.popup = Popup(title='爬取中，请耐心等待...', size_hint=(None, None), size=(400, 200))
        # 不能点击外部关闭
        self.popup.auto_dismiss = False
        self.popup.open()

    def show_tips_popup(self, text, auto_dismiss):
        # 创建弹出框
        self.tips_popup = Popup(title=text, size_hint=(None, None), size=(400, 200))
        # 不显示 进度条
        self.tips_popup.separator_color = [0, 0, 0, 0]
        self.tips_popup.open()
        #     延迟三秒后关闭弹出框
        if auto_dismiss:
            Clock.schedule_once(lambda dt: self.close_tips_popup(), 3)

    def close_loading_popup(self):
        # 关闭弹出框
        self.popup.dismiss()

    def close_tips_popup(self):
        # 关闭弹出框
        self.tips_popup.dismiss()

    def add_text(self, instance):
        # 获取输入框中的文本
        text = self.input_field.text.strip()
        if len(text) == 0:
            return
        if text:
            # 创建一个水平布局来放置 Label 和 删除按钮
            item_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, spacing=10)

            # 创建一个标签并添加到布局
            label = Label(text=text, size_hint_y=None, height=60)

            # 创建删除按钮并绑定事件
            delete_button = Button(
                text='删除',
                size_hint_x=0.2,
                width=60,
                size_hint_y=None,
                height=55,
                padding=[10, 10]  # 设置按钮的内边距，使其看起来更大
            )

            # 使用 partial 来绑定 delete_text 方法并传递 item_layout
            delete_button.bind(on_press=partial(self.delete_text, item_layout))

            # 将标签和删除按钮添加到布局
            item_layout.add_widget(label)
            item_layout.add_widget(delete_button)

            # 将整个布局添加到文本列表的顶部
            self.text_list_layout.add_widget(item_layout, )

            # 手动更新布局
            self.text_list_layout.canvas.ask_update()
            # 保存当前列表项到文件
            self.save_data(label.text)

            # 清除列表
            self.text_list_layout.clear_widgets()
            self.load_data()

            # 清空输入框
            self.input_field.text = ''

    def delete_text(self, item_layout, instance):
        self.text_list_layout.remove_widget(item_layout)
        self.remove_data(item_layout.children[1].text)

    def remove_data(self, text):
        textItems = []
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                items = json.load(f)

            for item in items:
                if item != text:
                    textItems.append(item)

        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(textItems, f, ensure_ascii=False, indent=4)

    def save_data(self, text):
        # 获取所有文本项
        compairList = []
        textItems = []
        #
        # textItems.append(text)
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                items = json.load(f)

            # 将保存的列表项添加到界面
            for item in items:
                textItems.append(item)
                compairList.append(item.split(":")[0])

        # 判断是否已经存在
        if text not in compairList:
            # 添加到最前面
            textItems.insert(0, text)
        else:
            Clock.schedule_once(lambda dt: self.show_tips_popup("该代码已经存在", True), 0)
            return

        # 保存为 JSON 格式
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(textItems, f, ensure_ascii=False, indent=4)

    def load_data(self):
        # 如果文件存在，加载保存的列表项
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                items = json.load(f)

            # 将保存的列表项添加到界面
            for item in items:
                item_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, spacing=10)

                label = Label(text=item, size_hint_y=None, height=60)

                delete_button = Button(
                    text='删除',
                    size_hint_x=0.2,
                    width=60,
                    size_hint_y=None,
                    height=55,
                    padding=[10, 10]
                )

                delete_button.bind(on_press=partial(self.delete_text, item_layout))

                item_layout.add_widget(label)
                item_layout.add_widget(delete_button)

                # 将保存的数据插入到顶部
                self.text_list_layout.add_widget(item_layout)

import akshare as ak
if __name__ == '__main__':
    # 创建result 文件夹
    if not os.path.exists("result"):
        os.makedirs("result")
    # 删除 temp 文件夹 如果存在
    if os.path.exists("temp"):
        shutil.rmtree("temp")
    MyApp().run()