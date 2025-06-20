import streamlit as st
import os
import json
from glom import glom, assign
from nsfw import NsfwNovelWriter, MODEL_OPTIONS
from domains import *
from persist import get_history_page, save, delete_novel

if not os.environ["OPENAI_API_KEY"]:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

st.title("NSFW 小说生成器")

# 注入自适应高度的CSS
st.markdown("""
    <style>
    textarea[data-baseweb="textarea"] {
        min-height: 60px !important;
        max-height: 600px !important;
        height: auto !important;
        overflow-y: auto !important;
        resize: vertical !important;
    }
    </style>
""", unsafe_allow_html=True)

# 公用的章节一键生成函数
def oneclick_generate_chapter(writer: NsfwNovelWriter, idx, section_count=None, progress_placeholder=None, chapters_progress=""):
    progress_placeholder.info(f"正在生成第{idx+1}章{chapters_progress}各节概要...")
    writer.design_sections(idx, section_count=section_count)
    total = len(writer.state.chapters[idx].sections)
    for sidx in range(total):
        if progress_placeholder:
            progress_placeholder.info(f"正在生成第{idx+1}章{chapters_progress}第{sidx+1}节正文（{sidx+1}/{total}）...")
        for _ in writer.write_content(idx, sidx):
            pass

# 初始化/恢复 writer
if 'writer' not in st.session_state:
    st.session_state['writer'] = NsfwNovelWriter()
writer: NsfwNovelWriter = st.session_state['writer']
state = writer.state

def bind_state(path: str):
    key = f'state#{path}'
    return {
        'value': glom(state, path, default=None),
        'key': key,
        'on_change': lambda: assign(state, path, st.session_state[key]),
    }

def rerun(partial: bool = False):
    if state.plot_requirements or state.title or state.overview or state.language or state.characters:
        save(state)
    st.rerun(scope="app" if not partial else "fragment")

# 导出/导入/导出Markdown同一行
model_choice = st.selectbox("选择模型", options=MODEL_OPTIONS, index=0, key="model_select")
if getattr(writer.model, 'model', None) != model_choice:
    writer.set_model(model_choice)
    
col_export, col_import, col_md, col_history = st.columns(4)
with col_export:
    if st.button("导出为JSON"):
        st.download_button(
            label="下载JSON",
            data=state.model_dump_json(),
            file_name=f"{state.title or 'NSFW小说'}.json",
            mime="application/json"
        )
with col_import:
    uploaded = st.file_uploader("从JSON导入", type=["json"], key="import_json_uploader")
    if uploaded is not None:
        try:
            data = json.load(uploaded)
            st.session_state['import_json_data'] = data
            st.success("文件已选择，请点击下方按钮应用。")
        except Exception as e:
            st.error(f"文件解析失败: {e}")
    if 'import_json_data' in st.session_state:
        if st.button("应用导入内容"):
            try:
                st.session_state['writer'] = NsfwNovelWriter()
                st.session_state['writer'].state = NSFWNovel.model_validate(st.session_state['import_json_data'])
                st.success("导入成功！")
                st.session_state.pop("import_json_uploader", None)
                st.session_state.pop("import_json_data", None)
                rerun()
            except Exception as e:
                st.error(f"导入失败: {e}")
with col_md:
    if st.button('生成Markdown'):
        writer.export_markdown()
        st.success('已生成导出文件！')
    if state.exported_markdown:
        @st.dialog("预览Markdown", width="large")
        def preview_markdown_dialog():
            st.markdown(state.exported_markdown)
        st.button("预览Markdown", on_click=preview_markdown_dialog)
        st.download_button('下载Markdown', data=state.exported_markdown, file_name=f"{state.title or 'NSFW小说'}.md", mime='text/markdown')

@st.dialog("历史记录", width="large")
def history_dialog():
    PAGE_SIZE = 10
    page = st.session_state.get('history_page', 1)
    total_count, rows = get_history_page(page, PAGE_SIZE)
    for row in rows:
        rid, state_json, create_time, update_time, version = row
        try:
            state_obj = json.loads(state_json)
        except Exception:
            state_obj = {}
        col1, col2, col3, col4, col5, col6 = st.columns([3,3,3,2,2,2])
        with col1:
            st.markdown(f"**标题：** {state_obj.get('title', '')}")
        with col2:
            st.markdown(f"**语言：** {state_obj.get('language', '')}")
        with col3:
            st.markdown(f"**更新时间：** {update_time[:19]}")
        with col4:
            st.markdown(f"**版本：** {version}")
        with col5:
            if st.button("导入", key=f"import_history_{rid}"):
                st.session_state['writer'] = NsfwNovelWriter()
                st.session_state['writer'].state = NSFWNovel.model_validate(state_obj)
                st.success("历史记录已导入！")
                rerun()
        with col6:
            if st.button("删除", key=f"delete_history_{rid}"):
                st.session_state['delete_confirm_id'] = rid
                st.session_state['show_delete_confirm'] = True
                rerun()
    # 分页控件
    total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE
    col_prev, col_page, col_next = st.columns([2,2,2])
    with col_prev:
        if page > 1 and st.button("上一页", key="history_prev"):
            st.session_state['history_page'] = page - 1
            rerun()
    with col_page:
        st.markdown(f"第 {page} / {total_pages} 页")
    with col_next:
        if page < total_pages and st.button("下一页", key="history_next"):
            st.session_state['history_page'] = page + 1
            rerun()
