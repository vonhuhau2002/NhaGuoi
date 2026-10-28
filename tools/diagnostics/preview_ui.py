"""Capture the real UI using sample content; no API, model inference or device access.

Run with DISPLAY pointing at an existing test X server; requires scrot.
"""

from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import patch
import tkinter as tk
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))
from cotu_app.app.desktop import VideoApp, initialize_x11
from cotu_app.core.paths import BASE, CONFIG_DIR
from cotu_app.features.video.content import learn_video


def main():
    initialize_x11()
    root=tk.Tk()
    app=VideoApp(root, no_rfid=True)
    output=BASE/'reports/ui'
    output.mkdir(exist_ok=True)
    errors=[]
    def capture():
        try:
            root.geometry('800x480+0+0')
            root.update()
            subprocess.run(['scrot','--overwrite',str(output/'nha-guoi-nghe-chuyen-800x480.png')],check=True)
            knowledge=learn_video(CONFIG_DIR/'video_stories.json',app.config,'elder',lambda p: [])
            fake=SimpleNamespace(total=37,completed=37,returncode=0,message='Sẵn sàng',poll=lambda:0)
            with patch('cotu_app.app.desktop.prepare_answers',return_value=fake):
                app.handle_result(('done',app.revision.value,('learn',knowledge,None)))
            app.tabs.select(app.qa_tab)
            # Populate the answer without starting audio or calling a model.
            sample=app.visible_questions[0]
            app.question.set(min([sample['question'], *sample.get('aliases',[])], key=len))
            app.questions.selection_set(0)
            app.show('Già làng trả lời:\n\n'+sample['answer'])
            app.audio_status.set('37 câu trả lời đã có giọng đọc · Chạm một câu để nghe.')
            root.update()
            subprocess.run(['scrot','--overwrite',str(output/'nha-guoi-hoi-dap-800x480.png')],check=True)
            app.tabs.select(app.chat_tab)
            app.chat_panel.append('Nhà Gươi\nXin chào em! Cùng khám phá những câu chuyện và văn hóa Cơ Tu.\n\nEm muốn tìm hiểu điều gì?\n')
            app.chat_panel.transcript.yview_moveto(0)
            app.status.set('Cùng Nhà Gươi khám phá văn hóa Cơ Tu.')
            root.update()
            subprocess.run(['scrot','--overwrite',str(output/'nha-guoi-tro-chuyen-800x480.png')],check=True)
            app.tabs.select(app.setup_tab)
            root.update()
            subprocess.run(['scrot','--overwrite',str(output/'nha-guoi-thiet-lap-800x480.png')],check=True)
            app.tabs.select(app.qa_tab)
            app.toggle_question_keyboard()
            root.update()
            subprocess.run(['scrot','--overwrite',str(output/'nha-guoi-ban-phim-800x480.png')],check=True)
            print('Preview captures saved; navigation button heights:',[b.winfo_height() for b in app.nav_buttons.values()])
        except BaseException as error:
            errors.append(error)
        finally:
            app.close()
    root.after(500,capture)
    root.mainloop()
    if errors: raise errors[0]

if __name__=='__main__':
    main()
