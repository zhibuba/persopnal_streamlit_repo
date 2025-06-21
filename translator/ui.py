import streamlit as st
import datetime
import os
from core import LLMTranslator, MODEL_OPTIONS, LANG_OPTIONS
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

st.set_page_config(page_title="LLM翻译器", layout="wide")
st.title("LLM翻译器")


# 下拉选择框同一行
col1, col2 = st.columns(2)
with col1:
    model_name = st.selectbox("选择模型", MODEL_OPTIONS)
with col2:
    tgt_lang = st.selectbox("选择目标语言", LANG_OPTIONS, index=0)

# 上传文件或输入文本
st.subheader("上传文本文件或直接输入文本")
file = st.file_uploader("上传文本文件")
input_text = st.text_area("或在此输入要翻译的文本", height=200)

# 翻译模式选择和翻译按钮同一行
mode_col, btn_col = st.columns([3, 1])
with mode_col:
    mode = st.radio("选择翻译模式", ["流式翻译", "并行翻译"], horizontal=True)
with btn_col:
    translate_clicked = st.button("翻译", use_container_width=True)

text = ""
title = ""
desc = ""

if file is not None:
    text = file.read().decode("utf-8")
    title = file.name
elif input_text.strip():
    text = input_text.strip()
    title = f"user_input_{datetime.datetime.now()}.txt"

if text:
    st.subheader("原文内容")
    with st.expander("显示原文"):
        st.write(text)
        
    if translate_clicked:
        translator = LLMTranslator(model_name=model_name)
        progress_bar = st.progress(0, text="翻译进度：0%")
        output_placeholder = st.empty()
        with st.spinner("正在翻译中..."):
            translated = []
            def progress_callback(idx, total, data):
                percent = int(idx / total * 100)
                progress_bar.progress(percent, text=f"翻译进度：{percent}%")
                if mode == "流式翻译":
                    output_placeholder.markdown("".join(translated))
                else:
                    output_placeholder.markdown("".join(data) if isinstance(data, list) else data)
            if mode == "流式翻译":
                for chunk in translator.translate_stream(text, tgt_lang, progress_callback=progress_callback):
                    translated.append(chunk)
                st.session_state["translated"] = "".join(translated)
            else:
                ctx = get_script_run_ctx()
                def initializer(thread):
                    add_script_run_ctx(thread=thread, ctx=ctx)
                result = translator.translate_parallel(text, tgt_lang, progress_callback=progress_callback, worker_thread_initializer=initializer)
                output_placeholder.markdown(result)
                st.session_state["translated"] = result
        st.success("翻译完成！")
        st.rerun()
        
    if "translated" in st.session_state:
        st.subheader("翻译结果")
        with st.expander("显示翻译结果"):
            st.write(st.session_state["translated"])
        st.download_button(
            label="下载翻译结果",
            data=st.session_state["translated"],
            file_name=f"{title or 'translation.txt'}",
            mime="text/plain"
        )
