import streamlit as st
import os
from nsfw import NsfwNovelWriter

if st.secrets.get("OPENAI_API_KEY"):
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

# 标题和概要编辑
if state.title is not None:
    title = st.text_input("小说标题：", value=state.title or "", key="title_input")
    overall = st.text_area("小说概要：", value=state.overview or "", key="overview_input")
    state.title = title
    state.overview = overall
    
    if st.button("生成角色列表"):
        if state.title and state.overview:
            writer.design_characters()
            st.success("角色列表生成成功！")
        else:
            st.warning("请先生成小说概要（标题和概要）后再生成角色列表。")

    # 角色编辑、增加、删除
    if state.title is not None:
        st.subheader("角色列表：")
        # 编辑和删除
        new_characters = []
        for idx, character in enumerate(state.characters):
            col1, col2 = st.columns([8, 1])
            with col1:
                edited = st.text_input(f"角色{idx+1}", value=character, key=f"character_{idx}")
            with col2:
                remove = st.button("删除", key=f"remove_character_{idx}")
            if not remove:
                new_characters.append(edited)
        # 增加角色
        new_char = st.text_input("新增角色", value="", key="add_character")
        add_char_clicked = st.button("添加角色")
        # 立即响应删除和添加
        if add_char_clicked and new_char.strip():
            new_characters.append(new_char.strip())
        if new_characters != state.characters:
            state.characters = new_characters
            st.success("角色列表已更新！")

    if st.button("生成章节概要"):
        if state.title and state.overview and state.language and state.characters:
            writer.design_chapters()
            st.success("章节概要生成成功！")
        else:
            st.warning("请先生成小说概要、角色列表后再生成章节概要。")

    # 展示章节概要及其sections编辑与生成
    if state.chapters:
        st.subheader("章节概要：")
        tab_titles = [chapter.title or f"章节{idx+1}" for idx, chapter in enumerate(state.chapters)]
        tabs = st.tabs(tab_titles)
        for idx, (chapter, tab) in enumerate(zip(state.chapters, tabs)):
            with tab:
                title = chapter.title or f"章节{idx+1}"
                overview = chapter.overview or ""
                st.markdown(f"**{title}**\n\n{overview}")

                # 生成sections按钮
                if st.button(f"为本章节生成小节", key=f"gen_sections_{idx}"):
                    writer.design_sections(idx)
                    st.success(f"已为{title}生成小节！")

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
                            height=None  # 自适应高度
                        )
                        # 写回state
                        section.title = sec_title
                        section.overview = sec_overview
                        section.content = sec_content

