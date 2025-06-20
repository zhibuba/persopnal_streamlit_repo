import streamlit as st
import os
from translator import LLMTranslator, MODEL_OPTIONS, LANG_OPTIONS
from pixiv import get_pixiv_novel

st.set_page_config(page_title="LLM小说翻译器", layout="wide")
st.title("LLM小说翻译器")


# 下拉选择框同一行
col1, col2 = st.columns(2)
with col1:
    model_name = st.selectbox("选择模型", MODEL_OPTIONS)
with col2:
    tgt_lang = st.selectbox("选择目标语言", LANG_OPTIONS, index=0)

# 上传文件或输入Pixiv小说ID/URL
st.subheader("上传txt文本或输入Pixiv小说ID/URL")
file = st.file_uploader("上传.txt文件", type=["txt"])
pixiv_input = st.text_input("或输入Pixiv小说ID/URL")

text = ""
novel_title = ""
novel_desc = ""

if file is not None:
    text = file.read().decode("utf-8")
    novel_title = file.name
elif pixiv_input:
    try:
        title, desc, content = get_pixiv_novel(pixiv_input)
        text = content
        novel_title = title
        novel_desc = desc
    except Exception as e:
        st.error(f"获取Pixiv小说失败: {e}")

if text:
    st.subheader("原文内容")
    with st.expander("显示原文"):
        st.write(text)

    if st.button("翻译"):
        translator = LLMTranslator(model_name=model_name)
        output_placeholder = st.empty()
        with st.spinner("正在翻译中..."):
            translated = []
            for chunk in translator.stream_translate(text, tgt_lang):
                translated.append(chunk)
                text = "".join(translated)
                output_placeholder.markdown(f"<div style='white-space: pre-wrap'>{text}</div>", unsafe_allow_html=True)
        st.success("翻译完成！")
        
    if "translated" in st.session_state:
        st.download_button(
            label="下载翻译结果",
            data=text,
            file_name=f"{novel_title or 'translation'}.txt",
            mime="text/plain"
        )
else:
    st.info("请上传txt文件或输入Pixiv小说ID/URL。")
