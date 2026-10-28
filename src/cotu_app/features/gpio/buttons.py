"""Bốn nút kể chuyện, BCM → GND; nạp GPIO chỉ khi được bật."""

from functools import partial
import queue


# GPIO22 là RST của MFRC522 đang cài trên Pi này, không dùng cho nút.
DEFAULT_BUTTONS = {"person_1": 17, "person_2": 27, "person_3": 23, "person_4": 24}
RESERVED_PINS = {0, 1, 7, 8, 9, 10, 11, 22, 25}


def button_mapping(config, characters):
    mapping = config.get("gpio_buttons", DEFAULT_BUTTONS)
    if not isinstance(mapping, dict) or len(mapping) != 4:
        raise ValueError("gpio_buttons cần đúng 4 nhân vật, mỗi nhân vật một số GPIO BCM.")
    pins = []
    for cid, pin in mapping.items():
        if cid not in characters:
            raise ValueError(f"Nhân vật trong gpio_buttons không tồn tại: {cid}")
        if isinstance(pin, bool) or not isinstance(pin, int) or not 2 <= pin <= 27:
            raise ValueError("Chân nút phải là số GPIO BCM từ 2 đến 27, không phải số chân vật lý.")
        if pin in RESERVED_PINS:
            raise ValueError(f"GPIO{pin} được dành cho RFID/SPI; hãy chọn chân khác cho nút.")
        pins.append(pin)
    if len(set(pins)) != 4:
        raise ValueError("Bốn nút phải dùng 4 GPIO khác nhau.")
    return dict(mapping)


class StoryButtons:
    """Callback GPIO chỉ ghi hàng đợi; Tk/VLC xử lý ở luồng giao diện."""

    def __init__(self, mapping, events, *, pin_factory=None):
        from gpiozero import Button

        self.events = events
        self.buttons = []
        self.closed = False
        self.owns_factory = pin_factory is None
        if pin_factory is None:
            # lgpio hỗ trợ Pi 5; GPIO Zero tự chọn gpiochip theo hệ điều hành.
            from gpiozero.pins.lgpio import LGPIOFactory
            pin_factory = LGPIOFactory()
        self.factory = pin_factory
        try:
            for cid, pin in mapping.items():
                button = Button(pin, pull_up=True, bounce_time=0.08, pin_factory=self.factory)
                self.buttons.append(button)
                button.when_pressed = partial(self.enqueue, cid)
        except Exception:
            self.close()
            raise

    def enqueue(self, cid):
        if not self.closed:
            try:
                self.events.put_nowait(cid)
            except queue.Full:
                pass

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            for button in self.buttons:
                button.close()
        finally:
            if self.owns_factory:
                self.factory.close()


def test_buttons(mapping, characters):
    """Thử dây/nút ở Terminal, không mở RFID, video hoặc mic."""
    events = queue.Queue(maxsize=16)
    buttons = StoryButtons(mapping, events)
    try:
        print("Đang đọc 4 nút; thả nút rồi bấm từng nút. Ctrl+C để thoát.", flush=True)
        for cid, pin in mapping.items():
            print(f"GPIO{pin}: {characters[cid]['name']} ({cid})", flush=True)
        while True:
            try:
                cid = events.get(timeout=0.2)
            except queue.Empty:
                continue
            print(f"Đã bấm GPIO{mapping[cid]} → {characters[cid]['name']} ({cid})", flush=True)
    except KeyboardInterrupt:
        return 0
    finally:
        buttons.close()
