import gradio as gr

from infer import KokoroVietnameseTTS


tts: KokoroVietnameseTTS | None = None


def get_tts() -> KokoroVietnameseTTS:
    global tts
    if tts is None:
        tts = KokoroVietnameseTTS(device="cuda")
    return tts


def predict(text: str, speed: float):
    if not text.strip():
        raise gr.Error("Nhập văn bản tiếng Việt trước.")
    sample_rate, audio, phonemes = get_tts().synthesize(text, speed=speed)
    return (sample_rate, audio), phonemes


examples = [
    ["Xin chào, tôi là giọng đọc Ngọc Huyền.", 1.0],
    ["Tường nhà khách được sơn lại vào sáng nay.", 1.0],
    ["Hôm nay lớp mình học cấu trúc câu: have to.", 0.95],
    ["Cảm ơn quý khách đã tin tưởng và sử dụng dịch vụ của chúng tôi.", 1.0],
]


with gr.Blocks(title="Kokoro Vietnamese - Ngọc Huyền") as demo:
    gr.Markdown("# Kokoro Vietnamese - Ngọc Huyền")
    text = gr.Textbox(
        label="Văn bản",
        value="Xin chào, tôi là giọng đọc Ngọc Huyền.",
        lines=4,
    )
    speed = gr.Slider(0.7, 1.3, value=1.0, step=0.05, label="Tốc độ")
    button = gr.Button("Tạo giọng đọc", variant="primary")
    audio = gr.Audio(label="Audio", type="numpy")
    phonemes = gr.Textbox(label="Phoneme", lines=5)
    gr.Examples(examples=examples, inputs=[text, speed])
    button.click(predict, inputs=[text, speed], outputs=[audio, phonemes])


if __name__ == "__main__":
    demo.launch()