with col_history:
    if st.button("历史记录"):
        history_dialog()

if st.session_state.get('show_delete_confirm', False):
    @st.dialog("确认删除", width="small")
    def delete_confirm_dialog():
        st.warning("确定要删除该历史记录吗？此操作不可恢复！")
        col_ok, col_cancel = st.columns(2)
        with col_ok:
            if st.button("确认删除"):
                delete_novel(st.session_state['delete_confirm_id'])
                st.session_state['show_delete_confirm'] = False
                st.session_state['delete_confirm_id'] = None
                st.rerun()
        with col_cancel:
            if st.button("取消"):
                st.session_state['show_delete_confirm'] = False
                st.session_state['delete_confirm_id'] = None
    delete_confirm_dialog()

# 需求输入
st.text_area(
    "你想要怎样的情节（情节要求）",
    height=80,
    **bind_state("plot_requirements")
)

st.text_area(
    "你对小说创作有哪些要求（写作要求）",
    height=80,
    **bind_state("writing_requirements")
)

# 生成/重置按钮同一行
col_gen, col_reset, col_edit_content = st.columns([1,1,2])
with col_gen:
    if st.button("生成小说概要"):
        if state.plot_requirements:
            writer.design_overall(state.plot_requirements, state.writing_requirements)
            st.success("生成成功！")
        else:
            st.warning("请输入情节要求后再生成。")
with col_reset:
    if st.button("重置"):
        st.session_state['writer'] = NsfwNovelWriter()
        st.success("已重置所有内容！")
        rerun()
with col_edit_content:
    edit_content = st.checkbox("编辑正文", value=False, key="edit_content_checkbox")

# 标题和概要编辑
if state.title is not None:
    st.text_input("小说标题：", **bind_state("title"))
    st.text_area("小说概要：", **bind_state("overview"), height=
                 250)
    st.subheader("角色列表：")
    # 角色展示、编辑、删除
    remove_idx = None
    for idx, character in enumerate(state.characters):
        col1, col2, col3 = st.columns([3, 8, 2])
        with col1:
            st.text_input(f"角色名{idx+1}", **bind_state(f"characters.{idx}.name"))
        with col2:
            st.text_area(f"角色描述{idx+1}", **bind_state(f"characters.{idx}.description"))
        with col3:
            if st.button("删除", key=f"remove_character_{idx}"):
                remove_idx = idx
    if remove_idx is not None:
        del state.characters[remove_idx]
        rerun()
    # 增加角色（同一行，on_click清空输入）
    def _add_character_inputs():
        from domains import NSFWCharacter
        if st.session_state["add_character_name"].strip():
            state.characters.append(NSFWCharacter(name=st.session_state["add_character_name"], description=st.session_state["add_character_desc"]))
            st.session_state["add_character_name"] = ""
            st.session_state["add_character_desc"] = ""
    coln1, coln2, coln3 = st.columns([3, 8, 2])
    with coln1:
        st.text_input("新增角色名", value="", key="add_character_name")
    with coln2:
        st.text_area("新增角色描述", value="", key="add_character_desc")
    with coln3:
        st.button("添加角色", key="add_character_btn", on_click=_add_character_inputs)

    # 章节编辑区域
