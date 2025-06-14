import streamlit as st
import os
import json
from nsfw import NsfwNovelWriter
from domains import NSFWNovel

if not os.environ["OPENAI_API_KEY"]:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

st.title("NSFW 小说生成器")
st.markdown("""
请输入你的 NSFW 小说需求，点击生成后将展示小说的标题和概要。
""")

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

# 初始化/恢复 writer
if 'writer' not in st.session_state:
    st.session_state['writer'] = NsfwNovelWriter()
writer: NsfwNovelWriter = st.session_state['writer']
state = writer.state

# 需求输入
requirements = st.text_area(
    "输入你的 NSFW 小说需求：",
    height=150,
    value=state.requirements or "",
    key="requirements_input"
)
writer.state.requirements = requirements

# 生成按钮
if st.button("生成小说概要"):
    if requirements.strip():
        writer.design_overall(requirements)
        st.success("生成成功！")
    else:
        st.warning("请输入需求后再生成。")

# 重置按钮
if st.button("重置"):
    st.session_state['writer'] = NsfwNovelWriter()
    st.success("已重置所有内容！")
    st.rerun()

# 导出/导入state
col_export, col_import = st.columns(2)
with col_export:
    if st.button("导出为JSON"):
        st.download_button(
            label="下载JSON",
            data=json.dumps(state.model_dump(), ensure_ascii=False, indent=2),
            file_name=f"{state.title or 'NSFW小说'}.json",
            mime="application/json"
        )
with col_import:
    uploaded = st.file_uploader("从JSON导入", type=["json"])
    if uploaded is not None:
        try:
            data = json.load(uploaded)
            st.session_state['writer'] = NsfwNovelWriter()
            st.session_state['writer'].state = NSFWNovel.model_validate(data)
            st.success("导入成功！")
            st.rerun()
        except Exception as e:
            st.error(f"导入失败: {e}")

# 标题和概要编辑
if state.title is not None:
    title = st.text_input("小说标题：", value=state.title or "", key="title_input")
    overall = st.text_area("小说概要：", value=state.overview or "", key="overview_input")
    state.title = title
    state.overview = overall
    st.subheader("角色列表：")
    # 编辑和删除
    new_characters = []
    for idx, character in enumerate(state.characters):
        col1, col2, col3 = st.columns([4, 8, 2])
        with col1:
            edited_name = st.text_input(f"角色名{idx+1}", value=character.name, key=f"character_name_{idx}")
        with col2:
            edited_desc = st.text_input(f"角色描述{idx+1}", value=character.description, key=f"character_desc_{idx}")
        with col3:
            remove = st.button("删除", key=f"remove_character_{idx}")
        if not remove:
            from domains import NSFWCharacter
            new_characters.append(NSFWCharacter(name=edited_name, description=edited_desc))
    # 增加角色（放到同一行）
    coln1, coln2, coln3 = st.columns([4, 8, 2])
    with coln1:
        new_char_name = st.text_input("新增角色名", value="", key="add_character_name")
    with coln2:
        new_char_desc = st.text_input("新增角色描述", value="", key="add_character_desc")
    with coln3:
        add_char_clicked = st.button("添加角色")
    if add_char_clicked and new_char_name.strip():
        from domains import NSFWCharacter
        new_characters.append(NSFWCharacter(name=new_char_name, description=new_char_desc))
    state.characters = new_characters

    # 角色列表直接由state.characters渲染，无需单独生成按钮
    def rerender():
        st.rerun()

    # 章节生成按钮逻辑不变
    if st.button('生成章节概要'):
        if state.title and state.overview and state.language and state.characters:
            writer.design_chapters()
            for chapter in state.chapters:
                chapter.sections.clear()
            st.success('章节概要生成成功！')
            rerender()
        else:
            st.warning('请先生成小说概要后再生成章节概要。')

    # 导出markdown按钮
    if not hasattr(state, 'exported_markdown'):
        state.exported_markdown = None
    if st.button('生成导出文件'):
        writer.export_markdown()
        st.success('已生成导出文件！')
    if state.exported_markdown:
        st.download_button('下载导出Markdown', data=state.exported_markdown, file_name=f"{state.title or 'NSFW小说'}.md", mime='text/markdown')

    # 展示章节概要及其sections编辑与生成
    if state.chapters:
        st.subheader("章节概要：")
        tab_titles = [chapter.title or f"章节{idx+1}" for idx, chapter in enumerate(state.chapters)]
        tabs = st.tabs(tab_titles)
        for idx, (chapter, tab) in enumerate(zip(state.chapters, tabs)):
            with tab:
                # 章节标题和概要可编辑
                chapter_title = st.text_input(f"章节{idx+1}标题", value=chapter.title or f"章节{idx+1}", key=f"chapter_title_{idx}")
                chapter_overview = st.text_area(f"章节{idx+1}概要", value=chapter.overview or "", key=f"chapter_overview_{idx}")
                chapter.title = chapter_title
                chapter.overview = chapter_overview
                # 生成sections按钮
                if st.button(f"为本章节生成小节", key=f"gen_sections_{idx}"):
                    writer.design_sections(idx)
                    st.success(f"已为{chapter_title}生成小节！")
                # 展示并可编辑sections
                if chapter.sections:
                    st.markdown("**小节列表：**")
                    for sidx, section in enumerate(chapter.sections):
                        sec_title = st.text_input(f"章节{idx+1}小节{sidx+1}标题", value=section.title or "", key=f"section_title_{idx}_{sidx}")
                        sec_overview = st.text_area(f"章节{idx+1}小节{sidx+1}概要", value=section.overview or "", key=f"section_overview_{idx}_{sidx}")
                        # 生成正文按钮
                        if st.button(f"生成章节{idx+1}小节{sidx+1}正文", key=f"gen_content_{idx}_{sidx}"):
                            writer.write_section_content(idx, sidx)
                            st.success(f"已为章节{idx+1}小节{sidx+1}生成正文！")
                        # 正文内容自适应高度
                        sec_content = st.text_area(
                            f"章节{idx+1}小节{sidx+1}内容",
                            value=section.content or "",
                            key=f"section_content_{idx}_{sidx}",
                            height=400  # 设置较大的默认高度
                        )
                        # 写回state
                        section.title = sec_title
                        section.overview = sec_overview
                        section.content = sec_content

