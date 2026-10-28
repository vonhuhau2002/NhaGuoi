"""Reusable Tk chat panel: one worker, queued updates and explicit lifecycle."""

import queue
import threading
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from cotu_app.core.branding import APP_NAME, CHAT_NAME
from cotu_app.ui import theme
from .presentation import visitor_answer


class ChatPanel(ttk.Frame):
    def __init__(self, parent, service, offline=False, *, before_send=None,
                 read_answer=None, stop_audio=None, keyboard_factory=None):
        super().__init__(parent, padding=4, style='Story.TFrame')
        self.root, self.service, self.offline = self.winfo_toplevel(), service, offline
        theme.configure_styles(self.root)
        self.before_send, self.read_answer = before_send, read_answer
        self.stop_audio = stop_audio
        self.events, self.history = queue.Queue(), []
        self.generation, self.busy, self.closed = 0, False, False
        self.cancel = threading.Event()
        self.character_id, self.last_answer, self.keyboard = 'elder', None, None
        self.heading = ttk.Label(self, text=CHAT_NAME,
                                 font=(theme.FONT, 15, 'bold'))
        self.heading.pack(anchor='w')
        label = ('Tư liệu thử nghiệm, chưa duyệt' if service.retriever.mode == 'research'
                 else 'Tư liệu đã duyệt')
        self.notice = ttk.Label(self, text='Ưu tiên đáp án có sẵn. ' + label +
                                ' · Câu chưa có sẽ gửi cùng tư liệu tới Google.',
                                font=('DejaVu Sans', 9), wraplength=730)
        self.notice.pack(anchor='w', pady=(2, 4))
        self.tools = ttk.Frame(self)
        self.tools.pack(fill='x', pady=(0, 4))
        self.stop_button = ttk.Button(self.tools, text='Dừng trả lời', command=self.stop, state='disabled')
        self.stop_button.pack(side='left')
        ttk.Button(self.tools, text='Hỏi mới', command=self.reset).pack(side='left', padx=8)
        self.read_button = None
        if read_answer is not None:
            self.read_button = ttk.Button(self.tools, text='Nghe trả lời', command=self.read_last, state='disabled')
            self.read_button.pack(side='left')
        if stop_audio is not None:
            ttk.Button(self.tools, text='Dừng đọc', command=stop_audio).pack(side='left', padx=8)
        ttk.Button(self.tools, text='Gợi ý', command=self.toggle_examples).pack(side='right')
        self.status = tk.StringVar(value='Sẵn sàng. Gõ câu hỏi hoặc chạm câu mẫu bên dưới.')
        self.status_label = ttk.Label(self, textvariable=self.status, wraplength=730,
                                      font=('DejaVu Sans', 9))
        self.status_label.pack(fill='x', pady=(0, 4))
        self.entry_row = ttk.Frame(self)
        self.entry_row.pack(fill='x', pady=(0, 5))
        ttk.Label(self.entry_row, text='Câu hỏi', font=(theme.FONT, 10, 'bold')).pack(side='left', padx=(0, 8))
        self.entry = ttk.Entry(self.entry_row, font=('DejaVu Sans', 15), width=1,
                               exportselection=False)
        self.entry.pack(side='left', fill='x', expand=True)
        self.entry.bind('<Return>', self.send)
        if keyboard_factory is not None:
            ttk.Button(self.entry_row, text='Bàn phím', command=self.toggle_keyboard).pack(side='left', padx=5)
        self.send_button = ttk.Button(self.entry_row, text='Gửi', command=self.send, style='Primary.TButton')
        self.send_button.pack(side='left', padx=(5, 0))
        self.examples = ttk.Frame(self)
        for title, question in (('Nhà gươl', 'Nhà Gươl dùng để làm gì?'),
                                ('Chim Tring', 'Chim Tring trên nóc nhà Gươl tượng trưng cho điều gì?'),
                                ('Nói lý, hát lý', 'Nói lý hát lý là gì?')):
            ttk.Button(self.examples, text=title, command=lambda q=question: self.example(q)).pack(side='left', padx=(0, 5))
        self.body = ttk.Frame(self)
        self.body.pack(fill='both', expand=True)
        self.transcript = ScrolledText(self.body, wrap='word', font=(theme.FONT, 12),
                                       bg=theme.SURFACE, fg=theme.INK, relief='flat',
                                       padx=12, pady=10, spacing3=8, highlightthickness=1,
                                       highlightbackground=theme.LINE, width=1, height=1, state='disabled')
        self.transcript.pack(fill='both', expand=True)
        if keyboard_factory is not None:
            self.keyboard = keyboard_factory(
                self, self.entry, self.send, before=self.body,
                hide_when_open=(self.heading, self.notice, self.tools, self.status_label, self.examples))
            self.entry.bind('<ButtonRelease-1>', self.open_keyboard, add='+')
        self.bind('<Configure>', self.resize, add='+')
        self.poll_id = self.after(40, self.poll)

    def resize(self, event):
        width = max(200, event.width - 20)
        self.status_label.configure(wraplength=width)
        self.notice.configure(wraplength=width)

    def open_keyboard(self, event=None):
        if self.keyboard is not None and self.root.attributes('-fullscreen'):
            self.keyboard.show()

    def toggle_keyboard(self):
        if self.keyboard is not None:
            self.keyboard.toggle()

    def toggle_examples(self):
        self.hide_keyboard()
        if self.examples.winfo_manager():
            self.examples.pack_forget()
        else:
            self.examples.pack(fill='x', pady=(0, 8), before=self.body)

    def hide_keyboard(self):
        if self.keyboard is not None:
            self.keyboard.hide()

    def set_character(self, character_id, name=None, *, reset=False):
        if reset or character_id != self.character_id:
            self.reset()
        self.character_id = character_id
        self.heading.configure(text=f'{APP_NAME} · Trò chuyện với {name or character_id}')

    def append(self, text):
        self.transcript.configure(state='normal')
        self.transcript.insert('end', text)
        self.transcript.see('end')
        self.transcript.configure(state='disabled')

    def example(self, question):
        return self.submit_question(question)

    def submit_question(self, question):
        if self.closed:
            return False
        if self.busy:
            self.status.set('Đang trả lời câu trước. Bấm Dừng hoặc chờ hoàn tất.')
            return False
        self.entry.delete(0, 'end')
        self.entry.insert(0, question)
        return self.send()

    def send(self, event=None):
        question = self.entry.get().strip()
        if self.closed or self.busy or not question:
            return False
        if len(question) > 1200:
            self.status.set('Câu hỏi tối đa 1.200 ký tự.')
            return False
        if self.before_send is not None:
            notice = self.before_send()
            if notice:
                self.status.set(notice)
                return False
        self.hide_keyboard()
        self.examples.pack_forget()
        self.busy, self.cancel, self.last_answer = True, threading.Event(), None
        self.send_button.configure(state='disabled')
        self.stop_button.configure(state='normal')
        if self.read_button is not None:
            self.read_button.configure(state='disabled')
        self.entry.delete(0, 'end')
        if len(self.transcript.get('1.0', 'end')) > 80000:
            self.transcript.configure(state='normal')
            self.transcript.delete('1.0', 'end-30000c')
            self.transcript.configure(state='disabled')
        self.append(f'\nEm: {question}\n\n{APP_NAME}: ')
        self.answer_start = self.transcript.index('end-1c')
        self.status.set('Nhà Gươi đang tìm câu trả lời…')
        generation, history, cancel = self.generation, self.history[:], self.cancel
        character_id = self.character_id
        service, events, offline = self.service, self.events, self.offline

        def work():
            try:
                result = service.ask(
                    question, history, character_id=character_id, offline=offline,
                    cancel=cancel, on_delta=lambda text: None)
                events.put((generation, 'done', (question, result)))
            except Exception:
                events.put((generation, 'error', 'Không xử lý được câu hỏi; kiểm tra cấu hình hoặc dựng lại index.'))

        threading.Thread(target=work, daemon=True, name='cotu-chat').start()
        return True

    def replace_answer(self, text):
        self.transcript.configure(state='normal')
        self.transcript.delete(self.answer_start, 'end')
        self.transcript.configure(state='disabled')
        self.append(text + '\n')

    def poll(self):
        if self.closed:
            return
        for _ in range(100):
            try:
                generation, kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if kind in {'done', 'error'}:
                self.busy = False
                self.send_button.configure(state='normal')
                self.stop_button.configure(state='disabled')
            if generation != self.generation:
                if kind in {'done', 'error'}:
                    self.status.set('Sẵn sàng. Đã bỏ phản hồi của phiên trước.')
                continue
            if kind == 'delta':
                # Show one completed answer, rather than an unvalidated draft
                # that may still contain source IDs or intermediate variants.
                continue
            elif self.cancel.is_set():
                self.replace_answer('Đã dừng câu hỏi.')
                self.status.set('Đã dừng. Bạn có thể gửi câu hỏi mới.')
            elif kind == 'done':
                question, result = payload
                answer = visitor_answer(result)
                self.replace_answer(answer)
                if result.status == 'answered':
                    self.last_answer = result
                    self.history.extend([{'role': 'user', 'content': question},
                                         {'role': 'assistant', 'content': answer}])
                    self.history = self.history[-4:]
                    if self.read_button is not None:
                        self.read_button.configure(state='normal')
                label = {'answered': 'Đã trả lời', 'extractive_fallback': 'Chưa thể tổng hợp câu trả lời',
                         'insufficient_evidence': 'Cần thêm thông tin',
                         'clarification_needed': 'Em hỏi rõ hơn nhé'}.get(result.status, 'Đã xử lý câu hỏi')
                if result.metrics.get('route') == 'curated':
                    label = 'Đã trả lời từ bộ hỏi đáp có sẵn'
                self.status.set(label + '.')
                # Read only the completed, validated answer, never streamed drafts.
                if result.status == 'answered':
                    self.read_last()
            else:
                self.replace_answer(payload)
                self.status.set(payload)
        self.poll_id = self.after(40, self.poll)

    def read_last(self):
        if self.last_answer is not None and self.read_answer is not None:
            self.read_answer(self.last_answer.audio_text or visitor_answer(self.last_answer),
                             self.last_answer.character_id)

    def stop(self):
        if self.busy:
            self.cancel.set()
            self.status.set('Đang dừng; chờ mạng trả dữ liệu hoặc hết timeout.')

    def reset(self):
        self.cancel.set()
        if self.stop_audio is not None:
            self.stop_audio()
        self.generation += 1
        self.history.clear()
        self.last_answer = None
        self.hide_keyboard()
        if self.read_button is not None:
            self.read_button.configure(state='disabled')
        self.entry.delete(0, 'end')
        self.transcript.configure(state='normal')
        self.transcript.delete('1.0', 'end')
        self.transcript.configure(state='disabled')
        self.status.set('Đã xóa ngữ cảnh.' + (' Đang chờ lượt cũ dừng.' if self.busy else ' Sẵn sàng.'))

    def dispose(self):
        if not self.closed:
            self.closed = True
            self.cancel.set()
            if getattr(self, 'poll_id', None) is not None:
                self.after_cancel(self.poll_id)
            self.hide_keyboard()

    def destroy(self):
        self.dispose()
        super().destroy()


class ChatWindow:
    def __init__(self, root, service, offline=False):
        self.root = root
        root.title(CHAT_NAME)
        root.geometry('800x480' if root.winfo_screenheight() <= 600 else '1000x680')
        root.minsize(800, 480)
        self.panel = ChatPanel(root, service, offline)
        self.panel.pack(fill='both', expand=True)
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.panel.entry.focus_set()

    def close(self):
        self.panel.dispose()
        self.root.destroy()


def run_desktop(service, offline=False):
    root = tk.Tk()
    ChatWindow(root, service, offline)
    root.mainloop()