@st.fragment
def single_chapter_area(idx: int, chapter: NSFWChapter):
    col_ch_add, col_ch_del = st.columns([2,2])
    with col_ch_add:
        if st.button(f"添加下一章", key=f"add_chapter_after_{idx}"):
            from domains import NSFWChapter
            writer.state.chapters.insert(idx+1, NSFWChapter(title="", overview="", sections=[]))
            rerun()
    with col_ch_del:
        if st.button(f"删除本章", key=f"delete_chapter_{idx}"):
            del writer.state.chapters[idx]
            rerun()
    st.text_input(f"第{idx+1}章标题", **bind_state(f"chapters.{idx}.title"))
    st.text_area(f"第{idx+1}章概要", **bind_state(f"chapters.{idx}.overview"), height=200)
    col_sec1, col_sec2, col_sec3 = st.columns([2,2,2])
    with col_sec1:
        section_count = st.selectbox(f"节数量", options=["AUTO"] + [str(i) for i in range(1, 21)], index=0, key=f"section_count_{idx}")
    with col_sec2:
        if st.button(f"生成节概要", key=f"gen_sections_{idx}"):
            writer.design_sections(idx, section_count=None if section_count=="AUTO" else int(section_count))
            st.success(f"已为{chapter.title}生成节！")
            #rerun()
    with col_sec3:
        if st.button(f"一键生成本章", key=f"oneclick_gen_{idx}"):
            progress_placeholder = st.empty()
            oneclick_generate_chapter(writer, idx, section_count=None if section_count=="AUTO" else int(section_count), progress_placeholder=progress_placeholder)
            progress_placeholder.success(f"已为第{idx+1}章一键生成所有节概要和正文！")
            #rerun()
    if chapter.sections:
        col_fb_1, col_fb_2 = st.columns([6, 2])
        with col_fb_1:
            feedback = st.text_input('各节概要反馈', key=f'feedback_input_{idx}')
        with col_fb_2:
            if st.button('提交反馈', key=f'feedback_button_{idx}'):
                writer.design_sections(idx, user_feedback=feedback)
                #rerun()
    for sidx, section in enumerate(chapter.sections):
        col_secA, col_secB = st.columns([4, 8])
        with col_secA:
            st.text_input(f"第{idx+1}章第{sidx+1}节标题", **bind_state(f"chapters.{idx}.sections.{sidx}.title"))
        with col_secB:
            st.text_area(f"第{idx+1}章第{sidx+1}节概要", **bind_state(f"chapters.{idx}.sections.{sidx}.overview"), height=150)
        to_generate = False
        user_feedback = None
        if st.button(f"生成第{idx+1}章第{sidx+1}节正文", key=f"gen_content_{idx}_{sidx}"):
            to_generate = True
    
        if section.content:
            col_fb_1, col_fb_2 = st.columns([6, 2])
            with col_fb_1:
                feedback = st.text_input(f'第{idx+1}章第{sidx+1}节正文反馈', key=f'feedback_input_{idx}_{sidx}')
            with col_fb_2:
                if st.button('提交反馈', key=f'feedback_button_{idx}_{sidx}'):
                    to_generate = True
                    user_feedback = feedback
                    
        if to_generate:
            with st.empty():
                for partial in writer.write_content(idx, sidx, user_feedback=user_feedback):
                    st.write(partial)
                st.write('')
            
        if section.content:
            if st.session_state.get("edit_content_checkbox", True):
                st.text_area(
                    f"第{idx+1}章第{sidx+1}节内容",
                    **bind_state(f"chapters.{idx}.sections.{sidx}.content"),
                    height=500
                )
            else:
                st.write(section.content)
        col_sec_add, col_sec_del = st.columns([2,2])
        with col_sec_add:
            if st.button(f"添加下一节", key=f"add_section_after_{idx}_{sidx}"):
                chapter.sections.insert(sidx+1, NSFWSection(title="", overview="", content=None))
                rerun(partial=True)
        with col_sec_del:
            if st.button(f"删除本节", key=f"delete_section_{idx}_{sidx}"):
                del chapter.sections[sidx]
                rerun(partial=True)
        if section.after_state:
            with st.expander("本节后角色状态", expanded=False):
                for cname in section.after_state:
                    st.markdown(f"**{cname}**")
                    st.text_area(f"衣着状态", **bind_state(f"chapters.{idx}.sections.{sidx}.after_state.{cname}.clothing"))
                    st.text_area(f"心理状态", **bind_state(f"chapters.{idx}.sections.{sidx}.after_state.{cname}.psychological"))
                    st.text_area(f"生理状态", **bind_state(f"chapters.{idx}.sections.{sidx}.after_state.{cname}.physiological"))

def chapter_area():
    col_ch1, col_ch2, col_ch3 = st.columns([2,2,2])
    with col_ch1:
        chapter_count = st.selectbox("章数量", options=["AUTO"] + [str(i) for i in range(1, 21)], index=0, key="chapter_count")
    with col_ch2:
        if st.button('生成章概要'):
            if state.title and state.overview and state.language and state.characters:
                writer.design_chapters(chapter_count=None if chapter_count=="AUTO" else int(chapter_count))
                for chapter in state.chapters:
                    chapter.sections.clear()
                st.success('章概要生成成功！')
                rerun()
            else:
                st.warning('请先生成小说概要后再生成章概要。')
    with col_ch3:
        if st.button('一键生成全文', key='oneclick_gen_all'):
            progress_placeholder = st.empty()
            progress_placeholder.info("正在生成所有章概要...")
            writer.design_chapters(chapter_count=None if chapter_count=="AUTO" else int(chapter_count))
            for idx, chapter in enumerate(state.chapters):
                oneclick_generate_chapter(writer, idx, progress_placeholder=progress_placeholder, chapters_progress=f"（{idx + 1}/{len(state.chapters)}）")
            progress_placeholder.success("已为所有章节一键生成概要和正文！")
            rerun()
    if state.chapters:
        # 章概要反馈输入框和按钮，放在所有tab上方
        col_ch_fb_1, col_ch_fb_2 = st.columns([6, 2])
        with col_ch_fb_1:
            chapter_feedback = st.text_input('各章概要反馈', key='chapter_feedback_input')
        with col_ch_fb_2:
            if st.button('提交章概要反馈', key='chapter_feedback_button'):
                writer.design_chapters(user_feedback=chapter_feedback)
                rerun()
        tab_titles = [chapter.title or f"第{idx+1}章" for idx, chapter in enumerate(state.chapters)]
        tabs = st.tabs(tab_titles)
        for idx, (chapter, tab) in enumerate(zip(state.chapters, tabs)):
            with tab:
                single_chapter_area(idx, chapter)
                
if state.overview:
    chapter_area()



